"""Branching question tree engine for clinical interviews.

Loads YAML question trees, tracks state, and determines the next
question based on previous answers. Supports branching logic where
answers determine subsequent question paths.

Constraint: max 10 questions per interview.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

TREES_DIR = Path(__file__).resolve().parent.parent / "clinical" / "question_trees"


class QuestionTreeEngine:
    def __init__(self, chief_complaint: str) -> None:
        self.chief_complaint = chief_complaint
        self._tree = self._load_tree(chief_complaint)
        self._asked: list[str] = []
        self._answers: dict[str, Any] = {}
        self._current_index = 0

    def _load_tree(self, complaint: str) -> dict:
        path = TREES_DIR / f"{complaint}.yaml"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        # Fallback to general question tree
        general_path = TREES_DIR / "general.yaml"
        with open(general_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def next_question(self) -> dict | None:
        """Return the next question dict, or None if interview complete."""
        if len(self._asked) >= 10:
            return None

        initial = self._tree.get("initial_questions", [])
        if self._current_index < len(initial):
            q = initial[self._current_index]
            self._current_index += 1
            return q

        # Check branching questions based on answers
        branching = self._tree.get("branching", {})
        for answer_qid, answer_val in self._answers.items():
            branch_key = f"{answer_qid}_{answer_val}"
            if branch_key in branching:
                branch = branching[branch_key]
                if "trigger_red_flag" in branch:
                    return {"red_flag": branch["trigger_red_flag"]}
                next_qs = branch.get("next_questions", [])
                for nq in next_qs:
                    if nq.get("id") not in self._asked:
                        return nq

        return None

    def record_answer(self, question_id: str, answer: Any) -> None:
        self._asked.append(question_id)
        self._answers[question_id] = answer

    @property
    def asked_count(self) -> int:
        return len(self._asked)

    @property
    def answers(self) -> dict[str, Any]:
        return dict(self._answers)
