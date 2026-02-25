from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from models import SessionLocal, Project, TimesheetRow, Invoice
import uvicorn
from datetime import datetime, timedelta
from typing import List
from pydantic import BaseModel

app = FastAPI(title="Levita One")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models for timesheet saving
class DayEntry(BaseModel):
    project_id: int
    day_rate: float
    hours: List[float] # 7 days

class WeeklyTimesheetSave(BaseModel):
    week_start: str # YYYY-MM-DD
    entries: List[DayEntry]
    reset_status: bool = False

class TimesheetSubmit(BaseModel):
    project_id: int
    week_start: str # YYYY-MM-DD

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/projects", response_class=HTMLResponse)
async def list_projects(request: Request, db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    return templates.TemplateResponse("projects.html", {"request": request, "projects": projects})

@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    return templates.TemplateResponse("project_detail.html", {"request": request, "project": project})

@app.post("/projects/add")
async def add_project(
    name: str = Form(...),
    client_name: str = Form(...),
    day_rate: float = Form(0.0),
    hours_per_day: float = Form(8.0),
    salesforce_code: str = Form(None),
    timesheet_system: str = Form("None"),
    client_ref: str = Form(None),
    agreed_days: float = Form(0.0),
    days_cycle_unit: str = Form("Week"),
    uk_vat: bool = Form(True),
    key_contact: str = Form(None),
    key_contact_email: str = Form(None),
    address: str = Form(None),
    is_active: bool = Form(True),
    db: Session = Depends(get_db)
):
    new_project = Project(
        name=name,
        client_name=client_name,
        day_rate=day_rate,
        hours_per_day=hours_per_day,
        salesforce_code=salesforce_code,
        timesheet_system=timesheet_system,
        client_ref=client_ref,
        agreed_days=agreed_days,
        days_cycle_unit=days_cycle_unit,
        uk_vat=uk_vat,
        key_contact=key_contact,
        key_contact_email=key_contact_email,
        address=address,
        is_active=is_active
    )
    db.add(new_project)
    db.commit()
    return RedirectResponse(url="/projects", status_code=303)

@app.post("/projects/{project_id}")
async def update_project(
    project_id: int,
    name: str = Form(...),
    client_name: str = Form(...),
    day_rate: float = Form(...),
    hours_per_day: float = Form(...),
    salesforce_code: str = Form(None),
    timesheet_system: str = Form("None"),
    client_ref: str = Form(None),
    agreed_days: float = Form(0.0),
    days_cycle_unit: str = Form("Week"),
    uk_vat: bool = Form(True),
    key_contact: str = Form(None),
    key_contact_email: str = Form(None),
    address: str = Form(None),
    is_active: bool = Form(False),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.name = name
        project.client_name = client_name
        project.day_rate = day_rate
        project.hours_per_day = hours_per_day
        project.salesforce_code = salesforce_code
        project.timesheet_system = timesheet_system
        project.client_ref = client_ref
        project.agreed_days = agreed_days
        project.days_cycle_unit = days_cycle_unit
        project.uk_vat = uk_vat
        project.key_contact = key_contact
        project.key_contact_email = key_contact_email
        project.address = address
        project.is_active = is_active
        db.commit()
    return RedirectResponse(url="/projects", status_code=303)

@app.post("/projects/toggle/{project_id}")
async def toggle_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.is_active = not project.is_active
        db.commit()
    return RedirectResponse(url="/projects", status_code=303)

@app.get("/timesheets", response_class=HTMLResponse)
async def timesheet_page(request: Request, date: str = None, db: Session = Depends(get_db)):
    if date:
        try:
            current_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            current_date = datetime.now()
    else:
        current_date = datetime.now()
    
    # Calculate Monday of the current week
    monday = (current_date - timedelta(days=current_date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_dates = [(monday + timedelta(days=i)).date() for i in range(7)]
    
    prev_week = (monday - timedelta(days=7)).strftime("%Y-%m-%d")
    next_week = (monday + timedelta(days=7)).strftime("%Y-%m-%d")
    
    live_projects = db.query(Project).filter(Project.is_active == True).all()
    
    # Fetch existing saved rows for this week
    saved_rows = db.query(TimesheetRow).filter(TimesheetRow.week_start_date == monday.date()).all()
    saved_data = {row.project_id: row for row in saved_rows}
    
    return templates.TemplateResponse("timesheets.html", {
        "request": request,
        "week_dates": week_dates,
        "prev_week": prev_week,
        "next_week": next_week,
        "projects": live_projects,
        "current_monday": monday.date(),
        "saved_data": saved_data
    })

@app.post("/timesheets/save")
async def save_timesheet(data: WeeklyTimesheetSave, db: Session = Depends(get_db)):
    week_start = datetime.strptime(data.week_start, "%Y-%m-%d").date()
    
    for entry in data.entries:
        # Check if row already exists
        row = db.query(TimesheetRow).filter(
            TimesheetRow.project_id == entry.project_id,
            TimesheetRow.week_start_date == week_start
        ).first()
        
        if not row:
            row = TimesheetRow(
                project_id=entry.project_id,
                week_start_date=week_start
            )
            db.add(row)
        
        row.day1_hours = entry.hours[0]
        row.day2_hours = entry.hours[1]
        row.day3_hours = entry.hours[2]
        row.day4_hours = entry.hours[3]
        row.day5_hours = entry.hours[4]
        row.day6_hours = entry.hours[5]
        row.day7_hours = entry.hours[6]
        row.day_rate = entry.day_rate
        
        if data.reset_status:
            row.status = ""
    
    db.commit()
    return {"status": "success"}

@app.post("/timesheets/submit")
async def submit_timesheet(data: TimesheetSubmit, db: Session = Depends(get_db)):
    week_start = datetime.strptime(data.week_start, "%Y-%m-%d").date()
    row = db.query(TimesheetRow).filter(
        TimesheetRow.project_id == data.project_id,
        TimesheetRow.week_start_date == week_start
    ).first()
    
    if row:
        row.status = "Pending"
        db.commit()
        return {"status": "success"}
    return {"status": "error", "message": "Timesheet row not found"}

import calendar
from dateutil.relativedelta import relativedelta

@app.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request, month: str = None, week: str = None, view: str = "monthly", db: Session = Depends(get_db)):
    if view == "weekly":
        if week:
            try:
                current_date = datetime.strptime(week, "%Y-%m-%d").date()
            except ValueError:
                current_date = datetime.now().date()
        else:
            current_date = datetime.now().date()
        
        # Adjust to Monday
        current_date = current_date - timedelta(days=current_date.weekday())
        
        first_day = current_date
        last_day = current_date + timedelta(days=6)
        
        prev_period = (current_date - timedelta(days=7)).strftime("%Y-%m-%d")
        next_period = (current_date + timedelta(days=7)).strftime("%Y-%m-%d")
        display_name = f"Week of {current_date.strftime('%d %b %Y')}"
    else:
        if month:
            try:
                current_month_date = datetime.strptime(month, "%Y-%m")
            except ValueError:
                current_month_date = datetime.now().replace(day=1)
        else:
            current_month_date = datetime.now().replace(day=1)
        
        first_day = current_month_date.replace(day=1).date()
        last_day = (current_month_date + relativedelta(day=31)).date()
        
        prev_period = (current_month_date - relativedelta(months=1)).strftime("%Y-%m")
        next_period = (current_month_date + relativedelta(months=1)).strftime("%Y-%m")
        display_name = current_month_date.strftime("%B %Y")

    projects = db.query(Project).all()
    
    # Fetch timesheet rows that overlap with the period
    # A week (week_start_date to week_start_date + 6) overlaps with [first_day, last_day] if:
    # week_start_date <= last_day AND week_start_date + 6 >= first_day
    # Which is equivalent to: week_start_date <= last_day AND week_start_date >= first_day - 6 days
    start_search = first_day - timedelta(days=6)
    saved_rows = db.query(TimesheetRow).filter(
        TimesheetRow.week_start_date <= last_day,
        TimesheetRow.week_start_date >= start_search
    ).all()
    
    project_billing = []
    
    for project in projects:
        total_hours = 0
        project_row_ids = []
        has_invoice = False
        
        # Calculate hours for this project in this period
        for row in saved_rows:
            if row.project_id == project.id:
                project_row_ids.append(row.id)
                if row.invoice_id:
                    has_invoice = True
                # Iterate through each day of the week
                for i in range(7):
                    day_date = row.week_start_date + timedelta(days=i)
                    if first_day <= day_date <= last_day:
                        if i == 0: total_hours += row.day1_hours
                        elif i == 1: total_hours += row.day2_hours
                        elif i == 2: total_hours += row.day3_hours
                        elif i == 3: total_hours += row.day4_hours
                        elif i == 4: total_hours += row.day5_hours
                        elif i == 5: total_hours += row.day6_hours
                        elif i == 6: total_hours += row.day7_hours
        
        hours_per_day = project.hours_per_day or 8.0
        total_days = total_hours / hours_per_day if hours_per_day > 0 else 0
        billable_amount = total_days * (project.day_rate or 0)
        
        # Agreed days logic
        agreed_days = project.agreed_days or 0
        if project.days_cycle_unit == 'Week':
            agreed_display = f"{agreed_days} / week"
        else:
            agreed_display = f"{agreed_days} / month"

        project_billing.append({
            "project": project,
            "total_hours": total_hours,
            "total_days": total_days,
            "agreed_display": agreed_display,
            "billable_amount": billable_amount,
            "row_ids": ",".join(map(str, project_row_ids)),
            "has_invoice": has_invoice
        })
    
    # Calendar view data (still monthly for context, or we could change it)
    cal_date = current_date if view == "weekly" else current_month_date
    cal = calendar.monthcalendar(cal_date.year, cal_date.month)
    
    today = datetime.now()
    is_current = (today.year == cal_date.year and today.month == cal_date.month)
    if view == "weekly":
        is_current = (today.date() >= first_day and today.date() <= last_day)

    return templates.TemplateResponse("billing.html", {
        "request": request,
        "display_name": display_name,
        "current_period": week if view == "weekly" else (month or current_month_date.strftime("%Y-%m")),
        "prev_period": prev_period,
        "next_period": next_period,
        "project_billing": project_billing,
        "calendar": cal,
        "year": cal_date.year,
        "month_int": cal_date.month,
        "today_day": today.day,
        "is_current": is_current,
        "view": view,
        "current_week": week or (datetime.now().date() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d"),
        "current_month": month or current_month_date.strftime("%Y-%m")
    })

@app.post("/billing/invoice")
async def create_invoice(project_id: int = Form(...), row_ids: str = Form(...), db: Session = Depends(get_db)):
    # Create a simple invoice
    project = db.query(Project).get(project_id)
    if not project:
        return {"status": "error", "message": "Project not found"}
    
    ids = [int(rid) for rid in row_ids.split(",") if rid]
    rows = db.query(TimesheetRow).filter(TimesheetRow.id.in_(ids)).all()
    
    if not rows:
        return {"status": "error", "message": "No timesheet rows found"}
    
    total_hours = 0
    for row in rows:
        total_hours += (row.day1_hours + row.day2_hours + row.day3_hours + row.day4_hours + 
                       row.day5_hours + row.day6_hours + row.day7_hours)
    
    hours_per_day = project.hours_per_day or 8.0
    total_days = total_hours / hours_per_day if hours_per_day > 0 else 0
    billable_amount = total_days * (project.day_rate or 0)
    
    import uuid
    invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
    
    new_invoice = Invoice(
        project_id=project_id,
        invoice_number=invoice_number,
        amount=billable_amount,
        status="Draft"
    )
    db.add(new_invoice)
    db.flush() # Get ID
    
    for row in rows:
        row.invoice_id = new_invoice.id
    
    db.commit()
    return RedirectResponse(url="/billing", status_code=303)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
