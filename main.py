import os
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Smart Blood Donor System")

# Mount Static and Templates folder
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "current_year": datetime.now(timezone.utc).year},
    )


@app.get("/about", response_class=HTMLResponse)
async def serve_about(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={"request": request, "current_year": datetime.now(timezone.utc).year},
    )


@app.get("/contact", response_class=HTMLResponse)
async def serve_contact(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="contact.html",
        context={
            "request": request,
            "current_year": datetime.now(timezone.utc).year,
            "contact_email": os.environ.get("PUBLIC_CONTACT_EMAIL", "").strip(),
        },
    )


@app.get("/terms", response_class=HTMLResponse)
async def serve_terms(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="terms.html",
        context={"request": request, "current_year": datetime.now(timezone.utc).year},
    )


@app.get("/privacy", response_class=HTMLResponse)
async def serve_privacy(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={"request": request, "current_year": datetime.now(timezone.utc).year},
    )


@app.get("/auth/register", response_class=HTMLResponse)
async def serve_registration(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"request": request, "current_year": datetime.now(timezone.utc).year},
    )

@app.get("/api/v1/donors/live-ticker")
def get_live_ticker():
    return [
        {"blood_group": "O+", "message": "Mijanur R. verified in Farmgate, Dhaka (Just now)"},
        {"blood_group": "A-", "message": "Farhana Y. completed donation at DMCH (10 mins ago)"},
        {"blood_group": "B+", "message": "Anisur R. verified in Dhanmondi (20 mins ago)"},
        {"blood_group": "O-", "message": "Sultana K. responded to emergency request (35 mins ago)"},
        {"blood_group": "AB+", "message": "Tanvir A. available in Mirpur-10 (45 mins ago)"}
    ]