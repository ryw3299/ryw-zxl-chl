from docx import Document

from src.schemas import DocumentUnit, InputAsset

from .shared import infer_title, normalize_text


def extract_docx_units(asset: InputAsset, logger=None) -> list[DocumentUnit]:
    document = Document(asset.file_path)
    units: list[DocumentUnit] = []
    current_title = ""
    current_body: list[str] = []
    section_number = 0

    def flush_section() -> None:
        nonlocal section_number, current_title, current_body

        normalized_body = normalize_text("\n".join(current_body))
        if not normalized_body and not current_title:
            return

        section_number += 1
        title = current_title or infer_title(normalized_body, fallback=f"Section {section_number}")
        text = normalized_body if normalized_body else title
        units.append(
            DocumentUnit(
                unit_id=f"{asset.asset_id}_section_{section_number}",
                unit_type="section",
                index=section_number,
                title=title,
                text=text,
                source_ref=f"section {section_number}",
                source_asset_id=asset.asset_id or "unknown_asset",
                metadata={
                    "file_name": asset.file_name,
                    "file_type": asset.file_type,
                    "source_index": section_number,
                    "char_count": len(text),
                },
            )
        )
        current_title = ""
        current_body = []

    for paragraph in document.paragraphs:
        text = normalize_text(paragraph.text)
        if not text:
            continue

        style_name = paragraph.style.name.lower() if paragraph.style and paragraph.style.name else ""
        is_heading = style_name.startswith("heading")

        if is_heading:
            flush_section()
            current_title = text
            continue

        current_body.append(text)

    flush_section()

    if logger is not None:
        logger.info("Parsed docx asset %s into %d unit(s)", asset.asset_id, len(units))

    return units
