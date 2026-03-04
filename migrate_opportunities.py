import csv
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Opportunity, OpportunityNote, Contact

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "sqlite:///timesheets.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def migrate_opportunities(csv_file_path):
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
            # Use semicolon as delimiter based on file inspection
            reader = csv.DictReader(csvfile, delimiter=';')
            
            for row in reader:
                # 1. Identify Client Name (Opportunity Name)
                client_name = row.get('order_name_set_by_the_manager', '').strip()
                if not client_name:
                    # Fallback to order_id if name is missing
                    client_name = f"Opportunity {row.get('order_id')}"

                # 2. Map Stage
                stage = row.get('order_status_name', 'Unknown')

                # 3. Map Financials
                try:
                    contract_value = float(row.get('order_amount_budget', 0))
                except (ValueError, TypeError):
                    contract_value = 0.0

                try:
                    day_rate = float(row.get('userfield_2 (Day Rate)', 0))
                except (ValueError, TypeError):
                    day_rate = 0.0

                # 4. Map Contract Type
                contract_type = row.get('userfield_1 (Rate Type)', '')

                # 5. Handle Created Date
                created_at_str = row.get('order_date_time', '')
                created_at = datetime.now()
                if created_at_str:
                    try:
                        created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        pass

                # 6. Find Contact
                contact = None
                person_ids_str = row.get('person_ids', '').strip()
                if person_ids_str:
                    # person_ids might contain multiple IDs, but we take the first one
                    try:
                        legacy_person_id = int(person_ids_str.split(',')[0])
                        contact = session.query(Contact).filter_by(legacy_id=legacy_person_id).first()
                    except (ValueError, IndexError):
                        pass

                # 7. Create Opportunity
                opportunity = Opportunity(
                    client_name=client_name,
                    stage=stage,
                    day_rate=day_rate,
                    contract_value=contract_value,
                    contract_type=contract_type,
                    created_at=created_at,
                    contact=contact
                )
                session.add(opportunity)
                session.flush() # Get opportunity ID for notes

                # 8. Handle Notes (from buyer comments or additional fields)
                comments = row.get('order_buyer_comments', '').strip()
                if comments:
                    note = OpportunityNote(content=comments, opportunity=opportunity)
                    session.add(note)

                # Also add tags as a note if they exist
                tags = row.get('order_tags', '').strip()
                if tags:
                    note = OpportunityNote(content=f"Tags: {tags}", opportunity=opportunity)
                    session.add(note)

            session.commit()
            logger.info("Opportunities migration completed successfully.")

    except Exception as e:
        session.rollback()
        logger.error(f"Opportunities migration failed: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    csv_path = r'C:\Users\Alex\Downloads\Export_Orders_bJHmTU.csv'
    migrate_opportunities(csv_path)
