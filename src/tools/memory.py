"""MemoryTool - QA history tool for student agent."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from src.memory.history import QAHistoryStore
from src.schemas.common import QAHistoryItem, QARecord, ReferenceItem


class MemoryTool:
    """Tool for QA history operations: get_history, add, search.

    Consumes QAHistoryStore as the underlying storage.
    Output follows the student_tools_contract_v1.md specification.
    """

    def __init__(self, store: Optional[QAHistoryStore] = None):
        self._store = store or QAHistoryStore()

    def run(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute a memory action.

        Args:
            action: Dict with keys:
                - command: "get_history" | "add" | "search"
                - session_id: str
                - lesson_id: str | None (add only)
                - question: str | None (add only)
                - answer: str | None (add only)
                - references: list[dict] | None (add only)
                - keyword: str | None (search only)
                - limit: int (default 5)

        Returns:
            Dict with keys:
                - records: list[dict]
                - total: int
        """
        command = action.get("command", "")

        if command == "get_history":
            return self._get_history(action)
        elif command == "add":
            return self._add(action)
        elif command == "search":
            return self._search(action)
        else:
            raise ValueError(f"unknown memory command: {command!r}")

    def _get_history(self, action: dict[str, Any]) -> dict[str, Any]:
        session_id = action.get("session_id", "")
        limit = action.get("limit", 5)

        if not session_id:
            return {"records": [], "total": 0}

        items: list[QAHistoryItem] = self._store.get_by_session(session_id)
        total = len(items)
        records = [_item_to_dict(item) for item in items[:limit]]
        return {"records": records, "total": total}

    def _add(self, action: dict[str, Any]) -> dict[str, Any]:
        session_id = action.get("session_id", "")
        lesson_id = action.get("lesson_id", "")
        question = action.get("question", "")
        answer = action.get("answer", "")
        references_raw = action.get("references") or []

        if not question or not answer:
            raise ValueError("add requires question and answer")
        if not session_id or not lesson_id:
            raise ValueError("add requires session_id and lesson_id")

        references = [_parse_reference(r) for r in references_raw]

        record = QARecord(
            qa_record_id=str(uuid.uuid4()),
            session_id=session_id,
            lesson_id=lesson_id,
            question=question,
            answer=answer,
            references=references,
        )
        self._store.add(record)

        return {"records": [_record_to_dict(record)], "total": 1}

    def _search(self, action: dict[str, Any]) -> dict[str, Any]:
        keyword = action.get("keyword", "")
        lesson_id = action.get("lesson_id")
        limit = action.get("limit", 5)

        if not keyword:
            raise ValueError("search requires keyword")

        items: list[QAHistoryItem] = self._store.search(
            keyword=keyword,
            lesson_id=lesson_id,
            limit=limit,
        )
        total = len(items)
        records = [_item_to_dict(item) for item in items]
        return {"records": records, "total": total}


def _item_to_dict(item: QAHistoryItem) -> dict[str, Any]:
    return {
        "qa_record_id": item.qa_record_id,
        "question": item.question,
        "answer": item.answer,
        "understanding_level": (item.understanding_level.value if item.understanding_level else None),
        "current_section_id": item.current_section_id,
        "current_page": item.current_page,
    }


def _record_to_dict(record: QARecord) -> dict[str, Any]:
    return {
        "qa_record_id": record.qa_record_id,
        "course_id": record.course_id,
        "lesson_id": record.lesson_id,
        "session_id": record.session_id,
        "question": record.question,
        "answer": record.answer,
        "understanding_level": (record.understanding_level.value if record.understanding_level else None),
        "references": [{"source_type": r.source_type, "snippet": r.snippet} for r in record.references],
        "current_section_id": record.current_section_id,
        "current_page": record.current_page,
    }


def _parse_reference(raw: Any) -> ReferenceItem:
    if isinstance(raw, ReferenceItem):
        return raw
    if isinstance(raw, dict):
        return ReferenceItem(
            source_type=raw.get("source_type", "lesson"),
            source_name=raw.get("source_name", ""),
            snippet=raw.get("snippet", ""),
            course_id=raw.get("course_id"),
            lesson_id=raw.get("lesson_id"),
            section_id=raw.get("section_id"),
            script_block_id=raw.get("script_block_id"),
            page=raw.get("page"),
            score=raw.get("score"),
        )
    return ReferenceItem(snippet=str(raw))
