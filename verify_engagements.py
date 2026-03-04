from models import SessionLocal, Project

def verify_engagements():
    session = SessionLocal()
    projects = session.query(Project).all()
    
    print(f"Total engagements (projects) in DB: {len(projects)}")
    print("-" * 30)
    
    for p in projects:
        print(f"Name: {p.name}")
        print(f"  Client: {p.client_name}")
        print(f"  Day Rate: {p.day_rate}")
        print(f"  Key Contact: {p.key_contact} ({p.key_contact_email})")
        print(f"  System: {p.timesheet_system}")
        print("-" * 15)
        
    session.close()

if __name__ == "__main__":
    verify_engagements()
