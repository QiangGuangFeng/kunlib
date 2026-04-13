"""报告生成工具。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

DISCLAIMER = (
    "KunLib is a research and educational tool for genetic breeding analysis. "
    "It does not provide clinical or production-grade decisions. "
    "Results should be validated by domain experts before use in breeding programs."
)


def generate_report_header(
    title: str,
    skill_name: str,
    skill_version: str = "",
    extra: dict[str, str] | None = None,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# {title}", "", f"**Date**: {now}", f"**Skill**: {skill_name}"]
    if skill_version:
        lines.append(f"**Version**: {skill_version}")
    if extra:
        for k, v in extra.items():
            lines.append(f"**{k}**: {v}")
    lines.extend(["", "---", ""])
    return "\n".join(lines)


def generate_report_footer() -> str:
    return f"\n---\n\n## Disclaimer\n\n*{DISCLAIMER}*\n"
