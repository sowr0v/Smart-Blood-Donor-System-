from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Smart Blood Donor System")

# Mount Static and Templates folder
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )

@app.get("/auth/register", response_class=HTMLResponse)
async def serve_registration(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"request": request},
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