from __future__ import annotations

import json
from typing import Any

from .ai_router import AIRouter
from .database import execute, log_workflow, utc_now
from .scoring import build_gap_analysis

CONTENT_TYPES = ["SEO Article", "Social Posts", "Ad Copy", "Email Sequence", "Video Script", "FAQ + Schema", "GEO/AEO Optimizer"]


def generate_content(company: dict[str, Any] | None, content_type: str, topic: str, tone: str = "corporate") -> str:
    router = AIRouter()
    context = ""
    if company:
        gap = build_gap_analysis(company)
        context = f"""
        Company: {company.get('name')}
        Industry: {company.get('industry')}
        Market: {company.get('city')}, {company.get('country')}
        Lead score: {company.get('lead_score')} ({company.get('score_value')})
        Content gap: {gap['content_gap']}
        Keyword gap: {gap['keyword_gap']}
        """
    system = "You are an AI content strategist for SEO, GEO and AEO. Output structured, ready-to-use marketing content."
    user = f"""
    Content type: {content_type}
    Topic: {topic}
    Tone: {tone}
    {context}
    Requirements: include content gap analysis, keyword gap analysis, recommended headings, FAQ questions, schema suggestions, and CTA where useful.
    """
    return router.complete(system, user, task="content").text


def save_content(company_id: int | None, content_type: str, title: str, text: str, keywords: list[str]) -> int:
    content_id = execute(
        """
        INSERT INTO content_pieces(company_id, type, title, generated_text, seo_keywords, published, created_at)
        VALUES(?,?,?,?,?,?,?)
        """,
        (company_id, content_type, title, text, json.dumps(keywords), 0, utc_now()),
    )
    log_workflow("CONTENT", "SAVE", "SUCCESS", f"Saved {content_type}: {title}")
    return content_id


def schema_markup(company: dict[str, Any]) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": company.get("name"),
        "url": company.get("website"),
        "address": {
            "@type": "PostalAddress",
            "addressLocality": company.get("city"),
            "addressCountry": company.get("country"),
        },
        "sameAs": [x for x in [company.get("instagram"), company.get("linkedin")] if x],
    }
    return json.dumps(data, indent=2)
