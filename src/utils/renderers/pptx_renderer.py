import logging
import shutil
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pymupdf
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from src.schemas import InputAsset, LessonScript, PageBlock, PPTOutline, SlideOutline
from src.utils.logging_utils import resolve_runtime_output_path

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)
PAGE_BG = RGBColor(248, 249, 251)
ACCENT = RGBColor(18, 88, 132)
ACCENT_DARK = RGBColor(13, 47, 71)
ACCENT_LIGHT = RGBColor(225, 239, 247)
SECONDARY = RGBColor(214, 108, 36)
TEXT_DARK = RGBColor(35, 39, 47)
TEXT_MUTED = RGBColor(91, 101, 112)
WHITE = RGBColor(255, 255, 255)
BORDER = RGBColor(208, 214, 222)
FONT_NAME = "Microsoft YaHei"
DIRECT_IMAGE_FILE_TYPES = {"png", "jpg", "jpeg", "webp", "image"}
PAGE_RENDER_FILE_TYPES = {"pdf", "pptx", "ppt"} | DIRECT_IMAGE_FILE_TYPES

logger = logging.getLogger(__name__)


def render_ppt_outline(
    ppt_outline: PPTOutline | dict,
    output_path: str | Path,
    lesson_script: Optional[LessonScript | dict] = None,
    source_assets: Optional[Sequence[InputAsset | dict]] = None,
    source_pages: Optional[Sequence[PageBlock | dict]] = None,
) -> Path:
    outline = ppt_outline if isinstance(ppt_outline, PPTOutline) else PPTOutline.model_validate(ppt_outline)
    _ = (
        lesson_script
        if lesson_script is None or isinstance(lesson_script, LessonScript)
        else LessonScript.model_validate(lesson_script)
    )
    normalized_assets = [
        asset if isinstance(asset, InputAsset) else InputAsset.model_validate(asset)
        for asset in (source_assets or [])
    ]
    normalized_pages = [
        page if isinstance(page, PageBlock) else PageBlock.model_validate(page)
        for page in (source_pages or [])
    ]

    resolved_output_path = resolve_runtime_output_path(str(output_path))
    if resolved_output_path is None:
        raise RuntimeError("Unable to resolve PPT output path.")

    render_context = _build_render_context(
        output_path=resolved_output_path,
        source_assets=normalized_assets,
        source_pages=normalized_pages,
    )

    presentation = Presentation()
    presentation.slide_width = SLIDE_WIDTH
    presentation.slide_height = SLIDE_HEIGHT
    presentation.core_properties.title = outline.deck_title
    presentation.core_properties.subject = "ChaoxingAgent generated presentation"
    presentation.core_properties.author = "ChaoxingAgent"

    for slide_index, slide_outline in enumerate(outline.slides, start=1):
        _render_slide(
            presentation=presentation,
            slide_outline=slide_outline,
            slide_index=slide_index,
            total_slides=len(outline.slides),
            render_context=render_context,
        )

    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(resolved_output_path)
    return resolved_output_path


def _render_slide(
    presentation: Presentation,
    slide_outline: SlideOutline,
    slide_index: int,
    total_slides: int,
    render_context: dict,
) -> None:
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    _set_slide_background(slide)

    if slide_outline.layout_template == "cover_layout":
        _render_cover_slide(slide, slide_outline, render_context)
    elif slide_outline.layout_template == "agenda_layout":
        _render_agenda_slide(slide, slide_outline, render_context)
    elif slide_outline.layout_template == "formula_layout":
        _render_formula_slide(slide, slide_outline, render_context)
    elif slide_outline.layout_template == "process_layout":
        _render_process_slide(slide, slide_outline, render_context)
    elif slide_outline.layout_template == "summary_layout":
        _render_summary_slide(slide, slide_outline, render_context)
    elif slide_outline.layout_template == "example_layout":
        _render_example_slide(slide, slide_outline, render_context)
    elif slide_outline.layout_template == "comparison_layout":
        _render_comparison_slide(slide, slide_outline, render_context)
    else:
        _render_standard_slide(slide, slide_outline, render_context)

    _add_slide_footer(slide, slide_outline, slide_index, total_slides)


def _set_slide_background(slide) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = PAGE_BG


def _render_cover_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    """Simplified cover slide - title centered with bullets at bottom."""
    # Full screen background
    bg = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(0),
        Inches(0),
        SLIDE_WIDTH,
        SLIDE_HEIGHT,
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = ACCENT_DARK
    bg.line.fill.background()

    # Centered title
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11.33), Inches(1.5))
    tf = title_box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = slide_outline.title
    p.alignment = PP_ALIGN.CENTER
    _style_run(p.runs[0], font_size=36, bold=True, color=WHITE)

    # Subtitle
    if slide_outline.subtitle:
        sub_box = slide.shapes.add_textbox(Inches(1), Inches(4), Inches(11.33), Inches(0.6))
        stf = sub_box.text_frame
        stf.clear()
        sp = stf.paragraphs[0]
        sp.text = slide_outline.subtitle
        sp.alignment = PP_ALIGN.CENTER
        _style_run(sp.runs[0], font_size=18, color=RGBColor(200, 200, 200))

    # Bullets at bottom (3-4 items in a row)
    bullets = slide_outline.bullets[:4]
    if bullets:
        card_width = Inches(3.0)
        gap = Inches(0.3)
        start_x = (SLIDE_WIDTH - (card_width * len(bullets) + gap * (len(bullets) - 1))) / 2

        for i, bullet in enumerate(bullets):
            left = start_x + i * (card_width + gap)
            # Card background
            card = slide.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, Inches(5.2), card_width, Inches(1.8)
            )
            card.fill.solid()
            card.fill.fore_color.rgb = WHITE
            card.line.fill.background()

            # Number circle
            circle = slide.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.OVAL, left + Inches(0.15), Inches(5.4), Inches(0.4), Inches(0.4)
            )
            circle.fill.solid()
            circle.fill.fore_color.rgb = SECONDARY
            circle.line.fill.background()

            # Number text
            num_box = slide.shapes.add_textbox(left + Inches(0.15), Inches(5.42), Inches(0.4), Inches(0.4))
            ntf = num_box.text_frame
            ntf.clear()
            np = ntf.paragraphs[0]
            np.text = str(i + 1)
            np.alignment = PP_ALIGN.CENTER
            _style_run(np.runs[0], font_size=12, bold=True, color=WHITE)

            # Bullet text
            text_box = slide.shapes.add_textbox(left + Inches(0.6), Inches(5.4), Inches(2.2), Inches(1.4))
            ttf = text_box.text_frame
            ttf.clear()
            ttf.word_wrap = True
            tp = ttf.paragraphs[0]
            tp.text = bullet[:30]  # Truncate if too long
            _style_run(tp.runs[0], font_size=11, color=TEXT_DARK)


def _render_standard_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    """Simplified standard slide - top title bar + main content area."""

    # Top title bar
    title_bar = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(0), SLIDE_WIDTH, Inches(1.0)
    )
    title_bar.fill.solid()
    title_bar.fill.fore_color.rgb = ACCENT
    title_bar.line.fill.background()

    # Title text
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12), Inches(0.6))
    tf = title_box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = slide_outline.title
    p.alignment = PP_ALIGN.LEFT
    _style_run(p.runs[0], font_size=28, bold=True, color=WHITE)

    # Check for visual
    has_visual = any(visual.visual_type != "none" for visual in slide_outline.visual_plan)

    if has_visual:
        # Left: bullets (60%), Right: visual (40%)
        _add_bullets(
            slide=slide,
            title=slide_outline.title,
            bullets=slide_outline.bullets,
            left=Inches(0.5),
            top=Inches(1.3),
            width=Inches(7.5),
            height=Inches(5.5),
            numbered=False,
            compact=False,
            font_size=18,
        )

        # Visual on right
        _add_visual_slot(
            slide=slide,
            slide_outline=slide_outline,
            render_context=render_context,
            title="素材",
            left=Inches(8.2),
            top=Inches(1.3),
            width=Inches(4.8),
            height=Inches(5.5),
            fill_color=WHITE,
            text_color=TEXT_DARK,
        )
    else:
        # Full width bullets
        _add_bullets(
            slide=slide,
            title=slide_outline.title,
            bullets=slide_outline.bullets,
            left=Inches(0.5),
            top=Inches(1.3),
            width=Inches(12.3),
            height=Inches(5.5),
            numbered=False,
            compact=False,
            font_size=20,
        )


def _render_agenda_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    """Simplified - use standard layout."""
    _render_standard_slide(slide, slide_outline, render_context)


def _render_formula_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    """Simplified - use standard layout."""
    _render_standard_slide(slide, slide_outline, render_context)


def _render_process_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    """Simplified - use standard layout."""
    _render_standard_slide(slide, slide_outline, render_context)


def _render_summary_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    """Simplified - use standard layout."""
    _render_standard_slide(slide, slide_outline, render_context)


def _render_example_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    """Simplified example slide - uses standard layout."""
    # Use standard slide layout for consistency
    _render_standard_slide(slide, slide_outline, render_context)


def _render_comparison_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    """Simplified comparison slide - two column layout."""
    # Top title bar
    title_bar = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(0), SLIDE_WIDTH, Inches(1.0)
    )
    title_bar.fill.solid()
    title_bar.fill.fore_color.rgb = ACCENT
    title_bar.line.fill.background()

    # Title text
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12), Inches(0.6))
    tf = title_box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = slide_outline.title
    p.alignment = PP_ALIGN.LEFT
    _style_run(p.runs[0], font_size=28, bold=True, color=WHITE)

    # Two column layout for comparison
    bullets = list(slide_outline.bullets or [])
    midpoint = max(1, (len(bullets) + 1) // 2)
    left_bullets = bullets[:midpoint]
    right_bullets = bullets[midpoint:] or ["待补充"]

    # Left column title
    left_title = slide.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(5.5), Inches(0.4))
    tf = left_title.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = "对比维度 A"
    _style_run(p.runs[0], font_size=16, bold=True, color=ACCENT_DARK)

    # Right column title
    right_title = slide.shapes.add_textbox(Inches(6.5), Inches(1.3), Inches(5.5), Inches(0.4))
    tf = right_title.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = "对比维度 B"
    _style_run(p.runs[0], font_size=16, bold=True, color=SECONDARY)

    # Left bullets
    _add_bullets(
        slide=slide,
        title="",
        bullets=left_bullets,
        left=Inches(0.5),
        top=Inches(1.8),
        width=Inches(5.5),
        height=Inches(4.0),
    )

    # Right bullets
    _add_bullets(
        slide=slide,
        title="",
        bullets=right_bullets,
        left=Inches(6.5),
        top=Inches(1.8),
        width=Inches(5.5),
        height=Inches(4.0),
    )


def _add_top_bar(slide) -> None:
    bar = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(0),
        Inches(0),
        SLIDE_WIDTH,
        Inches(0.34),
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()


def _add_slide_title(slide, title: str, subtitle: Optional[str]) -> None:
    title_box = slide.shapes.add_textbox(Inches(0.78), Inches(0.58), Inches(11.1), Inches(0.65))
    title_frame = title_box.text_frame
    title_frame.clear()
    title_frame.word_wrap = True
    paragraph = title_frame.paragraphs[0]
    paragraph.text = title
    _style_run(paragraph.runs[0], font_size=24, bold=True, color=TEXT_DARK)

    if subtitle:
        subtitle_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.1), Inches(8.4), Inches(0.36))
        subtitle_frame = subtitle_box.text_frame
        subtitle_frame.clear()
        paragraph = subtitle_frame.paragraphs[0]
        paragraph.text = subtitle
        _style_run(paragraph.runs[0], font_size=11, color=TEXT_MUTED)


def _add_bullets(
    slide,
    title: str,
    bullets: Sequence[str],
    left,
    top,
    width,
    height,
    numbered: bool = False,
    compact: bool = False,
    font_size: Optional[int] = None,
) -> None:
    bullet_box = slide.shapes.add_textbox(left, top, width, height)
    frame = bullet_box.text_frame
    frame.clear()
    frame.word_wrap = True
    for index, bullet in enumerate(bullets or [title], start=1):
        paragraph = frame.paragraphs[0] if index == 1 else frame.add_paragraph()
        paragraph.text = f"{index}. {bullet}" if numbered else f"- {bullet}"
        paragraph.level = 0
        paragraph.space_after = Pt(5 if compact else 8)
        _style_run(paragraph.runs[0], font_size=font_size or (14 if compact else 15), color=TEXT_DARK)


def _add_bullets_columns(
    slide, bullets: Sequence[str], left, top, width, height, columns: int, font_size: int
) -> None:
    column_width = width / columns
    rows_per_column = max(1, (len(bullets) + columns - 1) // columns)
    for column in range(columns):
        subset = list(bullets[column * rows_per_column : (column + 1) * rows_per_column])
        if not subset:
            continue
        _add_bullets(
            slide=slide,
            title="",
            bullets=subset,
            left=left + column * column_width,
            top=top,
            width=column_width - Inches(0.15),
            height=height,
            compact=True,
            font_size=font_size,
        )


def _add_highlight_panel(slide, left, top, width, height, fill_color: RGBColor) -> None:
    panel = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        left,
        top,
        width,
        height,
    )
    panel.fill.solid()
    panel.fill.fore_color.rgb = fill_color
    panel.line.color.rgb = BORDER
    panel.line.width = Pt(1.0)


def _add_column_title(slide, title: str, left, top, color: RGBColor) -> None:
    title_box = slide.shapes.add_textbox(left, top, Inches(2.4), Inches(0.35))
    frame = title_box.text_frame
    frame.clear()
    paragraph = frame.paragraphs[0]
    paragraph.text = title
    _style_run(paragraph.runs[0], font_size=13, bold=True, color=color)


def _add_note_panel(slide, title: str, text: str, left, top, width, height) -> None:
    _add_highlight_panel(slide, left, top, width, height, WHITE)
    title_box = slide.shapes.add_textbox(
        left + Inches(0.18), top + Inches(0.14), width - Inches(0.36), Inches(0.28)
    )
    title_frame = title_box.text_frame
    title_frame.clear()
    paragraph = title_frame.paragraphs[0]
    paragraph.text = title
    _style_run(paragraph.runs[0], font_size=11, bold=True, color=ACCENT_DARK)

    content_box = slide.shapes.add_textbox(
        left + Inches(0.18), top + Inches(0.46), width - Inches(0.36), height - Inches(0.58)
    )
    content_frame = content_box.text_frame
    content_frame.clear()
    content_frame.word_wrap = True
    paragraph = content_frame.paragraphs[0]
    paragraph.text = text
    _style_run(paragraph.runs[0], font_size=10, color=TEXT_MUTED)


def count_presentation_pages(file_path: str | Path) -> int:
    source_path = Path(file_path)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        with pymupdf.open(source_path) as document:
            return len(document)
    if suffix in {".pptx", ".ppt"}:
        return len(Presentation(source_path).slides)

    raise ValueError(f"Unsupported preview source type: {source_path.suffix or '<none>'}")


def render_presentation_preview_image(
    file_path: str | Path,
    slide_number: int,
    cache_dir: str | Path,
) -> tuple[Optional[Path], Optional[str]]:
    source_path = Path(file_path)
    target_cache_dir = Path(cache_dir)
    target_cache_dir.mkdir(parents=True, exist_ok=True)

    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        rendered = _render_pdf_page_image(source_path, slide_number, target_cache_dir)
        if rendered is not None:
            return rendered, None
        return None, f"PDF page unavailable: {slide_number}"

    if suffix in {".pptx", ".ppt"}:
        return _render_pptx_slide_image(
            source_path,
            slide_number,
            target_cache_dir,
            {"visual_warning_keys": set()},
        )

    return None, f"Unsupported preview source type: {source_path.suffix or '<none>'}"


def _add_source_badge(slide, left, top, width, height, labels: Sequence[str]) -> None:
    _add_highlight_panel(slide, left, top, width, height, RGBColor(246, 248, 252))
    text = "来源页：" + ("、".join(labels) if labels else "无")
    _add_text_panel(
        slide=slide,
        text=text,
        left=left + Inches(0.16),
        top=top + Inches(0.08),
        width=width - Inches(0.32),
        height=height - Inches(0.24),
        font_size=9,
        bold=False,
        color=TEXT_MUTED,
    )


def _add_text_panel(
    slide, text: str, left, top, width, height, font_size: int, bold: bool, color: RGBColor
) -> None:
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    _style_run(paragraph.runs[0], font_size=font_size, bold=bold, color=color)


def _add_step_badge(slide, index: int, left, top) -> None:
    badge = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.OVAL,
        left,
        top,
        Inches(0.42),
        Inches(0.42),
    )
    badge.fill.solid()
    badge.fill.fore_color.rgb = ACCENT
    badge.line.fill.background()
    text_box = slide.shapes.add_textbox(left, top + Inches(0.02), Inches(0.42), Inches(0.32))
    frame = text_box.text_frame
    frame.clear()
    paragraph = frame.paragraphs[0]
    paragraph.text = str(index)
    paragraph.alignment = PP_ALIGN.CENTER
    _style_run(paragraph.runs[0], font_size=11, bold=True, color=WHITE)


def _add_visual_slot(
    slide,
    slide_outline: SlideOutline,
    render_context: dict,
    title: str,
    left,
    top,
    width,
    height,
    fill_color: RGBColor,
    text_color: RGBColor,
) -> None:
    image_path = _resolve_visual_image_path(slide_outline, render_context)
    if image_path is not None and image_path.exists():
        slide.shapes.add_picture(str(image_path), left, top, width=width, height=height)
        return

    panel = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        left,
        top,
        width,
        height,
    )
    panel.fill.solid()
    panel.fill.fore_color.rgb = fill_color
    panel.line.color.rgb = BORDER if fill_color != ACCENT_DARK else WHITE
    panel.line.width = Pt(1.0)

    visual_types = [
        visual.visual_type for visual in slide_outline.visual_plan if visual.visual_type != "none"
    ]
    label = title
    if visual_types:
        label += "\n" + " / ".join(_visual_label(item) for item in visual_types[:2])
        source_ids = []
        for visual in slide_outline.visual_plan:
            for source_unit_id in visual.source_unit_ids[:2]:
                if source_unit_id not in source_ids:
                    source_ids.append(source_unit_id)
        if source_ids:
            label += "\n" + "、".join(source_ids[:2])
    else:
        label += "\n无额外素材"

    text_box = slide.shapes.add_textbox(
        left + Inches(0.2), top + Inches(0.18), width - Inches(0.4), height - Inches(0.36)
    )
    frame = text_box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = frame.paragraphs[0]
    paragraph.text = label
    paragraph.alignment = PP_ALIGN.CENTER
    _style_run(paragraph.runs[0], font_size=13, bold=True, color=text_color)


def _add_slide_footer(slide, slide_outline: SlideOutline, slide_index: int, total_slides: int) -> None:
    source_hint = "、".join(slide_outline.source_page_ids[:3]) or "无来源页"
    footer_box = slide.shapes.add_textbox(Inches(0.75), Inches(6.8), Inches(11.8), Inches(0.28))
    frame = footer_box.text_frame
    frame.clear()
    paragraph = frame.paragraphs[0]
    paragraph.text = f"来源: {source_hint}"
    _style_run(paragraph.runs[0], font_size=9, color=TEXT_MUTED)

    index_box = slide.shapes.add_textbox(Inches(12.0), Inches(6.78), Inches(0.7), Inches(0.28))
    index_frame = index_box.text_frame
    index_frame.clear()
    paragraph = index_frame.paragraphs[0]
    paragraph.text = f"{slide_index}/{total_slides}"
    paragraph.alignment = PP_ALIGN.RIGHT
    _style_run(paragraph.runs[0], font_size=10, color=TEXT_MUTED)


def _style_run(run, font_size: int, color: RGBColor, bold: bool = False) -> None:
    run.font.name = FONT_NAME
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color


def _short_note(text: str, limit: int = 140) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _visual_label(visual_type: str) -> str:
    return {
        "source_image": "来源图片",
        "source_table": "来源表格",
        "source_formula": "来源公式",
    }.get(visual_type, "来源素材")


def _visual_slot_title(slide_type: str) -> str:
    return {
        "formula": "公式素材",
        "example": "案例素材",
        "comparison": "对比素材",
        "process": "流程素材",
        "summary": "总结素材",
    }.get(slide_type, "来源素材")


def _build_render_context(
    output_path: Path,
    source_assets: Sequence[InputAsset],
    source_pages: Sequence[PageBlock],
) -> dict:
    asset_by_id = {asset.asset_id: asset for asset in source_assets if asset.asset_id}
    page_by_id = {(page.page_id or f"page_{page.page}"): page for page in source_pages}
    cache_dir = output_path.parent / f"{output_path.stem}_assets"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return {
        "asset_by_id": asset_by_id,
        "page_by_id": page_by_id,
        "cache_dir": cache_dir,
    }


def _resolve_visual_image_path(slide_outline: SlideOutline, render_context: dict) -> Optional[Path]:
    """Resolve visual image from visual_plan's source_unit_ids.

    The source_unit_ids format is: {asset_id}_slide_{slide_number}
    e.g., 'manual_asset_1_slide_7' -> asset_id='manual_asset_1', slide_number=7
    """
    # First, try to use visual_plan's source_unit_ids
    for visual in slide_outline.visual_plan:
        if visual.visual_type == "none":
            continue

        for source_unit_id in visual.source_unit_ids:
            # Parse source_unit_id: {asset_id}_slide_{number}
            slide_number = _parse_slide_number(source_unit_id)
            if slide_number is None:
                continue

            # Try to find the asset from the unit_id prefix
            asset_id_prefix = source_unit_id.rsplit("_slide_", 1)[0]
            asset = render_context["asset_by_id"].get(asset_id_prefix)

            if asset is None:
                continue

            file_path = Path(asset.file_path)
            file_type = (asset.file_type or "").lower()

            if file_type == "pdf":
                result = _render_pdf_page_image(file_path, slide_number, render_context["cache_dir"])
                if result:
                    return result
            elif file_type in {"pptx", "ppt"}:
                result = _render_pptx_slide_image(file_path, slide_number, render_context["cache_dir"])
                if result:
                    return result
            elif file_type in {"png", "jpg", "jpeg", "webp", "image"} and file_path.exists():
                return file_path

    # Fallback: try source_page_ids
    for page_id in slide_outline.source_page_ids:
        page = render_context["page_by_id"].get(page_id)
        if page is None:
            continue
        asset = render_context["asset_by_id"].get(page.file_id)
        if asset is None:
            continue
        file_path = Path(asset.file_path)
        file_type = (asset.file_type or page.file_type or "").lower()
        if file_type == "pdf":
            return _render_pdf_page_image(file_path, page.page, render_context["cache_dir"])
        if file_type in {"png", "jpg", "jpeg", "webp", "image"} and file_path.exists():
            return file_path
    return None


def _parse_slide_number(source_unit_id: str) -> Optional[int]:
    """Parse slide number from source_unit_id.

    Examples:
        'manual_asset_1_slide_7' -> 7
        'asset_slide_10' -> 10
    """
    try:
        # Format: {anything}_slide_{number}
        if "_slide_" in source_unit_id:
            num_str = source_unit_id.rsplit("_slide_", 1)[-1]
            return int(num_str)
    except (ValueError, IndexError):
        pass
    return None


def _render_pdf_page_image(pdf_path: Path, page_number: int, cache_dir: Path) -> Optional[Path]:
    if not pdf_path.exists():
        return None
    cache_path = cache_dir / f"{pdf_path.stem}_page_{page_number}.png"
    if cache_path.exists():
        return cache_path
    with pymupdf.open(pdf_path) as document:
        if page_number < 1 or page_number > len(document):
            return None
        page = document[page_number - 1]
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6), alpha=False)
        pixmap.save(str(cache_path))
    return cache_path


def _render_pptx_slide_image(pptx_path: Path, slide_number: int, cache_dir: Path) -> Optional[Path]:
    """Render a PPTX slide to image using LibreOffice.

    Args:
        pptx_path: Path to the PPTX file.
        slide_number: 1-based slide number.
        cache_dir: Directory to save cached images.

    Returns:
        Path to the rendered image, or None if failed.
    """
    if not pptx_path.exists():
        return None

    # Check if LibreOffice is available
    soffice_path = _find_soffice_path()
    if not soffice_path:
        return None

    # Try direct PNG export first (LibreOffice can export all slides as PNG)
    cache_path = cache_dir / f"{pptx_path.stem}_slide_{slide_number}.png"
    if cache_path.exists():
        return cache_path

    try:
        # Use LibreOffice to convert PPTX to PNG
        # This exports all slides, we need to find the specific slide number
        result = _convert_pptx_to_png_with_libreoffice(pptx_path, cache_dir, soffice_path)

        if not result:
            return None

        # Find the generated PNG for the specific slide
        all_pngs = sorted(cache_dir.glob(f"{pptx_path.stem}_slide_*.png"))

        if slide_number <= len(all_pngs):
            return all_pngs[slide_number - 1]

        return None

    except Exception:
        return None


def _find_soffice_path() -> Optional[str]:
    """Find LibreOffice executable path."""
    import shutil
    from pathlib import Path

    candidates = [
        shutil.which("soffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    return None


def _convert_pptx_to_png_with_libreoffice(pptx_path: Path, output_dir: Path, soffice_path: str) -> bool:
    """Convert PPTX to PNG using LibreOffice."""
    import subprocess

    output_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            soffice_path,
            "--headless",
            "--nologo",
            "--nodefault",
            "--norestore",
            "--convert-to",
            "png",
            "--outdir",
            str(output_dir),
            str(pptx_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    return result.returncode == 0


def _copy_shape_to_slide(shape, target_slide):
    """Copy a shape from one slide to another."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    try:
        # Get shape properties
        left = shape.left
        top = shape.top
        width = shape.width
        height = shape.height

        if shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX:
            # Create new text box
            new_shape = target_slide.shapes.add_textbox(left, top, width, height)
            # Copy text
            if shape.text_frame:
                new_shape.text_frame.text = shape.text_frame.text
            return new_shape
        elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            # For pictures, we'd need to extract and re-add
            return None
        else:
            # For other shapes, try to add as picture placeholder
            return None
    except Exception:
        return None


# Updated renderer implementations below override earlier simplified helpers.
# Keeping them here avoids rewriting the entire module while restoring layout
# variety and a more reliable visual extraction path.
def _primary_note_text(slide_outline: SlideOutline, fallback: str = "") -> str:
    for candidate in (slide_outline.subtitle, slide_outline.speaker_notes, fallback):
        if candidate:
            return _short_note(candidate, 180)
    if slide_outline.bullets:
        return _short_note(slide_outline.bullets[0], 180)
    return _short_note(slide_outline.title, 180)


def _has_visual_candidate(slide_outline: SlideOutline, render_context: dict) -> bool:
    if any(visual.visual_type != "none" for visual in slide_outline.visual_plan):
        return True

    for page_id in slide_outline.source_page_ids:
        page = render_context["page_by_id"].get(page_id)
        if page is None:
            continue
        asset = render_context["asset_by_id"].get(page.file_id) if page.file_id else None
        file_type = (page.file_type or (asset.file_type if asset else "") or "").lower()
        if file_type in PAGE_RENDER_FILE_TYPES:
            return True
    return False


def _warn_once(render_context: dict, key: str, message: str) -> None:
    warning_keys = render_context.setdefault("visual_warning_keys", set())
    if key in warning_keys:
        return
    logger.warning(message)
    warning_keys.add(key)


def _render_asset_page_image(
    file_path: Path,
    file_type: str,
    page_number: int,
    render_context: dict,
) -> tuple[Optional[Path], Optional[str]]:
    if not file_path.exists():
        return None, f"Source file missing: {file_path.name}"

    if file_type == "pdf":
        rendered = _render_pdf_page_image(file_path, page_number, render_context["cache_dir"])
        if rendered is not None:
            return rendered, None
        return None, f"PDF page unavailable: {file_path.name}#{page_number}"

    if file_type in {"pptx", "ppt"}:
        return _render_pptx_slide_image(file_path, page_number, render_context["cache_dir"], render_context)

    if file_type in DIRECT_IMAGE_FILE_TYPES:
        return file_path, None

    return None, None


def _visual_failure_text(messages: Sequence[str]) -> Optional[str]:
    for message in messages:
        if message:
            return message
    return None


def _build_render_context(
    output_path: Path,
    source_assets: Sequence[InputAsset],
    source_pages: Sequence[PageBlock],
) -> dict:
    asset_by_id = {asset.asset_id: asset for asset in source_assets if asset.asset_id}
    page_by_id = {(page.page_id or f"page_{page.page}"): page for page in source_pages}
    cache_dir = output_path.parent / f"{output_path.stem}_assets"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return {
        "asset_by_id": asset_by_id,
        "page_by_id": page_by_id,
        "cache_dir": cache_dir,
        "visual_warning_keys": set(),
    }


def _visual_label(visual_type: str) -> str:
    return {
        "source_image": "Source image",
        "source_table": "Source table",
        "source_formula": "Source formula",
    }.get(visual_type, "Source visual")


def _visual_slot_title(slide_type: str) -> str:
    return {
        "formula": "Formula visual",
        "example": "Example visual",
        "comparison": "Comparison visual",
        "process": "Process visual",
        "summary": "Summary visual",
    }.get(slide_type, "Source visual")


def _add_source_badge(slide, left, top, width, height, labels: Sequence[str]) -> None:
    _add_highlight_panel(slide, left, top, width, height, RGBColor(246, 248, 252))
    text = "Source pages: " + (", ".join(labels) if labels else "n/a")
    _add_text_panel(
        slide=slide,
        text=text,
        left=left + Inches(0.16),
        top=top + Inches(0.08),
        width=width - Inches(0.32),
        height=height - Inches(0.24),
        font_size=9,
        bold=False,
        color=TEXT_MUTED,
    )


def _add_slide_footer(slide, slide_outline: SlideOutline, slide_index: int, total_slides: int) -> None:
    source_hint = ", ".join(slide_outline.source_page_ids[:3]) or "n/a"
    footer_box = slide.shapes.add_textbox(Inches(0.75), Inches(6.8), Inches(11.2), Inches(0.28))
    frame = footer_box.text_frame
    frame.clear()
    paragraph = frame.paragraphs[0]
    paragraph.text = f"Source: {source_hint}"
    _style_run(paragraph.runs[0], font_size=9, color=TEXT_MUTED)

    index_box = slide.shapes.add_textbox(Inches(12.0), Inches(6.78), Inches(0.7), Inches(0.28))
    index_frame = index_box.text_frame
    index_frame.clear()
    paragraph = index_frame.paragraphs[0]
    paragraph.text = f"{slide_index}/{total_slides}"
    paragraph.alignment = PP_ALIGN.RIGHT
    _style_run(paragraph.runs[0], font_size=10, color=TEXT_MUTED)


def _add_visual_slot(
    slide,
    slide_outline: SlideOutline,
    render_context: dict,
    title: str,
    left,
    top,
    width,
    height,
    fill_color: RGBColor,
    text_color: RGBColor,
) -> None:
    image_path, warning = _resolve_visual_image_path(slide_outline, render_context)
    if image_path is not None and image_path.exists():
        slide.shapes.add_picture(str(image_path), left, top, width=width, height=height)
        return

    panel = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        left,
        top,
        width,
        height,
    )
    panel.fill.solid()
    panel.fill.fore_color.rgb = fill_color
    panel.line.color.rgb = BORDER if fill_color != ACCENT_DARK else WHITE
    panel.line.width = Pt(1.0)

    visual_types = [
        visual.visual_type for visual in slide_outline.visual_plan if visual.visual_type != "none"
    ]
    label_lines = [title]
    if visual_types:
        label_lines.append(" / ".join(_visual_label(item) for item in visual_types[:2]))
        source_ids = []
        for visual in slide_outline.visual_plan:
            for source_unit_id in visual.source_unit_ids[:2]:
                if source_unit_id not in source_ids:
                    source_ids.append(source_unit_id)
        if source_ids:
            label_lines.append(", ".join(source_ids[:2]))
    else:
        label_lines.append("No extracted image")

    if warning:
        label_lines.append(_short_note(warning, 90))

    text_box = slide.shapes.add_textbox(
        left + Inches(0.2), top + Inches(0.18), width - Inches(0.4), height - Inches(0.36)
    )
    frame = text_box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = frame.paragraphs[0]
    paragraph.text = "\n".join(label_lines)
    paragraph.alignment = PP_ALIGN.CENTER
    _style_run(paragraph.runs[0], font_size=13, bold=True, color=text_color)


def _resolve_visual_image_path(
    slide_outline: SlideOutline, render_context: dict
) -> tuple[Optional[Path], Optional[str]]:
    failure_messages: list[str] = []
    visuals = sorted(
        slide_outline.visual_plan,
        key=lambda item: 0 if item.visual_type == "source_image" else 1,
    )

    for visual in visuals:
        if visual.visual_type == "none":
            continue

        for source_unit_id in visual.source_unit_ids:
            slide_number = _parse_slide_number(source_unit_id)
            if slide_number is None:
                continue

            asset_id_prefix = source_unit_id.rsplit("_slide_", 1)[0]
            asset = render_context["asset_by_id"].get(asset_id_prefix)
            if asset is None:
                continue

            file_path = Path(asset.file_path)
            file_type = (asset.file_type or "").lower()
            image_path, warning = _render_asset_page_image(file_path, file_type, slide_number, render_context)
            if image_path is not None:
                return image_path, None
            if warning:
                failure_messages.append(warning)

    for page_id in slide_outline.source_page_ids:
        page = render_context["page_by_id"].get(page_id)
        if page is None:
            continue
        asset = render_context["asset_by_id"].get(page.file_id) if page.file_id else None
        if asset is None:
            continue

        file_path = Path(asset.file_path)
        file_type = (asset.file_type or page.file_type or "").lower()
        image_path, warning = _render_asset_page_image(file_path, file_type, page.page, render_context)
        if image_path is not None:
            return image_path, None
        if warning:
            failure_messages.append(warning)

    return None, _visual_failure_text(failure_messages)


def _render_standard_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    title_bar = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(0), SLIDE_WIDTH, Inches(1.0)
    )
    title_bar.fill.solid()
    title_bar.fill.fore_color.rgb = ACCENT
    title_bar.line.fill.background()

    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12), Inches(0.6))
    tf = title_box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = slide_outline.title
    p.alignment = PP_ALIGN.LEFT
    _style_run(p.runs[0], font_size=28, bold=True, color=WHITE)

    bullets = list(slide_outline.bullets or [slide_outline.title])
    note_text = _primary_note_text(slide_outline)
    has_visual = _has_visual_candidate(slide_outline, render_context)

    if has_visual:
        text_height = Inches(5.2)
        if note_text:
            _add_note_panel(
                slide=slide,
                title="Teaching cue",
                text=note_text,
                left=Inches(0.5),
                top=Inches(5.75),
                width=Inches(7.4),
                height=Inches(0.7),
            )
            text_height = Inches(4.4)

        _add_bullets(
            slide=slide,
            title=slide_outline.title,
            bullets=bullets,
            left=Inches(0.5),
            top=Inches(1.3),
            width=Inches(7.4),
            height=text_height,
            numbered=False,
            compact=False,
            font_size=18,
        )
        _add_visual_slot(
            slide=slide,
            slide_outline=slide_outline,
            render_context=render_context,
            title="Source visual",
            left=Inches(8.2),
            top=Inches(1.3),
            width=Inches(4.8),
            height=Inches(5.2),
            fill_color=WHITE,
            text_color=TEXT_DARK,
        )
        return

    if len(bullets) >= 5:
        _add_bullets_columns(
            slide=slide,
            bullets=bullets,
            left=Inches(0.5),
            top=Inches(1.4),
            width=Inches(12.1),
            height=Inches(4.5),
            columns=2,
            font_size=15,
        )
    else:
        _add_bullets(
            slide=slide,
            title=slide_outline.title,
            bullets=bullets,
            left=Inches(0.5),
            top=Inches(1.35),
            width=Inches(12.1),
            height=Inches(4.8),
            numbered=False,
            compact=False,
            font_size=20,
        )

    if note_text:
        _add_note_panel(
            slide=slide,
            title="Teaching cue",
            text=note_text,
            left=Inches(0.5),
            top=Inches(5.95),
            width=Inches(12.1),
            height=Inches(0.55),
        )


def _render_agenda_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    _add_top_bar(slide)
    _add_slide_title(slide, slide_outline.title, slide_outline.subtitle)

    bullets = list(slide_outline.bullets or [slide_outline.title])
    intro_text = _primary_note_text(slide_outline, fallback=bullets[0])
    _add_highlight_panel(slide, Inches(0.75), Inches(1.55), Inches(2.35), Inches(4.95), ACCENT_DARK)
    _add_text_panel(
        slide=slide,
        text="AGENDA",
        left=Inches(0.98),
        top=Inches(1.8),
        width=Inches(1.8),
        height=Inches(0.35),
        font_size=12,
        bold=True,
        color=WHITE,
    )
    _add_text_panel(
        slide=slide,
        text=_short_note(intro_text, 120),
        left=Inches(0.98),
        top=Inches(2.25),
        width=Inches(1.88),
        height=Inches(3.8),
        font_size=15,
        bold=False,
        color=WHITE,
    )

    card_width = Inches(4.35)
    card_height = Inches(1.08)
    start_x = Inches(3.45)
    start_y = Inches(1.68)
    gap_x = Inches(0.32)
    gap_y = Inches(0.28)
    for index, bullet in enumerate(bullets[:6], start=1):
        row = (index - 1) // 2
        column = (index - 1) % 2
        card_left = start_x + column * (card_width + gap_x)
        card_top = start_y + row * (card_height + gap_y)
        _add_highlight_panel(slide, card_left, card_top, card_width, card_height, WHITE)
        _add_step_badge(slide, index, card_left + Inches(0.16), card_top + Inches(0.28))
        _add_text_panel(
            slide=slide,
            text=_short_note(bullet, 56),
            left=card_left + Inches(0.72),
            top=card_top + Inches(0.2),
            width=card_width - Inches(0.92),
            height=card_height - Inches(0.28),
            font_size=14,
            bold=False,
            color=TEXT_DARK,
        )

    if slide_outline.source_page_ids:
        _add_source_badge(
            slide=slide,
            left=Inches(3.45),
            top=Inches(5.95),
            width=Inches(9.0),
            height=Inches(0.42),
            labels=slide_outline.source_page_ids[:4],
        )


def _render_formula_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    _add_top_bar(slide)
    _add_slide_title(slide, slide_outline.title, slide_outline.subtitle)

    bullets = list(slide_outline.bullets or [slide_outline.title])
    note_text = _primary_note_text(slide_outline, fallback=bullets[0])
    has_visual = _has_visual_candidate(slide_outline, render_context)

    if has_visual:
        _add_visual_slot(
            slide=slide,
            slide_outline=slide_outline,
            render_context=render_context,
            title=_visual_slot_title(slide_outline.slide_type),
            left=Inches(0.75),
            top=Inches(1.65),
            width=Inches(5.7),
            height=Inches(4.55),
            fill_color=WHITE,
            text_color=TEXT_DARK,
        )
        bullet_left = Inches(6.75)
        bullet_width = Inches(5.75)
    else:
        _add_highlight_panel(slide, Inches(0.75), Inches(1.65), Inches(4.45), Inches(4.55), ACCENT_LIGHT)
        _add_text_panel(
            slide=slide,
            text="FORMULA",
            left=Inches(1.0),
            top=Inches(1.95),
            width=Inches(2.0),
            height=Inches(0.3),
            font_size=12,
            bold=True,
            color=ACCENT_DARK,
        )
        _add_text_panel(
            slide=slide,
            text=_short_note(note_text, 140),
            left=Inches(1.0),
            top=Inches(2.35),
            width=Inches(3.95),
            height=Inches(3.1),
            font_size=17,
            bold=False,
            color=TEXT_DARK,
        )
        bullet_left = Inches(5.45)
        bullet_width = Inches(7.05)

    _add_highlight_panel(slide, bullet_left, Inches(1.65), bullet_width, Inches(3.55), WHITE)
    _add_column_title(slide, "Key points", bullet_left + Inches(0.2), Inches(1.88), ACCENT_DARK)
    _add_bullets(
        slide=slide,
        title="",
        bullets=bullets,
        left=bullet_left + Inches(0.18),
        top=Inches(2.18),
        width=bullet_width - Inches(0.36),
        height=Inches(2.7),
        compact=True,
        font_size=14,
    )
    _add_note_panel(
        slide=slide,
        title="Interpretation",
        text=note_text,
        left=bullet_left,
        top=Inches(5.38),
        width=bullet_width,
        height=Inches(0.9),
    )


def _render_process_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    _add_top_bar(slide)
    _add_slide_title(slide, slide_outline.title, slide_outline.subtitle)

    bullets = list(slide_outline.bullets or [slide_outline.title])
    steps = bullets[:4]
    extra_steps = bullets[4:]
    card_width = Inches(2.65)
    gap = Inches(0.42)
    start_x = Inches(0.78)
    card_top = Inches(2.15)

    for index, bullet in enumerate(steps, start=1):
        card_left = start_x + (index - 1) * (card_width + gap)
        if index < len(steps):
            connector = slide.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.RECTANGLE,
                card_left + card_width,
                card_top + Inches(0.63),
                gap - Inches(0.08),
                Inches(0.08),
            )
            connector.fill.solid()
            connector.fill.fore_color.rgb = ACCENT_LIGHT
            connector.line.fill.background()

        _add_step_badge(slide, index, card_left + Inches(1.06), Inches(1.58))
        _add_highlight_panel(slide, card_left, card_top, card_width, Inches(1.45), WHITE)
        _add_text_panel(
            slide=slide,
            text=_short_note(bullet, 52),
            left=card_left + Inches(0.18),
            top=card_top + Inches(0.24),
            width=card_width - Inches(0.36),
            height=Inches(0.96),
            font_size=13,
            bold=False,
            color=TEXT_DARK,
        )

    note_text = _primary_note_text(slide_outline, fallback=" -> ".join(steps))
    has_visual = _has_visual_candidate(slide_outline, render_context)
    if has_visual:
        _add_note_panel(
            slide=slide,
            title="Process cue",
            text=_short_note(" ".join(extra_steps) if extra_steps else note_text, 180),
            left=Inches(0.78),
            top=Inches(4.25),
            width=Inches(7.1),
            height=Inches(1.35),
        )
        _add_visual_slot(
            slide=slide,
            slide_outline=slide_outline,
            render_context=render_context,
            title=_visual_slot_title(slide_outline.slide_type),
            left=Inches(8.2),
            top=Inches(4.05),
            width=Inches(4.3),
            height=Inches(1.7),
            fill_color=WHITE,
            text_color=TEXT_DARK,
        )
        return

    _add_note_panel(
        slide=slide,
        title="Process cue",
        text=_short_note(" ".join(extra_steps) if extra_steps else note_text, 220),
        left=Inches(0.78),
        top=Inches(4.3),
        width=Inches(11.75),
        height=Inches(1.25),
    )


def _render_summary_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    _add_top_bar(slide)
    _add_slide_title(slide, slide_outline.title, slide_outline.subtitle)

    bullets = list(slide_outline.bullets or [slide_outline.title])
    summary_text = _primary_note_text(slide_outline, fallback=bullets[0])
    _add_highlight_panel(slide, Inches(0.75), Inches(1.6), Inches(11.75), Inches(0.95), ACCENT_LIGHT)
    _add_text_panel(
        slide=slide,
        text=_short_note(summary_text, 150),
        left=Inches(1.0),
        top=Inches(1.9),
        width=Inches(11.2),
        height=Inches(0.32),
        font_size=18,
        bold=True,
        color=ACCENT_DARK,
    )

    has_visual = _has_visual_candidate(slide_outline, render_context)
    if has_visual:
        _add_bullets_columns(
            slide=slide,
            bullets=bullets,
            left=Inches(0.75),
            top=Inches(2.95),
            width=Inches(7.0),
            height=Inches(2.95),
            columns=2,
            font_size=13,
        )
        _add_visual_slot(
            slide=slide,
            slide_outline=slide_outline,
            render_context=render_context,
            title=_visual_slot_title(slide_outline.slide_type),
            left=Inches(8.0),
            top=Inches(2.95),
            width=Inches(4.55),
            height=Inches(2.95),
            fill_color=WHITE,
            text_color=TEXT_DARK,
        )
    elif len(bullets) >= 4:
        _add_bullets_columns(
            slide=slide,
            bullets=bullets,
            left=Inches(0.75),
            top=Inches(2.95),
            width=Inches(11.75),
            height=Inches(2.95),
            columns=2,
            font_size=14,
        )
    else:
        _add_bullets(
            slide=slide,
            title="",
            bullets=bullets,
            left=Inches(0.75),
            top=Inches(2.95),
            width=Inches(11.75),
            height=Inches(2.95),
            compact=False,
            font_size=18,
        )

    _add_note_panel(
        slide=slide,
        title="Wrap-up",
        text=summary_text,
        left=Inches(0.75),
        top=Inches(6.05),
        width=Inches(11.75),
        height=Inches(0.45),
    )


def _render_example_slide(slide, slide_outline: SlideOutline, render_context: dict) -> None:
    _add_top_bar(slide)
    _add_slide_title(slide, slide_outline.title, slide_outline.subtitle)

    bullets = list(slide_outline.bullets or [slide_outline.title])
    note_text = _primary_note_text(slide_outline, fallback=bullets[0])
    has_visual = _has_visual_candidate(slide_outline, render_context)

    if has_visual:
        _add_visual_slot(
            slide=slide,
            slide_outline=slide_outline,
            render_context=render_context,
            title=_visual_slot_title(slide_outline.slide_type),
            left=Inches(0.75),
            top=Inches(1.68),
            width=Inches(6.0),
            height=Inches(4.35),
            fill_color=WHITE,
            text_color=TEXT_DARK,
        )
        _add_note_panel(
            slide=slide,
            title="Case setup",
            text=note_text,
            left=Inches(7.05),
            top=Inches(1.68),
            width=Inches(5.45),
            height=Inches(1.05),
        )
        _add_bullets(
            slide=slide,
            title="",
            bullets=bullets,
            left=Inches(7.05),
            top=Inches(2.95),
            width=Inches(5.45),
            height=Inches(3.1),
            compact=True,
            font_size=14,
        )
    else:
        _add_highlight_panel(slide, Inches(0.75), Inches(1.68), Inches(5.0), Inches(4.35), ACCENT_LIGHT)
        _add_text_panel(
            slide=slide,
            text="CASE",
            left=Inches(1.02),
            top=Inches(1.98),
            width=Inches(1.5),
            height=Inches(0.3),
            font_size=12,
            bold=True,
            color=ACCENT_DARK,
        )
        _add_text_panel(
            slide=slide,
            text=_short_note(note_text, 150),
            left=Inches(1.02),
            top=Inches(2.35),
            width=Inches(4.45),
            height=Inches(3.2),
            font_size=17,
            bold=False,
            color=TEXT_DARK,
        )
        _add_bullets(
            slide=slide,
            title="",
            bullets=bullets,
            left=Inches(6.05),
            top=Inches(1.95),
            width=Inches(6.5),
            height=Inches(4.1),
            compact=True,
            font_size=14,
        )

    if slide_outline.source_page_ids:
        _add_source_badge(
            slide=slide,
            left=Inches(0.75),
            top=Inches(6.12),
            width=Inches(11.75),
            height=Inches(0.38),
            labels=slide_outline.source_page_ids[:4],
        )


@lru_cache(maxsize=1)
def _find_soffice_path() -> Optional[str]:
    candidates = [
        shutil.which("soffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def _render_pptx_slide_image(
    pptx_path: Path,
    slide_number: int,
    cache_dir: Path,
    render_context: Optional[dict] = None,
) -> tuple[Optional[Path], Optional[str]]:
    if not pptx_path.exists():
        return None, f"Source file missing: {pptx_path.name}"

    soffice_path = _find_soffice_path()
    if not soffice_path:
        message = f"LibreOffice not found, unable to render PPT preview for {pptx_path.name}."
        if render_context is not None:
            _warn_once(render_context, f"missing-soffice:{pptx_path}", message)
        return None, "LibreOffice unavailable for PPT preview"

    preview_pdf_path = cache_dir / f"{pptx_path.stem}_render.pdf"
    if not preview_pdf_path.exists():
        ok, detail = _convert_pptx_to_pdf_with_libreoffice(pptx_path, preview_pdf_path, soffice_path)
        if not ok:
            message = f"LibreOffice failed to render PPT preview for {pptx_path.name}: {detail}"
            if render_context is not None:
                _warn_once(render_context, f"ppt-render:{pptx_path}", message)
            return None, "PPT preview export failed"

    rendered = _render_pdf_page_image(preview_pdf_path, slide_number, cache_dir)
    if rendered is not None:
        return rendered, None

    message = f"PPT preview page {slide_number} is unavailable for {pptx_path.name}."
    if render_context is not None:
        _warn_once(render_context, f"ppt-page:{pptx_path}:{slide_number}", message)
    return None, f"PPT preview page unavailable: {slide_number}"


def _convert_pptx_to_pdf_with_libreoffice(
    pptx_path: Path,
    output_pdf_path: Path,
    soffice_path: str,
) -> tuple[bool, str]:
    import subprocess

    output_dir = output_pdf_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = output_dir / f"{pptx_path.stem}_libreoffice_profile"
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
            "pdf",
            "--outdir",
            str(output_dir),
            str(pptx_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    generated_pdf_path = output_dir / f"{pptx_path.stem}.pdf"
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    detail = stderr or stdout or "LibreOffice did not return a usable output file."

    if result.returncode != 0 and not generated_pdf_path.exists():
        return False, detail
    if not generated_pdf_path.exists():
        return False, detail

    if generated_pdf_path != output_pdf_path:
        if output_pdf_path.exists():
            output_pdf_path.unlink()
        generated_pdf_path.replace(output_pdf_path)

    return True, ""


def _add_note_panel(slide, title: str, text: str, left, top, width, height) -> None:
    safe_height = max(height, Inches(0.68))
    _add_highlight_panel(slide, left, top, width, safe_height, WHITE)
    title_box = slide.shapes.add_textbox(
        left + Inches(0.18), top + Inches(0.12), width - Inches(0.36), Inches(0.24)
    )
    title_frame = title_box.text_frame
    title_frame.clear()
    paragraph = title_frame.paragraphs[0]
    paragraph.text = title
    _style_run(paragraph.runs[0], font_size=11, bold=True, color=ACCENT_DARK)

    content_box = slide.shapes.add_textbox(
        left + Inches(0.18),
        top + Inches(0.4),
        width - Inches(0.36),
        max(safe_height - Inches(0.5), Inches(0.18)),
    )
    content_frame = content_box.text_frame
    content_frame.clear()
    content_frame.word_wrap = True
    paragraph = content_frame.paragraphs[0]
    paragraph.text = text
    _style_run(paragraph.runs[0], font_size=10, color=TEXT_MUTED)
