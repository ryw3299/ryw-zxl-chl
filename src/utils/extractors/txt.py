from pathlib import Path

from src.schemas import DocumentUnit, InputAsset

from .shared import infer_title, normalize_text, split_text_paragraphs


def extract_txt_units(asset: InputAsset, logger=None) -> list[DocumentUnit]:
    text = Path(asset.file_path).read_text(encoding="utf-8")
    raw_chunks = split_text_paragraphs(text)
    chunks = raw_chunks or [text.strip()]

    units: list[DocumentUnit] = []
    for index, chunk in enumerate(chunks, start=1):
        normalized_chunk = normalize_text(chunk)
        units.append(
            DocumentUnit(
                unit_id=f"{asset.asset_id}_chunk_{index}",
                unit_type="chunk",
                index=index,
                title=infer_title(normalized_chunk, fallback=f"Chunk {index}"),
                text=normalized_chunk,
                source_ref=f"chunk {index}",
                source_asset_id=asset.asset_id or "unknown_asset",
                metadata={
                    "file_name": asset.file_name,
                    "file_type": asset.file_type,
                    "source_index": index,
                    "char_count": len(normalized_chunk),
                },
            )
        )

    if logger is not None:
        logger.info("Parsed txt asset %s into %d unit(s)", asset.asset_id, len(units))

    return units
