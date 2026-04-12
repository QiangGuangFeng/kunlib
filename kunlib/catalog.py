"""自动生成 catalog.json —— 零手动维护。"""
from __future__ import annotations

import json
from pathlib import Path
from kunlib.skill import SkillMeta, Param
from kunlib.registry import KUNLIB_SKILLS_DIR


def _param_type_name(p: Param) -> str:
    """Return a stable string representation of a Param's type."""
    return p.type.__name__ if isinstance(p.type, type) else str(p.type)


def generate_catalog(
    registry: dict[str, SkillMeta],
    output_dir: Path | None = None,
) -> Path:
    out = Path(output_dir or KUNLIB_SKILLS_DIR)
    out.mkdir(parents=True, exist_ok=True)

    catalog = {
        "version": "1.0.0",
        "generated_by": "kunlib catalog",
        "skill_count": len(registry),
        "skills": [
            {
                "name": m.name,
                "version": m.version,
                "description": m.description,
                "author": m.author,
                "tags": m.tags,
                "emoji": m.emoji,
                "trigger_keywords": m.trigger_keywords,
                "chaining_partners": m.chaining_partners,
                "input_formats": m.input_formats,
                "has_demo": m.has_demo,
                "requires_bins": m.requires_bins,
                "params": [
                    {"name": p.name, "type": _param_type_name(p),
                     "required": p.required, "default": p.default, "help": p.help, "is_flag": p.is_flag}
                    for p in m.params
                ],
            }
            for m in sorted(registry.values(), key=lambda x: x.name)
        ],
    }

    path = out / "catalog.json"
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    return path
