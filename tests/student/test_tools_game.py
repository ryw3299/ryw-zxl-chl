from src.schemas import StructuredLessonContent
from src.tools.game import GameAction, GameTool


def _build_structured_content() -> StructuredLessonContent:
    return StructuredLessonContent.model_validate(
        {
            "course_id": "course-1",
            "lesson_id": "lesson-1",
            "lesson_summary": "材料力学基础",
            "pages": [
                {
                    "page_id": "page-1",
                    "lesson_id": "lesson-1",
                    "section_id": "sec-1",
                    "page": 1,
                    "title": "应力基础",
                    "content": "应力表示单位面积上的内力，是材料力学中的基础概念。",
                    "summary": "应力是单位面积上的内力。",
                    "key_points": ["应力"],
                    "knowledge_points": ["应力"],
                    "page_role": "definition",
                },
                {
                    "page_id": "page-2",
                    "lesson_id": "lesson-1",
                    "section_id": "sec-2",
                    "page": 2,
                    "title": "变形基础",
                    "content": "变形表示构件形状或尺寸的变化。",
                    "summary": "变形是结构响应。",
                    "key_points": ["变形"],
                    "knowledge_points": ["变形"],
                    "page_role": "content",
                },
            ],
            "sections": [
                {
                    "section_id": "sec-1",
                    "lesson_id": "lesson-1",
                    "name": "基础概念",
                    "summary": "讲解应力定义。",
                    "page_range": [1],
                    "key_points": ["应力"],
                    "knowledge_points": ["应力"],
                    "section_type": "content",
                }
            ],
            "knowledge_points": ["应力", "变形"],
        }
    )


def test_game_tool_generates_multiple_choice_quiz():
    tool = GameTool(_build_structured_content())
    observation = tool.run(
        GameAction(
            question="什么是应力？",
            lesson_id="lesson-1",
            session_id="session-1",
        )
    )

    assert observation.game_type == "multiple_choice"
    assert observation.prompt
    assert len(observation.choices) == 4
    assert observation.correct_choice == observation.choices[0]
    assert observation.references


def test_game_tool_prefers_page_when_provided():
    tool = GameTool(_build_structured_content())
    observation = tool.run(
        GameAction(
            question="来一道题",
            lesson_id="lesson-1",
            session_id="session-1",
            page=2,
        )
    )

    assert "变形" in observation.correct_choice or "变形" in observation.explanation
