import base64
import hashlib
import hmac
import json
import time

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Smart Blood Donor System")

# Mount Static and Templates folder
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

JWT_SECRET = "smart-blood-donor-system-secret"
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


async def _render_login_page(request: Request, error: str | None = None, admin_console: bool = False):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "error": error, "admin_console": admin_console},
    )


@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


@app.get("/find-blood", response_class=HTMLResponse)
async def find_blood(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="find_blood.html",
        context={"request": request},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, admin_console: bool = False):
    return await _render_login_page(request, admin_console=admin_console)


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    phone_number: str = Form(...),
    password: str = Form(""),
    otp: str = Form(""),
    admin_console: str = Form(""),
):
    normalized_phone = phone_number.strip()
    is_admin_console = admin_console.lower() in {"on", "true", "1", "admin"}
    user = USERS.get(normalized_phone)
    if not user:
        return await _render_login_page(request, error="Invalid credentials", admin_console=is_admin_console)

    valid_password = password == user["password"] or otp == user["password"]
    if not valid_password:
        return await _render_login_page(request, error="Invalid credentials", admin_console=is_admin_console)

    token = _generate_jwt(normalized_phone, user["role"])
    destination = ROLE_DASHBOARDS.get(user["role"], "/")
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


@app.get("/donor/dashboard", response_class=HTMLResponse)
async def donor_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request, "role": "Donor", "title": "Donor Dashboard"},
    )


@app.get("/seeker/dashboard", response_class=HTMLResponse)
async def seeker_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request, "role": "Seeker", "title": "Seeker Dashboard"},
    )


@app.get("/hospital/dashboard", response_class=HTMLResponse)
async def hospital_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request, "role": "Hospital", "title": "Hospital Dashboard"},
    )


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request, "role": "Admin", "title": "Admin Console"},
    )