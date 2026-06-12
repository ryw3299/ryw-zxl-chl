import pymupdf

from src.schemas import DocumentUnit, InputAsset

from .shared import infer_title, normalize_text


def extract_pdf_units(asset: InputAsset, logger=None) -> list[DocumentUnit]:
    units: list[DocumentUnit] = []

    with pymupdf.open(asset.file_path) as document:
        for page_number, page in enumerate(document, start=1):
            page_text = normalize_text(page.get_text("text"))
            if not page_text:
                if logger is not None:
                    logger.warning(
                        "Skipping empty pdf page %d for asset %s",
                        page_number,
                        asset.asset_id,
                    )
                continue

            units.append(
                DocumentUnit(
                    unit_id=f"{asset.asset_id}_page_{page_number}",
                    unit_type="page",
                    index=page_number,
                    title=infer_title(page_text, fallback=f"Page {page_number}"),
                    text=page_text,
                    source_ref=f"page {page_number}",
                    source_asset_id=asset.asset_id or "unknown_asset",
                    metadata={
                        "file_name": asset.file_name,
                        "file_type": asset.file_type,
                        "source_index": page_number,
                        "char_count": len(page_text),
                    },
                )
            )

    if logger is not None:
        logger.info("Parsed pdf asset %s into %d unit(s)", asset.asset_id, len(units))

    return units
