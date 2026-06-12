import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

LIBREOFFICE_PPTX_FILTER = "Impress MS PowerPoint 2007 XML"


def convert_legacy_ppt_to_pptx(file_path: str, logger=None) -> Path:
    source_path = Path(file_path).resolve()
    if source_path.suffix.lower() != ".ppt":
        return source_path
    if not source_path.exists():
        raise FileNotFoundError(f"Legacy .ppt source file does not exist: {source_path}")

    target_path = _build_target_path(source_path)
    backend_status = get_ppt_conversion_backend_status()

    if logger is not None:
        logger.info("Attempting to convert legacy .ppt file %s", source_path)
        logger.info("PPT conversion backends: %s", backend_status)

    if backend_status["libreoffice"]:
        try:
            _convert_with_libreoffice(source_path, target_path, backend_status["libreoffice"])
        except Exception as exc:
            if logger is not None:
                logger.warning("LibreOffice conversion failed for %s: %s", source_path, exc)
            raise RuntimeError(
                f"Legacy .ppt conversion failed for {source_path.name}. LibreOffice failed: {exc}"
            ) from exc
    else:
        raise RuntimeError(
            "Legacy .ppt conversion requires LibreOffice, but LibreOffice is not available on this machine."
        )

    if logger is not None:
        logger.info("Converted %s to %s", source_path, target_path)

    return target_path


def get_ppt_conversion_backend_status() -> dict[str, str | bool | None]:
    return {
        "powerpoint_com": False,
        "libreoffice": _find_soffice_path(),
    }


def _build_target_path(source_path: Path) -> Path:
    conversion_root = Path(tempfile.gettempdir()) / "ChaoxingAgentRuntime" / "conversions" / "ppt"
    conversion_root.mkdir(parents=True, exist_ok=True)

    path_hash = hashlib.sha1(str(source_path).encode("utf-8")).hexdigest()[:8]
    target_name = f"{source_path.stem}_{path_hash}.pptx"
    return conversion_root / target_name


def _find_soffice_path() -> str | None:
    candidates = [
        shutil.which("soffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    return None


def _convert_with_libreoffice(source_path: Path, target_path: Path, soffice_path: str) -> None:
    output_dir = target_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = output_dir / "libreoffice_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_uri = profile_dir.resolve().as_uri()

    result = subprocess.run(
        [
            soffice_path,
            "--headless",
            "--nologo",
            "--nodefault",
            "--norestore",
            "--nolockcheck",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to",
            f"pptx:{LIBREOFFICE_PPTX_FILTER}",
            "--outdir",
            str(output_dir),
            str(source_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    generated_path = output_dir / f"{source_path.stem}.pptx"
    if result.returncode != 0 and not generated_path.exists():
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or "LibreOffice returned a non-zero exit code without extra output."
        raise RuntimeError(f"LibreOffice failed to convert {source_path.name}: {detail}")

    if not generated_path.exists():
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or "No output file was produced."
        raise RuntimeError(f"LibreOffice conversion finished without producing a .pptx file. {detail}")

    if generated_path != target_path:
        if target_path.exists():
            target_path.unlink()
        generated_path.replace(target_path)
