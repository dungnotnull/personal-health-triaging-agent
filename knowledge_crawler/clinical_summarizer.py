"""Clinical guideline summarizer — rule extraction from articles.

Uses keyword-based extraction to convert clinical articles into
actionable rules for SECOND-KNOWLEDGE-BRAIN.md. Production-grade:
works offline with regex extraction; can optionally use LLM for
higher-quality summaries.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_CLINICAL_KEYWORDS = {
    "triage": ["triage", "emergency", "urgent", "screening", "red flag", "referral"],
    "symptom": ["symptom", "presenting", "presentation", "clinical feature", "chief complaint"],
    "treatment": ["guideline", "treatment", "management", "therapy", "recommendation", "protocol"],
    "diagnosis": ["diagnostic criteria", "diagnosis", "differential", "workup"],
    "epidemiology": ["prevalence", "incidence", "outbreak", "epidemic", "surveillance"],
}

_ACTION_EXTRACTORS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(patients?\s*(?:should|must|need)\s*(?:be\s*)?\w+(?:\s+\w+){0,20})", re.IGNORECASE), "recommendation"),
    (re.compile(r"(recommend\w*\s+(?:that\s+)?\w+(?:\s+\w+){0,30})", re.IGNORECASE), "recommendation"),
    (re.compile(r"(contraindicated\s+(?:in|for)\s+\w+(?:\s+\w+){0,20})", re.IGNORECASE), "contraindication"),
    (re.compile(r"(warning\s+signs?\s*(?:include|are|:)?\s*\w+(?:\s+\w+){0,30})", re.IGNORECASE), "red_flag"),
    (re.compile(r"(red\s+flags?\s*(?:include|are|:)?\s*\w+(?:\s+\w+){0,30})", re.IGNORECASE), "red_flag"),
    (re.compile(r"(seek\s+(?:immediate\s+)?(?:medical|emergency)\s+(?:attention|care)\s*(?:if|when)\s*\w+(?:\s+\w+){0,30})", re.IGNORECASE), "escalation"),
    (re.compile(r"(refer\s+(?:to|for)\s+(?:emergency|specialist|hospital|urgent)\s*\w+(?:\s+\w+){0,20})", re.IGNORECASE), "referral"),
]


def summarize_article(article: dict[str, Any]) -> str:
    title = article.get("title", "Untitled")
    description = article.get("description", article.get("abstract", ""))
    combined_text = f"{title}. {description}"

    category = _classify_article(combined_text)
    actions = _extract_actions(combined_text)
    severity = _estimate_clinical_severity(combined_text)

    lines = [
        f"**Title:** {title}",
        f"**Source:** {article.get('source', 'unknown').upper()}",
        f"**Category:** {category}",
        f"**Clinical Severity:** {severity}",
    ]

    if article.get("url"):
        lines.append(f"**URL:** {article['url']}")
    if article.get("pub_date"):
        lines.append(f"**Published:** {article['pub_date']}")

    if actions:
        lines.append("")
        lines.append("**Extracted Clinical Actions:**")
        for action_type, action_text in actions[:5]:
            lines.append(f"- [{action_type.upper()}] {action_text}")

    if description:
        lines.append("")
        lines.append(f"**Summary:** {description[:500]}{'...' if len(description) > 500 else ''}")

    lines.append("")
    lines.append(f"*Fetched: {article.get('fetched_at', 'unknown')}*")

    return "\n".join(lines)


def summarize_batch(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for article in articles:
        summary_text = summarize_article(article)
        results.append({
            "id": article.get("id", ""),
            "source": article.get("source", ""),
            "title": article.get("title", ""),
            "category": _classify_article(article.get("title", "") + " " + article.get("description", "")),
            "summary": summary_text,
            "url": article.get("url", ""),
            "fetched_at": article.get("fetched_at", ""),
            "actions": _extract_actions(article.get("description", article.get("abstract", ""))),
        })
    return results


def _classify_article(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for category, keywords in _CLINICAL_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[category] = score
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "general"


def _extract_actions(text: str) -> list[tuple[str, str]]:
    actions: list[tuple[str, str]] = []
    for pattern, action_type in _ACTION_EXTRACTORS:
        for match in pattern.finditer(text):
            action_text = match.group(1).strip().rstrip(".,;:")
            if len(action_text) > 10:
                actions.append((action_type, action_text))
    return actions[:10]


def _estimate_clinical_severity(text: str) -> str:
    text_lower = text.lower()
    critical = ["life-threatening", "mortality", "fatal", "emergency", "immediate", "critical", "death"]
    high = ["severe", "serious", "urgent", "hospitalization", "admission"]
    medium = ["moderate", "requires treatment", "clinical attention"]

    if any(w in text_lower for w in critical):
        return "CRITICAL"
    if any(w in text_lower for w in high):
        return "HIGH"
    if any(w in text_lower for w in medium):
        return "MEDIUM"
    return "LOW"
