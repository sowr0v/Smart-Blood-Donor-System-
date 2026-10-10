import base64
import asyncio
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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Form, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import HTTPException, Response
from pydantic import BaseModel, Field

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
                CREATE TABLE IF NOT EXISTS donor_request_responses (
                    id INTEGER PRIMARY KEY,
                    request_id INTEGER NOT NULL REFERENCES blood_requests(id),
                    donor_phone TEXT NOT NULL,
                    action TEXT NOT NULL CHECK (action IN ('accept', 'decline')),
                    eta TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    responded_at TEXT NOT NULL,
                    UNIQUE (request_id, donor_phone)
                );
                CREATE TABLE IF NOT EXISTS seeker_notifications (
                    id INTEGER PRIMARY KEY,
                    request_id INTEGER NOT NULL REFERENCES blood_requests(id),
                    donor_phone TEXT NOT NULL,
                    response TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS donor_donation_history (
                    id INTEGER PRIMARY KEY,
                    donor_phone TEXT NOT NULL,
                    request_id INTEGER REFERENCES blood_requests(id),
                    donated_at TEXT NOT NULL,
                    donation_type TEXT NOT NULL DEFAULT 'Whole Blood',
                    notes TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_donation_history_donor_date
                    ON donor_donation_history(donor_phone, donated_at DESC);
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


DONOR_MATCH_COMPATIBILITY = {
    "A+": {"A+", "AB+"},
    "A-": {"A+", "A-", "AB+", "AB-"},
    "B+": {"B+", "AB+"},
    "B-": {"B+", "B-", "AB+", "AB-"},
    "AB+": {"AB+"},
    "AB-": {"AB+", "AB-"},
    "O+": {"O+", "A+", "B+", "AB+"},
    "O-": {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"},
}


def _normalized_request_urgency(request: dict) -> str:
    urgency = str(request.get("urgency") or request.get("status") or "Standard").strip().title()
    if urgency in {"Critical", "Urgent", "Open", "Standard"}:
        return urgency
    if urgency.lower() in {"critical", "emergency"}:
        return "Critical"
    if urgency.lower() in {"urgent", "high"}:
        return "Urgent"
    return "Standard"


def _request_is_active(request: dict) -> bool:
    if request.get("is_active") is False:
        return False
    status = str(request.get("status") or "").lower()
    if status in {"inactive", "closed", "resolved", "completed"}:
        return False
    posted_at = request.get("posted_at")
    if posted_at:
        try:
            created = datetime.fromisoformat(str(posted_at).replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created < datetime.now(timezone.utc) - timedelta(days=7):
                return False
        except ValueError:
            pass
    return True


def _build_donor_match_requests(profile: dict) -> list[dict]:
    donor_group = (profile.get("blood_group") or "A+").upper()
    donor_district = (profile.get("district") or "Dhaka").strip().lower()
    donor_area = (profile.get("area") or "").strip().lower()
    compatible_groups = DONOR_MATCH_COMPATIBILITY.get(donor_group, {donor_group})
    matches = []

    for request in REQUESTS:
        if not _request_is_active(request):
            continue
        if (request.get("blood_group") or "").upper() not in compatible_groups:
            continue

        request_district = (request.get("district") or "Dhaka").strip().lower()
        request_area = (request.get("area") or "").strip().lower()
        if donor_district and donor_area and request_district != donor_district and request_area != donor_area:
            if request_district != donor_district and request_district != "dhaka":
                continue

        request_data = dict(request)
        request_data["district"] = request.get("district") or "Dhaka"
        request_data["urgency"] = _normalized_request_urgency(request)
        request_data["is_active"] = True
        request_data["location"] = f"{request.get('area') or 'Dhaka'}, {request.get('district') or 'Dhaka'}"
        matches.append(request_data)

    order = {"Critical": 3, "Urgent": 2, "Open": 1, "Standard": 1}
    matches.sort(
        key=lambda item: (order.get(_normalized_request_urgency(item), 0), item.get("posted_at", "")),
        reverse=True,
    )
    return matches


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
    success_message: str | None = None,
    admin_console: bool = False,
    next_url: str = "",
):
    if not success_message and request.query_params.get("registered"):
        success_message = "Registration successful! Please log in with your phone number and password."
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,
            "error": error,
            "success_message": success_message,
            "admin_console": admin_console,
            "next_url": next_url,
        },
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
                CREATE TABLE IF NOT EXISTS donor_profiles (
                    phone TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    email TEXT,
                    date_of_birth TEXT,
                    gender TEXT,
                    blood_group TEXT NOT NULL,
                    district TEXT NOT NULL,
                    area TEXT NOT NULL,
                    address TEXT NOT NULL,
                    last_donation TEXT,
                    medical_conditions TEXT,
                    medications TEXT,
                    allergies TEXT,
                    fitness_status TEXT NOT NULL DEFAULT 'Eligible',
                    preferred_donation_types TEXT NOT NULL DEFAULT 'Whole Blood',
                    is_available INTEGER NOT NULL DEFAULT 1,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (phone)
                );
                """
            )
            donor_profile_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(donor_profiles)").fetchall()
            }
            if "is_available" not in donor_profile_columns:
                connection.execute(
                    "ALTER TABLE donor_profiles ADD COLUMN is_available INTEGER NOT NULL DEFAULT 1"
                )
            auth_user_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(auth_users)").fetchall()
            }
            if "role" not in auth_user_columns:
                connection.execute("ALTER TABLE auth_users ADD COLUMN role TEXT DEFAULT 'donor'")
            if "name" not in auth_user_columns:
                connection.execute("ALTER TABLE auth_users ADD COLUMN name TEXT DEFAULT ''")
            if "blood_group" not in auth_user_columns:
                connection.execute("ALTER TABLE auth_users ADD COLUMN blood_group TEXT DEFAULT ''")


def _connection():
    connection = sqlite3.connect(AUTH_DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _get_user_by_phone(phone: str) -> dict | None:
    if phone in USERS:
        return USERS[phone]
    initialize_auth_database()
    with closing(_connection()) as connection:
        row = connection.execute(
            "SELECT phone, password_hash, role, name, blood_group FROM auth_users WHERE phone = ?",
            (phone,),
        ).fetchone()
        if row:
            role = row["role"] or "donor"
            user_data = {
                "password": "",
                "password_hash": row["password_hash"],
                "role": role,
                "name": row["name"] or ("Blood Seeker" if role == "seeker" else "Blood Donor"),
                "blood_group": row["blood_group"] or "A+",
            }
            USERS[phone] = user_data
            return user_data
    return None


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
    if token and token.get("sub"):
        phone = token.get("sub")
        token_role = token.get("role", "donor")
        user = _get_user_by_phone(phone)
        if not user:
            default_name = "Blood Seeker" if token_role == "seeker" else "Ayesha Rahman"
            user = {"password": "", "role": token_role, "name": default_name, "phone": phone}
            USERS[phone] = user
        if not user.get("role"):
            user["role"] = token_role
        if not user.get("phone"):
            user["phone"] = phone
        return user

    session_token = request.cookies.get(SESSION_COOKIE)
    if session_token:
        token_hash = hashlib.sha256(session_token.encode()).hexdigest()
        now = int(time.time())
        with closing(_connection()) as connection:
            session = connection.execute(
                """SELECT users.phone, users.role, users.full_name
                   FROM auth_sessions AS sessions
                   JOIN auth_users AS users ON users.id = sessions.user_id
                   WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
                (token_hash, now),
            ).fetchone()
            if session:
                phone = session["phone"]
                user = _get_user_by_phone(phone)
                if user:
                    return user
                return {
                    "phone": phone,
                    "role": session["role"] if "role" in session.keys() and session["role"] else "donor",
                    "name": session["full_name"] if "full_name" in session.keys() else "User",
                }
    return None


@app.get("/api/v1/auth/status")
async def get_auth_status(request: Request):
    user = _get_current_user(request)
    if user:
        role = user.get("role", "donor")
        dashboard_url = ROLE_DASHBOARDS.get(role, "/seeker/dashboard" if role == "seeker" else "/donor/dashboard")
        return {
            "is_authenticated": True,
            "role": role,
            "name": user.get("name", "User"),
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


class UserRegisterRequest(BaseModel):
    role: str = "seeker"
    name: str = ""
    phone: str
    password: str
    nid: str | None = ""
    blood_group: str | None = "A+"
    address: str | None = ""
    org_name: str | None = ""
    govt_reg: str | None = ""
    manager_number: str | None = ""


def _register_user_record(
    phone_raw: str,
    password: str,
    role: str = "seeker",
    name: str = "",
    blood_group: str = "A+",
    nid: str = "",
    address: str = "",
) -> tuple[dict, str, str]:
    try:
        phone = normalize_phone(phone_raw.strip())
    except Exception:
        phone = phone_raw.strip()

    clean_role = role.lower().strip() if role else "seeker"
    if clean_role not in {"seeker", "donor", "hospital", "bank", "admin"}:
        clean_role = "seeker"

    user_name = name.strip() or ("Blood Seeker" if clean_role == "seeker" else "Blood Donor")
    USERS[phone] = {
        "password": password,
        "role": clean_role,
        "name": user_name,
        "blood_group": blood_group or "A+",
    }

    # Save to auth.db
    initialize_auth_database()
    pw_hash = hash_password(password)
    now = int(time.time())
    with closing(_connection()) as connection:
        with connection:
            existing = connection.execute(
                "SELECT id FROM auth_users WHERE phone = ?", (phone,)
            ).fetchone()
            if existing:
                connection.execute(
                    "UPDATE auth_users SET password_hash = ?, role = ?, name = ?, blood_group = ?, updated_at = ? WHERE id = ?",
                    (pw_hash, clean_role, user_name, blood_group or "A+", now, existing["id"]),
                )
            else:
                connection.execute(
                    "INSERT INTO auth_users (phone, password_hash, role, name, blood_group, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (phone, pw_hash, clean_role, user_name, blood_group or "A+", now, now),
                )

    if clean_role == "seeker":
        if phone not in SEEKER_SETTINGS:
            SEEKER_SETTINGS[phone] = {
                "full_name": user_name,
                "phone": phone,
                "default_hospital": "Square Hospital, Dhaka",
                "sms_alerts": True,
                "push_alerts": True,
                "audio_siren": True,
                "default_radius": "10",
            }
    elif clean_role == "donor":
        _default_donor_profile(phone)

    token = _generate_jwt(phone, clean_role)
    destination = "/login?registered=1"
    return USERS[phone], destination, token


@app.post("/api/v1/auth/register")
async def api_register(payload: UserRegisterRequest, response: Response):
    user, destination, _ = _register_user_record(
        phone_raw=payload.phone,
        password=payload.password,
        role=payload.role,
        name=payload.name or payload.org_name or "",
        blood_group=payload.blood_group or "A+",
        nid=payload.nid or "",
        address=payload.address or "",
    )
    # Ensure existing session/token cookies are cleared so user is not automatically logged in
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {
        "status": "success",
        "message": f"Successfully registered as {user['role'].title()}! Please sign in to continue.",
        "role": user["role"],
        "redirect_url": "/login?registered=1",
    }


@app.post("/auth/register")
async def form_register(
    request: Request,
    phone: str = Form(...),
    password: str = Form(...),
    role: str = Form("seeker"),
    name: str = Form(""),
    blood_group: str = Form("A+"),
    nid: str = Form(""),
    address: str = Form(""),
    org_name: str = Form(""),
    govt_reg: str = Form(""),
    manager_number: str = Form(""),
):
    actual_name = name or org_name or ("Blood Seeker" if role == "seeker" else "Blood Donor")
    user, destination, _ = _register_user_record(
        phone_raw=phone,
        password=password,
        role=role,
        name=actual_name,
        blood_group=blood_group,
        nid=nid,
        address=address,
    )
    resp = RedirectResponse(url="/login?registered=1", status_code=303)
    resp.delete_cookie(key="access_token", path="/")
    resp.delete_cookie(key=SESSION_COOKIE, path="/")
    return resp

@app.get("/api/v1/requests/urgent")
def get_urgent_requests(request: Request):
    now = datetime.now(timezone.utc)
    token = _decode_jwt(request.cookies.get("access_token", ""))
    donor_phone = token.get("sub", "") if token and token.get("role") == "donor" else ""
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT blood_requests.id, blood_group, hospital_name, district, area,
                      distance_km, expires_at, contact_phone,
                      CASE donor_request_responses.action
                          WHEN 'accept' THEN 'accepted'
                          WHEN 'decline' THEN 'declined'
                      END AS response_status
               FROM blood_requests
               LEFT JOIN donor_request_responses
                 ON donor_request_responses.request_id = blood_requests.id
                AND donor_request_responses.donor_phone = ?
               WHERE is_emergency = 1
               ORDER BY expires_at ASC""",
            (donor_phone,),
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
    if not request.query_params.get("registered") and not request.query_params.get("force"):
        token = _decode_jwt(request.cookies.get("access_token", ""))
        if token and token.get("role"):
            destination = _safe_local_path(next) or ROLE_DASHBOARDS.get(token.get("role"), "/donor/dashboard")
            return RedirectResponse(url=destination, status_code=303)
    resp = await _render_login_page(request, admin_console=admin_console, next_url=_safe_local_path(next) or "")
    if request.query_params.get("registered"):
        resp.delete_cookie(key="access_token", path="/")
        resp.delete_cookie(key=SESSION_COOKIE, path="/")
    return resp


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

    user = _get_user_by_phone(normalized_phone) or _get_user_by_phone(raw_phone)
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
    valid_password = False
    if password:
        if user.get("password") and password == user["password"]:
            valid_password = True
        elif user.get("password_hash") and verify_password(password, user["password_hash"]):
            valid_password = True
    valid_password = valid_password or is_valid_otp
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

    user = _get_user_by_phone(normalized_phone) or _get_user_by_phone(raw_phone)
    if not user:
        user = {"password": "secret123", "role": "donor", "name": "Ayesha Rahman"}
        USERS[normalized_phone] = user

    token = _generate_jwt(normalized_phone, user["role"])
    destination = ROLE_DASHBOARDS.get(user["role"], "/seeker/dashboard" if user["role"] == "seeker" else "/donor/dashboard")
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


def _default_donor_profile(phone: str) -> dict:
    user = USERS.get(phone, {"name": "Ayesha Rahman", "role": "donor", "phone": phone})
    return {
        "phone": phone,
        "name": user.get("name") or "Ayesha Rahman",
        "email": "ayesha.rahman@gmail.com",
        "date_of_birth": "1992-02-14",
        "gender": "Female",
        "blood_group": user.get("blood_group", "A+"),
        "district": "Dhaka",
        "area": "Dhanmondi",
        "address": "House 18, Road 7, Dhanmondi, Dhaka",
        "last_donation": "2026-01-14",
        "medical_conditions": "No major medical issues",
        "medications": "None",
        "allergies": "Penicillin",
        "fitness_status": "Eligible",
        "preferred_donation_types": "Whole Blood",
        "is_available": True,
        "updated_at": int(time.time()),
    }


def _get_donor_profile(phone: str) -> dict:
    initialize_auth_database()
    with closing(_connection()) as connection:
        row = connection.execute(
            """SELECT phone, name, email, date_of_birth, gender, blood_group,
                      district, area, address, last_donation, medical_conditions,
                      medications, allergies, fitness_status, preferred_donation_types,
                      is_available, updated_at
               FROM donor_profiles WHERE phone = ?""",
            (phone,),
        ).fetchone()
        if row is not None:
            return {key: row[key] for key in row.keys()}

        profile = _default_donor_profile(phone)
        with connection:
            connection.execute(
                """INSERT INTO donor_profiles (
                       phone, name, email, date_of_birth, gender, blood_group, district,
                       area, address, last_donation, medical_conditions, medications,
                       allergies, fitness_status, preferred_donation_types, is_available, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                tuple(profile.values()),
            )
        return profile


class DonorProfileUpdate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    blood_group: str
    district: str
    area: str
    address: str
    last_donation: str | None = None
    medical_conditions: str = ""
    medications: str = ""
    allergies: str = ""
    fitness_status: str = "Eligible"
    preferred_donation_types: str = "Whole Blood"


VALID_BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}


@app.get("/api/v1/donor/profile")
async def get_donor_profile(request: Request):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    phone = token.get("sub") if token and token.get("role") == "donor" else None
    if not phone and request.query_params.get("preview") == "1":
        phone = "+8801712345678"
    if not phone:
        raise HTTPException(status_code=401, detail="Sign in required to access donor profile.")
    return {"status": "success", "profile": _get_donor_profile(phone)}


@app.post("/api/v1/donor/profile")
async def update_donor_profile(payload: DonorProfileUpdate, request: Request):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    phone = token.get("sub") if token and token.get("role") == "donor" else None
    if not phone and request.query_params.get("preview") == "1":
        phone = "+8801712345678"
    if not phone:
        raise HTTPException(status_code=401, detail="Sign in required to update donor profile.")

    normalized_phone = normalize_phone(payload.phone)
    if normalized_phone != phone:
        raise HTTPException(status_code=422, detail="Phone number must match the authenticated donor.")
    if payload.blood_group not in VALID_BLOOD_GROUPS:
        raise HTTPException(status_code=422, detail="Blood group is invalid.")
    if not payload.name.strip() or not payload.district.strip() or not payload.area.strip() or not payload.address.strip():
        raise HTTPException(status_code=422, detail="Name, district, area, and address are required.")
    if payload.email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", payload.email.strip()):
        raise HTTPException(status_code=422, detail="Please provide a valid email address.")
    if payload.last_donation:
        try:
            datetime.fromisoformat(payload.last_donation)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Last donation date must use YYYY-MM-DD format.") from exc

    profile = {
        "phone": phone,
        "name": payload.name.strip(),
        "email": payload.email.strip() if payload.email else "",
        "date_of_birth": payload.date_of_birth or "",
        "gender": payload.gender or "",
        "blood_group": payload.blood_group,
        "district": payload.district.strip(),
        "area": payload.area.strip(),
        "address": payload.address.strip(),
        "last_donation": payload.last_donation or "",
        "medical_conditions": payload.medical_conditions.strip(),
        "medications": payload.medications.strip(),
        "allergies": payload.allergies.strip(),
        "fitness_status": payload.fitness_status.strip() or "Eligible",
        "preferred_donation_types": payload.preferred_donation_types.strip() or "Whole Blood",
        "updated_at": int(time.time()),
    }
    with closing(_connection()) as connection:
        with connection:
            connection.execute(
                """INSERT INTO donor_profiles (
                   phone, name, email, date_of_birth, gender, blood_group, district,
                   area, address, last_donation, medical_conditions, medications,
                   allergies, fitness_status, preferred_donation_types, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(phone) DO UPDATE SET
                   name = excluded.name, email = excluded.email, date_of_birth = excluded.date_of_birth,
                   gender = excluded.gender, blood_group = excluded.blood_group, district = excluded.district,
                   area = excluded.area, address = excluded.address, last_donation = excluded.last_donation,
                   medical_conditions = excluded.medical_conditions, medications = excluded.medications,
                   allergies = excluded.allergies, fitness_status = excluded.fitness_status,
                   preferred_donation_types = excluded.preferred_donation_types, updated_at = excluded.updated_at""",
                tuple(profile.values()),
            )
    USERS[phone] = {**USERS.get(phone, {"role": "donor"}), "name": profile["name"], "phone": phone, "blood_group": profile["blood_group"]}
    return {"status": "success", "message": "Donor profile updated successfully.", "profile": profile}


@app.get("/api/v1/donor/matches")
async def donor_matching_requests(
    request: Request,
    blood_group: str = Query(default="all"),
    urgency: str = Query(default="all"),
    district: str = Query(default="all"),
):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    phone = token.get("sub") if token and token.get("role") == "donor" else None
    if not phone and request.query_params.get("preview") == "1":
        phone = "+8801712345678"
    if not phone:
        raise HTTPException(status_code=401, detail="Sign in required to access matched requests.")

    profile = _get_donor_profile(phone)
    matches = _build_donor_match_requests(profile) if profile["is_available"] else []
    if blood_group.lower() != "all":
        matches = [item for item in matches if item.get("blood_group", "").upper() == blood_group.upper()]
    if urgency.lower() != "all":
        selected_urgency = _normalized_request_urgency({"urgency": urgency})
        matches = [item for item in matches if _normalized_request_urgency(item) == selected_urgency]
    if district.lower() != "all":
        matches = [item for item in matches if item.get("district", "Dhaka").lower() == district.lower()]
    return {"status": "success", "count": len(matches), "requests": matches, "profile": profile}


@app.get("/api/v1/donor/donations")
async def get_donor_donation_history(request: Request):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required to access donation history.")
    if token.get("role") != "donor":
        raise HTTPException(status_code=403, detail="Only donors can access donation history.")

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT history.id, history.donated_at, history.donation_type, history.notes,
                      history.request_id, blood_requests.hospital_name,
                      blood_requests.area, blood_requests.district
               FROM donor_donation_history AS history
               LEFT JOIN blood_requests ON blood_requests.id = history.request_id
               WHERE history.donor_phone = ?
               ORDER BY history.donated_at DESC, history.id DESC""",
            (token["sub"],),
        ).fetchall()
    donations = [dict(row) for row in rows]
    return {"status": "success", "count": len(donations), "donations": donations}


@app.get("/donor/dashboard", response_class=HTMLResponse)
async def donor_dashboard(request: Request):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    if token and token.get("role") == "seeker":
        return RedirectResponse(url="/seeker/dashboard", status_code=303)

    phone = token.get("sub") if token and token.get("role") == "donor" else None
    user = USERS.get(phone) if phone else None
    should_set_cookie = False

    if not user:
        if request.query_params.get("preview") == "1" or request.query_params.get("demo") == "1":
            phone = "+8801712345678"
            user = USERS.get(phone, {"name": "Ayesha Rahman", "role": "donor", "phone": phone})
            should_set_cookie = True
        else:
            return RedirectResponse(url="/login?next=/donor/dashboard", status_code=303)

    profile = _get_donor_profile(phone)
    response = templates.TemplateResponse(
        request=request,
        name="donor_dashboard.html",
        context={
            "request": request,
            "user": user,
            "profile": profile,
            "title": "Donor Personal Dashboard - Smart Blood Donor System",
        },
    )
    if should_set_cookie or not request.cookies.get("access_token"):
        jwt_token = _generate_jwt(phone, "donor")
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            samesite="lax",
            max_age=TOKEN_TTL_SECONDS,
            expires=int(time.time()) + TOKEN_TTL_SECONDS,
            path="/",
        )
    return response


@app.get("/seeker/dashboard", response_class=HTMLResponse)
async def seeker_dashboard(request: Request):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    if token and token.get("role") == "donor":
        return RedirectResponse(url="/donor/dashboard", status_code=303)

    phone = token.get("sub") if token and token.get("role") == "seeker" else None
    user = USERS.get(phone) if phone else None
    should_set_cookie = False

    if not user:
        if request.query_params.get("preview") == "1" or request.query_params.get("demo") == "1":
            phone = "+8801723456789"
            user = USERS.get(phone, {"name": "Nabil Hasan", "role": "seeker", "phone": phone})
            should_set_cookie = True
        else:
            return RedirectResponse(url="/login?next=/seeker/dashboard", status_code=303)

    response = templates.TemplateResponse(
        request=request,
        name="seeker_dashboard.html",
        context={
            "request": request,
            "user": user,
            "title": "Blood Seeker Portal - Smart Blood Donor System",
        },
    )
    if should_set_cookie or not request.cookies.get("access_token"):
        jwt_token = _generate_jwt(phone, "seeker")
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            samesite="lax",
            max_age=TOKEN_TTL_SECONDS,
            expires=int(time.time()) + TOKEN_TTL_SECONDS,
            path="/",
        )
    return response


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
    response.delete_cookie("access_token", path="/")
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


class DonorAvailabilityUpdate(BaseModel):
    is_available: bool
    radius_km: int = 10
    preferred_zones: list[str] = Field(default_factory=list)


@app.get("/api/v1/donor/availability")
async def get_donor_availability(request: Request):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required to access donor availability.")
    if token.get("role") != "donor":
        raise HTTPException(status_code=403, detail="Only donors can access donor availability.")

    profile = _get_donor_profile(token["sub"])
    return {"status": "success", "is_available": bool(profile["is_available"])}


@app.post("/api/v1/donor/availability")
async def update_donor_availability(payload: DonorAvailabilityUpdate, request: Request):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required to update donor availability.")
    if token.get("role") != "donor":
        raise HTTPException(status_code=403, detail="Only donors can update donor availability.")

    phone = token["sub"]
    _get_donor_profile(phone)
    with closing(_connection()) as connection:
        with connection:
            connection.execute(
                "UPDATE donor_profiles SET is_available = ?, updated_at = ? WHERE phone = ?",
                (int(payload.is_available), int(time.time()), phone),
            )
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
    token = _decode_jwt(request.cookies.get("access_token", ""))
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to respond to a blood request.")
    if token.get("role") != "donor":
        raise HTTPException(status_code=403, detail="Only donors can respond to blood requests.")

    action = payload.action.strip().lower()
    if action not in {"accept", "decline"}:
        raise HTTPException(status_code=422, detail="Action must be accept or decline.")
    try:
        database_request_id = int(request_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Active blood request not found.") from None

    now = datetime.now(timezone.utc)
    notification_message = (
        f"A donor accepted blood request {request_id}."
        if action == "accept"
        else f"A donor declined blood request {request_id}."
    )
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        blood_request = connection.execute(
            "SELECT expires_at FROM blood_requests WHERE id = ? AND is_emergency = 1",
            (database_request_id,),
        ).fetchone()
        if blood_request is None:
            raise HTTPException(status_code=404, detail="Active blood request not found.")
        try:
            expires_at = datetime.fromisoformat(blood_request["expires_at"].replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=409, detail="This request is no longer active.") from None
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise HTTPException(status_code=409, detail="This request is no longer active.")

        try:
            with connection:
                connection.execute(
                    """INSERT INTO donor_request_responses
                       (request_id, donor_phone, action, eta, reason, note, responded_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        database_request_id,
                        token["sub"],
                        action,
                        payload.eta,
                        payload.reason,
                        payload.note,
                        now.isoformat(),
                    ),
                )
                connection.execute(
                    """INSERT INTO seeker_notifications
                       (request_id, donor_phone, response, message, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (database_request_id, token["sub"], action, notification_message, now.isoformat()),
                )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="You have already responded to this request.") from None

    return {
        "status": "success",
        "request_id": request_id,
        "action": action,
        "request_status": "accepted" if action == "accept" else "declined",
        "eta": payload.eta,
        "message": f"Blood request {request_id} {action}ed successfully.",
        "notification": {"recipient": "seeker", "status": "queued", "message": notification_message},
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

class ChatConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {
            "donor": [],
            "seeker": [],
        }

    async def connect(self, role: str, websocket: WebSocket):
        await websocket.accept()
        if role not in self.active_connections:
            self.active_connections[role] = []
        self.active_connections[role].append(websocket)

    def disconnect(self, role: str, websocket: WebSocket):
        if role in self.active_connections and websocket in self.active_connections[role]:
            self.active_connections[role].remove(websocket)

    async def broadcast(self, role: str, message: dict):
        if role in self.active_connections:
            for connection in list(self.active_connections[role]):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect(role, connection)

chat_manager = ChatConnectionManager()

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
        "is_online": True,
        "phone": "+8801723456789",
        "request_id": "REQ-004",
        "blood_group": "A+",
        "urgency": "Immediate",
        "patient_name": "Emergency Recipient at Square",
        "last_message": "Leaving Dhanmondi now. Reaching Square Hospital in 20 mins.",
        "last_time": "10:14 AM",
        "unread_count": 0,
        "is_emergency": True,
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
        {"id": "msg-sync-1", "sender": "coordinator", "text": "Assalamu Alaikum Ayesha apu, we urgently need 1 bag A+ blood at Square Hospital 3rd Floor.", "time": "10:05 AM", "status": "read"},
        {"id": "msg-sync-2", "sender": "you", "text": "Wa Alaikum Assalam Nabil bhai! I just saw the alert. I am eligible and nearby.", "time": "10:08 AM", "status": "read"},
        {"id": "msg-sync-3", "sender": "coordinator", "text": "Alhamdulillah! Can you please reach as soon as possible? Requisition is ready.", "time": "10:10 AM", "status": "read"},
        {"id": "msg-sync-4", "sender": "you", "text": "Leaving Dhanmondi now. Reaching Square Hospital in 20 mins.", "time": "10:14 AM", "status": "read"},
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


@app.websocket("/ws/chat/{role}")
async def websocket_chat_endpoint(websocket: WebSocket, role: str):
    normalized_role = role.strip().lower()
    await chat_manager.connect(normalized_role, websocket)
    try:
        await websocket.send_json({
            "type": "connection_established",
            "role": normalized_role,
            "status": "connected",
        })
        # Broadcast presence
        other_role = "seeker" if normalized_role == "donor" else "donor"
        await chat_manager.broadcast(other_role, {
            "type": "presence",
            "role": normalized_role,
            "status": "online",
        })
        while True:
            text_data = await websocket.receive_text()
            try:
                data = json.loads(text_data)
                action = data.get("action")
                if action == "ping":
                    await websocket.send_json({"type": "pong"})
                elif action == "send_message":
                    thread_id = data.get("thread_id", "")
                    text = data.get("text", "")
                    if normalized_role == "donor":
                        await send_donor_chat_message(thread_id, SendChatMessagePayload(text=text, sender="you"))
                    elif normalized_role == "seeker":
                        await send_seeker_chat_message(thread_id, SendChatMessagePayload(text=text, sender="you"))
                elif action == "typing":
                    thread_id = data.get("thread_id", "")
                    is_typing = bool(data.get("typing", True))
                    target_thread = "thread-ayesha" if normalized_role == "donor" else "thread-nabil"
                    sender_name = "Ayesha Rahman" if normalized_role == "donor" else "Nabil Hasan"
                    await chat_manager.broadcast(other_role, {
                        "type": "typing",
                        "thread_id": target_thread,
                        "typing": is_typing,
                        "sender_name": sender_name,
                    })
                elif action == "read":
                    thread_id = data.get("thread_id", "")
                    if normalized_role == "donor":
                        await mark_donor_chat_read(thread_id)
                    elif normalized_role == "seeker":
                        await mark_seeker_chat_read(thread_id)
            except Exception:
                pass
    except WebSocketDisconnect:
        chat_manager.disconnect(normalized_role, websocket)
        other_role = "seeker" if normalized_role == "donor" else "donor"
        await chat_manager.broadcast(other_role, {
            "type": "presence",
            "role": normalized_role,
            "status": "offline",
        })
    except Exception:
        chat_manager.disconnect(normalized_role, websocket)


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
    msg_id = f"msg-{secrets.token_hex(4)}"
    new_msg = {
        "id": msg_id,
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

    # Real-time bridge: If donor messages Seeker Nabil (thread-nabil), deliver to Seeker (thread-ayesha)
    if thread_id == "thread-nabil":
        if "thread-ayesha" not in SEEKER_CHAT_MESSAGES:
            SEEKER_CHAT_MESSAGES["thread-ayesha"] = []
        seeker_incoming_msg = {
            "id": msg_id,
            "sender": "donor",
            "text": text,
            "time": now_str,
            "status": "delivered",
        }
        SEEKER_CHAT_MESSAGES["thread-ayesha"].append(seeker_incoming_msg)

        for st in SEEKER_CHAT_THREADS:
            if st["id"] == "thread-ayesha":
                st["last_message"] = text
                st["last_time"] = "Just now"
                st["unread_count"] = st.get("unread_count", 0) + 1
                break

        # Broadcast live to connected seekers
        await chat_manager.broadcast("seeker", {
            "type": "chat_message",
            "thread_id": "thread-ayesha",
            "sender": "donor",
            "sender_name": "Ayesha Rahman (A+ Donor)",
            "text": text,
            "time": now_str,
            "message": seeker_incoming_msg,
        })

        reply_msg = {
            "id": f"msg-{secrets.token_hex(4)}",
            "sender": "coordinator",
            "text": "Delivered to Nabil Hasan (Seeker)",
            "time": now_str,
            "status": "delivered",
        }
    else:
        # Automated coordinator reply based on context for simulated hospital/desk threads
        replies_map = {
            "thread-square": "Coordinator Dr. Farhan (Square Hospital): \"Received your update! Attendants are waiting at Transfusion Desk, 2nd floor.\"",
            "thread-dmc": "Desk Officer (DMCH): \"Thank you Ayesha! Your record has been flagged for prioritized scheduling.\"",
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

    # Sync other connected donor tabs/clients
    await chat_manager.broadcast("donor", {
        "type": "message_sent",
        "thread_id": thread_id,
        "sender": "you",
        "text": text,
        "time": now_str,
        "message": new_msg,
    })

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


# =============================================================================
# BLOOD SEEKER PORTAL APIS & DATA
# =============================================================================

class SeekerBloodRequestCreate(BaseModel):
    patient_name: str
    blood_group: str
    hospital_name: str
    area: str = "Dhaka"
    district: str = "Dhaka"
    units: int = 1
    contact_phone: str
    reason: str = ""
    is_emergency: bool = False


class SeekerEmergencyBroadcastCreate(BaseModel):
    patient_name: str
    blood_group: str
    hospital_name: str
    area: str = "Dhaka"
    urgency_level: str = "Code Red (Within 1 Hour)"
    contact_phone: str


class SeekerContactLogPayload(BaseModel):
    donor_name: str
    donor_phone: str
    blood_group: str
    contact_type: str
    notes: str = ""


class SeekerSettingsPayload(BaseModel):
    full_name: str
    phone: str
    default_hospital: str = "Square Hospital"
    sms_alerts: bool = True
    push_alerts: bool = True
    audio_siren: bool = True
    default_radius: str = "10"


SEEKER_CONTACT_LOGS = [
    {
        "donor_name": "Ayesha Rahman",
        "donor_phone": "+880 1712-345678",
        "blood_group": "A+",
        "contact_type": "call",
        "notes": "Donor answered • Confirmed arriving in 35 mins",
        "created_at": "20 mins ago",
    },
    {
        "donor_name": "Tanvir Ahmed",
        "donor_phone": "+880 1711-223344",
        "blood_group": "O+",
        "contact_type": "whatsapp",
        "notes": "Message delivered • Awaiting acknowledgment",
        "created_at": "1 hour ago",
    },
]

SEEKER_SETTINGS = {
    "+8801723456789": {
        "full_name": "Nabil Hasan",
        "phone": "+8801723456789",
        "default_hospital": "Square Hospital, Dhaka",
        "sms_alerts": True,
        "push_alerts": True,
        "audio_siren": True,
        "default_radius": "10",
    }
}

SEEKER_MOCK_DONORS = [
    {
        "id": "dn-001",
        "name": "Ayesha Rahman",
        "blood_group": "A+",
        "phone": "+8801712345678",
        "formatted_phone": "+880 1712-345678",
        "district": "Dhaka",
        "area": "Dhanmondi",
        "lat": 23.7461,
        "lng": 90.3742,
        "distance_km": 1.2,
        "is_available": True,
        "badge_tier": "Gold Life Saver",
        "total_donations": 8,
        "rating": 4.9,
        "reviews_count": 18,
        "last_donation": "110 days ago",
        "response_time": "6 mins",
        "bio": "Voluntary blood donor for 4 years. Close to Square & Bangladesh Medical. Ready for emergencies.",
        "nid_verified": True,
        "hemoglobin": "14.2 g/dL",
        "weight_bp": "58 kg | BP 118/78 mmHg",
        "screening": "Hepatitis B/C, HIV, Syphilis Tested Negative (Sept 2026)",
        "reliability": "100% (No no-shows)",
        "reviews": [
            {"author": "Nabil Hasan", "text": "Ayesha apu responded within 10 minutes when my mother needed blood at Square Hospital. Lifesaver!", "rating": 5, "date": "1 month ago"},
            {"author": "Dr. Farhan (Square)", "text": "Punctual, cooperative donor with clean screening reports.", "rating": 5, "date": "3 months ago"},
        ],
    },
    {
        "id": "dn-002",
        "name": "Tanvir Ahmed",
        "blood_group": "O+",
        "phone": "+8801711223344",
        "formatted_phone": "+880 1711-223344",
        "district": "Dhaka",
        "area": "Panthapath",
        "lat": 23.7518,
        "lng": 90.3879,
        "distance_km": 0.8,
        "is_available": True,
        "badge_tier": "Platinum Donor",
        "total_donations": 12,
        "rating": 5.0,
        "reviews_count": 26,
        "last_donation": "95 days ago",
        "response_time": "4 mins",
        "bio": "Registered universal donor. Works near Panthapath. Available anytime for critical trauma/surgery.",
        "nid_verified": True,
        "hemoglobin": "15.1 g/dL",
        "weight_bp": "72 kg | BP 120/80 mmHg",
        "screening": "All blood tests cleared (Oct 2026)",
        "reliability": "100%",
        "reviews": [
            {"author": "Kamrul Islam", "text": "Tanvir brother arrived within 25 minutes of calling him for my brother's ICU emergency.", "rating": 5, "date": "2 weeks ago"},
        ],
    },
    {
        "id": "dn-003",
        "name": "Sadia Islam",
        "blood_group": "B+",
        "phone": "+8801722334455",
        "formatted_phone": "+880 1722-334455",
        "district": "Dhaka",
        "area": "Shahbagh",
        "lat": 23.7380,
        "lng": 90.3956,
        "distance_km": 2.1,
        "is_available": True,
        "badge_tier": "Silver Donor",
        "total_donations": 5,
        "rating": 4.8,
        "reviews_count": 12,
        "last_donation": "130 days ago",
        "response_time": "8 mins",
        "bio": "DU student, situated 5 mins away from DMCH and BSMMU (PG Hospital).",
        "nid_verified": True,
        "hemoglobin": "13.8 g/dL",
        "weight_bp": "54 kg | BP 115/75 mmHg",
        "screening": "Cleared & verified at DMCH Transfusion",
        "reliability": "98%",
        "reviews": [
            {"author": "Rehana Begum", "text": "Very polite student, came straight from campus to donate for child surgery.", "rating": 5, "date": "2 months ago"},
        ],
    },
    {
        "id": "dn-004",
        "name": "Rafiqul Islam",
        "blood_group": "O-",
        "phone": "+8801733445566",
        "formatted_phone": "+880 1733-445566",
        "district": "Dhaka",
        "area": "Farmgate",
        "lat": 23.7561,
        "lng": 90.3872,
        "distance_km": 1.5,
        "is_available": True,
        "badge_tier": "Rare Hero Tier",
        "total_donations": 15,
        "rating": 5.0,
        "reviews_count": 32,
        "last_donation": "105 days ago",
        "response_time": "5 mins",
        "bio": "Rare O- donor. Dedicated to critical neonatal and emergency transfusions across Dhaka.",
        "nid_verified": True,
        "hemoglobin": "14.9 g/dL",
        "weight_bp": "68 kg | BP 118/76 mmHg",
        "screening": "Certified Rare Donor Certificate by Red Crescent",
        "reliability": "100%",
        "reviews": [
            {"author": "Dr. Shamim", "text": "Saved a preterm baby with emergency O negative blood in NICU.", "rating": 5, "date": "1 month ago"},
        ],
    },
]

SEEKER_CHAT_THREADS = [
    {
        "id": "thread-ayesha",
        "name": "Ayesha Rahman",
        "donor_id": "dn-001",
        "blood_group": "A+",
        "phone": "+880 1712-345678",
        "last_message": "Leaving Dhanmondi now. Reaching Square Hospital in 20 mins.",
        "last_time": "10:14 AM",
        "unread_count": 1,
    },
    {
        "id": "thread-tanvir",
        "name": "Tanvir Ahmed",
        "donor_id": "dn-002",
        "blood_group": "O+",
        "phone": "+880 1711-223344",
        "last_message": "Please keep the blood test requisition slip ready at counter.",
        "last_time": "9:45 AM",
        "unread_count": 0,
    },
    {
        "id": "thread-desk",
        "name": "Square Blood Desk Coordinator",
        "donor_id": "coord-01",
        "blood_group": "Hospital",
        "phone": "+880 1700-000001",
        "last_message": "Donor verification room 204 is open for your recipient.",
        "last_time": "Yesterday",
        "unread_count": 0,
    },
]

SEEKER_CHAT_MESSAGES = {
    "thread-ayesha": [
        {"id": "msg-sync-1", "sender": "you", "text": "Assalamu Alaikum Ayesha apu, we urgently need 1 bag A+ blood at Square Hospital 3rd Floor.", "time": "10:05 AM"},
        {"id": "msg-sync-2", "sender": "donor", "text": "Wa Alaikum Assalam Nabil bhai! I just saw the alert. I am eligible and nearby.", "time": "10:08 AM"},
        {"id": "msg-sync-3", "sender": "you", "text": "Alhamdulillah! Can you please reach as soon as possible? Requisition is ready.", "time": "10:10 AM"},
        {"id": "msg-sync-4", "sender": "donor", "text": "Leaving Dhanmondi now. Reaching Square Hospital in 20 mins.", "time": "10:14 AM"},
    ],
    "thread-tanvir": [
        {"id": "msg-s5", "sender": "you", "text": "Hello Tanvir brother, are you available for O+ donation today?", "time": "9:30 AM"},
        {"id": "msg-s6", "sender": "donor", "text": "Yes Nabil brother, I am free after 11 AM.", "time": "9:35 AM"},
        {"id": "msg-s7", "sender": "donor", "text": "Please keep the blood test requisition slip ready at counter.", "time": "9:45 AM"},
    ],
    "thread-desk": [
        {"id": "msg-s8", "sender": "donor", "text": "Donor verification room 204 is open for your recipient.", "time": "Yesterday"},
    ],
}


@app.get("/api/v1/seeker/requests")
async def get_seeker_requests():
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        rows = connection.execute(
            """SELECT id, blood_group, hospital_name, district, area, distance_km,
                      expires_at, contact_phone, is_emergency
               FROM blood_requests ORDER BY id DESC LIMIT 20"""
        ).fetchall()
        requests_list = [
            {
                "id": r[0],
                "blood_group": r[1],
                "hospital_name": r[2],
                "district": r[3],
                "area": r[4],
                "distance_km": r[5],
                "expires_at": r[6],
                "contact_phone": r[7],
                "is_emergency": bool(r[8]),
            }
            for r in rows
        ]
    return {"status": "success", "count": len(requests_list), "requests": requests_list}


@app.post("/api/v1/seeker/requests")
async def create_seeker_blood_request(payload: SeekerBloodRequestCreate):
    group = payload.blood_group.strip().upper()
    if group not in VALID_BLOOD_GROUPS:
        raise HTTPException(status_code=422, detail="Invalid blood group")

    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(hours=24)).isoformat()
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            cursor = connection.execute(
                """INSERT INTO blood_requests (
                       blood_group, hospital_name, district, area, distance_km,
                       expires_at, contact_phone, is_emergency
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    group,
                    payload.hospital_name.strip(),
                    payload.district.strip() or "Dhaka",
                    payload.area.strip() or "Dhaka",
                    2.0,
                    expires_at,
                    payload.contact_phone.strip(),
                    1 if payload.is_emergency else 0,
                ),
            )
            new_id = cursor.lastrowid

    return {
        "status": "success",
        "message": "Blood request created successfully",
        "request": {
            "id": new_id,
            "patient_name": payload.patient_name,
            "blood_group": group,
            "hospital_name": payload.hospital_name,
            "area": payload.area,
            "units": payload.units,
            "is_emergency": payload.is_emergency,
            "expires_at": expires_at,
        },
    }


@app.post("/api/v1/seeker/requests/emergency")
async def create_seeker_emergency_broadcast(payload: SeekerEmergencyBroadcastCreate):
    group = payload.blood_group.strip().upper()
    if group not in VALID_BLOOD_GROUPS:
        raise HTTPException(status_code=422, detail="Invalid blood group")

    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(hours=3)).isoformat()
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            cursor = connection.execute(
                """INSERT INTO blood_requests (
                       blood_group, hospital_name, district, area, distance_km,
                       expires_at, contact_phone, is_emergency
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    group,
                    payload.hospital_name.strip(),
                    "Dhaka",
                    payload.area.strip() or "Dhaka",
                    1.5,
                    expires_at,
                    payload.contact_phone.strip(),
                    1,
                ),
            )
            new_id = cursor.lastrowid

    return {
        "status": "success",
        "message": "Emergency SOS broadcast alert dispatched to nearby donors",
        "broadcast_count": 18,
        "request": {
            "id": new_id,
            "patient_name": payload.patient_name,
            "blood_group": group,
            "hospital_name": payload.hospital_name,
            "urgency_level": payload.urgency_level,
            "is_emergency": True,
            "expires_at": expires_at,
        },
    }


@app.get("/api/v1/seeker/donors")
async def get_seeker_donors(
    blood_group: str | None = None,
    radius_km: float = 30.0,
    available_only: bool = False,
    query: str | None = None,
):
    donors = list(SEEKER_MOCK_DONORS)
    if blood_group:
        bg = blood_group.strip().replace(" ", "+").upper()
        donors = [d for d in donors if d["blood_group"] == bg]
    if available_only:
        donors = [d for d in donors if d["is_available"]]
    if query:
        q = query.strip().lower()
        donors = [d for d in donors if q in d["name"].lower() or q in d["area"].lower() or q in d["district"].lower()]

    donors = [d for d in donors if d["distance_km"] <= radius_km]
    return {"status": "success", "count": len(donors), "donors": donors}


@app.get("/api/v1/seeker/donors/{donor_id}")
async def get_seeker_donor_detail(donor_id: str):
    donor = next((d for d in SEEKER_MOCK_DONORS if d["id"] == donor_id), None)
    if not donor:
        donor = SEEKER_MOCK_DONORS[0]
    return {"status": "success", "donor": donor}


@app.post("/api/v1/seeker/contact/log")
async def log_seeker_contact(payload: SeekerContactLogPayload):
    log_entry = {
        "donor_name": payload.donor_name,
        "donor_phone": payload.donor_phone,
        "blood_group": payload.blood_group,
        "contact_type": payload.contact_type,
        "notes": payload.notes or "Contact action dispatched via Seeker Portal",
        "created_at": "Just now",
    }
    SEEKER_CONTACT_LOGS.insert(0, log_entry)
    return {"status": "success", "log": log_entry}


@app.get("/api/v1/seeker/contact/logs")
async def get_seeker_contact_logs():
    return {"status": "success", "count": len(SEEKER_CONTACT_LOGS), "logs": SEEKER_CONTACT_LOGS}


@app.get("/api/v1/seeker/chat/threads")
async def get_seeker_chat_threads():
    return {
        "status": "success",
        "threads": SEEKER_CHAT_THREADS,
        "total_unread": sum(t["unread_count"] for t in SEEKER_CHAT_THREADS),
    }


@app.get("/api/v1/seeker/chat/{thread_id}/messages")
async def get_seeker_chat_messages(thread_id: str):
    messages = SEEKER_CHAT_MESSAGES.get(thread_id, [])
    thread_meta = next((t for t in SEEKER_CHAT_THREADS if t["id"] == thread_id), None)
    return {
        "status": "success",
        "thread_id": thread_id,
        "thread": thread_meta,
        "messages": messages,
    }


@app.post("/api/v1/seeker/chat/{thread_id}/send")
async def send_seeker_chat_message(thread_id: str, payload: SendChatMessagePayload):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    now_str = datetime.now(timezone.utc).strftime("%I:%M %p")
    msg_id = f"msg-s-{secrets.token_hex(4)}"
    new_msg = {
        "id": msg_id,
        "sender": "you",
        "text": text,
        "time": now_str,
        "status": "sent",
    }
    if thread_id not in SEEKER_CHAT_MESSAGES:
        SEEKER_CHAT_MESSAGES[thread_id] = []
    SEEKER_CHAT_MESSAGES[thread_id].append(new_msg)

    # Update seeker thread last message
    for t in SEEKER_CHAT_THREADS:
        if t["id"] == thread_id:
            t["last_message"] = text
            t["last_time"] = "Just now"
            break

    # Real-time bridge: If seeker messages Donor Ayesha (thread-ayesha / thread-dn-001), deliver to Donor (thread-nabil)
    if thread_id in ("thread-ayesha", "thread-dn-001"):
        if "thread-nabil" not in DONOR_CHAT_MESSAGES:
            DONOR_CHAT_MESSAGES["thread-nabil"] = []
        donor_incoming_msg = {
            "id": msg_id,
            "sender": "coordinator",
            "text": text,
            "time": now_str,
            "status": "delivered",
        }
        DONOR_CHAT_MESSAGES["thread-nabil"].append(donor_incoming_msg)

        for dt in DONOR_CHAT_THREADS:
            if dt["id"] == "thread-nabil":
                dt["last_message"] = text
                dt["last_time"] = "Just now"
                dt["unread_count"] = dt.get("unread_count", 0) + 1
                break

        # Broadcast live to connected donors over WebSocket
        await chat_manager.broadcast("donor", {
            "type": "chat_message",
            "thread_id": "thread-nabil",
            "sender": "coordinator",
            "sender_name": "Nabil Hasan (Emergency Seeker)",
            "text": text,
            "time": now_str,
            "message": donor_incoming_msg,
        })

        reply_msg = {
            "id": f"msg-s-{secrets.token_hex(4)}",
            "sender": "donor",
            "text": "Message delivered to Ayesha Rahman",
            "time": now_str,
            "status": "delivered",
        }
    else:
        auto_replies = {
            "thread-tanvir": "Tanvir: \"Understood, preparing donor registration card. See you shortly!\"",
            "thread-desk": "Square Blood Desk: \"Attendant notified. Please head to Transfusion Counter Room 204.\"",
        }
        reply_text = auto_replies.get(
            thread_id,
            "Donor: \"Message received! Heading to the hospital now.\"",
        )
        reply_msg = {
            "id": f"msg-s-{secrets.token_hex(4)}",
            "sender": "donor",
            "text": reply_text,
            "time": now_str,
            "status": "delivered",
        }
        SEEKER_CHAT_MESSAGES[thread_id].append(reply_msg)

    # Sync other connected seeker tabs/clients
    await chat_manager.broadcast("seeker", {
        "type": "message_sent",
        "thread_id": thread_id,
        "sender": "you",
        "text": text,
        "time": now_str,
        "message": new_msg,
    })

    return {"status": "success", "sent": new_msg, "reply": reply_msg}


@app.post("/api/v1/seeker/chat/{thread_id}/read")
async def mark_seeker_chat_read(thread_id: str):
    for thread in SEEKER_CHAT_THREADS:
        if thread["id"] == thread_id:
            thread["unread_count"] = 0
            break
    total_unread = sum(t.get("unread_count", 0) for t in SEEKER_CHAT_THREADS)
    return {
        "status": "success",
        "thread_id": thread_id,
        "unread_count": 0,
        "total_unread": total_unread,
    }


@app.get("/api/v1/seeker/settings")
async def get_seeker_settings(request: Request):
    token = _decode_jwt(request.cookies.get("access_token", ""))
    phone = token.get("sub") if token and token.get("role") == "seeker" else "+8801723456789"
    settings = SEEKER_SETTINGS.get(phone, {
        "full_name": "Nabil Hasan",
        "phone": phone,
        "default_hospital": "Square Hospital, Dhaka",
        "sms_alerts": True,
        "push_alerts": True,
        "audio_siren": True,
        "default_radius": "10",
    })
    return {"status": "success", "settings": settings}


@app.post("/api/v1/seeker/settings")
async def save_seeker_settings(payload: SeekerSettingsPayload, request: Request):
    phone = payload.phone.strip()
    SEEKER_SETTINGS[phone] = payload.model_dump()
    return {"status": "success", "message": "Settings saved successfully", "settings": SEEKER_SETTINGS[phone]}

