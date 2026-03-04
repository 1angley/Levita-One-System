from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Opportunity, Contact, OpportunityNote

DATABASE_URL = "sqlite:///timesheets.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def verify_opportunities():
    print("--- Opportunity Verification Results ---")
    
    # 1. Total Count
    opp_count = session.query(Opportunity).count()
    print(f"Total Opportunities: {opp_count}")
    
    # 2. Check Linked Contacts
    linked_opps = session.query(Opportunity).filter(Opportunity.contact_id.isnot(None)).count()
    print(f"Opportunities with linked contacts: {linked_opps}")
    
    # 3. Check specific examples
    # Order ID 5: SCI Tender Process, Budget 29250, Day Rate 750, Rate Type "Day Rate Outside IR35", Person ID 180
    opp5 = session.query(Opportunity).filter(Opportunity.client_name == "SCI Tender Process").first()
    if opp5:
        print(f"\nOpportunity: {opp5.client_name}")
        print(f"  Stage: {opp5.stage}")
        print(f"  Value: {opp5.contract_value}")
        print(f"  Day Rate: {opp5.day_rate}")
        print(f"  Type: {opp5.contract_type}")
        print(f"  Contact: {opp5.contact.name if opp5.contact else 'N/A'}")
        print(f"  Notes: {[n.content for n in opp5.notes]}")

    # Order ID 20: product manager, person_ids 458
    opp20 = session.query(Opportunity).filter(Opportunity.client_name == "product manager").first()
    if opp20:
        print(f"\nOpportunity: {opp20.client_name}")
        print(f"  Contact: {opp20.contact.name if opp20.contact else 'N/A'} (Legacy ID 458 - Janu Kapoor)")

if __name__ == "__main__":
    verify_opportunities()
    session.close()
