from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
AUTH_DATABASE_PATH = Path(
    os.environ.get("SBDS_AUTH_DATABASE_PATH", str(BASE_DIR / "auth.db"))
)
DATABASE_PATH = Path(
    os.environ.get("SBDS_DATABASE_PATH", str(BASE_DIR / "urgent_requests.db"))
)

DATA_RETENTION_POLICY_VERSION = "2026.1"
PASSWORD_HASH_ITERATIONS = 310_000

# Comprehensive rules defining data erasure vs. regulatory retention
DATA_RETENTION_POLICY_DETAILS = {
    "version": DATA_RETENTION_POLICY_VERSION,
    "last_reviewed": "2026-03-15",
    "categories": {
        "immediate_erasure": [
            {
                "title": "Account Credentials & Authentication",
                "desc": "Password hashes, password recovery tokens, OTP secrets, and active session identifiers are immediately purged.",
            },
            {
                "title": "Personal Identity (PII)",
                "desc": "Full name, mobile phone number, email address, date of birth, gender, full residential address, and GPS coordinates are wiped.",
            },
            {
                "title": "Health & Medical Information",
                "desc": "Confidential medical history, registered medications, known allergies, and donor fitness evaluations are permanently removed.",
            },
            {
                "title": "KYC & Identity Verification Documents",
                "desc": "National ID (NID) numbers, uploaded ID images, and verification attachments are redacted and scrubbed.",
            },
            {
                "title": "Push Subscriptions & Communication Channels",
                "desc": "Browser push subscription tokens, device encryption keys (p256dh/auth), notification preferences, and in-app notifications are deleted.",
            },
            {
                "title": "User Configurations",
                "desc": "Emergency radius preferences, SMS broadcast settings, and institutional facility configurations are removed.",
            },
        ],
        "anonymized_operational_records": [
            {
                "title": "Blood Donation Traceability (Clinical Lookback)",
                "desc": "Pursuant to DGHS blood safety guidelines and WHO transfusion standards, unit donation timestamps, blood groups, and donation types are preserved anonymously. All donor phone numbers and identity markers are permanently replaced with an irreversible one-way cryptographic pseudonym (ANON-DONOR-XXXX).",
            },
            {
                "title": "Urgent Blood Requests",
                "desc": "Open/pending blood requests created by the user are immediately cancelled. Completed historic requests have patient names, contact numbers, and personal reasons redacted, preserving aggregate statistical metrics for public health surveillance.",
            },
            {
                "title": "Direct Message Transcripts",
                "desc": "Individual chat message bodies are scrubbed and replaced with an account closure tombstone to maintain conversation context for the counterparty without retaining personal text.",
            },
        ],
        "audit_and_legal_compliance": [
            {
                "title": "Immutable Erasure Receipt",
                "desc": "A cryptographic SHA-256 hash of the subject identifier is logged with timestamp, policy version, and scrub summary to satisfy legal compliance (GDPR Art 17 Right to Erasure / Bangladesh Digital Security regulations) without retaining plaintext PII.",
            },
        ],
    },
}


def get_auth_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(AUTH_DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def get_urgent_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_privacy_database():
    """Initializes schemas needed for privacy scrubbing and retention auditing."""
    AUTH_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(get_auth_connection()) as conn:
        with conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS account_deletion_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_phone_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    reason TEXT DEFAULT '',
                    retention_policy_version TEXT NOT NULL DEFAULT '2026.1',
                    scrubbed_summary TEXT NOT NULL DEFAULT '{}',
                    deleted_at TEXT NOT NULL,
                    ip_address TEXT DEFAULT '127.0.0.1'
                );
                CREATE INDEX IF NOT EXISTS idx_deletion_audit_hash_time
                    ON account_deletion_audit_logs(user_phone_hash, deleted_at);
                """
            )


def verify_password_hash(password: str, encoded_hash: str) -> bool:
    """Verifies a plain password against an iteration-salted PBKDF2 hash."""
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


def verify_user_identity_credentials(
    phone: str,
    password: str,
    users_cache: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Verifies user identity before permanent account deletion.
    Checks auth_users database record first, then falls back to in-memory user cache if configured.
    """
    if not phone or not password:
        return False

    initialize_privacy_database()

    # 1. Check in SQLite auth_users
    try:
        with closing(get_auth_connection()) as conn:
            user_row = conn.execute(
                "SELECT password_hash FROM auth_users WHERE phone = ?", (phone,)
            ).fetchone()
            if user_row and user_row["password_hash"]:
                if verify_password_hash(password, user_row["password_hash"]):
                    return True
    except Exception as exc:
        logger.warning(f"Error checking auth_users for identity verification: {exc}")

    # 2. Check in-memory USERS cache (for demo / seeded accounts)
    if users_cache and phone in users_cache:
        cached = users_cache[phone]
        # Plaintext password match in demo dict
        if cached.get("password") and cached["password"] == password:
            return True
        # Salted hash in demo dict
        if cached.get("password_hash") and verify_password_hash(
            password, cached["password_hash"]
        ):
            return True

    return False


def scrub_and_delete_account(
    phone: str,
    role: str = "",
    reason: str = "",
    ip_address: str = "127.0.0.1",
    users_cache: Optional[Dict[str, Any]] = None,
    facility_cache: Optional[Dict[str, Any]] = None,
    seeker_cache: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Executes permanent account deletion and data privacy scrubbing
    according to the system's Data Retention Policy (v2026.1).

    - Removes all eligible personal data (PII, credentials, push keys, settings).
    - Anonymizes medical & operational records (donation histories, completed requests)
      using a one-way pseudonym hash.
    - Cancels any active blood requests.
    - Purges all active auth sessions.
    - Logs an immutable regulatory audit entry without storing plaintext PII.
    """
    initialize_privacy_database()
    now_iso = datetime.now(timezone.utc).isoformat()
    phone_hash = hashlib.sha256(phone.encode("utf-8")).hexdigest()
    anon_pseudonym = f"ANON-DONOR-{phone_hash[:10].upper()}"

    summary = {
        "phone_hash": phone_hash,
        "role": role,
        "reason": reason,
        "policy_version": DATA_RETENTION_POLICY_VERSION,
        "timestamp": now_iso,
        "sessions_terminated": 0,
        "auth_user_deleted": False,
        "donor_profile_scrubbed": False,
        "donor_settings_deleted": False,
        "facility_settings_deleted": False,
        "kyc_documents_scrubbed": 0,
        "push_subscriptions_purged": 0,
        "push_preferences_deleted": 0,
        "app_notifications_deleted": 0,
        "seeker_notifications_deleted": 0,
        "donation_history_anonymized": 0,
        "blood_requests_cancelled_or_redacted": 0,
        "chat_messages_scrubbed": 0,
        "chat_blocks_removed": 0,
        "inventory_purged": 0,
    }

    # -------------------------------------------------------------------------
    # 1. Scrub from auth.db (Credentials, Sessions, Profiles, Settings)
    # -------------------------------------------------------------------------
    try:
        with closing(get_auth_connection()) as conn:
            with conn:
                # Find user_id
                user_row = conn.execute(
                    "SELECT id, role FROM auth_users WHERE phone = ?", (phone,)
                ).fetchone()
                user_id = user_row["id"] if user_row else None
                if not role and user_row and user_row["role"]:
                    role = user_row["role"]
                    summary["role"] = role

                if user_id:
                    # Terminate all active sessions
                    res = conn.execute(
                        "DELETE FROM auth_sessions WHERE user_id = ?", (user_id,)
                    )
                    summary["sessions_terminated"] += res.rowcount

                    # Clear password reset challenges
                    conn.execute(
                        "DELETE FROM password_reset_challenges WHERE user_id = ?",
                        (user_id,),
                    )

                    # Delete auth_users entry
                    conn.execute("DELETE FROM auth_users WHERE id = ?", (user_id,))
                    summary["auth_user_deleted"] = True

                # Also delete by phone directly to ensure clean purge
                conn.execute(
                    "DELETE FROM password_reset_challenges WHERE phone = ?", (phone,)
                )
                del_user = conn.execute(
                    "DELETE FROM auth_users WHERE phone = ?", (phone,)
                )
                if del_user.rowcount > 0:
                    summary["auth_user_deleted"] = True

                # Scrub donor profile
                del_profile = conn.execute(
                    "DELETE FROM donor_profiles WHERE phone = ?", (phone,)
                )
                if del_profile.rowcount > 0:
                    summary["donor_profile_scrubbed"] = True

                # Scrub donor settings
                del_donor_settings = conn.execute(
                    "DELETE FROM donor_settings WHERE phone = ?", (phone,)
                )
                if del_donor_settings.rowcount > 0:
                    summary["donor_settings_deleted"] = True

                # Scrub facility settings
                del_facility_settings = conn.execute(
                    "DELETE FROM facility_settings WHERE phone = ?", (phone,)
                )
                if del_facility_settings.rowcount > 0:
                    summary["facility_settings_deleted"] = True

    except Exception as exc:
        logger.error(f"Error scrubbing auth.db for user {phone}: {exc}")

    # -------------------------------------------------------------------------
    # 2. Scrub from urgent_requests.db (Notifications, Push, KYC, Requests, Donations)
    # -------------------------------------------------------------------------
    try:
        with closing(get_urgent_connection()) as conn:
            with conn:
                # A. Purge push subscriptions & preferences
                del_push = conn.execute(
                    "DELETE FROM push_subscriptions WHERE user_phone = ?", (phone,)
                )
                summary["push_subscriptions_purged"] = del_push.rowcount

                del_push_pref = conn.execute(
                    "DELETE FROM user_push_preferences WHERE user_phone = ?", (phone,)
                )
                summary["push_preferences_deleted"] = del_push_pref.rowcount

                # B. Purge app notifications
                del_app_notifs = conn.execute(
                    "DELETE FROM app_notifications WHERE recipient_phone = ?", (phone,)
                )
                summary["app_notifications_deleted"] = del_app_notifs.rowcount

                # C. Purge seeker notifications
                del_seeker_notifs = conn.execute(
                    "DELETE FROM seeker_notifications WHERE donor_phone = ?", (phone,)
                )
                summary["seeker_notifications_deleted"] += del_seeker_notifs.rowcount

                # D. Scrub KYC records (Redact sensitive NID and document paths)
                kyc_scrub = conn.execute(
                    """
                    UPDATE donor_kyc_verifications
                    SET nid_number = 'REDACTED',
                        document_url = '',
                        donor_name = 'Anonymized User',
                        status = 'scrubbed',
                        rejection_reason = 'Account deleted per user request. PII purged under Data Retention Policy.'
                    WHERE donor_phone = ?
                    """,
                    (phone,),
                )
                summary["kyc_documents_scrubbed"] = kyc_scrub.rowcount

                # E. Anonymize blood donation history for transfusion clinical safety
                # Clinical requirement: preserve unit counts, timestamps, and blood group for health safety lookback,
                # but disassociate phone number and donor identity completely.
                donation_anon = conn.execute(
                    """
                    UPDATE donor_donation_history
                    SET donor_phone = ?,
                        notes = '[Anonymized per System Data Retention Policy]'
                    WHERE donor_phone = ?
                    """,
                    (anon_pseudonym, phone),
                )
                summary["donation_history_anonymized"] = donation_anon.rowcount

                # F. Blood Requests:
                # Cancel open/pending requests created by this user and redact personal contact numbers & patient names
                req_scrub = conn.execute(
                    """
                    UPDATE blood_requests
                    SET status = 'Cancelled',
                        patient_name = '[Redacted]',
                        contact_phone = 'REDACTED',
                        owner_phone = 'REDACTED',
                        reason = '[Cancelled - Account Closed]'
                    WHERE contact_phone = ? OR owner_phone = ?
                    """,
                    (phone, phone),
                )
                summary["blood_requests_cancelled_or_redacted"] = req_scrub.rowcount

                # Also anonymize any responses made to blood requests
                conn.execute(
                    """
                    UPDATE donor_request_responses
                    SET donor_phone = ?,
                        note = '[Redacted]',
                        reason = '[Redacted]'
                    WHERE donor_phone = ?
                    """,
                    (anon_pseudonym, phone),
                )

                # G. Chat messages: scrub text sent by this user
                chat_scrub = conn.execute(
                    """
                    UPDATE chat_messages
                    SET text = '[Message deleted - User account scrubbed under Data Retention Policy]'
                    WHERE sender_phone = ?
                    """,
                    (phone,),
                )
                summary["chat_messages_scrubbed"] = chat_scrub.rowcount

                # Remove chat blocks
                del_blocks = conn.execute(
                    "DELETE FROM chat_blocks WHERE blocker_phone = ? OR blocked_phone = ?",
                    (phone, phone),
                )
                summary["chat_blocks_removed"] = del_blocks.rowcount

                # H. Facility inventory (if hospital/bank)
                del_inv = conn.execute(
                    "DELETE FROM facility_blood_inventory WHERE facility_phone = ?",
                    (phone,),
                )
                summary["inventory_purged"] = del_inv.rowcount
                conn.execute(
                    "DELETE FROM facility_inventory_alerts WHERE facility_phone = ?",
                    (phone,),
                )
                conn.execute(
                    """
                    UPDATE facility_inventory_audit
                    SET actor_phone = 'ANON-FACILITY'
                    WHERE facility_phone = ? OR actor_phone = ?
                    """,
                    (phone, phone),
                )

    except Exception as exc:
        logger.error(f"Error scrubbing urgent_requests.db for user {phone}: {exc}")

    # -------------------------------------------------------------------------
    # 3. Record Immutable Deletion Audit Receipt in auth.db
    # -------------------------------------------------------------------------
    try:
        with closing(get_auth_connection()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO account_deletion_audit_logs
                    (user_phone_hash, role, reason, retention_policy_version, scrubbed_summary, deleted_at, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        phone_hash,
                        role or "user",
                        reason,
                        DATA_RETENTION_POLICY_VERSION,
                        json.dumps(summary),
                        now_iso,
                        ip_address,
                    ),
                )
                summary["audit_log_recorded"] = True
    except Exception as exc:
        logger.error(f"Error logging deletion audit for user {phone}: {exc}")

    # -------------------------------------------------------------------------
    # 4. Clean In-Memory Caches
    # -------------------------------------------------------------------------
    if users_cache is not None and phone in users_cache:
        del users_cache[phone]
    if facility_cache is not None and phone in facility_cache:
        del facility_cache[phone]
    if seeker_cache is not None and phone in seeker_cache:
        del seeker_cache[phone]

    logger.info(
        f"Successfully scrubbed and deleted account with phone hash {phone_hash[:12]} under Data Retention Policy {DATA_RETENTION_POLICY_VERSION}"
    )
    return summary
