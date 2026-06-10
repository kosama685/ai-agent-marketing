from __future__ import annotations

import json
from typing import Any

from .ai_router import AIRouter
from .database import execute, log_workflow, utc_now


def score_company(company: dict[str, Any]) -> dict[str, Any]:
    router = AIRouter()
    system = (
        "You are an expert sales qualification analyst for a Sales & Marketing AI ERP. "
        "Return strict JSON with score, score_value, reasoning, pain_points, and next_best_action."
    )
    user = f"""
    Analyze this business for digital growth opportunity.
    Company: {company.get('name')}
    Industry: {company.get('industry')}
    Country: {company.get('country')}
    City: {company.get('city')}
    Website: {company.get('website')}
    Instagram: {company.get('instagram')}
    LinkedIn: {company.get('linkedin')}
    Rating: {company.get('rating')}
    Reviews: {company.get('reviews')}
    Current score reason: {company.get('score_reason')}
    Factors: bad website, weak SEO, low reviews, no social activity, slow website, missing booking engine, missing Arabic GEO/AEO.
    """
    result = router.complete(system=system, user=user, task="scoring", json_mode=True)
    try:
        data = json.loads(result.text)
    except Exception:
        data = {
            "score": "WARM",
            "score_value": 58,
            "reasoning": result.text[:500],
            "pain_points": ["Could not parse JSON from model output"],
            "next_best_action": "Review manually and send audit offer.",
        }
    label = str(data.get("score", "WARM")).upper()
    if label not in {"HOT", "WARM", "COLD"}:
        label = "WARM"
    score_value = int(data.get("score_value", 55) or 55)
    reason = str(data.get("reasoning", "AI analysis completed"))
    company_id = int(company["id"])
    execute(
        "UPDATE companies SET lead_score=?, score_value=?, score_reason=?, updated_at=? WHERE id=?",
        (label, score_value, reason, utc_now(), company_id),
    )
    gap = build_gap_analysis(company, data)
    execute(
        """
        INSERT INTO seo_audits(company_id, website_url, score, content_gap, keyword_gap, schema_gap, recommendations, created_at)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            company_id,
            company.get("website"),
            score_value,
            gap["content_gap"],
            gap["keyword_gap"],
            gap["schema_gap"],
            gap["recommendations"],
            utc_now(),
        ),
    )
    log_workflow("AI_SCORING", "DEEP_ANALYZE", "SUCCESS", f"Scored {company.get('name')} as {label} ({score_value})")
    data["score"] = label
    data["score_value"] = score_value
    data["model"] = result.model
    data["used_live_ai"] = result.used_live_ai
    return data


def build_gap_analysis(company: dict[str, Any], ai_data: dict[str, Any] | None = None) -> dict[str, str]:
    industry = company.get("industry", "business")
    city = company.get("city", "target city")
    country = company.get("country", "target country")
    brand = company.get("name", "the brand")
    pain_points = ai_data.get("pain_points", []) if ai_data else []
    content_gap = "\n".join(
        [
            f"Missing {industry} service landing pages for {city} and nearby buyer-intent searches.",
            "Limited comparison content that helps prospects choose packages or book a consultation.",
            "No clear FAQ cluster formatted for featured snippets and answer engines.",
            "Insufficient proof assets: case studies, testimonials, before/after metrics, ROI narratives.",
            "Arabic GEO/AEO pages should be added for local search and AI-answer visibility.",
        ]
    )
    keyword_gap = "\n".join(
        [
            f"best {industry.lower()} marketing agency in {city}",
            f"{industry.lower()} SEO services {country}",
            f"increase direct bookings {industry.lower()}",
            f"Arabic SEO for {industry.lower()} {city}",
            f"AI search optimization for {industry.lower()}",
            "WhatsApp lead generation service",
            "local business conversion rate optimization",
        ]
    )
    schema_gap = "\n".join(
        [
            "LocalBusiness / Organization JSON-LD",
            "FAQPage schema for buyer questions",
            "Service schema for core packages",
            "Review schema where compliant and verifiable",
            "BreadcrumbList and Article schema for content hub pages",
        ]
    )
    recommendations = "\n".join(
        [
            f"Prioritize a free digital audit offer for {brand}.",
            "Build a 90-day SEO/GEO/AEO sprint around commercial landing pages and FAQ clusters.",
            "Create a WhatsApp-first follow-up sequence with value reminders on Day 3, 5, 7, 10 and 14.",
            "Use social proof content to reduce trust friction before proposal stage.",
            *(str(p) for p in pain_points[:3]),
        ]
    )
    return {
        "content_gap": content_gap,
        "keyword_gap": keyword_gap,
        "schema_gap": schema_gap,
        "recommendations": recommendations,
    }
