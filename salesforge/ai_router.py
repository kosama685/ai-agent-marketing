from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from .config import ai_settings
from .database import log_workflow

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class AIResult:
    text: str
    model: str
    used_live_ai: bool


class AIRouter:
    """Central AI router with OpenRouter support and deterministic demo fallbacks."""

    def __init__(self) -> None:
        self.settings = ai_settings()

    def model_for_task(self, task: str) -> str:
        if task in {"scoring", "classification", "audit"}:
            return self.settings.model_scoring
        if task in {"content", "proposal", "outreach"}:
            return self.settings.model_creative
        return self.settings.model_fast

    def complete(self, system: str, user: str, task: str = "fast", json_mode: bool = False) -> AIResult:
        model = self.model_for_task(task)
        if not self.settings.enabled:
            return AIResult(text=self._fallback(system, user, task, json_mode), model="demo-local", used_live_ai=False)

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.25 if task in {"scoring", "audit"} else 0.72,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {self.settings.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://salesforge-ai-erp.streamlit.app",
                    "X-Title": "SalesForge AI ERP",
                },
                data=json.dumps(payload),
                timeout=40,
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            log_workflow("AI_ROUTER", task.upper(), "SUCCESS", f"OpenRouter call completed with {model}")
            return AIResult(text=text, model=model, used_live_ai=True)
        except Exception as exc:
            log_workflow("AI_ROUTER", task.upper(), "FALLBACK", f"OpenRouter failed; used local fallback. Reason: {exc}")
            return AIResult(text=self._fallback(system, user, task, json_mode), model="demo-local", used_live_ai=False)

    def _fallback(self, system: str, user: str, task: str, json_mode: bool) -> str:
        user_lower = user.lower()
        if task in {"scoring", "audit"} or json_mode:
            score = 62
            reasons = []
            if "no website" in user_lower or "website: none" in user_lower or "website: null" in user_lower:
                score += 18
                reasons.append("No visible conversion website")
            if "hotel" in user_lower or "restaurant" in user_lower or "clinic" in user_lower:
                score += 6
                reasons.append("Industry has urgent local SEO and conversion upside")
            if "low reviews" in user_lower or "reviews" in user_lower:
                reasons.append("Review velocity and reputation can improve")
            if "instagram: none" in user_lower or "linkedin: none" in user_lower:
                score += 8
                reasons.append("Social authority appears incomplete")
            score = max(30, min(score, 95))
            label = "HOT" if score >= 75 else "WARM" if score >= 52 else "COLD"
            return json.dumps(
                {
                    "score": label,
                    "score_value": score,
                    "reasoning": "; ".join(reasons) or "Moderate growth potential based on demo analysis.",
                    "pain_points": [
                        "Weak keyword coverage for high-intent local searches",
                        "Insufficient answer-engine FAQ structure",
                        "Missing conversion-led landing page narrative",
                    ],
                    "next_best_action": "Send a free audit offer and book a 20-minute strategy call.",
                },
                indent=2,
            )
        if task == "outreach":
            return (
                "Subject: Increase Direct Bookings and Qualified Enquiries\n\n"
                "Hello,\n\n"
                "I analyzed your digital presence and found several opportunities to improve search visibility, conversion flow, and AI-search discoverability.\n\n"
                "Key findings:\n- weak SEO visibility\n- limited structured FAQ content\n- missing Arabic GEO/AEO optimization\n- no clear conversion funnel\n\n"
                "We help brands improve direct enquiries, social reach, sales-qualified leads, and AI search visibility.\n\n"
                "Would you like a free marketing audit and strategy report?\n\nRegards,\nUsama Khan\nDirector Sales & Marketing"
            )
        if task == "proposal":
            return (
                "Executive Summary\n"
                "This proposal outlines a 90-day growth program focused on lead generation, SEO/GEO/AEO visibility, conversion-rate optimization, and automated follow-up. "
                "The plan prioritizes direct revenue impact, clearer brand positioning, and measurable pipeline creation.\n\n"
                "Strategic Plan\n"
                "1. Audit and fix conversion gaps.\n2. Build topical authority and Arabic search coverage.\n3. Launch targeted outreach and retargeting assets.\n4. Report weekly on leads, meetings, and ROI.\n\n"
                "Expected Outcome\n"
                "More qualified enquiries, stronger organic visibility, and a repeatable sales follow-up engine."
            )
        if task == "content":
            return (
                "# AI Search Optimized Content Plan\n\n"
                "## Content gaps\n- Local landing pages for priority cities\n- Comparison pages by service package\n- FAQ content for featured snippets and AI answers\n- Trust content: case studies, reviews, founder story\n\n"
                "## Keyword gaps\n- near me intent keywords\n- Arabic service keywords\n- high-conversion commercial keywords\n- problem-solution educational phrases\n\n"
                "## Recommended assets\n1. SEO article\n2. LinkedIn authority post\n3. Instagram carousel script\n4. FAQ schema block\n5. Sales email sequence"
            )
        return "Local demo AI response generated. Add OPENROUTER_API_KEY in secrets to enable live model routing."
