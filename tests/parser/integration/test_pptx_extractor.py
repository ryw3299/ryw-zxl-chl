from types import SimpleNamespace

from src.utils.extractors.pptx import _extract_shape_text, _extract_slide_title


def test_extract_shape_text_ignores_placeholder_graphic_frame_without_text():
    shape = SimpleNamespace(has_text_frame=False)
    assert _extract_shape_text(shape) == ""


def test_extract_shape_text_supports_text_frame_paragraphs():
    paragraph = SimpleNamespace(text="Chapter Title", runs=[])
    text_frame = SimpleNamespace(paragraphs=[paragraph])
    shape = SimpleNamespace(has_text_frame=True, text_frame=text_frame)
    assert _extract_shape_text(shape) == "Chapter Title"


def test_extract_slide_title_handles_non_text_title_shape():
    title_shape = SimpleNamespace(has_text_frame=False)
    slide = SimpleNamespace(shapes=SimpleNamespace(title=title_shape))
    assert _extract_slide_title(slide) == ""
