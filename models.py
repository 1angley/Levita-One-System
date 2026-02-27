from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime

Base = declarative_base()

class Project(Base):
    """The 'Target' for time entries (e.g., Client name, Internal code)."""
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    client_name = Column(String)
    day_rate = Column(Float)
    hours_per_day = Column(Float, default=8.0)
    salesforce_code = Column(String) # This maps to 'Timesheet System Code'
    timesheet_system = Column(String, default="None") # e.g., Salesforce, Other, TBC, None
    client_ref = Column(String)
    
    # New billing fields
    agreed_days = Column(Float, default=0.0)
    days_cycle_unit = Column(String, default="Week") # Week or Month
    uk_vat = Column(Boolean, default=True)
    
    # Extra project details
    key_contact = Column(String)
    key_contact_email = Column(String)
    address = Column(String)
    description = Column(String)
    create_draft_invoice_email = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    
    entries = relationship("TimeEntry", back_populates="project")

class TimeEntry(Base):
    """An individual day's entry for a project."""
    __tablename__ = 'time_entries'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    date = Column(Date, nullable=False)
    hours = Column(Float, nullable=False)
    description = Column(String)
    
    # Status tracking
    is_synced = Column(Boolean, default=False)
    synced_at = Column(DateTime)
    
    project = relationship("Project", back_populates="entries")

class TimesheetRow(Base):
    """A row in the weekly timesheet, representing a week of hours for a project."""
    __tablename__ = 'timesheet_rows'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    week_start_date = Column(Date, nullable=False) # Always the Monday
    
    # Hours for each day (Mon-Sun)
    day1_hours = Column(Float, default=0.0)
    day2_hours = Column(Float, default=0.0)
    day3_hours = Column(Float, default=0.0)
    day4_hours = Column(Float, default=0.0)
    day5_hours = Column(Float, default=0.0)
    day6_hours = Column(Float, default=0.0)
    day7_hours = Column(Float, default=0.0)
    
    day_rate = Column(Float)
    status = Column(String, default="") # "Pending", "Approved", or ""
    invoice_id = Column(Integer, ForeignKey('invoices.id'))
    
    project = relationship("Project")
    invoice = relationship("Invoice", back_populates="timesheet_rows")

class Invoice(Base):
    """An invoice generated for one or more timesheet rows."""
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    invoice_number = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    amount = Column(Float)
    status = Column(String, default="Draft") # Draft, Sent, Paid
    pdf_filename = Column(String)
    
    project = relationship("Project")
    timesheet_rows = relationship("TimesheetRow", back_populates="invoice")

class Settings(Base):
    """Global application settings."""
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    draft_invoice_email = Column(String)
    email_invoice_template = Column(String) # For the body of the email
    invoice_template_file = Column(String) # The filename from 'invoice templates' folder
    
    # New settings
    invoice_generation_timing = Column(String, default="Immediate") # Immediate or Batch
    batch_submission_time = Column(String) # e.g., "17:00"
    
    # Gmail integration settings
    gmail_credentials = Column(String) # JSON string for OAuth2 credentials
    gmail_connection_status = Column(Boolean, default=False)
    
    # Invoice numbering
    last_invoice_sequence = Column(Integer, default=1000)

# Database setup
DATABASE_URL = "sqlite:///timesheets.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized at timesheets.db")

if __name__ == "__main__":
    init_db()
