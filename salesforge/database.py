from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from .config import DB_PATH

SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@contextmanager
def connect(db_path: Path = DB_PATH):
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                website TEXT,
                industry TEXT NOT NULL,
                country TEXT NOT NULL,
                city TEXT,
                revenue_estimate REAL DEFAULT 0,
                source TEXT DEFAULT 'Demo',
                instagram TEXT,
                linkedin TEXT,
                reviews REAL DEFAULT 0,
                rating REAL DEFAULT 0,
                lead_score TEXT DEFAULT 'COLD',
                score_value INTEGER DEFAULT 0,
                score_reason TEXT,
                status TEXT DEFAULT 'NEW',
                owner TEXT DEFAULT 'Usama Khan',
                deleted_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT,
                email TEXT,
                phone TEXT,
                whatsapp TEXT,
                linkedin TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                contact_id INTEGER,
                title TEXT NOT NULL,
                stage TEXT DEFAULT 'NEW',
                value REAL DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                expected_close_date TEXT,
                probability INTEGER DEFAULT 10,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                contact_id INTEGER,
                channel TEXT NOT NULL,
                direction TEXT DEFAULT 'OUTBOUND',
                subject TEXT,
                content TEXT NOT NULL,
                ai_generated INTEGER DEFAULT 0,
                sent_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE SET NULL,
                FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                title TEXT NOT NULL,
                due_at TEXT,
                priority TEXT DEFAULT 'MEDIUM',
                status TEXT DEFAULT 'OPEN',
                created_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                meeting_at TEXT NOT NULL,
                outcome TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                deal_id INTEGER,
                package TEXT NOT NULL,
                total_value REAL DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                status TEXT DEFAULT 'DRAFT',
                version INTEGER DEFAULT 1,
                executive_summary TEXT,
                pdf_filename TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY(deal_id) REFERENCES deals(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                status TEXT DEFAULT 'DRAFT',
                due_date TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'DRAFT',
                target_audience TEXT,
                leads_found INTEGER DEFAULT 0,
                leads_contacted INTEGER DEFAULT 0,
                responses INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS content_pieces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                generated_text TEXT NOT NULL,
                seo_keywords TEXT,
                published INTEGER DEFAULT 0,
                scheduled_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS seo_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                website_url TEXT,
                score INTEGER DEFAULT 0,
                content_gap TEXT,
                keyword_gap TEXT,
                schema_gap TEXT,
                recommendations TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS exhibitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                booth_status TEXT DEFAULT 'PLANNED',
                leads_captured INTEGER DEFAULT 0,
                qr_code_data TEXT,
                follow_up_status TEXT DEFAULT 'READY',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS exhibition_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exhibition_id INTEGER NOT NULL,
                company_id INTEGER,
                attendee_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                interest TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(exhibition_id) REFERENCES exhibitions(id) ON DELETE CASCADE,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT DEFAULT 'SUCCESS',
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)", (str(SCHEMA_VERSION),))


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        cur = conn.execute(query, tuple(params))
        return [dict(row) for row in cur.fetchall()]


def fetch_one(query: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    with connect() as conn:
        cur = conn.execute(query, tuple(params))
        row = cur.fetchone()
        return dict(row) if row else None


def execute(query: str, params: Iterable[Any] = ()) -> int:
    with connect() as conn:
        cur = conn.execute(query, tuple(params))
        return int(cur.lastrowid or 0)


def execute_many(query: str, rows: Iterable[Iterable[Any]]) -> None:
    with connect() as conn:
        conn.executemany(query, rows)


def log_workflow(module: str, action: str, status: str, message: str) -> None:
    execute(
        "INSERT INTO workflow_logs(module, action, status, message, created_at) VALUES(?,?,?,?,?)",
        (module, action, status, message, utc_now()),
    )


def soft_delete_company(company_id: int) -> None:
    execute(
        "UPDATE companies SET deleted_at=?, updated_at=? WHERE id=?",
        (utc_now(), utc_now(), company_id),
    )


def add_company(company: dict[str, Any]) -> int:
    now = utc_now()
    company_id = execute(
        """
        INSERT INTO companies(
            name, website, industry, country, city, revenue_estimate, source,
            instagram, linkedin, reviews, rating, lead_score, score_value,
            score_reason, status, owner, created_at, updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            company.get("name"),
            company.get("website"),
            company.get("industry"),
            company.get("country"),
            company.get("city"),
            float(company.get("revenue_estimate", 0) or 0),
            company.get("source", "Manual"),
            company.get("instagram"),
            company.get("linkedin"),
            float(company.get("reviews", 0) or 0),
            float(company.get("rating", 0) or 0),
            company.get("lead_score", "COLD"),
            int(company.get("score_value", 0) or 0),
            company.get("score_reason"),
            company.get("status", "NEW"),
            company.get("owner", "Usama Khan"),
            now,
            now,
        ),
    )
    contact = company.get("contact") or {}
    if contact.get("full_name"):
        add_contact(company_id, contact)
    create_default_deal(company_id, company.get("industry", "Digital Growth"), company.get("revenue_estimate", 0))
    log_workflow("CRM", "ADD_COMPANY", "SUCCESS", f"Created lead: {company.get('name')}")
    return company_id


def add_contact(company_id: int, contact: dict[str, Any]) -> int:
    now = utc_now()
    return execute(
        """
        INSERT INTO contacts(company_id, full_name, role, email, phone, whatsapp, linkedin, created_at, updated_at)
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            contact.get("full_name", "Decision Maker"),
            contact.get("role", "Decision Maker"),
            contact.get("email"),
            contact.get("phone"),
            contact.get("whatsapp"),
            contact.get("linkedin"),
            now,
            now,
        ),
    )


def create_default_deal(company_id: int, industry: str, revenue_estimate: float = 0) -> int:
    now = utc_now()
    value = max(3500, min(75000, float(revenue_estimate or 0) * 0.012))
    close_date = (datetime.utcnow() + timedelta(days=28)).date().isoformat()
    return execute(
        """
        INSERT INTO deals(company_id, title, stage, value, currency, expected_close_date, probability, created_at, updated_at)
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (company_id, f"{industry} Digital Growth Retainer", "NEW", value, "USD", close_date, 10, now, now),
    )
