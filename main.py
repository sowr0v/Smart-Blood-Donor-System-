import base64
import hashlib
import hmac
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
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import HTTPException, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)
AUTH_DATABASE_PATH = Path(
    os.environ.get("SBDS_AUTH_DATABASE_PATH", str(Path(__file__).resolve().with_name("auth.db")))
)
SESSION_COOKIE = "sbds_session"
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
OTP_TTL_SECONDS = 10 * 60
RESET_TOKEN_TTL_SECONDS = 10 * 60
OTP_RESEND_SECONDS = 60
OTP_MAX_ATTEMPTS = 5
PASSWORD_HASH_ITERATIONS = 310_000
OTP_HASH_ITERATIONS = 120_000


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_auth_database()
    yield


app = FastAPI(title="Smart Blood Donor System", lifespan=lifespan)

# Mount Static and Templates folder
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


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
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request},
    )


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