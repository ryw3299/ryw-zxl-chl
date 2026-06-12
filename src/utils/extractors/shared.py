def normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    collapsed_lines = [line for line in lines if line]
    return "\n".join(collapsed_lines).strip()


def split_text_paragraphs(text: str) -> list[str]:
    return [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]


def infer_title(text: str, fallback: str, max_length: int = 80) -> str:
    for line in text.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate[:max_length]
    return fallback
