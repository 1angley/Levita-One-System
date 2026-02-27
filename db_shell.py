from models import SessionLocal, Project, TimeEntry, TimesheetRow, Invoice, Settings
import os

def main():
    session = SessionLocal()
    print("--- Levita One DB Shell ---")
    print("Models available: Project, TimeEntry, TimesheetRow, Invoice, Settings")
    print("Variable 'session' is ready for use.")
    print("Example: projects = session.query(Project).all()")
    print("Example: p = session.query(Project).first(); p.name = 'New Name'; session.commit()")
    print("Type 'exit()' to quit.")
    
    # This starts an interactive Python shell with the local variables available
    import code
    code.interact(local=locals())

if __name__ == "__main__":
    main()
