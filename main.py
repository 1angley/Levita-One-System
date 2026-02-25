from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from models import SessionLocal, Project
import uvicorn

app = FastAPI(title="Levita One")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    agreed_days: int = Form(0),
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
    agreed_days: int = Form(0),
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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
