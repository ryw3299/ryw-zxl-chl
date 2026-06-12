from typing import Any, Literal, Optional

from pydantic import Field

from .base import SchemaModel

FileType = Literal[
    "pdf",
    "pptx",
    "ppt",
    "docx",
    "txt",
    "md",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "image",
]
DocumentUnitType = Literal["page", "slide", "section", "chunk", "image_region"]
PageRole = Literal[
    "cover",
    "agenda",
    "content",
    "definition",
    "formula",
    "example",
    "summary",
    "exercise",
    "other",
]
SectionType = Literal["intro", "content", "example", "summary", "exercise", "other"]
LessonStatus = Literal["draft", "published", "archived"]
SessionStatus = Literal["active", "paused", "completed"]
UnderstandingLevel = Literal["full", "partial", "none"]
NextAction = Literal[
    "resume",
    "supplement_then_resume",
    "reteach_slowly",
    "trigger_game",
]
ScriptBlockType = Literal["opening", "teaching", "transition", "summary", "interaction"]
ReferenceSourceType = Literal["faq", "lesson", "script", "textbook", "knowledge_base", "fallback"]


class InputAsset(SchemaModel):
    asset_id: Optional[str] = Field(default=None, description="Input asset identifier")
    file_path: str = Field(..., description="Input file path")
    file_type: Optional[FileType] = Field(default=None, description="Input file type")
    file_name: str = Field(default="", description="Input file name")
    mime_type: Optional[str] = Field(default=None, description="Input mime type")


class SourceFile(SchemaModel):
    file_id: Optional[str] = Field(default=None, description="Stored source file identifier")
    file_name: str = Field(default="", description="Stored source file name")
    file_path: str = Field(default="", description="Stored source file path")
    file_type: Optional[FileType] = Field(default=None, description="Stored source file type")
    mime_type: Optional[str] = Field(default=None, description="Stored source mime type")


class DocumentUnit(SchemaModel):
    unit_id: str = Field(..., description="Normalized document unit identifier")
    unit_type: DocumentUnitType = Field(..., description="Normalized unit type")
    index: int = Field(..., description="1-based order within the parsed document")
    title: str = Field(default="", description="Unit title")
    text: str = Field(default="", description="Unit text content")
    source_ref: str = Field(default="", description="Human-readable source reference")
    source_asset_id: str = Field(..., description="Source asset identifier")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extractor-specific metadata")


class LessonInfo(SchemaModel):
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    lesson_name: str = Field(default="", description="Lesson name")
    lesson_status: LessonStatus = Field(default="draft", description="Lesson status")
    source_files: list[SourceFile] = Field(default_factory=list, description="Linked raw source files")


class PageBlock(SchemaModel):
    page_id: Optional[str] = Field(default=None, description="Teaching-layer page identifier")
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: Optional[str] = Field(default=None, description="Lesson identifier")
    section_id: Optional[str] = Field(default=None, description="Owning section identifier")
    page: int = Field(..., description="1-based page index")
    title: str = Field(default="", description="Page title")
    content: str = Field(default="", description="Page text content")
    summary: str = Field(default="", description="Page summary")
    key_points: list[str] = Field(default_factory=list, description="Teaching key points for the page")
    knowledge_points: list[str] = Field(default_factory=list, description="Extracted knowledge points")
    source_unit_ids: list[str] = Field(
        default_factory=list, description="Source document unit identifiers used to build this page"
    )
    page_role: PageRole = Field(default="other", description="Teaching role of the page")
    file_id: Optional[str] = Field(default=None, description="Source file identifier")
    file_type: Optional[FileType] = Field(default=None, description="Source file type")


class SectionBlock(SchemaModel):
    section_id: str = Field(..., description="Teaching-layer section identifier")
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: Optional[str] = Field(default=None, description="Lesson identifier")
    name: str = Field(..., description="Section name")
    summary: str = Field(default="", description="Section summary")
    page_range: list[int] = Field(default_factory=list, description="Covered page indices")
    key_points: list[str] = Field(default_factory=list, description="Teaching key points")
    knowledge_points: list[str] = Field(default_factory=list, description="Knowledge points")
    source_unit_ids: list[str] = Field(
        default_factory=list, description="Source document unit identifiers used to build this section"
    )
    section_type: SectionType = Field(default="other", description="Teaching role of the section")
    parent_section_id: Optional[str] = Field(default=None, description="Parent section identifier")


class ParsedDocument(SchemaModel):
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    source_assets: list[InputAsset] = Field(
        default_factory=list, description="Input assets included in parsing"
    )
    units: list[DocumentUnit] = Field(default_factory=list, description="Normalized document units")
    sections: list[SectionBlock] = Field(default_factory=list, description="Derived teaching sections")
    parse_instruction: Optional[str] = Field(default=None, description="User-provided parsing instruction")
    knowledge_points: list[str] = Field(default_factory=list, description="Parsed document knowledge points")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Parsed document metadata")


class StructuredLessonContent(SchemaModel):
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    source_asset_ids: list[str] = Field(
        default_factory=list, description="Source asset identifiers used to derive this content"
    )
    lesson_summary: str = Field(
        default="", description="Top-level summary grounded in the uploaded lesson materials"
    )
    pages: list["PageBlock"] = Field(default_factory=list, description="Teaching-layer pages")
    sections: list["SectionBlock"] = Field(default_factory=list, description="Teaching-layer sections")
    knowledge_points: list[str] = Field(default_factory=list, description="Teaching-layer knowledge points")
    parse_instruction: Optional[str] = Field(
        default=None, description="Parsing instruction carried into teaching structuring"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Structured teaching content metadata")


class ScriptBlock(SchemaModel):
    script_block_id: Optional[str] = Field(default=None, description="Script block identifier")
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: Optional[str] = Field(default=None, description="Lesson identifier")
    section_id: str = Field(..., description="Owning section identifier")
    title: str = Field(default="", description="Script block title")
    page_range: list[int] = Field(default_factory=list, description="Covered page indices")
    script_text: str = Field(default="", description="Script body text")
    key_points: list[str] = Field(default_factory=list, description="Emphasized teaching key points")
    block_type: ScriptBlockType = Field(default="teaching", description="Script block type")


class ReferenceItem(SchemaModel):
    source_type: ReferenceSourceType = Field(default="lesson", description="Reference source type")
    source_name: str = Field(default="", description="Reference source name")
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: Optional[str] = Field(default=None, description="Lesson identifier")
    section_id: Optional[str] = Field(default=None, description="Section identifier")
    script_block_id: Optional[str] = Field(default=None, description="Script block identifier")
    page: Optional[int] = Field(default=None, description="Matched page number")
    snippet: str = Field(default="", description="Matched content snippet")
    score: Optional[float] = Field(default=None, description="Retrieval or matching score")


class QAHistoryItem(SchemaModel):
    qa_record_id: Optional[str] = Field(default=None, description="Historical QA record identifier")
    question: str = Field(..., description="Historical question")
    answer: str = Field(..., description="Historical answer")
    understanding_level: Optional[UnderstandingLevel] = Field(
        default=None, description="Historical understanding level"
    )
    current_section_id: Optional[str] = Field(default=None, description="Section identifier at question time")
    current_page: Optional[int] = Field(default=None, description="Page number at question time")


class QARecord(SchemaModel):
    qa_record_id: str = Field(..., description="QA record identifier")
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    session_id: str = Field(..., description="Learning session identifier")
    current_section_id: Optional[str] = Field(default=None, description="Section identifier at question time")
    current_page: Optional[int] = Field(default=None, description="Page number at question time")
    question: str = Field(..., description="Student question")
    answer: str = Field(..., description="System answer")
    understanding_level: Optional[UnderstandingLevel] = Field(default=None, description="Understanding level")
    references: list[ReferenceItem] = Field(
        default_factory=list, description="Reference list used in the answer"
    )


class LearningSession(SchemaModel):
    session_id: str = Field(..., description="Learning session identifier")
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    user_id: Optional[str] = Field(default=None, description="Student or user identifier")
    status: SessionStatus = Field(default="active", description="Learning session status")
    current_section_id: Optional[str] = Field(default=None, description="Current section identifier")
    current_page: Optional[int] = Field(default=None, description="Current page number")
    current_script_block_id: Optional[str] = Field(
        default=None, description="Current script block identifier"
    )
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Learning progress percentage")


class LearningProgress(SchemaModel):
    session_id: str = Field(..., description="Learning session identifier")
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    current_section_id: Optional[str] = Field(default=None, description="Current section identifier")
    current_page: Optional[int] = Field(default=None, description="Current page number")
    current_script_block_id: Optional[str] = Field(
        default=None, description="Current script block identifier"
    )
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Learning progress percentage")
    last_action: Optional[NextAction] = Field(default=None, description="Last executed learning action")
