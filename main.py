import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Smart Blood Donor System")

# Mount Static and Templates folder
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

JWT_SECRET = os.environ.get("JWT_SECRET") or secrets.token_urlsafe(32)
ROLE_DASHBOARDS = {
    "donor": "/donor/dashboard",
    "seeker": "/seeker/dashboard",
    "hospital": "/hospital/dashboard",
    "admin": "/admin/dashboard",
}
USERS = {
    "+8801712345678": {"password": "secret123", "role": "donor", "name": "Ayesha Rahman"},
    "+8801723456789": {"password": "match123", "role": "seeker", "name": "Nabil Hasan"},
    "+8801734567890": {"password": "hospital123", "role": "hospital", "name": "Dhaka General"},
    "+8801745678901": {"password": "admin123", "role": "admin", "name": "System Admin"},
}
REQUESTS = [
    {
        "id": "req-001",
        "blood_group": "A+",
        "hospital": "Square Hospital",
        "area": "Farmgate",
        "units": 2,
        "status": "Critical",
        "posted_at": (datetime.now(timezone.utc) - timedelta(minutes=8)).isoformat(),
        "contact_name": "Blood Desk",
        "contact_phone": "+8801700000001",
    },
    {
        "id": "req-002",
        "blood_group": "O-",
        "hospital": "Green Life Hospital",
        "area": "Panthapath",
        "units": 1,
        "status": "Urgent",
        "posted_at": (datetime.now(timezone.utc) - timedelta(minutes=24)).isoformat(),
        "contact_name": "Emergency Desk",
        "contact_phone": "+8801700000002",
    },
    {
        "id": "req-003",
        "blood_group": "B+",
        "hospital": "Ibn Sina Hospital",
        "area": "Dhanmondi",
        "units": 3,
        "status": "Open",
        "posted_at": (datetime.now(timezone.utc) - timedelta(hours=1, minutes=12)).isoformat(),
        "contact_name": "Transfusion Unit",
        "contact_phone": "+8801700000003",
    },
    {
        "id": "req-004",
        "blood_group": "A+",
        "hospital": "Dhaka Medical College Hospital",
        "area": "Shahbagh",
        "units": 2,
        "status": "Urgent",
        "posted_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "contact_name": "Blood Bank",
        "contact_phone": "+8801700000004",
    },
]


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _generate_jwt(subject: str, role: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def _decode_jwt(token: str) -> dict | None:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        expected_signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
        signature = base64.urlsafe_b64decode(encoded_signature + "=" * (-len(encoded_signature) % 4))
        if not hmac.compare_digest(signature, expected_signature):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4)))
        if payload.get("exp", 0) <= int(time.time()) or payload.get("sub") not in USERS:
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _safe_local_path(path: str) -> str | None:
    parsed_path = urlsplit(path)
    if path.startswith("/") and not path.startswith("//") and not parsed_path.netloc and not parsed_path.scheme:
        return path
    return None


def _public_request(request: dict) -> dict:
    return {key: value for key, value in request.items() if not key.startswith("contact_")}


async def _render_login_page(
    request: Request,
    error: str | None = None,
    admin_console: bool = False,
    next_url: str = "",
):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "error": error, "admin_console": admin_console, "next_url": next_url},
    )


@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "blood_requests": [_public_request(item) for item in REQUESTS]},
    )


@app.get("/api/blood-requests")
async def blood_requests(blood_group: str | None = Query(default=None)):
    filtered_requests = REQUESTS
    if blood_group and blood_group.upper() != "ALL":
        filtered_requests = [item for item in REQUESTS if item["blood_group"] == blood_group.upper()]
    response = JSONResponse([_public_request(item) for item in filtered_requests])
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/requests/{request_id}/connect", response_class=HTMLResponse)
async def connect_to_request(request: Request, request_id: str):
    blood_request = next((item for item in REQUESTS if item["id"] == request_id), None)
    if blood_request is None:
        return HTMLResponse("Blood request not found", status_code=404)

    token = _decode_jwt(request.cookies.get("access_token", ""))
    if token is None:
        next_url = f"/requests/{request_id}/connect"
        return RedirectResponse(url=f"/login?next={next_url}", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="request_contact.html",
        context={"request": request, "blood_request": blood_request},
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


@app.get("/find-blood", response_class=HTMLResponse)
async def find_blood(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="find_blood.html",
        context={"request": request},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, admin_console: bool = False, next: str = ""):
    return await _render_login_page(request, admin_console=admin_console, next_url=_safe_local_path(next) or "")


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    phone_number: str = Form(...),
    password: str = Form(""),
    otp: str = Form(""),
    admin_console: str = Form(""),
    next_url: str = Form(""),
):
    normalized_phone = phone_number.strip()
    is_admin_console = admin_console.lower() in {"on", "true", "1", "admin"}
    user = USERS.get(normalized_phone)
    if not user:
        return await _render_login_page(
            request, error="Invalid credentials", admin_console=is_admin_console,
            next_url=_safe_local_path(next_url) or "",
        )

    valid_password = password == user["password"] or otp == user["password"]
    if not valid_password:
        return await _render_login_page(
            request, error="Invalid credentials", admin_console=is_admin_console,
            next_url=_safe_local_path(next_url) or "",
        )

    token = _generate_jwt(normalized_phone, user["role"])
    destination = _safe_local_path(next_url) or ROLE_DASHBOARDS.get(user["role"], "/")
    response = RedirectResponse(url=destination, status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax", max_age=3600)
    return response


@app.get("/auth/login", response_class=HTMLResponse)
async def auth_login(request: Request):
    return await login_page(request)


@app.get("/auth/register", response_class=HTMLResponse)
async def register(request: Request, role: str = "donor"):
    selected_role = role.lower() if role else "donor"
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"request": request, "selected_role": selected_role},
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={"request": request},
    )


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="contact.html",
        context={"request": request},
    )