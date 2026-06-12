#!/usr/bin/env python3
"""
auto_source_convert.py — Courseware Flash automatic source converter

Auto-detects file type and converts source material (PDF/PPTX/DOCX/etc.)
to Markdown using ppt-master source_to_md scripts.

Supports legacy .ppt via LibreOffice headless conversion to .pptx.

After conversion, any extracted images are consolidated into
`<project_path>/images/` and indexed in `images/manifest.json` so that
slide_plan.json can reference them as `image` content blocks.

Usage:
    python auto_source_convert.py <source_file> <project_path>

Output:
    Writes converted Markdown to <project_path>/sources/<stem>.md
    Copies extracted images to <project_path>/images/
    Writes/updates <project_path>/images/manifest.json
    Returns the path to the generated markdown file.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


MIN_IMAGE_BYTES = 5 * 1024
MIN_IMAGE_DIMENSION = 80
MIN_IMAGE_AREA = 12_000
MAX_ASPECT_RATIO = 6.0


def resolve_repo_root() -> Path:
    """Return repository root (where skills/ lives)."""
    script = Path(__file__).resolve()
    # script is at skills/courseware-flash/scripts/
    return script.parent.parent.parent.parent


def detect_converter(source_path: Path) -> tuple[str | None, str]:
    """Return (converter_script_name, file_category) for the given source file."""
    ext = source_path.suffix.lower()

    mapping = {
        ".pdf": ("pdf_to_md.py", "pdf"),
        ".pptx": ("ppt_to_md.py", "ppt"),
        ".pptm": ("ppt_to_md.py", "ppt"),
        ".ppsx": ("ppt_to_md.py", "ppt"),
        ".ppsm": ("ppt_to_md.py", "ppt"),
        ".potx": ("ppt_to_md.py", "ppt"),
        ".potm": ("ppt_to_md.py", "ppt"),
        ".docx": ("doc_to_md.py", "doc"),
        ".doc": ("doc_to_md.py", "doc"),
        ".odt": ("doc_to_md.py", "doc"),
        ".rtf": ("doc_to_md.py", "doc"),
        ".tex": ("doc_to_md.py", "doc"),
        ".rst": ("doc_to_md.py", "doc"),
        ".org": ("doc_to_md.py", "doc"),
        ".epub": ("doc_to_md.py", "doc"),
        ".html": ("doc_to_md.py", "doc"),
        ".htm": ("doc_to_md.py", "doc"),
        ".xlsx": ("excel_to_md.py", "excel"),
        ".xlsm": ("excel_to_md.py", "excel"),
        ".xls": ("excel_to_md.py", "excel"),
        ".csv": (None, "csv"),  # handled directly
        ".tsv": (None, "csv"),
        ".md": (None, "md"),   # no conversion needed
        ".txt": (None, "txt"), # no conversion needed
        ".ppt": ("ppt_to_md.py", "ppt"),  # legacy ppt: will be pre-converted to pptx
    }

    if ext in mapping:
        return mapping[ext]

    # URL detection: if the "file" is actually a URL string passed as arg
    name = source_path.name
    if name.startswith(("http://", "https://")):
        return ("web_to_md.py", "web")

    raise ValueError(f"Unsupported source file type: {ext} ({source_path})")


# ---------------------------------------------------------------------------
# LibreOffice .ppt → .pptx conversion
# ---------------------------------------------------------------------------

LIBREOFFICE_PPTX_FILTER = "Impress MS PowerPoint 2007 XML"


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


def _convert_with_libreoffice(source_path: Path, target_path: Path) -> None:
    soffice = _find_soffice_path()
    if not soffice:
        raise RuntimeError(
            "LibreOffice is required to convert legacy .ppt files, "
            "but soffice was not found. Please install LibreOffice."
        )

    output_dir = target_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = output_dir / "libreoffice_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_uri = profile_dir.resolve().as_uri()

    result = subprocess.run(
        [
            soffice,
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
        detail = (result.stderr or result.stdout or "LibreOffice returned non-zero exit code").strip()
        raise RuntimeError(f"LibreOffice failed to convert {source_path.name}: {detail}")

    if not generated_path.exists():
        detail = (result.stderr or result.stdout or "No output file produced").strip()
        raise RuntimeError(f"LibreOffice conversion finished without producing a .pptx: {detail}")

    if generated_path != target_path:
        if target_path.exists():
            target_path.unlink()
        generated_path.replace(target_path)


def convert_legacy_ppt(source_path: Path) -> Path:
    """Convert legacy .ppt to .pptx via LibreOffice. Return path to .pptx."""
    conversion_root = Path(tempfile.gettempdir()) / "courseware_flash_conversions"
    conversion_root.mkdir(parents=True, exist_ok=True)

    path_hash = hashlib.sha1(str(source_path).encode("utf-8")).hexdigest()[:8]
    target_name = f"{source_path.stem}_{path_hash}.pptx"
    target_path = conversion_root / target_name

    if target_path.exists():
        print(f"  Using cached conversion: {target_path}")
        return target_path

    print(f"  Converting legacy .ppt -> .pptx via LibreOffice...")
    _convert_with_libreoffice(source_path, target_path)
    print(f"  Converted: {target_path}")
    return target_path


# ---------------------------------------------------------------------------


def run_converter(script_path: Path, source_file: Path, output_file: Path) -> None:
    """Run the converter script via subprocess."""
    cmd = [sys.executable, str(script_path), str(source_file), "-o", str(output_file)]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Converter failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    if result.stdout:
        print(result.stdout)


def copy_or_read_directly(source_file: Path, output_file: Path) -> None:
    """For files that need no conversion (md, txt, csv)."""
    if source_file.suffix.lower() in (".md", ".txt", ".csv", ".tsv"):
        shutil.copy2(source_file, output_file)
        print(f"  Copied {source_file.name} -> {output_file}")
    else:
        raise ValueError(f"Direct handling not implemented for: {source_file}")


def _parse_image_filename(name: str, category: str) -> dict:
    """Extract page/slide hints from converter-generated image filenames.

    PPTX images: `slide_<NN>_image_<MM>.<ext>`
    PDF images:  `<stem>_p<N>_<M>.<ext>`
    """
    info: dict = {"page": None, "index": None}
    m = re.match(r"slide_(\d+)_image_(\d+)\.", name)
    if m:
        info["page"] = int(m.group(1))
        info["index"] = int(m.group(2))
        return info
    m = re.match(r".+?_p(\d+)_(\d+)\.", name)
    if m:
        info["page"] = int(m.group(1))
        info["index"] = int(m.group(2))
        return info
    return info


def _extract_image_context(md_text: str, asset_filename: str) -> dict:
    """Locate an image reference inside the converted markdown and pull
    the nearest heading plus a short context window.

    Returns:
        {"heading": str, "page": int|None, "context": str}
        Empty fields if the reference is not found.
    """
    lines = md_text.split("\n")
    pat = re.compile(
        r"!\[[^\]]*\]\([^)]*" + re.escape(asset_filename) + r"\)"
    )

    hit = None
    for i, line in enumerate(lines):
        if pat.search(line):
            hit = i
            break
    if hit is None:
        return {"heading": "", "page": None, "context": ""}

    heading = ""
    for j in range(hit - 1, -1, -1):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", lines[j])
        if m:
            heading = m.group(2).strip()
            break

    page = None
    for j in range(hit, -1, -1):
        m = re.search(r"<!--\s*Page\s+(\d+)\s*-->", lines[j])
        if m:
            page = int(m.group(1))
            break

    before = [l.strip() for l in lines[max(0, hit - 3):hit] if l.strip()]
    after = [l.strip() for l in lines[hit + 1:hit + 4] if l.strip()]
    context = " ".join(before + after)
    if len(context) > 240:
        context = context[:240].rstrip() + "…"

    return {"heading": heading, "page": page, "context": context}


def _extract_image_context_richer(md_text: str, asset_filename: str) -> dict:
    """Derive image heading/page/context from the whole slide section.

    This avoids the common failure mode where the local +/-3 line window only
    contains neighboring image markdown references.
    """

    def is_image_line(line: str) -> bool:
        return bool(re.search(r"!\[[^\]]*\]\([^)]*\)", line))

    def is_page_comment(line: str) -> bool:
        return bool(re.search(r"<!--\s*Page\s+\d+\s*-->", line))

    def is_slide_heading(line: str) -> bool:
        return bool(re.match(r"^##\s+Slide\b", line.strip(), flags=re.IGNORECASE))

    def normalize_heading(raw_heading: str) -> str:
        heading_text = raw_heading.strip()
        match = re.match(r"^Slide\s+\d+\s*:\s*(.+)$", heading_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return heading_text

    def clean_context_line(line: str) -> str:
        line = line.strip()
        if not line:
            return ""
        if is_image_line(line) or is_page_comment(line):
            return ""
        if line.startswith("> [Image]") or line.startswith("> [Chart]"):
            return ""
        if line.startswith("### Speaker Notes"):
            return ""
        return re.sub(r"\s+", " ", line)

    lines = md_text.split("\n")
    pattern = re.compile(r"!\[[^\]]*\]\([^)]*" + re.escape(asset_filename) + r"\)")

    hit = None
    for i, line in enumerate(lines):
        if pattern.search(line):
            hit = i
            break
    if hit is None:
        return {"heading": "", "page": None, "context": ""}

    section_start = 0
    for j in range(hit, -1, -1):
        if is_slide_heading(lines[j]):
            section_start = j
            break

    section_end = len(lines)
    for j in range(hit + 1, len(lines)):
        if is_slide_heading(lines[j]):
            section_end = j
            break

    section_lines = lines[section_start:section_end]

    heading = ""
    for line in section_lines:
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            heading = normalize_heading(match.group(2))
            break

    page = None
    for j in range(section_start, -1, -1):
        match = re.search(r"<!--\s*Page\s+(\d+)\s*-->", lines[j])
        if match:
            page = int(match.group(1))
            break

    context_lines: list[str] = []
    for line in section_lines:
        cleaned = clean_context_line(line)
        if not cleaned:
            continue
        if is_slide_heading(cleaned):
            continue
        context_lines.append(cleaned)
        if len(context_lines) >= 6:
            break

    context = " ".join(context_lines)
    if len(context) > 240:
        context = context[:240].rstrip() + "..."

    if not heading and context:
        heading = context[:80].strip()

    return {"heading": heading, "page": page, "context": context}


def _get_png_size(blob: bytes) -> tuple[int | None, int | None]:
    if len(blob) < 24 or blob[:8] != b"\x89PNG\r\n\x1a\n":
        return None, None
    return int.from_bytes(blob[16:20], "big"), int.from_bytes(blob[20:24], "big")


def _get_gif_size(blob: bytes) -> tuple[int | None, int | None]:
    if len(blob) < 10 or blob[:3] != b"GIF":
        return None, None
    return int.from_bytes(blob[6:8], "little"), int.from_bytes(blob[8:10], "little")


def _get_jpeg_size(blob: bytes) -> tuple[int | None, int | None]:
    if len(blob) < 4 or blob[:2] != b"\xff\xd8":
        return None, None
    i = 2
    while i + 9 < len(blob):
        if blob[i] != 0xFF:
            i += 1
            continue
        marker = blob[i + 1]
        i += 2
        if marker in {0xD8, 0xD9}:
            continue
        if i + 2 > len(blob):
            break
        seg_len = int.from_bytes(blob[i:i + 2], "big")
        if seg_len < 2 or i + seg_len > len(blob):
            break
        if marker in {
            0xC0, 0xC1, 0xC2, 0xC3,
            0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB,
            0xCD, 0xCE, 0xCF,
        } and i + 7 < len(blob):
            height = int.from_bytes(blob[i + 3:i + 5], "big")
            width = int.from_bytes(blob[i + 5:i + 7], "big")
            return width, height
        i += seg_len
    return None, None


def _detect_image_kind(blob: bytes) -> str | None:
    if len(blob) >= 8 and blob[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(blob) >= 3 and blob[:3] == b"GIF":
        return "gif"
    if len(blob) >= 2 and blob[:2] == b"\xff\xd8":
        return "jpeg"
    return None


def _read_image_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        blob = path.read_bytes()
    except OSError:
        return None, None

    kind = _detect_image_kind(blob)
    if kind == "png":
        return _get_png_size(blob)
    if kind == "gif":
        return _get_gif_size(blob)
    if kind in {"jpeg", "jpg"}:
        return _get_jpeg_size(blob)
    return None, None


def _should_skip_image(
    img_path: Path,
    width: int | None,
    height: int | None,
    context: dict,
    page_hashes: dict[int, set[str]],
    sha1: str,
) -> tuple[bool, str]:
    file_size = img_path.stat().st_size
    if file_size < MIN_IMAGE_BYTES:
        return True, f"tiny file ({file_size} bytes)"

    if width is not None and height is not None:
        if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
            return True, f"small dimensions ({width}x{height})"
        if width * height < MIN_IMAGE_AREA:
            return True, f"small area ({width * height})"
        aspect_ratio = max(width / max(height, 1), height / max(width, 1))
        if aspect_ratio > MAX_ASPECT_RATIO:
            return True, f"extreme aspect ratio ({width}x{height})"

    page = context.get("page")
    if isinstance(page, int):
        page_seen = page_hashes.setdefault(page, set())
        if sha1 in page_seen:
            return True, "duplicate image on same page"
        page_seen.add(sha1)

    heading = (context.get("heading") or "").strip().lower()
    ctx_text = (context.get("context") or "").strip().lower()
    generic_heading = not heading or bool(re.fullmatch(r"slide\s+\d+", heading))
    weak_context = not ctx_text or len(ctx_text) < 12
    if generic_heading and weak_context and file_size < 20 * 1024:
        return True, "generic context and low-information asset"

    return False, ""


def consolidate_images(
    source_file: Path,
    output_md: Path,
    project_path: Path,
) -> int:
    """Copy extracted images into `<project>/images/` and update manifest.

    The source-to-md converters drop extracted images into
    `<output_md.parent>/<output_md.stem>_files/`. We mirror them to
    `<project>/images/` (using the original filename) and write a JSON
    manifest entry per image with the source filename, page/slide hint,
    nearest heading, and a short text snippet around the reference.

    Returns the number of images successfully consolidated. Existing
    manifest entries from previous source conversions are preserved.
    """
    asset_dir = output_md.parent / f"{output_md.stem}_files"
    if not asset_dir.is_dir():
        return 0

    images_dir = project_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    try:
        md_text = output_md.read_text(encoding="utf-8")
    except OSError:
        md_text = ""

    manifest_path = images_dir / "manifest.json"
    manifest: list[dict] = []
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                manifest = existing
        except (OSError, json.JSONDecodeError):
            manifest = []

    seen_files = {entry.get("filename") for entry in manifest}
    page_hashes: dict[int, set[str]] = {}
    for entry in manifest:
        if isinstance(entry.get("page"), int) and entry.get("sha1"):
            page_hashes.setdefault(entry["page"], set()).add(entry["sha1"])
    copied = 0
    skipped = 0

    for img_path in sorted(asset_dir.iterdir()):
        if not img_path.is_file():
            continue
        if img_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
            continue

        target_name = img_path.name
        if target_name in seen_files:
            # Already recorded; refresh file in case it changed.
            try:
                shutil.copy2(img_path, images_dir / target_name)
            except OSError:
                pass
            continue

        target_path = images_dir / target_name
        meta = _parse_image_filename(target_name, "")
        ctx = _extract_image_context_richer(md_text, target_name)
        width, height = _read_image_dimensions(img_path)
        sha1 = hashlib.sha1(img_path.read_bytes()).hexdigest()
        should_skip, reason = _should_skip_image(
            img_path,
            width,
            height,
            {"page": meta["page"] if meta["page"] is not None else ctx["page"], **ctx},
            page_hashes,
            sha1,
        )
        if should_skip:
            skipped += 1
            print(f"  [SKIP] {img_path.name}: {reason}")
            continue

        try:
            shutil.copy2(img_path, target_path)
        except OSError as exc:
            print(f"  [WARN] Could not copy {img_path.name}: {exc}", file=sys.stderr)
            continue

        manifest.append(
            {
                "filename": target_name,
                "source_file": source_file.name,
                "page": meta["page"] if meta["page"] is not None else ctx["page"],
                "heading": ctx["heading"],
                "context": ctx["context"],
                "width": width,
                "height": height,
                "file_size": img_path.stat().st_size,
                "sha1": sha1,
            }
        )
        seen_files.add(target_name)
        copied += 1

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if copied:
        print(f"  Consolidated {copied} image(s) -> {images_dir}")
    if skipped:
        print(f"  Skipped {skipped} decorative/low-value image(s)")
    print(f"  Manifest: {manifest_path} ({len(manifest)} total entries)")
    return copied


def main() -> int:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <source_file> <project_path>")
        print("")
        print("Examples:")
        print(f"  {sys.argv[0]} chapter2.pdf projects/mechanics_ch2")
        print(f"  {sys.argv[0]} lecture.pptx projects/control_ch1")
        print(f"  {sys.argv[0]} notes.docx projects/english_unit3")
        print(f"  {sys.argv[0]} legacy.ppt projects/legacy_lesson")
        return 1

    source_file = Path(sys.argv[1]).resolve()
    project_path = Path(sys.argv[2]).resolve()

    if not source_file.exists():
        print(f"[ERROR] Source file not found: {source_file}", file=sys.stderr)
        return 1

    # Legacy .ppt pre-conversion
    original_source = source_file
    if source_file.suffix.lower() == ".ppt":
        try:
            source_file = convert_legacy_ppt(source_file)
        except RuntimeError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1

    # Create project structure
    sources_dir = project_path / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    output_md = sources_dir / f"{original_source.stem}.md"

    converter_name, category = detect_converter(source_file)

    if converter_name is None:
        # Direct copy (md, txt, csv)
        copy_or_read_directly(source_file, output_md)
    else:
        repo_root = resolve_repo_root()
        converter_script = (
            repo_root
            / "skills"
            / "ppt-master"
            / "scripts"
            / "source_to_md"
            / converter_name
        )
        if not converter_script.exists():
            print(
                f"[ERROR] Converter script not found: {converter_script}",
                file=sys.stderr,
            )
            return 1
        run_converter(converter_script, source_file, output_md)

    if not output_md.exists():
        print(f"[ERROR] Expected output file not found: {output_md}", file=sys.stderr)
        return 1

    # Mirror extracted images into <project>/images/ and write manifest.json
    try:
        consolidate_images(original_source, output_md, project_path)
    except Exception as exc:
        print(f"[WARN] Image consolidation failed: {exc}", file=sys.stderr)

    print(f"\nDone. Markdown written to: {output_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
