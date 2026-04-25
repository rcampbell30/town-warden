"""SQLite persistence for Town Warden."""

import json
import sqlite3
from datetime import datetime

DB_NAME = "town_warden.db"


def connect():
    return sqlite3.connect(DB_NAME)


def setup_database():
    conn = connect()
    cursor = conn.cursor()

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

    migrate_database(cursor)

    conn.commit()
    conn.close()


def migrate_database(cursor):
    cursor.execute("PRAGMA table_info(events)")
    columns = [column[1] for column in cursor.fetchall()]

    if "source_event_id" not in columns:
        cursor.execute("""
            ALTER TABLE events
            ADD COLUMN source_event_id TEXT
        """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_events_source_event_id
        ON events(source_event_id)
    """)


def event_exists(source_event_id):
    if not source_event_id:
        return False

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1
        FROM events
        WHERE source_event_id = ?
        LIMIT 1
    """, (source_event_id,))

    result = cursor.fetchone()
    conn.close()
    return result is not None


def save_event(event):
    conn = connect()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO events (
                timestamp,
                type,
                location,
                text,
                source,
                source_event_id,
                real_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get("timestamp", datetime.now().isoformat()),
            event.get("type"),
            event.get("location"),
            event.get("text"),
            event.get("source", "unknown"),
            event.get("source_event_id"),
            1 if event.get("real_data") else 0,
        ))
        conn.commit()
        saved = True

    except sqlite3.IntegrityError:
        saved = False

    conn.close()
    return saved


def save_alert(alert):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO alerts (timestamp, agent, type, location, message, severity, data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
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

    cursor.execute("""
        INSERT INTO risk_snapshots (timestamp, risk_map)
        VALUES (?, ?)
    """, (
        datetime.now().isoformat(),
        json.dumps(risk_map),
    ))

    conn.commit()
    conn.close()


def clear_database():
    """Clear local development data without deleting the database file."""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM risk_snapshots")
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM events")

    conn.commit()
    conn.close()
