from __future__ import annotations

import io
from datetime import date, timedelta
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .ai_router import AIRouter
from .database import execute, log_workflow, utc_now

PACKAGES = {
    "Basic": {"price": 2500, "duration": "30 days", "focus": "Audit, quick wins, and outreach setup"},
    "Growth": {"price": 6500, "duration": "90 days", "focus": "SEO/GEO/AEO sprint, content, CRM follow-up"},
    "Premium": {"price": 12500, "duration": "120 days", "focus": "Full funnel, social automation, proposal engine"},
    "Enterprise": {"price": 28000, "duration": "180 days", "focus": "Multi-market sales department automation"},
}


def generate_proposal_text(company: dict[str, Any], package: str) -> str:
    pkg = PACKAGES[package]
    router = AIRouter()
    system = "You are a senior B2B proposal strategist. Write a concise, executive-grade proposal section."
    user = f"""
    Company: {company.get('name')}
    Industry: {company.get('industry')}
    Country: {company.get('country')}
    Lead score: {company.get('lead_score')} / {company.get('score_value')}
    Score reason: {company.get('score_reason')}
    Package: {package}, price {pkg['price']} USD, duration {pkg['duration']}, focus {pkg['focus']}
    Include executive summary, 90-day strategy, SEO/GEO/AEO plan, outreach plan, ROI logic, and next steps.
    """
    return router.complete(system, user, task="proposal").text


def create_pdf(company: dict[str, Any], package: str, proposal_text: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "SalesForgeTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=colors.HexColor("#111827"),
        spaceAfter=12,
    )
    h2 = ParagraphStyle(
        "SalesForgeH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#4c1d95"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "SalesForgeBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.4,
        leading=15,
        textColor=colors.HexColor("#1f2937"),
    )
    story = [
        Paragraph("SalesForge AI ERP Proposal", title),
        Paragraph(f"Prepared for: <b>{company.get('name')}</b>", body),
        Paragraph(f"Industry: {company.get('industry')} | Market: {company.get('city')}, {company.get('country')}", body),
        Paragraph(f"Date: {date.today().isoformat()}", body),
        Spacer(1, 10),
    ]
    package_data = [
        ["Package", package],
        ["Investment", f"${PACKAGES[package]['price']:,.0f}"],
        ["Timeline", PACKAGES[package]["duration"]],
        ["Focus", PACKAGES[package]["focus"]],
        ["Estimated ROI Window", f"{(date.today() + timedelta(days=90)).isoformat()} onward"],
    ]
    table = Table(package_data, colWidths=[5 * cm, 11 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ede9fe")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c4b5fd")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 12))
    for block in proposal_text.split("\n\n"):
        clean = block.strip()
        if not clean:
            continue
        if len(clean) < 60 and not clean.endswith("."):
            story.append(Paragraph(clean, h2))
        else:
            story.append(Paragraph(clean.replace("\n", "<br/>"), body))
    story.extend(
        [
            Spacer(1, 16),
            Paragraph("Next Step", h2),
            Paragraph("Approve this proposal, schedule onboarding, and connect website/social/CRM access for implementation.", body),
            Spacer(1, 14),
            Paragraph("Regards,<br/><b>Usama Khan</b><br/>Director Sales & Marketing", body),
        ]
    )
    doc.build(story)
    return buffer.getvalue()


def save_proposal_record(company_id: int, deal_id: int | None, package: str, total_value: float, summary: str, filename: str) -> int:
    proposal_id = execute(
        """
        INSERT INTO proposals(company_id, deal_id, package, total_value, currency, status, executive_summary, pdf_filename, created_at)
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (company_id, deal_id, package, total_value, "USD", "DRAFT", summary[:2000], filename, utc_now()),
    )
    execute("UPDATE companies SET status='PROPOSAL_SENT', updated_at=? WHERE id=?", (utc_now(), company_id))
    execute("UPDATE deals SET stage='PROPOSAL_SENT', probability=55, updated_at=? WHERE company_id=?", (utc_now(), company_id))
    log_workflow("PROPOSAL", "GENERATE_PDF", "SUCCESS", f"Generated {package} proposal for company #{company_id}")
    return proposal_id
