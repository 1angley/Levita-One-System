from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Contact, Company, Tag, HistoricalEmail, Note

DATABASE_URL = "sqlite:///timesheets.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def verify_migration():
    print("--- Verification Results ---")
    
    # 1. Total Counts
    contact_count = session.query(Contact).count()
    company_count = session.query(Company).count()
    tag_count = session.query(Tag).count()
    hist_email_count = session.query(HistoricalEmail).count()
    
    print(f"Total Contacts: {contact_count}")
    print(f"Total Companies: {company_count}")
    print(f"Total Tags: {tag_count}")
    print(f"Total Historical Emails: {hist_email_count}")
    
    # 2. Check a contact with multiple emails
    # Oliver Evans (row 43) had 2 emails: oliver.evans@ctrpartners.co.uk|oliver.evans@jss-transform.com
    oliver = session.query(Contact).filter_by(name="Oliver Evans").first()
    if oliver:
        print(f"\nContact: {oliver.name}")
        print(f"  Primary Email: {oliver.current_email}")
        print(f"  Historical Emails: {[e.email for e in oliver.historical_emails]}")
    
    # 3. Check tags
    # Hannah Cottam (row 12) had tags "Recruiter|NED Recruiter"
    hannah = session.query(Contact).filter_by(name="Hannah Cottam").first()
    if hannah:
        print(f"\nContact: {hannah.name}")
        print(f"  Tags: {[t.name for t in hannah.tags]}")

    # 4. Check company
    # George Priestley (row 2) was with "Nigel Frank International Recruitment"
    george = session.query(Contact).filter_by(name="George Priestley").first()
    if george:
        print(f"\nContact: {george.name}")
        print(f"  Company: {george.company.name if george.company else 'N/A'}")

    # 5. Check Notes
    # Chloe Derrett (row 80) had email descriptions
    chloe = session.query(Contact).filter_by(name="Chloe Derrett").first()
    if chloe:
        print(f"\nContact: {chloe.name}")
        print(f"  Notes: {[n.content for n in chloe.notes]}")

if __name__ == "__main__":
    verify_migration()
    session.close()
