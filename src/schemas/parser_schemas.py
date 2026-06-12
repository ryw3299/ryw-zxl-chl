from pathlib import Path
from typing import Optional

from pydantic import Field, model_validator

from .base import BaseRequest, BaseResponse
from .common import (
    FileType,
    InputAsset,
    PageBlock,
    ParsedDocument,
    SectionBlock,
    SourceFile,
    StructuredLessonContent,
)


class ParserInput(BaseRequest):
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    assets: list[InputAsset] = Field(default_factory=list, description="Input assets to parse")
    parse_instruction: Optional[str] = Field(default=None, description="User-provided parsing instruction")

    file_id: Optional[str] = Field(default=None, description="Legacy single-file identifier")
    file_name: str = Field(default="", description="Legacy single-file name")
    file_path: Optional[str] = Field(default=None, description="Legacy single-file path")
    file_type: Optional[FileType] = Field(default=None, description="Legacy single-file type")

    @model_validator(mode="after")
    def normalize_legacy_single_file_input(self) -> "ParserInput":
        if not self.assets and self.file_path:
            self.assets = [
                InputAsset(
                    asset_id=self.file_id,
                    file_path=self.file_path,
                    file_type=self.file_type,
                    file_name=self.file_name or Path(self.file_path).name,
                )
            ]

        if not self.assets:
            raise ValueError("Either assets or legacy file_path/file_type input must be provided.")

        return self


class ParserOutput(BaseResponse):
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    source_file: Optional[SourceFile] = Field(
        default=None, description="Primary source file for legacy compatibility"
    )
    source_assets: list[InputAsset] = Field(default_factory=list, description="All parsed source assets")
    parsed_document: Optional[ParsedDocument] = Field(default=None, description="Normalized parsed document")
    structured_content: Optional[StructuredLessonContent] = Field(
        default=None, description="Teaching-layer structured content"
    )
    pages: list[PageBlock] = Field(default_factory=list, description="Teaching-layer page results")
    sections: list[SectionBlock] = Field(default_factory=list, description="Teaching-layer section results")
    total_units: int = Field(default=0, description="Total normalized document units")
    total_pages: int = Field(default=0, description="Total teaching-layer pages")
    knowledge_points: list[str] = Field(default_factory=list, description="Top-level knowledge points")
