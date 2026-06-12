from importlib import import_module
from pathlib import Path
from typing import Optional

from src.schemas import DocumentUnit, FileType, InputAsset, SourceFile
from src.utils.path_utils import ensure_existing_file, normalize_local_path

SUPPORTED_FILE_TYPES = {"pdf", "pptx", "ppt", "docx", "txt", "md"}


def detect_file_type(file_path: str, explicit_type: Optional[FileType] = None) -> FileType:
    if explicit_type is not None:
        return explicit_type

    suffix = Path(file_path).suffix.lower().lstrip(".")
    if suffix == "jpeg":
        return "jpeg"
    if suffix in SUPPORTED_FILE_TYPES:
        return suffix  # type: ignore[return-value]
    if suffix in {"png", "jpg", "webp"}:
        return suffix  # type: ignore[return-value]

    raise ValueError(f"Unsupported file type for path: {file_path}")


def load_assets(
    assets: list[InputAsset], logger=None
) -> tuple[list[InputAsset], list[SourceFile], list[DocumentUnit]]:
    normalized_assets: list[InputAsset] = []
    source_files: list[SourceFile] = []
    units: list[DocumentUnit] = []

    for index, asset in enumerate(assets, start=1):
        normalized_asset = _normalize_asset(asset, index)
        normalized_assets.append(normalized_asset)
        source_files.append(
            SourceFile(
                file_id=normalized_asset.asset_id,
                file_name=normalized_asset.file_name,
                file_path=normalized_asset.file_path,
                file_type=normalized_asset.file_type,
                mime_type=normalized_asset.mime_type,
            )
        )

        if logger is not None:
            logger.info(
                "Routing asset %s (%s) to parser",
                normalized_asset.asset_id,
                normalized_asset.file_type,
            )

        asset_units = _dispatch_asset_parser(normalized_asset, logger)
        _reindex_units(asset_units, start_index=len(units) + 1)
        units.extend(asset_units)

    return normalized_assets, source_files, units


def _normalize_asset(asset: InputAsset, index: int) -> InputAsset:
    normalized_path = normalize_local_path(asset.file_path)
    resolved_path = ensure_existing_file(normalized_path)
    file_type = detect_file_type(str(resolved_path), asset.file_type)
    file_name = asset.file_name or resolved_path.name
    asset_id = asset.asset_id or f"asset_{index}"

    return InputAsset(
        asset_id=asset_id,
        file_path=str(resolved_path),
        file_type=file_type,
        file_name=file_name,
        mime_type=asset.mime_type,
    )


def _dispatch_asset_parser(asset: InputAsset, logger=None) -> list[DocumentUnit]:
    parser_map = {
        "txt": ("src.utils.extractors.txt", "extract_txt_units"),
        "md": ("src.utils.extractors.txt", "extract_txt_units"),
        "pdf": ("src.utils.extractors.pdf", "extract_pdf_units"),
        "pptx": ("src.utils.extractors.pptx", "extract_pptx_units"),
        "ppt": ("src.utils.extractors.pptx", "extract_pptx_units"),
        "docx": ("src.utils.extractors.docx", "extract_docx_units"),
    }

    parser_target = parser_map.get(asset.file_type)
    if parser_target is None:
        raise ValueError(f"No parser registered for file type: {asset.file_type}")

    try:
        parser = _load_parser(parser_target)
        return parser(asset, logger)
    except ModuleNotFoundError as exc:
        dependency_name = exc.name or "required dependency"
        raise RuntimeError(
            f"Missing parser dependency '{dependency_name}' for file type {asset.file_type}. "
            f"Please install the dependency in the current Python environment."
        ) from exc
    except Exception:
        if logger is not None:
            logger.exception(
                "Failed to parse asset %s (%s)",
                asset.asset_id,
                asset.file_type,
            )
        raise


def _reindex_units(units: list[DocumentUnit], start_index: int) -> None:
    for offset, unit in enumerate(units):
        unit.index = start_index + offset


def _load_parser(parser_target: tuple[str, str]):
    module_name, function_name = parser_target
    module = import_module(module_name)
    return getattr(module, function_name)
