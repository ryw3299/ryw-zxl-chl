"""
Student-side helper functions for retrieval and content processing.
"""

from typing import Optional

from src.schemas import RetrievedContextItem
from src.schemas.common import PageBlock, ScriptBlock, SectionBlock

from .chunking import split_text_into_chunks
from .constants import MAX_CONTEXT_STRING_LENGTH


def map_to_retrieved_context_item(
    source_type: str,
    source_id: str,
    title: str,
    text: str,
    section_id: Optional[str] = None,
    page: Optional[int] = None,
    score: Optional[float] = None,
) -> RetrievedContextItem:
    """
    Map a content source to a RetrievedContextItem.

    Args:
        source_type: One of "page", "section", "script_block"
        source_id: Unique identifier of the source
        title: Human-readable title
        text: Retrieved text content
        section_id: Owning section identifier
        page: Owning page number
        score: Retrieval relevance score

    Returns:
        RetrievedContextItem mapped from the source
    """
    valid_sources = {"page", "section", "script_block"}
    if source_type not in valid_sources:
        raise ValueError(f"source_type must be one of {valid_sources}, got {source_type}")

    return RetrievedContextItem(
        source=source_type,  # type: ignore
        source_id=source_id,
        title=title,
        text=text,
        section_id=section_id,
        page=page,
        score=score,
    )


def build_context_string(
    items: list[RetrievedContextItem],
    max_length: int = MAX_CONTEXT_STRING_LENGTH,
    include_header: bool = True,
) -> str:
    """
    Build an LLM context string from a list of retrieved context items.

    Args:
        items: List of RetrievedContextItem to include in context
        max_length: Maximum total length of the context string
        include_header: Whether to include section/page headers

    Returns:
        Formatted context string suitable for LLM input
    """
    if not items:
        return ""

    context_parts = []
    current_length = 0

    for item in items:
        if include_header and item.title:
            header = f"[{item.source.upper()}] {item.title}"
            part = f"{header}\n{item.text}"
        else:
            part = item.text

        # Check if adding this part would exceed max_length
        if current_length + len(part) + 1 > max_length:
            # Try to add what we can
            remaining = max_length - current_length
            if remaining > 50:  # Only add if we can fit something meaningful
                context_parts.append(part[:remaining])
            break

        context_parts.append(part)
        current_length += len(part) + 1

    return "\n\n---\n\n".join(context_parts)


def extract_page_content(page: PageBlock) -> str:
    """
    Extract full text content from a PageBlock.

    Args:
        page: PageBlock to extract content from

    Returns:
        Full text content of the page
    """
    parts = []
    if page.title:
        parts.append(f"# {page.title}")
    if page.content:
        parts.append(page.content)
    if page.key_points:
        parts.append("Key points: " + ", ".join(page.key_points))
    return "\n".join(parts)


def extract_section_content(section: SectionBlock) -> str:
    """
    Extract full text content from a SectionBlock.

    Args:
        section: SectionBlock to extract content from

    Returns:
        Full text content of the section
    """
    parts = []
    if section.name:
        parts.append(f"# {section.name}")
    if section.summary:
        parts.append(section.summary)
    if section.key_points:
        parts.append("Key points: " + ", ".join(section.key_points))
    if section.knowledge_points:
        parts.append("Knowledge points: " + ", ".join(section.knowledge_points))
    return "\n".join(parts)


def extract_script_content(script: ScriptBlock) -> str:
    """
    Extract full text content from a ScriptBlock.

    Args:
        script: ScriptBlock to extract content from

    Returns:
        Full text content of the script
    """
    parts = []
    if script.title:
        parts.append(f"# {script.title}")
    if script.script_text:
        parts.append(script.script_text)
    if script.key_points:
        parts.append("Key points: " + ", ".join(script.key_points))
    return "\n".join(parts)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split long text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of overlapping characters between chunks

    Returns:
        List of text chunks
    """
    return split_text_into_chunks(text, chunk_size=chunk_size, overlap=overlap)
