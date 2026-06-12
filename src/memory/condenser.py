from src.schemas.common import QAHistoryItem


class StudentCondenser:
    """Compresses long QA conversation history into a concise summary."""

    def __init__(self, max_items: int = 10):
        """
        Args:
            max_items: Maximum number of recent QA items to retain verbatim.
        """
        self.max_items = max_items

    def condense(self, history: list[QAHistoryItem]) -> list[QAHistoryItem]:
        """
        Reduce long QA history by keeping the most recent items.

        For a minimal implementation, this returns the last `max_items` items.
        A full implementation could use an LLM to generate a summary of older items.

        Args:
            history: Full QA history list, assumed to be in chronological order.

        Returns:
            Condensed history containing at most `max_items` items.
        """
        if len(history) <= self.max_items:
            return list(history)

        # Keep the most recent items
        recent = history[-self.max_items :]

        # TODO: Generate a summary of older items using an LLM
        # when a full implementation is needed.

        return recent
