import csv
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Company, Contact, Tag, HistoricalEmail, Note

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "sqlite:///timesheets.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def parse_piped_field(field_str):
    """Parses a piped string like '|item1|item2|' into a list of items."""
    if not field_str or field_str == "| |":
        return []
    items = [item.strip() for item in field_str.split('|') if item.strip()]
    return items

def migrate_contacts(csv_file_path):
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # 1. Handle Company
                company_name = row.get('company_name', '').strip()
                company = None
                if company_name:
                    company = session.query(Company).filter_by(name=company_name).first()
                    if not company:
                        company = Company(name=company_name)
                        session.add(company)
                        session.flush() # Get company ID

                # 2. Handle Contact
                name = row.get('person_fullname', '').strip()
                if not name:
                    logger.warning(f"Skipping row with missing name: {row.get('person_id')}")
                    continue

                # Phones
                phones = parse_piped_field(row.get('person_phones', ''))
                primary_phone = phones[0] if phones else None
                
                # Emails
                emails = parse_piped_field(row.get('person_emails', ''))
                primary_email = emails[0] if emails else None
                historical_emails = emails[1:] if len(emails) > 1 else []
                
                # LinkedIn
                linkedin_url = None
                avatar_field = row.get('person_avatar', '')
                if "^LinkedIn" in avatar_field:
                    linkedin_url = avatar_field.split('^')[0].strip('|')
                elif avatar_field.startswith('|linkedin.com'):
                    linkedin_url = avatar_field.strip('|')
                
                # Create Contact
                contact = Contact(
                    legacy_id=int(row.get('person_id')),
                    name=name,
                    linkedin_profile_url=linkedin_url,
                    mobile_number=primary_phone,
                    current_email=primary_email,
                    role=row.get('person_function', ''),
                    comments=row.get('person_features', ''),
                    company=company
                )
                session.add(contact)
                session.flush()

                # 3. Handle Historical Emails
                for email_addr in historical_emails:
                    hist_email = HistoricalEmail(email=email_addr, contact=contact)
                    session.add(hist_email)

                # 4. Handle Tags
                tags_str = row.get('person_tags', '')
                if tags_str:
                    tag_names = [t.strip() for t in tags_str.split('|') if t.strip()]
                    for tag_name in tag_names:
                        tag = session.query(Tag).filter_by(name=tag_name).first()
                        if not tag:
                            tag = Tag(name=tag_name)
                            session.add(tag)
                            session.flush()
                        contact.tags.append(tag)

                # 5. Handle Additional Info (Descriptions)
                email_descs = parse_piped_field(row.get('person_emails_descriptions', ''))
                if email_descs:
                    note_content = f"Email Descriptions: {', '.join(email_descs)}"
                    note = Note(content=note_content, contact=contact)
                    session.add(note)
                
                phone_descs = parse_piped_field(row.get('person_phones_descriptions', ''))
                if phone_descs:
                    note_content = f"Phone Descriptions: {', '.join(phone_descs)}"
                    note = Note(content=note_content, contact=contact)
                    session.add(note)

            session.commit()
            logger.info("Migration completed successfully.")

    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    csv_path = r'C:\Users\Alex\Downloads\Export_Persons_AkUa2b.csv'
    migrate_contacts(csv_path)
