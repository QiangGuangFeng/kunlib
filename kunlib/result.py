"""KunLib 标准输出规范 —— 所有技能必须返回 KunResult。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DISCLAIMER = (
    "KunLib is a research and educational tool for genetic breeding analysis. "
    "It does not provide clinical or production-grade decisions. "
    "Results should be validated by domain experts before use in breeding programs."
)


@dataclass
class KunResult:
    """技能标准返回值。

    files 字段是灵活的分类字典，key 由技能自定义，例如:
        files = {
            "tables":   [Path("tables/phe_ebv.csv"), ...],
            "figures":  [Path("figures/manhattan.png"), ...],
            "matrices": [Path("matrices/grm.bin"), ...],
            "logs":     [Path("logs/plink.log"), ...],
        }
    """
    skill_name: str
    skill_version: str
    mode: str = "input"
    output_dir: Path | None = None
    summary: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    files: dict[str, list[Path]] = field(default_factory=dict)
    report_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict（用于 JSON 输出和 agent 响应）。"""
        serialized_files: dict[str, list[str]] = {}
        for category, paths in self.files.items():
            serialized: list[str] = []
            for f in paths:
                try:
                    serialized.append(str(f.relative_to(self.output_dir)) if self.output_dir else str(f))
                except ValueError:
                    serialized.append(str(f))
            serialized_files[category] = serialized

        return {
            "skill": self.skill_name,
            "version": self.skill_version,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "mode": self.mode,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "summary": self.summary,
            "data": self.data,
            "files": serialized_files,
            "report": str(self.report_path) if self.report_path else None,
            "disclaimer": DISCLAIMER,
        }

    def save(self, output_dir: Path | None = None) -> Path:
        """将 result.json 写入输出目录。"""
        out = Path(output_dir or self.output_dir or ".")
        out.mkdir(parents=True, exist_ok=True)
        path = out / "result.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str, ensure_ascii=False))
        return path
