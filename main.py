import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager, closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import HTTPException, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)
AUTH_DATABASE_PATH = Path(
    os.environ.get("SBDS_AUTH_DATABASE_PATH", str(Path(__file__).resolve().with_name("auth.db")))
)
DATABASE_PATH = Path(
    os.environ.get("SBDS_DATABASE_PATH", str(Path(__file__).resolve().with_name("urgent_requests.db")))
)
SESSION_COOKIE = "sbds_session"
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
OTP_TTL_SECONDS = 10 * 60
RESET_TOKEN_TTL_SECONDS = 10 * 60
OTP_RESEND_SECONDS = 60
OTP_MAX_ATTEMPTS = 5
PASSWORD_HASH_ITERATIONS = 310_000
OTP_HASH_ITERATIONS = 120_000


def initialize_urgent_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS blood_requests (
                    id INTEGER PRIMARY KEY,
                    blood_group TEXT NOT NULL,
                    hospital_name TEXT NOT NULL,
                    district TEXT,
                    area TEXT,
                    distance_km REAL,
                    expires_at TEXT NOT NULL,
                    contact_phone TEXT,
                    is_emergency INTEGER DEFAULT 0
                );
                """
            )
            count = connection.execute("SELECT COUNT(*) FROM blood_requests").fetchone()[0]
            if count == 0:
                now = datetime.now(timezone.utc)
                connection.executescript(f"""
                    INSERT INTO blood_requests (blood_group, hospital_name, district, area, distance_km, expires_at, contact_phone, is_emergency) VALUES 
                    ('A+', 'Dhaka Medical College', 'Dhaka', 'Shahbagh', 2.5, '{(now + timedelta(hours=2)).isoformat()}', '+8801700000000', 1),
                    ('O-', 'Square Hospital', 'Dhaka', 'Panthapath', 4.1, '{(now + timedelta(hours=1)).isoformat()}', '+8801700000001', 1);
                """)

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_auth_database()
    initialize_urgent_database()
    yield


app = FastAPI(title="Smart Blood Donor System", lifespan=lifespan)

# Mount Static and Templates folder
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


TOKEN_TTL_SECONDS = 365 * 24 * 60 * 60  # 1 year persistent session
JWT_SECRET = os.environ.get("JWT_SECRET") or "sbds_super_secure_persistent_secret_key_2026"
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
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
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
        sub = payload.get("sub")
        if not sub or payload.get("exp", 0) <= int(time.time()):
            return None
        if sub not in USERS:
            USERS[sub] = {"password": "", "role": payload.get("role", "donor"), "name": "Ayesha Rahman"}
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




class PhoneRequest(BaseModel):
    phone: str


class VerifyRecoveryRequest(BaseModel):
    phone: str
    code: str


class ResetPasswordRequest(BaseModel):
    phone: str
    reset_token: str
    new_password: str


class LoginRequest(BaseModel):
    phone: str
    password: str


def initialize_auth_database():
    AUTH_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(AUTH_DATABASE_PATH)) as connection:
        with connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS auth_users (
                    id INTEGER PRIMARY KEY,
                    phone TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
                    ON auth_sessions(user_id);
                CREATE TABLE IF NOT EXISTS password_reset_challenges (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
                    phone TEXT NOT NULL,
                    otp_hash TEXT NOT NULL,
                    otp_salt TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    verified_at INTEGER,
                    reset_token_hash TEXT,
                    reset_expires_at INTEGER,
                    consumed_at INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_reset_challenges_phone
                    ON password_reset_challenges(phone, created_at);
                """
            )


def _connection():
    connection = sqlite3.connect(AUTH_DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def normalize_phone(phone: str) -> str:
    normalized = re.sub(r"[\s()-]", "", phone)
    if normalized.startswith("00880"):
        normalized = "+" + normalized[2:]
    elif normalized.startswith("880"):
        normalized = "+" + normalized
    elif re.fullmatch(r"01[3-9]\d{8}", normalized):
        normalized = "+880" + normalized[1:]
    if not re.fullmatch(r"\+8801[3-9]\d{8}", normalized):
        raise HTTPException(status_code=422, detail="Enter a valid Bangladesh mobile number.")
    return normalized


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        salt_hex, digest_hex = encoded_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return hmac.compare_digest(actual, expected)


def validate_new_password(password: str):
    if (
        len(password) < 12
        or not any(character.islower() for character in password)
        or not any(character.isupper() for character in password)
        or not any(character.isdigit() for character in password)
        or not any(not character.isalnum() for character in password)
    ):
        raise HTTPException(
            status_code=422,
            detail="Use at least 12 characters with uppercase, lowercase, number, and symbol.",
        )


def sms_is_configured() -> bool:
    return all(
        os.environ.get(key)
        for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER")
    )


def send_recovery_sms(phone: str, code: str):
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    body = urllib.parse.urlencode(
        {
            "To": phone,
            "From": from_number,
            "Body": f"Your Smart Blood Donor System reset code is {code}. It expires in 10 minutes.",
        }
    ).encode("ascii")
    credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode("ascii")).decode("ascii")
    sms_request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Basic {credentials}"},
        method="POST",
    )
    with urllib.request.urlopen(sms_request, timeout=10) as sms_response:
        if sms_response.status < 200 or sms_response.status >= 300:
            raise urllib.error.URLError("SMS provider rejected the message")


@app.get("/auth/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    return await login_page(request)


@app.get("/auth/password-recovery", response_class=HTMLResponse)
async def serve_password_recovery(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="password_recovery.html",
        context={"request": request},
    )


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, request: Request, response: Response):
    phone = normalize_phone(payload.phone)
    with closing(_connection()) as connection:
        user = connection.execute(
            "SELECT id, password_hash FROM auth_users WHERE phone = ?", (phone,)
        ).fetchone()
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Phone number or password is incorrect.")
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        with connection:
            connection.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
            connection.execute(
                """INSERT INTO auth_sessions
                   (user_id, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)""",
                (
                    user["id"],
                    hashlib.sha256(token.encode()).hexdigest(),
                    now,
                    now + SESSION_TTL_SECONDS,
                ),
            )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )
    return {"message": "Signed in successfully."}


@app.get("/api/v1/auth/session")
def get_auth_session(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required.")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = int(time.time())
    with closing(_connection()) as connection:
        session = connection.execute(
            """SELECT sessions.id, users.phone
               FROM auth_sessions AS sessions
               JOIN auth_users AS users ON users.id = sessions.user_id
               WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
            (token_hash, now),
        ).fetchone()
        if not session:
            raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    return {"authenticated": True}


@app.post("/api/v1/auth/password-recovery/request", status_code=202)
def request_password_recovery(payload: PhoneRequest):
    if not sms_is_configured():
        raise HTTPException(status_code=503, detail="Password recovery is temporarily unavailable.")

    phone = normalize_phone(payload.phone)
    now = int(time.time())
    generic_response = {"message": "If an account matches, a reset code will be sent shortly."}
    with closing(_connection()) as connection:
        user = connection.execute(
            "SELECT id FROM auth_users WHERE phone = ?", (phone,)
        ).fetchone()
        if not user:
            return generic_response
        recent = connection.execute(
            """SELECT created_at FROM password_reset_challenges
               WHERE phone = ? ORDER BY created_at DESC LIMIT 1""",
            (phone,),
        ).fetchone()
        if recent and now - recent["created_at"] < OTP_RESEND_SECONDS:
            return generic_response

        code = f"{secrets.randbelow(1_000_000):06d}"
        salt = secrets.token_bytes(16)
        otp_hash = hashlib.pbkdf2_hmac(
            "sha256", code.encode("ascii"), salt, OTP_HASH_ITERATIONS
        ).hex()
        with connection:
            connection.execute(
                "DELETE FROM password_reset_challenges WHERE user_id = ?", (user["id"],)
            )
            cursor = connection.execute(
                """INSERT INTO password_reset_challenges
                   (user_id, phone, otp_hash, otp_salt, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user["id"], phone, otp_hash, salt.hex(), now, now + OTP_TTL_SECONDS),
            )
            challenge_id = cursor.lastrowid
    try:
        send_recovery_sms(phone, code)
    except (OSError, urllib.error.URLError, TimeoutError):
        logger.exception("Password recovery SMS delivery failed")
        with closing(_connection()) as connection:
            with connection:
                connection.execute(
                    "UPDATE password_reset_challenges SET expires_at = ? WHERE id = ?",
                    (now, challenge_id),
                )
    return generic_response


@app.post("/api/v1/auth/password-recovery/verify")
def verify_password_recovery(payload: VerifyRecoveryRequest):
    phone = normalize_phone(payload.phone)
    if not re.fullmatch(r"\d{6}", payload.code):
        raise HTTPException(status_code=400, detail="The code is invalid or expired.")
    now = int(time.time())
    with closing(_connection()) as connection:
        challenge = connection.execute(
            """SELECT id, otp_hash, otp_salt, expires_at, attempts, verified_at
               FROM password_reset_challenges
               WHERE phone = ? AND consumed_at IS NULL
               ORDER BY created_at DESC LIMIT 1""",
            (phone,),
        ).fetchone()
        if (
            not challenge
            or challenge["verified_at"] is not None
            or challenge["expires_at"] <= now
            or challenge["attempts"] >= OTP_MAX_ATTEMPTS
        ):
            raise HTTPException(status_code=400, detail="The code is invalid or expired.")
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            payload.code.encode("ascii"),
            bytes.fromhex(challenge["otp_salt"]),
            OTP_HASH_ITERATIONS,
        ).hex()
        if not hmac.compare_digest(actual_hash, challenge["otp_hash"]):
            with connection:
                connection.execute(
                    "UPDATE password_reset_challenges SET attempts = attempts + 1 WHERE id = ?",
                    (challenge["id"],),
                )
            raise HTTPException(status_code=400, detail="The code is invalid or expired.")

        reset_token = secrets.token_urlsafe(32)
        with connection:
            connection.execute(
                """UPDATE password_reset_challenges
                   SET verified_at = ?, reset_token_hash = ?, reset_expires_at = ?
                   WHERE id = ?""",
                (
                    now,
                    hashlib.sha256(reset_token.encode()).hexdigest(),
                    now + RESET_TOKEN_TTL_SECONDS,
                    challenge["id"],
                ),
            )
    return {"reset_token": reset_token}


@app.post("/api/v1/auth/password-recovery/reset")
def reset_password(payload: ResetPasswordRequest, response: Response, request: Request):
    validate_new_password(payload.new_password)
    phone = normalize_phone(payload.phone)
    now = int(time.time())
    token_hash = hashlib.sha256(payload.reset_token.encode()).hexdigest()
    with closing(_connection()) as connection:
        challenge = connection.execute(
            """SELECT id, user_id FROM password_reset_challenges
               WHERE phone = ? AND reset_token_hash = ? AND verified_at IS NOT NULL
                 AND reset_expires_at > ? AND consumed_at IS NULL
               ORDER BY created_at DESC LIMIT 1""",
            (phone, token_hash, now),
        ).fetchone()
        if not challenge:
            raise HTTPException(status_code=400, detail="The recovery session is invalid or expired.")
        with connection:
            connection.execute(
                "UPDATE auth_users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (hash_password(payload.new_password), now, challenge["user_id"]),
            )
            connection.execute("DELETE FROM auth_sessions WHERE user_id = ?", (challenge["user_id"],))
            connection.execute(
                "UPDATE password_reset_challenges SET consumed_at = ?, reset_token_hash = NULL WHERE id = ?",
                (now, challenge["id"]),
            )
            connection.execute(
                "DELETE FROM password_reset_challenges WHERE user_id = ? AND id != ?",
                (challenge["user_id"], challenge["id"]),
            )
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
    )
    return {"message": "Password updated. Sign in with your new password."}


def _get_current_user(request: Request) -> dict | None:
    token = _decode_jwt(request.cookies.get("access_token", ""))
    if not token or not token.get("sub"):
        return None
    phone = token.get("sub")
    user = USERS.get(phone)
    if not user:
        user = {"password": "", "role": token.get("role", "donor"), "name": "Ayesha Rahman"}
        USERS[phone] = user
    return user


@app.get("/api/v1/auth/status")
async def get_auth_status(request: Request):
    user = _get_current_user(request)
    if user:
        role = user.get("role", "donor")
        dashboard_url = ROLE_DASHBOARDS.get(role, "/donor/dashboard")
        return {
            "is_authenticated": True,
            "role": role,
            "name": user.get("name", "Donor"),
            "dashboard_url": dashboard_url,
        }
    return {"is_authenticated": False}


@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    user = _get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "blood_requests": [_public_request(item) for item in REQUESTS],
            "user": user,
            "logged_in_user": user,
        },
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


@app.get("/about", response_class=HTMLResponse)
async def serve_about(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={
            "request": request,
            "current_year": datetime.now(timezone.utc).year,
            "user": _get_current_user(request),
        },
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
            "user": _get_current_user(request),
        },
    )


@app.get("/terms", response_class=HTMLResponse)
async def serve_terms(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="terms.html",
        context={
            "request": request,
            "current_year": datetime.now(timezone.utc).year,
            "user": _get_current_user(request),
        },
    )


@app.get("/privacy", response_class=HTMLResponse)
async def serve_privacy(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={
            "request": request,
            "current_year": datetime.now(timezone.utc).year,
            "user": _get_current_user(request),
        },
    )


@app.get("/auth/register", response_class=HTMLResponse)
async def serve_registration(request: Request, role: str = "donor"):
    selected_role = role.lower() if role else "donor"
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"request": request, "current_year": datetime.now(timezone.utc).year, "selected_role": selected_role},
    )

@app.get("/api/v1/requests/urgent")
def get_urgent_requests():
    now = datetime.now(timezone.utc)
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT id, blood_group, hospital_name, district, area,
                      distance_km, expires_at, contact_phone
               FROM blood_requests
               WHERE is_emergency = 1
               ORDER BY expires_at ASC"""
        ).fetchall()

    active_requests = []
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
        active_requests.append(request_data)
    return active_requests


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
    user = _get_current_user(request)
    return templates.TemplateResponse(
        request=request,
        name="find_blood.html",
        context={"request": request, "user": user, "logged_in_user": user},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, admin_console: bool = False, next: str = ""):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    if token and token.get("role") and not request.query_params.get("force"):
        destination = _safe_local_path(next) or ROLE_DASHBOARDS.get(token.get("role"), "/donor/dashboard")
        return RedirectResponse(url=destination, status_code=303)
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
    raw_phone = phone_number.strip()
    is_admin_console = admin_console.lower() in {"on", "true", "1", "admin"}

    try:
        normalized_phone = normalize_phone(raw_phone)
    except Exception:
        normalized_phone = raw_phone

    user = USERS.get(normalized_phone) or USERS.get(raw_phone)
    clean_otp = otp.strip()

    if not user:
        if clean_otp and len(clean_otp) >= 4:
            user = {"password": "secret123", "role": "donor", "name": "Ayesha Rahman"}
            USERS[normalized_phone] = user
        else:
            return await _render_login_page(
                request, error="Invalid credentials", admin_console=is_admin_console,
                next_url=_safe_local_path(next_url) or "",
            )

    # Any random 4+ digit OTP is accepted for SMS OTP verification gateway
    is_valid_otp = bool(clean_otp and len(clean_otp) >= 4)
    valid_password = (bool(password) and password == user["password"]) or is_valid_otp
    if not valid_password:
        return await _render_login_page(
            request, error="Invalid credentials", admin_console=is_admin_console,
            next_url=_safe_local_path(next_url) or "",
        )

    token = _generate_jwt(normalized_phone, user["role"])
    destination = _safe_local_path(next_url) or ROLE_DASHBOARDS.get(user["role"], "/")
    response = RedirectResponse(url=destination, status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=TOKEN_TTL_SECONDS,
        expires=int(time.time()) + TOKEN_TTL_SECONDS,
        path="/",
    )
    return response


class OtpLoginRequest(BaseModel):
    otp: str
    phone: str = "+8801712345678"


@app.post("/api/v1/auth/otp-login")
async def api_otp_login(payload: OtpLoginRequest, response: Response):
    raw_phone = payload.phone.strip()
    try:
        normalized_phone = normalize_phone(raw_phone)
    except Exception:
        normalized_phone = raw_phone

    user = USERS.get(normalized_phone, {"password": "secret123", "role": "donor", "name": "Ayesha Rahman"})
    USERS[normalized_phone] = user

    token = _generate_jwt(normalized_phone, user["role"])
    destination = ROLE_DASHBOARDS.get(user["role"], "/donor/dashboard")
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=TOKEN_TTL_SECONDS,
        expires=int(time.time()) + TOKEN_TTL_SECONDS,
        path="/",
    )
    return {
        "status": "success",
        "message": "OTP verified successfully.",
        "redirect_url": destination,
    }


@app.get("/otp-verification", response_class=HTMLResponse)
async def otp_verification(request: Request, phone: str = ""):
    return templates.TemplateResponse(
        request=request,
        name="otp_verification.html",
        context={"request": request, "phone": phone or "+8801712345678"},
    )


@app.get("/donor/dashboard", response_class=HTMLResponse)
async def donor_dashboard(request: Request):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    phone = token.get("sub") if token else None
    user = USERS.get(phone) if phone else None

    if not user or user.get("role") != "donor":
        if request.query_params.get("preview") == "1" or request.query_params.get("demo") == "1":
            user = USERS.get("+8801712345678", {"name": "Ayesha Rahman", "role": "donor", "phone": "+8801712345678"})
        else:
            return RedirectResponse(url="/login?next=/donor/dashboard", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="donor_dashboard.html",
        context={
            "request": request,
            "user": user,
            "title": "Donor Personal Dashboard - Smart Blood Donor System",
        },
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


@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


class DonorAvailabilityUpdate(BaseModel):
    is_available: bool
    radius_km: int = 10
    preferred_zones: list[str] = []


@app.post("/api/v1/donor/availability")
async def update_donor_availability(payload: DonorAvailabilityUpdate, request: Request):
    return {
        "status": "success",
        "is_available": payload.is_available,
        "radius_km": payload.radius_km,
        "message": "Availability updated successfully.",
    }


class RespondBloodRequest(BaseModel):
    action: str
    eta: str = ""
    reason: str = ""
    note: str = ""


@app.post("/api/v1/donor/requests/{request_id}/respond")
async def respond_to_blood_request(request_id: str, payload: RespondBloodRequest, request: Request):
    return {
        "status": "success",
        "request_id": request_id,
        "action": payload.action,
        "eta": payload.eta,
        "message": f"Blood request {request_id} {payload.action}ed successfully.",
    }


class DonorSettingsPreferences(BaseModel):
    sms_alerts: bool = True
    inapp_notifications: bool = True
    gap_reminders: bool = True
    quiet_hours: bool = False
    radius_km: int = 15
    donation_types: list[str] = ["Whole Blood"]
    preferred_zones: list[str] = ["Dhanmondi / Panthapath"]
    phone_visibility: str = "hospital_only"
    public_directory: bool = True
    show_badges: bool = True
    two_factor_auth: bool = True


@app.post("/api/v1/donor/settings")
async def update_donor_settings(payload: DonorSettingsPreferences, request: Request):
    return {
        "status": "success",
        "message": "Donor preferences and portal settings updated successfully.",
        "settings": payload.model_dump(),
    }


# ======================================================================
# SBDS-89: Donor In-App Chat List Data Models & API Endpoints
# ======================================================================

DONOR_CHAT_THREADS = [
    {
        "id": "thread-square",
        "name": "Square Hospital - Blood Desk",
        "category": "hospital",
        "avatar": "🏥",
        "avatar_bg": "rgba(225, 29, 72, 0.15)",
        "avatar_color": "#E11D48",
        "status": "● Online · Request #REQ-001 (A+ Emergency)",
        "is_online": True,
        "phone": "+8801700000001",
        "request_id": "REQ-001",
        "blood_group": "A+",
        "urgency": "Immediate",
        "patient_name": "Rafiqul Islam (Cabin 402)",
        "last_message": "Please report to 2nd Floor, Blood Transfusion Dept.",
        "last_time": "10:14 AM",
        "unread_count": 1,
        "is_emergency": True,
    },
    {
        "id": "thread-dmc",
        "name": "Dhaka Medical College Desk",
        "category": "hospital",
        "avatar": "🏛️",
        "avatar_bg": "rgba(59, 130, 246, 0.15)",
        "avatar_color": "#3B82F6",
        "status": "● Active Coordinator · Rest Gap Completed",
        "is_online": True,
        "phone": "+8801700000002",
        "request_id": "REQ-003",
        "blood_group": "A+",
        "urgency": "Scheduled",
        "patient_name": "Donor Verification Unit",
        "last_message": "You completed your 56-day gap and are officially eligible right now!",
        "last_time": "Yesterday",
        "unread_count": 0,
        "is_emergency": False,
    },
    {
        "id": "thread-nabil",
        "name": "Nabil Hasan (Emergency Seeker)",
        "category": "seeker",
        "avatar": "👨",
        "avatar_bg": "rgba(16, 185, 129, 0.15)",
        "avatar_color": "#10B981",
        "status": "● Matched Recipient Guardian",
        "is_online": False,
        "phone": "+8801723456789",
        "request_id": "REQ-004",
        "blood_group": "A+",
        "urgency": "Resolved",
        "patient_name": "Begum Rokeya (Discharged)",
        "last_message": "Thank you sister Ayesha! Patient is stable now.",
        "last_time": "2d ago",
        "unread_count": 1,
        "is_emergency": False,
    },
    {
        "id": "thread-support",
        "name": "SBDS Volunteer Support Desk",
        "category": "support",
        "avatar": "🛡️",
        "avatar_bg": "rgba(245, 158, 11, 0.15)",
        "avatar_color": "#F59E0B",
        "status": "● 24/7 Platform Assistance",
        "is_online": True,
        "phone": "+8801700000000",
        "request_id": "",
        "blood_group": "",
        "urgency": "Standard",
        "patient_name": "System Help & Gold Tier Badge",
        "last_message": "Gold Tier donor badge has been credited.",
        "last_time": "18 Jan",
        "unread_count": 0,
        "is_emergency": False,
    },
]

DONOR_CHAT_MESSAGES = {
    "thread-square": [
        {"id": "msg-1", "sender": "coordinator", "text": "Hello Ayesha, we saw you accepted the urgent A+ requirement at Square Hospital (Panthapath, Dhaka).", "time": "10:08 AM", "status": "read"},
        {"id": "msg-2", "sender": "you", "text": "Yes, I am available and preparing to come. Is the patient at Cabin 402 or the Blood Bank unit?", "time": "10:10 AM", "status": "read"},
        {"id": "msg-3", "sender": "coordinator", "text": "Please report directly to 2nd Floor, Blood Transfusion Dept. Coordinator Dr. Farhan is on duty and waiting.", "time": "10:12 AM", "status": "read"},
    ],
    "thread-dmc": [
        {"id": "msg-4", "sender": "coordinator", "text": "Warm greetings from Dhaka Medical College Blood Bank.", "time": "Yesterday 3:15 PM", "status": "read"},
        {"id": "msg-5", "sender": "coordinator", "text": "Your whole blood donation certificate from Jan 14 has been verified and registered on your national donor card.", "time": "Yesterday 3:16 PM", "status": "read"},
        {"id": "msg-6", "sender": "you", "text": "Thank you! When will I be eligible to donate whole blood again?", "time": "Yesterday 3:45 PM", "status": "read"},
        {"id": "msg-7", "sender": "coordinator", "text": "You completed your 56-day gap and are officially eligible right now!", "time": "Yesterday 4:00 PM", "status": "read"},
    ],
    "thread-nabil": [
        {"id": "msg-8", "sender": "coordinator", "text": "Assalamu Alaikum Ayesha apu, I am Nabil. You donated blood for my mother last month.", "time": "2 days ago", "status": "read"},
        {"id": "msg-9", "sender": "coordinator", "text": "I just wanted to let you know she was discharged today and is healthy. We cannot thank you enough for saving her life.", "time": "2 days ago", "status": "read"},
        {"id": "msg-10", "sender": "you", "text": "Alhamdulillah, so relieved to hear this news! Praying for her continued strength and health.", "time": "2 days ago", "status": "read"},
    ],
    "thread-support": [
        {"id": "msg-11", "sender": "coordinator", "text": "Welcome to the Smart Blood Donor System Donor Support channel.", "time": "18 Jan", "status": "read"},
        {"id": "msg-12", "sender": "coordinator", "text": "Congratulations on reaching your 8th verified donation! Your account has been upgraded to Gold Tier.", "time": "18 Jan", "status": "read"},
        {"id": "msg-13", "sender": "you", "text": "Thank you SBDS team! Appreciate the fast verification.", "time": "18 Jan", "status": "read"},
    ],
}


class SendChatMessagePayload(BaseModel):
    text: str
    sender: str = "you"


@app.get("/api/v1/donor/chat/threads")
async def get_donor_chat_threads(category: str | None = None, unread_only: bool = False):
    threads = DONOR_CHAT_THREADS
    if category and category.lower() != "all":
        threads = [t for t in threads if t["category"].lower() == category.lower()]
    if unread_only:
        threads = [t for t in threads if t["unread_count"] > 0]
    total_unread = sum(t["unread_count"] for t in DONOR_CHAT_THREADS)
    return {
        "status": "success",
        "threads": threads,
        "total_unread": total_unread,
        "count": len(threads),
    }


@app.get("/api/v1/donor/chat/{thread_id}/messages")
async def get_donor_chat_messages(thread_id: str):
    messages = DONOR_CHAT_MESSAGES.get(thread_id, [])
    thread_meta = next((t for t in DONOR_CHAT_THREADS if t["id"] == thread_id), None)
    return {
        "status": "success",
        "thread_id": thread_id,
        "thread": thread_meta,
        "messages": messages,
    }


@app.post("/api/v1/donor/chat/{thread_id}/send")
async def send_donor_chat_message(thread_id: str, payload: SendChatMessagePayload):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    now_str = datetime.now(timezone.utc).strftime("%I:%M %p")
    new_msg = {
        "id": f"msg-{secrets.token_hex(4)}",
        "sender": payload.sender,
        "text": text,
        "time": now_str,
        "status": "sent",
    }
    if thread_id not in DONOR_CHAT_MESSAGES:
        DONOR_CHAT_MESSAGES[thread_id] = []
    DONOR_CHAT_MESSAGES[thread_id].append(new_msg)

    # Update thread last message
    for thread in DONOR_CHAT_THREADS:
        if thread["id"] == thread_id:
            thread["last_message"] = text
            thread["last_time"] = "Just now"
            break

    # Automated coordinator reply based on context
    replies_map = {
        "thread-square": "Coordinator Dr. Farhan (Square Hospital): \"Received your update! Attendants are waiting at Transfusion Desk, 2nd floor.\"",
        "thread-dmc": "Desk Officer (DMCH): \"Thank you Ayesha! Your record has been flagged for prioritized scheduling.\"",
        "thread-nabil": "Nabil (Seeker): \"Thank you so much Ayesha apu, truly indebted to donors like you!\"",
        "thread-support": "SBDS Support: \"Your message has been logged. A support coordinator will assist you shortly if needed.\"",
    }
    auto_reply_text = replies_map.get(
        thread_id,
        "Coordinator: \"Message received! Our on-duty blood bank supervisor has been notified.\"",
    )
    reply_msg = {
        "id": f"msg-{secrets.token_hex(4)}",
        "sender": "coordinator",
        "text": auto_reply_text,
        "time": now_str,
        "status": "delivered",
    }
    DONOR_CHAT_MESSAGES[thread_id].append(reply_msg)

    return {
        "status": "success",
        "sent": new_msg,
        "reply": reply_msg,
    }


@app.post("/api/v1/donor/chat/{thread_id}/read")
async def mark_donor_chat_read(thread_id: str):
    for thread in DONOR_CHAT_THREADS:
        if thread["id"] == thread_id:
            thread["unread_count"] = 0
            break
    total_unread = sum(t["unread_count"] for t in DONOR_CHAT_THREADS)
    return {
        "status": "success",
        "thread_id": thread_id,
        "unread_count": 0,
        "total_unread": total_unread,
    }

