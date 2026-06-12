from typing import Any, Literal, Optional

from pydantic import Field, model_validator

from .base import BaseRequest, BaseResponse, SchemaModel
from .common import PageBlock, ScriptBlock, SectionBlock, StructuredLessonContent

PresentationCardType = Literal[
    "cover",
    "agenda",
    "concept",
    "formula",
    "example",
    "comparison",
    "process",
    "summary",
]

VisualType = Literal["none", "source_image", "source_table", "source_formula"]


class VisualPlan(SchemaModel):
    visual_type: VisualType = Field(
        default="none", description="Planned visual asset type for a presentation card or slide"
    )
    source_unit_ids: list[str] = Field(
        default_factory=list, description="Source document units used to derive this visual"
    )
    caption: str = Field(default="", description="Optional visual caption")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Renderer-specific visual metadata")


class PresentationCard(SchemaModel):
    card_id: str = Field(..., description="Presentation card identifier")
    card_type: PresentationCardType = Field(..., description="Presentation card taxonomy type")
    title: str = Field(default="", description="Presentation card title")
    subtitle: Optional[str] = Field(default=None, description="Optional presentation card subtitle")
    bullets: list[str] = Field(default_factory=list, description="Main bullet points to display")
    body_text: Optional[str] = Field(default=None, description="Optional supporting body text")
    speaker_notes: str = Field(default="", description="Speaker notes derived from the lesson content")
    visual_plan: list[VisualPlan] = Field(default_factory=list, description="Visual usage plan for this card")
    source_section_ids: list[str] = Field(
        default_factory=list, description="Source teaching section identifiers"
    )
    source_page_ids: list[str] = Field(default_factory=list, description="Source teaching page identifiers")
    source_unit_ids: list[str] = Field(default_factory=list, description="Source document unit identifiers")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Presentation card metadata")


class PresentationSection(SchemaModel):
    section_id: str = Field(..., description="Presentation section identifier")
    title: str = Field(default="", description="Presentation section title")
    summary: str = Field(default="", description="Presentation section summary")
    cards: list[PresentationCard] = Field(
        default_factory=list, description="Presentation cards under this section"
    )
    source_page_ids: list[str] = Field(
        default_factory=list, description="Source teaching page identifiers for this section"
    )
    source_unit_ids: list[str] = Field(
        default_factory=list, description="Source document unit identifiers for this section"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Presentation section metadata")


class PresentationOutline(SchemaModel):
    lesson_title: str = Field(default="", description="Presentation-level lesson title")
    lesson_summary: str = Field(default="", description="Top-level presentation summary")
    sections: list[PresentationSection] = Field(default_factory=list, description="Presentation sections")
    knowledge_points: list[str] = Field(
        default_factory=list, description="Lesson knowledge points selected for presentation"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Presentation outline metadata")


class LessonScript(SchemaModel):
    lesson_title: str = Field(default="", description="Lesson script title")
    script_blocks: list[ScriptBlock] = Field(
        default_factory=list, description="Generated lesson script blocks"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Lesson script metadata")


class SlideOutline(SchemaModel):
    slide_id: str = Field(..., description="PPT slide identifier")
    slide_type: PresentationCardType = Field(..., description="PPT slide taxonomy type")
    layout_template: str = Field(default="", description="Renderer layout template key")
    title: str = Field(default="", description="Slide title")
    subtitle: Optional[str] = Field(default=None, description="Optional slide subtitle")
    bullets: list[str] = Field(default_factory=list, description="Slide bullet points")
    speaker_notes: str = Field(default="", description="Speaker notes attached to the slide")
    visual_plan: list[VisualPlan] = Field(
        default_factory=list, description="Visual usage plan for this slide"
    )
    source_section_ids: list[str] = Field(
        default_factory=list, description="Source teaching section identifiers"
    )
    source_page_ids: list[str] = Field(default_factory=list, description="Source teaching page identifiers")
    source_unit_ids: list[str] = Field(default_factory=list, description="Source document unit identifiers")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Slide metadata")


class PPTOutline(SchemaModel):
    deck_title: str = Field(default="", description="PPT deck title")
    theme_name: str = Field(default="", description="Renderer theme or template name")
    slides: list[SlideOutline] = Field(default_factory=list, description="Slides prepared for PPT rendering")
    metadata: dict[str, Any] = Field(default_factory=dict, description="PPT outline metadata")


class GenerateInput(BaseRequest):
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    lesson_name: str = Field(default="", description="Lesson display name")
    structured_content: StructuredLessonContent = Field(
        ..., description="Structured lesson content produced by the parser"
    )
    pages: list[PageBlock] = Field(default_factory=list, description="Compatibility view of structured pages")
    sections: list[SectionBlock] = Field(
        default_factory=list, description="Compatibility view of structured sections"
    )
    teacher_notes: str = Field(default="", description="Optional teacher notes for generation")
    generate_instruction: str = Field(
        default="", description="Optional generation instruction that guides output emphasis"
    )

    @model_validator(mode="after")
    def populate_from_structured_content(self) -> "GenerateInput":
        if self.course_id is None:
            self.course_id = self.structured_content.course_id
        if not self.pages:
            self.pages = list(self.structured_content.pages)
        if not self.sections:
            self.sections = list(self.structured_content.sections)
        return self


class GenerateOutput(BaseResponse):
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    presentation_outline: PresentationOutline = Field(
        ..., description="Primary presentation outline generated from the lesson content"
    )
    teacher_feedback_text: str = Field(
        default="", description="Short natural-language feedback returned to the teacher"
    )
    lesson_script: LessonScript = Field(
        ..., description="Lesson script derived from the presentation outline"
    )
    ppt_outline: PPTOutline = Field(
        ..., description="PPT-oriented outline derived from the presentation outline"
    )
    total_cards: int = Field(default=0, description="Total number of presentation cards")
    total_script_blocks: int = Field(default=0, description="Total number of generated script blocks")
    total_slides: int = Field(default=0, description="Total number of PPT slides")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Generate stage metadata")

    @model_validator(mode="after")
    def populate_totals(self) -> "GenerateOutput":
        if self.total_cards == 0:
            self.total_cards = sum(len(section.cards) for section in self.presentation_outline.sections)
        if self.total_script_blocks == 0:
            self.total_script_blocks = len(self.lesson_script.script_blocks)
        if self.total_slides == 0:
            self.total_slides = len(self.ppt_outline.slides)
        return self
