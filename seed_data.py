from models import SessionLocal, Project, Settings, init_db
import os

def seed():
    # Attempt to delete existing DB to start fresh with new schema
    if os.path.exists("timesheets.db"):
        try:
            os.remove("timesheets.db")
            print("Old database deleted. Starting fresh.")
        except PermissionError:
            print("ERROR: Could not delete 'timesheets.db' because it's currently in use.")
            print("Please STOP the 'Levita One Web' process in PyCharm first, then try again.")
            return
    
    init_db()
    
    session = SessionLocal()

    # Seed default settings
    settings = Settings(
        draft_invoice_email="alex@levita.co.uk",
        email_invoice_template="Hello {{ contact_name }}\n\nPlease find attached the latest invoice for the Project {{ project_name }}, {{ client_ref }}\n\nany issues please do let me know.\n\nThanks\nAlex",
        invoice_template_file="default.html",
        invoice_generation_timing="Immediate",
        last_invoice_sequence=1001
    )
    session.add(settings)
    print("Default settings seeded (template: default.html).")
    
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
            "agreed_days": 0,
            "days_cycle_unit": "Week",
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
    
    for p_data in projects_data:
        project = Project(**p_data)
        session.add(project)
    
    session.commit()
    print(f"Successfully seeded {len(projects_data)} projects.")
    session.close()

if __name__ == "__main__":
    seed()
