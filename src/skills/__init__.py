"""Student skill loader and registry."""

from collections.abc import Iterable
from pathlib import Path
from typing import Optional

SKILLS_DIR = Path(__file__).parent
SKILL_DIRS: tuple[str, ...] = (
    "definition",
    "reasoning",
    "procedure",
    "example",
    "comparison",
    "summary",
    "quiz",
    "game",
)


class Skill:
    """Represents a loaded skill with its metadata."""

    def __init__(self, name: str, directory: Path):
        self.name = name
        self.directory = directory
        self.skill_md_path = directory / "SKILL.md"
        self._content: Optional[str] = None

    @property
    def exists(self) -> bool:
        return self.skill_md_path.exists()

    @property
    def content(self) -> str:
        """Lazy-load skill content from SKILL.md."""
        if self._content is None:
            if self.skill_md_path.exists():
                self._content = self.skill_md_path.read_text(encoding="utf-8")
            else:
                self._content = ""
        return self._content

    def reload(self) -> None:
        """Force reload of skill content."""
        self._content = None

    def __repr__(self) -> str:
        return f"Skill(name={self.name}, path={self.directory})"


class SkillLoader:
    """Loads and manages student skills."""

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or SKILLS_DIR
        self._skills: dict[str, Skill] = {}
        self._loaded = False

    def load_skills(self) -> dict[str, Skill]:
        """Load all available skills from the skills directory."""
        if self._loaded:
            return self._skills

        self._skills.clear()

        for skill_name in self._ordered_skill_names():
            skill_dir = self.skills_dir / skill_name
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                self._skills[skill_name] = Skill(name=skill_name, directory=skill_dir)

        self._loaded = True
        return self._skills

    def load_all(self) -> dict[str, Skill]:
        """Backward-compatible alias for load_skills."""
        return self.load_skills()

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a specific skill by name."""
        if not self._loaded:
            self.load_skills()
        return self._skills.get(name)

    def get_skill_content(self, name: str) -> str:
        """Get the SKILL.md content for a specific skill."""
        skill = self.get_skill(name)
        if skill:
            return skill.content
        return ""

    def list_skill_names(self) -> list[str]:
        """List all available skill names in load order."""
        if not self._loaded:
            self.load_skills()
        return list(self._skills.keys())

    def list_skills(self) -> list[str]:
        """List all available skill names."""
        return self.list_skill_names()

    def skill_exists(self, name: str) -> bool:
        """Check if a skill exists."""
        if not self._loaded:
            self.load_skills()
        return name in self._skills

    def reload(self) -> None:
        """Reload all skills."""
        self._loaded = False
        self._skills.clear()
        self.load_skills()

    def _ordered_skill_names(self) -> Iterable[str]:
        if not self.skills_dir.exists():
            return []
        discovered = [
            path.name for path in self.skills_dir.iterdir() if path.is_dir() and (path / "SKILL.md").exists()
        ]
        canonical = [name for name in SKILL_DIRS if name in discovered]
        extras = sorted(name for name in discovered if name not in SKILL_DIRS)
        return [*canonical, *extras]


# Global default loader instance
_default_loader: Optional[SkillLoader] = None


def get_loader() -> SkillLoader:
    """Get the global default skill loader."""
    global _default_loader
    if _default_loader is None:
        _default_loader = SkillLoader()
    return _default_loader


def load_all_skills() -> dict[str, Skill]:
    """Load all skills using the global loader."""
    return get_loader().load_skills()


def load_skills() -> dict[str, Skill]:
    """Load skills using the global loader."""
    return load_all_skills()


def get_skill(name: str) -> Optional[Skill]:
    """Get a specific skill by name using the global loader."""
    return get_loader().get_skill(name)


def get_skill_content(name: str) -> str:
    """Get skill markdown content using the global loader."""
    return get_loader().get_skill_content(name)


def list_skills() -> list[str]:
    """List all skill names using the global loader."""
    return get_loader().list_skill_names()


# Skill names as constants for type-safe usage
SKILL_DEFINITION = "definition"
SKILL_REASONING = "reasoning"
SKILL_PROCEDURE = "procedure"
SKILL_EXAMPLE = "example"
SKILL_COMPARISON = "comparison"
SKILL_SUMMARY = "summary"
SKILL_QUIZ = "quiz"
SKILL_GAME = "game"

ALL_SKILLS = SKILL_DIRS

__all__ = [
    "ALL_SKILLS",
    "SKILL_COMPARISON",
    "SKILL_DEFINITION",
    "SKILL_DIRS",
    "SKILL_EXAMPLE",
    "SKILL_GAME",
    "SKILL_PROCEDURE",
    "SKILL_QUIZ",
    "SKILL_REASONING",
    "SKILL_SUMMARY",
    "SKILLS_DIR",
    "Skill",
    "SkillLoader",
    "get_loader",
    "get_skill",
    "get_skill_content",
    "list_skills",
    "load_all_skills",
    "load_skills",
]
