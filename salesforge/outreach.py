from __future__ import annotations

from typing import Any

from .ai_router import AIRouter
from .database import execute, fetch_one, log_workflow, utc_now


def get_primary_contact(company_id: int) -> dict[str, Any] | None:
    return fetch_one("SELECT * FROM contacts WHERE company_id=? ORDER BY id LIMIT 1", (company_id,))


def generate_outreach(company: dict[str, Any], channel: str = "Email", offer: str = "free marketing audit") -> str:
    router = AIRouter()
    contact = get_primary_contact(int(company["id"])) or {}
    system = (
        "You write concise, premium B2B sales outreach for a Director of Sales & Marketing. "
        "Use a helpful audit-first tone, not spam. Include specific digital pain points and a clear CTA."
    )
    user = f"""
    Lead: {company.get('name')}
    Industry: {company.get('industry')}
    Country: {company.get('country')}
    City: {company.get('city')}
    Contact: {contact.get('full_name', 'Decision Maker')} / {contact.get('role', 'Decision Maker')}
    Score: {company.get('lead_score')} ({company.get('score_value')})
    Reasoning: {company.get('score_reason')}
    Channel: {channel}
    Offer: {offer}
    Required signature: Usama Khan, Director Sales & Marketing
    """
    return router.complete(system, user, task="outreach").text


def log_outreach(company_id: int, contact_id: int | None, channel: str, subject: str, content: str, ai_generated: bool = True) -> int:
    comm_id = execute(
        """
        INSERT INTO communications(company_id, contact_id, channel, direction, subject, content, ai_generated, sent_at)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (company_id, contact_id, channel.upper(), "OUTBOUND", subject, content, int(ai_generated), utc_now()),
    )
    execute("UPDATE companies SET status='CONTACTED', updated_at=? WHERE id=?", (utc_now(), company_id))
    log_workflow("OUTREACH", f"SEND_{channel.upper()}", "SUCCESS", f"Logged {channel} outreach for company #{company_id}")
    return comm_id


def build_sequence(company_id: int) -> list[dict[str, str]]:
    return [
        {"day": "Day 1", "channel": "Email", "action": "Intro audit offer", "status": "Ready"},
        {"day": "Day 3", "channel": "Email", "action": "Case study / success story", "status": "Queued"},
        {"day": "Day 5", "channel": "Email", "action": "SEO/GEO/AEO audit report", "status": "Queued"},
        {"day": "Day 7", "channel": "WhatsApp", "action": "Value follow-up", "status": "Queued"},
        {"day": "Day 10", "channel": "LinkedIn", "action": "Meeting request", "status": "Queued"},
        {"day": "Day 14", "channel": "Email", "action": "Proposal reminder", "status": "Queued"},
    ]
