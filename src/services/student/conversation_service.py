"""Conversation lifecycle management.

Provides a stable ``persistence_dir`` per session so that OpenHands
``Conversation`` events survive across requests.  Also reads recent
turns from the persisted conversation history or from the API-supplied
``history_qa`` list.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[3] / "data"


class ConversationService:
    def __init__(self, data_root: Path | str | None = None):
        self._data_root = Path(data_root) if data_root else _DEFAULT_DATA_ROOT

    def get_conversation_dir(self, session_id: str) -> Path:
        """Return (and create) a stable directory for the given session."""
        conv_dir = self._data_root / "conversations" / session_id
        conv_dir.mkdir(parents=True, exist_ok=True)
        return conv_dir

    def load_recent_turns(
        self,
        session_id: str,
        *,
        limit: int = 5,
        fallback_history_qa: Optional[list[dict[str, Any]]] = None,
    ) -> list[dict[str, Any]]:
        """Load recent Q&A turns for prompt context.

        Priority:
        1. Persisted conversation events (if available)
        2. ``fallback_history_qa`` supplied by the API caller
        """
        turns = self._read_persisted_turns(session_id, limit=limit)
        if turns:
            return turns

        if fallback_history_qa:
            return [
                {
                    "question": item.get("question", ""),
                    "answer": item.get("answer", ""),
                    "understanding_level": item.get("understandingLevel") or item.get("understanding_level"),
                    "current_section_id": item.get("currentSectionId") or item.get("current_section_id"),
                    "current_page": item.get("currentPage") or item.get("current_page"),
                }
                for item in fallback_history_qa[-limit:]
            ]

        return []

    def _read_persisted_turns(self, session_id: str, *, limit: int) -> list[dict[str, Any]]:
        """Read turns from the conversation persistence directory."""
        conv_dir = self._data_root / "conversations" / session_id
        turns_file = conv_dir / "turns.json"
        if not turns_file.exists():
            return []
        try:
            data = json.loads(turns_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data[-limit:]
        except Exception:
            logger.debug("Failed to read persisted turns for session %s", session_id)
        return []

    def append_turn(self, session_id: str, turn: dict[str, Any]) -> None:
        """Persist a new turn to the conversation file."""
        conv_dir = self.get_conversation_dir(session_id)
        turns_file = conv_dir / "turns.json"
        turns: list[dict[str, Any]] = []
        if turns_file.exists():
            try:
                turns = json.loads(turns_file.read_text(encoding="utf-8"))
            except Exception:
                turns = []
        turns.append(turn)
        turns_file.write_text(
            json.dumps(turns, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
