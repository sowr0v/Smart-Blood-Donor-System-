"""
Database abstraction layer for Smart Blood Donor System (SBDS).
Supports both Online PostgreSQL and local SQLite (for local testing/fallback).
"""

from __future__ import annotations

import os
import re
import sys
import sqlite3
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Automatically load .env from project root
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL")

TABLES_WITH_ID = {
    "auth_users",
    "auth_sessions",
    "password_reset_challenges",
    "blood_requests",
    "donor_request_responses",
    "seeker_notifications",
    "donor_donation_history",
    "chat_reports",
    "facility_inventory_audit",
    "facility_inventory_alerts",
    "donor_kyc_verifications",
    "hospital_blood_inventory",
    "user_moderation_reports",
    "user_reviews",
    "app_notifications",
    "push_subscriptions",
    "push_dispatch_logs",
    "sms_dispatch_logs",
    "request_moderation_logs",
    "admin_settings",
    "admin_audit_logs",
    "account_phone_update_challenges",
    "contact_messages",
}


def is_postgres(db_path: Optional[Any] = None) -> bool:
    """
    Determines whether queries should route to PostgreSQL or SQLite.
    Returns False when running in tests with temporary SQLite databases.
    """
    if os.environ.get("SBDS_USE_SQLITE") == "1":
        return False

    # If running under unittest and not explicitly forced to Postgres, use SQLite
    if "unittest" in sys.modules and os.environ.get("SBDS_FORCE_POSTGRES") != "1":
        return False

    if db_path is not None:
        path_str = str(db_path).lower()
        if "temp" in path_str or "tmp" in path_str:
            return False

    url = os.environ.get("DATABASE_URL")
    return bool(url and (url.startswith("postgresql://") or url.startswith("postgres://")))


def translate_sql(sql: str, for_executemany: bool = False) -> tuple[str, bool]:
    """
    Translates SQLite query syntax to PostgreSQL syntax:
    - Replaces parameter placeholders '?' with '%s' (outside string literals).
    - Converts 'INSERT OR IGNORE INTO ...' to 'INSERT INTO ... ON CONFLICT DO NOTHING'.
    - Converts 'INSERT OR REPLACE INTO ...' to upsert 'ON CONFLICT (...) DO UPDATE SET ...'.
    - Intercepts 'PRAGMA table_info(table)' and queries information_schema.
    - Appends 'RETURNING id' for single INSERTs on tables with auto-increment ID.
    - Handles 'BEGIN' / 'BEGIN IMMEDIATE' as no-ops (psycopg2 manages transactions).
    """
    sql_stripped = sql.strip()
    append_returning = False

    # 1. No-op transactions and pragmas, and translate SQLite AUTOINCREMENT
    sql_stripped = re.sub(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", "SERIAL PRIMARY KEY", sql_stripped, flags=re.IGNORECASE)
    sql_stripped = re.sub(r"\bAUTOINCREMENT\b", "", sql_stripped, flags=re.IGNORECASE)

    if re.match(r"^BEGIN(?:\s+IMMEDIATE)?\s*;?$", sql_stripped, re.IGNORECASE):
        return "-- NO-OP BEGIN", False

    if re.match(r"^PRAGMA\s+foreign_keys", sql_stripped, re.IGNORECASE):
        return "-- NO-OP PRAGMA foreign_keys", False

    # 2. PRAGMA table_info(table_name)
    pragma_match = re.match(
        r"^PRAGMA\s+table_info\s*\(\s*['\"]?(\w+)['\"]?\s*\)",
        sql_stripped,
        re.IGNORECASE,
    )
    if pragma_match:
        t_name = pragma_match.group(1).lower()
        translated_pragma = f"""
            SELECT 
                ordinal_position - 1 AS cid,
                column_name AS name,
                data_type AS type,
                CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull,
                column_default AS dflt_value,
                0 AS pk
            FROM information_schema.columns
            WHERE table_schema = 'public' AND lower(table_name) = '{t_name}'
            ORDER BY ordinal_position
        """
        return translated_pragma, False

    # 3. INSERT OR IGNORE INTO table ...
    match_ignore = re.match(
        r"^INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)([\s\S]+)$",
        sql_stripped,
        re.IGNORECASE,
    )
    if match_ignore:
        table_name = match_ignore.group(1)
        rest = match_ignore.group(2).rstrip("; \t\n")
        sql_stripped = f"INSERT INTO {table_name}{rest} ON CONFLICT DO NOTHING"

    # 4. INSERT OR REPLACE INTO table (cols) VALUES (vals)
    match_replace = re.match(
        r"^INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)$",
        sql_stripped,
        re.IGNORECASE,
    )
    if match_replace:
        table_name = match_replace.group(1)
        cols = [c.strip() for c in match_replace.group(2).split(",")]
        vals = match_replace.group(3)
        pk_col = cols[0]
        update_cols = [f"{c} = EXCLUDED.{c}" for c in cols[1:]]
        update_str = ", ".join(update_cols)
        sql_stripped = (
            f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({vals}) "
            f"ON CONFLICT ({pk_col}) DO UPDATE SET {update_str}"
        )

    # 5. Check if single INSERT into table with auto-id should return id
    if not for_executemany:
        match_insert = re.match(r"^INSERT\s+INTO\s+(\w+)", sql_stripped, re.IGNORECASE)
        if match_insert:
            t_name = match_insert.group(1).lower()
            if t_name in TABLES_WITH_ID and "RETURNING" not in sql_stripped.upper():
                sql_stripped = sql_stripped.rstrip("; \t\n") + " RETURNING id"
                append_returning = True

    # 6. Replace '?' with '%s' outside single-quoted strings and escape literal '%'
    parts = re.split(r"('(?:''|[^'])*')", sql_stripped)
    for i in range(0, len(parts), 2):
        parts[i] = parts[i].replace("%", "%%").replace("?", "%s")
    for i in range(1, len(parts), 2):
        parts[i] = parts[i].replace("%", "%%")
    final_sql = "".join(parts)

    return final_sql, append_returning


class PostgresCursorWrapper:
    """Wrapper around psycopg2 DictCursor providing an interface matching sqlite3.Cursor."""

    def __init__(self, raw_cursor: psycopg2.extensions.cursor):
        self._raw_cursor = raw_cursor
        self.lastrowid: Optional[int] = None

    def execute(self, sql: str, params: Any = None) -> PostgresCursorWrapper:
        translated, will_return = translate_sql(sql, for_executemany=False)
        if translated.startswith("-- NO-OP"):
            return self

        try:
            self._raw_cursor.execute(translated, params or ())
        except psycopg2.IntegrityError as exc:
            raise sqlite3.IntegrityError(str(exc)) from exc
        except psycopg2.OperationalError as exc:
            raise sqlite3.OperationalError(str(exc)) from exc

        if will_return:
            try:
                row = self._raw_cursor.fetchone()
                self.lastrowid = row[0] if row else None
            except Exception:
                self.lastrowid = None
        else:
            self.lastrowid = None

        return self

    def executemany(self, sql: str, seq_of_params: Any) -> PostgresCursorWrapper:
        translated, _ = translate_sql(sql, for_executemany=True)
        if translated.startswith("-- NO-OP"):
            return self

        try:
            self._raw_cursor.executemany(translated, seq_of_params)
        except psycopg2.IntegrityError as exc:
            raise sqlite3.IntegrityError(str(exc)) from exc
        except psycopg2.OperationalError as exc:
            raise sqlite3.OperationalError(str(exc)) from exc

        self.lastrowid = None
        return self

    def fetchone(self) -> Any:
        return self._raw_cursor.fetchone()

    def fetchall(self) -> list[Any]:
        return self._raw_cursor.fetchall()

    def fetchmany(self, size: Optional[int] = None) -> list[Any]:
        if size is not None:
            return self._raw_cursor.fetchmany(size)
        return self._raw_cursor.fetchmany()

    @property
    def description(self) -> Any:
        return self._raw_cursor.description

    @property
    def rowcount(self) -> int:
        return self._raw_cursor.rowcount

    def close(self) -> None:
        self._raw_cursor.close()

    def __iter__(self):
        return iter(self._raw_cursor)

    def __enter__(self) -> PostgresCursorWrapper:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class PostgresConnectionWrapper:
    """Wrapper around psycopg2 Connection providing an interface matching sqlite3.Connection."""

    def __init__(self, raw_conn: psycopg2.extensions.connection):
        self._raw_conn = raw_conn
        self._row_factory = None

    @property
    def row_factory(self) -> Any:
        return self._row_factory

    @row_factory.setter
    def row_factory(self, val: Any) -> None:
        self._row_factory = val

    def cursor(self) -> PostgresCursorWrapper:
        raw_cur = self._raw_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return PostgresCursorWrapper(raw_cur)

    def execute(self, sql: str, params: Any = None) -> PostgresCursorWrapper:
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, seq_of_params: Any) -> PostgresCursorWrapper:
        cur = self.cursor()
        cur.executemany(sql, seq_of_params)
        return cur

    def executescript(self, script: str) -> PostgresConnectionWrapper:
        statements = script.split(";")
        for stmt in statements:
            s = stmt.strip()
            if s:
                self.execute(s)
        return self

    def commit(self) -> None:
        self._raw_conn.commit()

    def rollback(self) -> None:
        self._raw_conn.rollback()

    def close(self) -> None:
        self._raw_conn.close()

    def __enter__(self) -> PostgresConnectionWrapper:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()


_orig_sqlite3_connect = sqlite3.connect

def connect(database: Optional[Any] = None, *args: Any, **kwargs: Any) -> Any:
    """
    Connect to database.
    If PostgreSQL is enabled, connects to PostgreSQL database.
    Otherwise, connects to SQLite using standard sqlite3.connect().
    """
    if is_postgres(database):
        url = os.environ.get("DATABASE_URL")
        raw_conn = psycopg2.connect(url)
        return PostgresConnectionWrapper(raw_conn)

    # Fallback to local SQLite
    target = database or str(ROOT_DIR / "urgent_requests.db")
    if "timeout" not in kwargs:
        kwargs["timeout"] = 10
    return _orig_sqlite3_connect(target, *args, **kwargs)

# Monkey-patch sqlite3.connect so all database access across the app uses connect()
sqlite3.connect = connect
