from pathlib import Path

from src.utils.converters import ppt as ppt_converter


def test_convert_legacy_ppt_to_pptx_uses_libreoffice_only():
    source_path = Path(r"E:\ChaoXingAgent\tests\parser\fixtures\generated\dummy_legacy.ppt")
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"dummy")

    target_path = source_path.with_suffix(".pptx")
    if target_path.exists():
        target_path.unlink()

    original_build_target_path = ppt_converter._build_target_path
    original_get_status = ppt_converter.get_ppt_conversion_backend_status
    original_convert_libreoffice = ppt_converter._convert_with_libreoffice

    try:
        ppt_converter._build_target_path = lambda _source_path: target_path
        ppt_converter.get_ppt_conversion_backend_status = lambda: {
            "powerpoint_com": False,
            "libreoffice": "soffice.exe",
        }

        def fake_convert_libreoffice(_source_path, _target_path, _soffice_path):
            _target_path.write_bytes(b"pptx")

        ppt_converter._convert_with_libreoffice = fake_convert_libreoffice

        result = ppt_converter.convert_legacy_ppt_to_pptx(str(source_path))
        assert result == target_path
        assert target_path.exists()
    finally:
        ppt_converter._build_target_path = original_build_target_path
        ppt_converter.get_ppt_conversion_backend_status = original_get_status
        ppt_converter._convert_with_libreoffice = original_convert_libreoffice
        if source_path.exists():
            source_path.unlink()
        if target_path.exists():
            target_path.unlink()
