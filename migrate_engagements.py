from models import SessionLocal, Project, Contact
import datetime

def migrate_engagements():
    session = SessionLocal()

    projects_data = [
        {
            "name": "CRM Tender",
            "client_name": "SCI",
            "day_rate": 750.0,
            "hours_per_day": 8.0,
            "timesheet_system": "Other",
            "salesforce_code": None, 
            "client_ref": None,
            "agreed_days": 0,
            "days_cycle_unit": "Week",
            "uk_vat": True,
            "key_contact": "Nigel Fish",
            "key_contact_email": "nigel.fish@soci.org, invoices@soci.org",
            "address": "14/15 Belgrave Square, London, SW1X 8PB",
            "create_draft_invoice_email": True
        },
        {
            "name": "Startup Work",
            "client_name": "Consid S5 AB",
            "day_rate": 800.0,
            "hours_per_day": 8.0,
            "timesheet_system": "Other",
            "salesforce_code": None,
            "client_ref": None,
            "agreed_days": 0.5,
            "days_cycle_unit": "Month",
            "uk_vat": False,
            "key_contact": "Bo Kenneryd",
            "key_contact_email": "vincent.holland@consid.se; bo.kenneryd@consid.se",
            "address": "Storgatan 16 B, 341 44 Ljungby, Sweden"
        },
        {
            "name": "Rail Delivery Group - Handover",
            "client_name": "Transform",
            "day_rate": 600.0,
            "hours_per_day": 8.0,
            "timesheet_system": "Salesforce",
            "salesforce_code": "RSP: SoW073 Future Lennon Analytical Shadowing P2 (CIL)",
            "client_ref": "E001435 - RSP:SoW073 Future Lennon AS P2",
            "agreed_days": 3,
            "days_cycle_unit": "Week",
            "uk_vat": True,
            "key_contact": None,
            "key_contact_email": "finance@transformuk.com",
            "address": "60 Great Portland Street, London, W1W 7RT"
        },
        {
            "name": "Mid Sussex District Council",
            "client_name": "Mid Sussex District Council",
            "day_rate": 677.0,
            "hours_per_day": 8.0,
            "timesheet_system": "TBC",
            "salesforce_code": None,
            "client_ref": None,
            "agreed_days": 4,
            "days_cycle_unit": "Week",
            "uk_vat": True,
            "key_contact": None,
            "key_contact_email": None,
            "address": None
        },
        {
            "name": "Rail Delivery Group - Delivery",
            "client_name": "Transform",
            "day_rate": 600.0,
            "hours_per_day": 8.0,
            "timesheet_system": "Salesforce",
            "salesforce_code": "E001435 - RSP:SoW073 Future Lennon AS P3",
            "client_ref": "E001435 - RSP:SoW073 Future Lennon AS P3",
            "agreed_days": 3,
            "days_cycle_unit": "Week",
            "uk_vat": True,
            "key_contact": None,
            "key_contact_email": "finance@transformuk.com",
            "address": "60 Great Portland Street, London, W1W 7RT"
        }
    ]

    count = 0
    for p_data in projects_data:
        # Check if project already exists
        existing_project = session.query(Project).filter_by(name=p_data["name"]).first()
        if existing_project:
            print(f"Project '{p_data['name']}' already exists. Skipping.")
            continue
        
        project = Project(**p_data)
        session.add(project)
        count += 1
    
    session.commit()
    print(f"Successfully migrated {count} engagements (projects).")
    session.close()

if __name__ == "__main__":
    migrate_engagements()
