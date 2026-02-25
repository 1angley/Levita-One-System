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
    agreed_days = Column(Integer, default=0)
    days_cycle_unit = Column(String, default="Week") # Week or Month
    uk_vat = Column(Boolean, default=True)
    
    # Extra project details
    key_contact = Column(String)
    key_contact_email = Column(String)
    address = Column(String)
    
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

# Database setup
DATABASE_URL = "sqlite:///timesheets.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized at timesheets.db")

if __name__ == "__main__":
    init_db()
