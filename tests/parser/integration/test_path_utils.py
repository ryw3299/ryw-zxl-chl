from src.utils.path_utils import normalize_local_path, parse_asset_input_lines, parse_asset_input_spec


def test_normalize_local_path_strips_wrapping_quotes():
    assert (
        normalize_local_path('"C:\\Users\\Lenovo\\Desktop\\demo.pptx"')
        == r"C:\Users\Lenovo\Desktop\demo.pptx"
    )
    assert (
        normalize_local_path("'C:\\Users\\Lenovo\\Desktop\\demo.pdf'") == r"C:\Users\Lenovo\Desktop\demo.pdf"
    )


def test_parse_asset_input_spec_supports_optional_type_suffix():
    path_value, explicit_type = parse_asset_input_spec(r'"C:\Users\Lenovo\Desktop\demo.pptx"|pptx')
    assert path_value == r"C:\Users\Lenovo\Desktop\demo.pptx"
    assert explicit_type == "pptx"


def test_parse_asset_input_lines_supports_multiple_assets():
    parsed = parse_asset_input_lines(
        [
            r'"C:\Users\Lenovo\Desktop\a.pptx"',
            r"C:\Users\Lenovo\Desktop\b.pdf|pdf",
        ]
    )
    assert parsed == [
        (r"C:\Users\Lenovo\Desktop\a.pptx", None),
        (r"C:\Users\Lenovo\Desktop\b.pdf", "pdf"),
    ]
