from importlib import import_module

__all__ = [
    "extract_docx_units",
    "extract_pdf_units",
    "extract_pptx_units",
    "extract_txt_units",
]


def __getattr__(name: str):
    module_map = {
        "extract_docx_units": ("src.utils.extractors.docx", "extract_docx_units"),
        "extract_pdf_units": ("src.utils.extractors.pdf", "extract_pdf_units"),
        "extract_pptx_units": ("src.utils.extractors.pptx", "extract_pptx_units"),
        "extract_txt_units": ("src.utils.extractors.txt", "extract_txt_units"),
    }

    target = module_map.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = target
    module = import_module(module_name)
    return getattr(module, attr_name)
