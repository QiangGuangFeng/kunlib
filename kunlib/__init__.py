"""KunLib — Genetic Breeding Analysis Skill Library."""

__version__ = "0.1.0"

from kunlib.skill import skill, Param, SkillMeta, get_registry
from kunlib.result import KunResult

__all__ = [
    "skill",
    "Param",
    "KunResult",
    "SkillMeta",
    "get_registry",
]
