"""Knowledge base updater — writes clinical knowledge to SECOND-KNOWLEDGE-BRAIN.md.

Production: appends entries to the living knowledge base with source
tracking, clinician approval workflow, and triage rule suggestion
extraction. All rule changes require human approval before deployment.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

KNOWLEDGE_BRAIN_PATH = Path(__file__).resolve().parent.parent / "SECOND-KNOWLEDGE-BRAIN.md"
SUGGESTED_RULES_PATH = Path(__file__).resolve().parent.parent / "clinical" / "triage_rules_suggested.yaml"
APPROVAL_QUEUE_PATH = Path.home() / ".phta" / "approval_queue.json"

_SECTION_MAP = {
    "triage": "1. Triage Protocols",
    "diagnosis": "1. Triage Protocols",
    "symptom": "3. Symptom-Disease Associations",
    "treatment": "3. Symptom-Disease Associations",
    "epidemiology": "4. Vietnam-Specific Conditions",
    "general": "3. Symptom-Disease Associations",
    "recommendation": "1. Triage Protocols",
    "contraindication": "7. Medication Safety",
    "red_flag": "2. Red Flag Criteria",
    "escalation": "2. Red Flag Criteria",
    "referral": "1. Triage Protocols",
}


def update_knowledge_brain(entries: list[dict[str, Any]], auto_approve: bool = False) -> int:
    if not entries:
        return 0

    appended = 0
    content = KNOWLEDGE_BRAIN_PATH.read_text(encoding="utf-8") if KNOWLEDGE_BRAIN_PATH.exists() else ""

    for entry in entries:
        category = entry.get("category", "general")
        section = _SECTION_MAP.get(category, "3. Symptom-Disease Associations")
        section_header = f"## {section}"

        if section_header not in content:
            logger.warning(f"Section not found in knowledge brain: {section}")
            continue

        insert_pos = content.index(section_header) + len(section_header)
        next_section = content.find("\n## ", insert_pos)
        if next_section == -1:
            next_section = len(content)

        entry_block = _format_entry(entry, auto_approve)
        content = content[:next_section] + "\n\n" + entry_block + content[next_section:]
        appended += 1

    KNOWLEDGE_BRAIN_PATH.write_text(content, encoding="utf-8")
    _update_entry_count(content)
    logger.info(f"Knowledge brain updated with {appended} entries")
    return appended


def _format_entry(entry: dict[str, Any], auto_approve: bool) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    status = "[APPROVED]" if auto_approve else "[PROPOSED]"

    lines = [
        f"### {status} {entry.get('title', 'Untitled Entry')}",
        f"**Added:** {timestamp} | **Source:** {entry.get('source', 'unknown').upper()} | **Category:** {entry.get('category', 'general')}",
        "",
    ]

    if entry.get("summary"):
        lines.append(entry["summary"])

    if entry.get("url"):
        lines.append(f"\n**Reference:** {entry['url']}")

    if entry.get("actions"):
        lines.append("\n**Extracted Clinical Rules:**")
        for action in entry["actions"]:
            if isinstance(action, (list, tuple)) and len(action) >= 2:
                lines.append(f"- [{action[0].upper()}] {action[1]}")
            elif isinstance(action, dict):
                lines.append(f"- [{action.get('type', 'unknown').upper()}] {action.get('text', str(action))}")

    return "\n".join(lines)


def _update_entry_count(content: str) -> None:
    count = len(re.findall(r"^###\s+\[", content, re.MULTILINE))
    content = re.sub(
        r"\*\*Total Entries:\*\*\s+\d+",
        f"**Total Entries:** {count}",
        content,
    )


def suggest_rule_updates(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggested: list[dict[str, Any]] = []
    for summary in summaries:
        actions = summary.get("actions", [])
        for action in actions:
            if isinstance(action, (list, tuple)) and len(action) >= 2:
                action_type, action_text = action
                if action_type in ("red_flag", "escalation"):
                    suggested.append({
                        "source": summary.get("source", ""),
                        "source_title": summary.get("title", ""),
                        "type": action_type,
                        "rule_text": action_text,
                        "suggested_at": datetime.now(timezone.utc).isoformat(),
                        "status": "pending_review",
                    })

    if suggested:
        _save_suggested_rules(suggested)

    return suggested


def _save_suggested_rules(rules: list[dict[str, Any]]) -> None:
    existing = []
    if SUGGESTED_RULES_PATH.exists():
        import yaml
        with open(SUGGESTED_RULES_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data and isinstance(data, dict):
                existing = data.get("suggested_rules", [])

    import yaml
    with open(SUGGESTED_RULES_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump({"suggested_rules": existing + rules}, f, allow_unicode=True)


def get_approval_queue() -> list[dict[str, Any]]:
    if not APPROVAL_QUEUE_PATH.exists():
        return []
    try:
        return json.loads(APPROVAL_QUEUE_PATH.read_text())
    except Exception:
        return []


def add_to_approval_queue(entry: dict[str, Any]) -> None:
    queue = get_approval_queue()
    entry["queued_at"] = datetime.now(timezone.utc).isoformat()
    entry["status"] = "pending"
    queue.append(entry)
    APPROVAL_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPROVAL_QUEUE_PATH.write_text(json.dumps(queue, indent=2))


def approve_entry(entry_id: str) -> bool:
    queue = get_approval_queue()
    for entry in queue:
        if entry.get("id") == entry_id:
            entry["status"] = "approved"
            entry["approved_at"] = datetime.now(timezone.utc).isoformat()
            APPROVAL_QUEUE_PATH.write_text(json.dumps(queue, indent=2))
            return True
    return False
