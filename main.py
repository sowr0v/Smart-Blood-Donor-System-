import os
import sqlite3
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_urgent_requests_db()
    yield


app = FastAPI(title="Smart Blood Donor System", lifespan=lifespan)
DATABASE_PATH = Path(
    os.environ.get(
        "SBDS_DATABASE_PATH",
        str(Path(__file__).resolve().with_name("urgent_requests.db")),
    )
)

# Mount Static and Templates folder
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def initialize_urgent_requests_db():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS blood_requests (
                    id INTEGER PRIMARY KEY,
                    blood_group TEXT NOT NULL,
                    hospital_name TEXT NOT NULL,
                    district TEXT NOT NULL,
                    area TEXT NOT NULL,
                    distance_km REAL,
                    expires_at TEXT NOT NULL,
                    contact_phone TEXT,
                    is_emergency INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_blood_requests_emergency_expiry "
                "ON blood_requests (is_emergency, expires_at)"
            )


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


@app.get("/api/v1/requests/urgent")
def get_urgent_requests():
    now = datetime.now(timezone.utc)
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, blood_group, hospital_name, district, area,
                   distance_km, expires_at, contact_phone
            FROM blood_requests
            WHERE is_emergency = 1
            ORDER BY expires_at ASC
            """
        ).fetchall()

    requests = []
    for row in rows:
        try:
            expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        except ValueError:
            continue
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            continue

        request_data = dict(row)
        request_data["expires_at"] = expires_at.isoformat()
        requests.append(request_data)
    return requests

@app.get("/api/v1/donors/live-ticker")
def get_live_ticker():
    return [
        {"blood_group": "O+", "message": "Mijanur R. verified in Farmgate, Dhaka (Just now)"},
        {"blood_group": "A-", "message": "Farhana Y. completed donation at DMCH (10 mins ago)"},
        {"blood_group": "B+", "message": "Anisur R. verified in Dhanmondi (20 mins ago)"},
        {"blood_group": "O-", "message": "Sultana K. responded to emergency request (35 mins ago)"},
        {"blood_group": "AB+", "message": "Tanvir A. available in Mirpur-10 (45 mins ago)"}
    ]