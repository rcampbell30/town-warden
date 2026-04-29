"""Database persistence for Town Warden.

SQLite remains the local/default backend. PostgreSQL is enabled only when
DATABASE_URL starts with postgres/postgresql, which keeps local development and
tests simple while allowing Render Postgres in production.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta

from config import DATABASE_URL


DB_NAME = os.getenv("TOWN_WARDEN_DB", "town_warden.db")


def database_backend():
    return "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite"


def placeholder():
    return "%s" if database_backend() == "postgres" else "?"


def connect():
    if database_backend() == "postgres":
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "DATABASE_URL is set to PostgreSQL but psycopg is not installed. "
                "Install backend requirements before starting the app."
            ) from exc

        return psycopg.connect(DATABASE_URL)

    return sqlite3.connect(DB_NAME)


def setup_database():
    conn = connect()
    cursor = conn.cursor()

    if database_backend() == "postgres":
        setup_postgres(cursor)
    else:
        setup_sqlite(cursor)

    conn.commit()
    conn.close()


def setup_sqlite(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            type TEXT,
            location TEXT,
            text TEXT,
            source TEXT,
            source_event_id TEXT,
            real_data INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            agent TEXT,
            type TEXT,
            location TEXT,
            message TEXT,
            severity TEXT,
            data TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            risk_map TEXT
        )
    """)

    migrate_sqlite(cursor)


def setup_postgres(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            timestamp TEXT,
            type TEXT,
            location TEXT,
            text TEXT,
            source TEXT,
            source_event_id TEXT,
            real_data INTEGER,
            metadata TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            timestamp TEXT,
            agent TEXT,
            type TEXT,
            location TEXT,
            message TEXT,
            severity TEXT,
            data TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_snapshots (
            id SERIAL PRIMARY KEY,
            timestamp TEXT,
            risk_map TEXT
        )
    """)

    cursor.execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS source_event_id TEXT")
    cursor.execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS metadata TEXT")
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_events_source_event_id
        ON events(source_event_id)
    """)


def migrate_sqlite(cursor):
    cursor.execute("PRAGMA table_info(events)")
    columns = [column[1] for column in cursor.fetchall()]

    if "source_event_id" not in columns:
        cursor.execute("""
            ALTER TABLE events
            ADD COLUMN source_event_id TEXT
        """)

    if "metadata" not in columns:
        cursor.execute("""
            ALTER TABLE events
            ADD COLUMN metadata TEXT
        """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_events_source_event_id
        ON events(source_event_id)
    """)


def is_unique_violation(exc):
    if isinstance(exc, sqlite3.IntegrityError):
        return True

    if database_backend() == "postgres":
        try:
            import psycopg
        except ImportError:
            return False

        return isinstance(exc, psycopg.errors.UniqueViolation)

    return False


def event_exists(source_event_id):
    if not source_event_id:
        return False

    conn = connect()
    cursor = conn.cursor()
    ph = placeholder()

    cursor.execute(f"""
        SELECT 1
        FROM events
        WHERE source_event_id = {ph}
        LIMIT 1
    """, (source_event_id,))

    result = cursor.fetchone()
    conn.close()
    return result is not None


def save_event(event):
    conn = connect()
    cursor = conn.cursor()
    ph = placeholder()

    try:
        cursor.execute(f"""
            INSERT INTO events (
                timestamp,
                type,
                location,
                text,
                source,
                source_event_id,
                real_data,
                metadata
            )
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (
            event.get("timestamp", datetime.now().isoformat()),
            event.get("type"),
            event.get("location"),
            event.get("text"),
            event.get("source", "unknown"),
            event.get("source_event_id"),
            1 if event.get("real_data") else 0,
            json.dumps(event.get("metadata") or {}),
        ))
        conn.commit()
        return True

    except Exception as exc:
        conn.rollback()
        if is_unique_violation(exc):
            return False
        raise

    finally:
        conn.close()


def save_alert(alert):
    conn = connect()
    cursor = conn.cursor()
    ph = placeholder()

    cursor.execute(f"""
        INSERT INTO alerts (timestamp, agent, type, location, message, severity, data)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (
        datetime.now().isoformat(),
        alert.get("agent"),
        alert.get("type"),
        alert.get("location"),
        alert.get("message"),
        alert.get("severity"),
        json.dumps(alert),
    ))

    conn.commit()
    conn.close()


def save_risk_snapshot(risk_map):
    conn = connect()
    cursor = conn.cursor()
    ph = placeholder()

    cursor.execute(f"""
        INSERT INTO risk_snapshots (timestamp, risk_map)
        VALUES ({ph}, {ph})
    """, (
        datetime.now().isoformat(),
        json.dumps(risk_map),
    ))

    conn.commit()
    conn.close()


def clear_database():
    """Clear local development/test data without deleting the database file."""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM risk_snapshots")
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM events")

    conn.commit()
    conn.close()


def cleanup_old_records(event_retention_days=90, alert_retention_days=90, risk_snapshot_retention_days=30):
    """Delete old persisted rows using ISO timestamp strings."""
    conn = connect()
    cursor = conn.cursor()
    ph = placeholder()
    now = datetime.now()
    deleted = {}

    retention_plan = {
        "events": event_retention_days,
        "alerts": alert_retention_days,
        "risk_snapshots": risk_snapshot_retention_days,
    }

    for table, days in retention_plan.items():
        if days is None or int(days) <= 0:
            deleted[table] = 0
            continue

        cutoff = (now - timedelta(days=int(days))).isoformat()
        cursor.execute(f"DELETE FROM {table} WHERE timestamp < {ph}", (cutoff,))
        deleted[table] = max(cursor.rowcount or 0, 0)

    conn.commit()
    conn.close()
    return deleted
