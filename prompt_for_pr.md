# KunLib 完整构建 Prompt

以下是你需要创建的所有文件及其完整内容。

---

## 1. `kunlib/__init__.py`

```python name=kunlib/__init__.py
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
```

---

## 2. `kunlib/skill.py`

```python name=kunlib/skill.py
"""KunLib Skill SDK — 声明式技能注册框架。

开发者在技能主脚本中使用 @skill 装饰器即可完成:
  1. 元信息注册（name, tags, trigger_keywords, params...）
  2. argparse 自动构建
  3. CLI 入口 (run_cli)
  4. 被 kunlib CLI / agent adapter 发现和调用
"""
from __future__ import annotations

import argparse
import functools
import inspect
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from kunlib.result import KunResult


@dataclass
class Param:
    """技能参数声明。

    name 使用 kebab-case (e.g. "trait-pos")，与 CLI flag 一致。
    argparse 会自动将其转为 snake_case 属性 (args.trait_pos)。
    """
    name: str
    type: type = str
    required: bool = False
    default: Any = None
    help: str = ""
    is_flag: bool = False


@dataclass
class SkillMeta:
    """技能元信息，由 @skill 装饰器自动填充。"""
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    trigger_keywords: list[str] = field(default_factory=list)
    chaining_partners: list[str] = field(default_factory=list)
    input_formats: list[str] = field(default_factory=list)
    requires_bins: list[str] = field(default_factory=list)
    emoji: str = "🧬"
    params: list[Param] = field(default_factory=list)
    script_path: Path | None = None
    has_demo: bool = False
    entry_func: Callable | None = None

    def build_parser(self) -> argparse.ArgumentParser:
        """从 self.params 自动构建 ArgumentParser。"""
        parser = argparse.ArgumentParser(
            prog=f"kunlib run {self.name}",
            description=self.description,
        )
        for p in self.params:
            flag = f"--{p.name}"
            if p.is_flag:
                parser.add_argument(flag, action="store_true", default=False, help=p.help)
            else:
                kw: dict[str, Any] = {"type": p.type, "help": p.help, "default": p.default}
                if p.required:
                    kw["required"] = True
                parser.add_argument(flag, **kw)
        return parser

    def run_cli(self, argv: list[str] | None = None) -> KunResult | None:
        """解析命令行参数 → 执行 entry_func → 保存并打印结果。

        脚本的 if __name__ == "__main__" 直接调用此方法即可。
        argv=None 时读 sys.argv，测试时可传入自定义参数列表。
        """
        parser = self.build_parser()
        args = parser.parse_args(argv)
        result = self.entry_func(args)
        if isinstance(result, KunResult):
            result.save()
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return result


# --------------------------------------------------------------------------- #
# Global registry
# --------------------------------------------------------------------------- #

_SKILL_REGISTRY: dict[str, SkillMeta] = {}


def get_registry() -> dict[str, SkillMeta]:
    """返回当前进程中所有已注册的技能。"""
    return _SKILL_REGISTRY


def skill(
    name: str,
    *,
    version: str = "0.1.0",
    description: str = "",
    author: str = "",
    tags: list[str] | None = None,
    trigger_keywords: list[str] | None = None,
    chaining_partners: list[str] | None = None,
    input_formats: list[str] | None = None,
    requires_bins: list[str] | None = None,
    emoji: str = "🧬",
    params: list[Param] | None = None,
):
    """技能注册装饰器 —— 开发者唯一需要使用的接口。

    用法::

        @skill(
            name="hiblup-ebv",
            version="0.1.0",
            description="GBLUP breeding values via HI-BLUP",
            params=[
                Param("input", help="Input directory"),
                Param("output", required=True, help="Output directory"),
                Param("demo", is_flag=True, help="Run with synthetic data"),
            ],
        )
        def run(args: argparse.Namespace) -> KunResult:
            ...

        if __name__ == "__main__":
            run.__kunlib_meta__.run_cli()
    """
    def decorator(func: Callable) -> Callable:
        meta = SkillMeta(
            name=name,
            version=version,
            description=description,
            author=author,
            tags=tags or [],
            trigger_keywords=trigger_keywords or [],
            chaining_partners=chaining_partners or [],
            input_formats=input_formats or [],
            requires_bins=requires_bins or [],
            emoji=emoji,
            params=params or [],
            script_path=Path(inspect.getfile(func)).resolve(),
            has_demo=any(p.name == "demo" for p in (params or [])),
            entry_func=func,
        )
        _SKILL_REGISTRY[name] = meta

        @functools.wraps(func)
        def wrapper(*a, **kw):
            return func(*a, **kw)

        wrapper.__kunlib_meta__ = meta
        return wrapper

    return decorator
```

---

## 3. `kunlib/result.py`

```python name=kunlib/result.py
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
    """技能标准返回值。"""
    skill_name: str
    skill_version: str
    mode: str = "input"                          # "input" | "demo"
    output_dir: Path | None = None
    summary: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    figures: list[Path] = field(default_factory=list)
    tables: list[Path] = field(default_factory=list)
    report_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict（用于 JSON 输出和 agent 响应）。"""
        return {
            "skill": self.skill_name,
            "version": self.skill_version,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "mode": self.mode,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "summary": self.summary,
            "data": self.data,
            "figures": [str(f) for f in self.figures],
            "tables": [str(t) for t in self.tables],
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
```

---

## 4. `kunlib/registry.py`

```python name=kunlib/registry.py
"""KunLib 技能自动发现 —— 扫描 skills/ 目录加载 @skill 装饰器。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from kunlib.skill import SkillMeta, get_registry

# kunlib 自带的 skills/ 目录
KUNLIB_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def discover_builtin_skills() -> dict[str, SkillMeta]:
    """扫描 kunlib 仓库自带的 skills/ 目录。"""
    return discover_skills_from_directory(KUNLIB_SKILLS_DIR)


def discover_skills_from_directory(skills_dir: Path) -> dict[str, SkillMeta]:
    """扫描指定目录：每个含 SKILL.md 的子目录视为技能。

    加载其中的 .py 文件会触发 @skill 装饰器执行，
    从而自动注册到全局 _SKILL_REGISTRY。
    """
    skills_dir = Path(skills_dir)
    if not skills_dir.exists():
        return get_registry()

    for folder in sorted(skills_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith((".", "_")):
            continue
        if not (folder / "SKILL.md").exists():
            continue
        for py_file in folder.glob("*.py"):
            if py_file.name.startswith("test_") or py_file.name == "__init__.py":
                continue
            _safe_load(py_file, folder.name)

    return get_registry()


def discover_skills_from_entry_points() -> dict[str, SkillMeta]:
    """通过 Python entry_points 发现第三方扩展技能。"""
    if sys.version_info >= (3, 12):
        from importlib.metadata import entry_points
        eps = entry_points(group="kunlib.skills")
    else:
        from importlib.metadata import entry_points
        all_eps = entry_points()
        eps = all_eps.get("kunlib.skills", [])

    for ep in eps:
        try:
            ep.load()
        except Exception as e:
            print(f"[kunlib] Warning: failed to load skill '{ep.name}': {e}", file=sys.stderr)

    return get_registry()


def discover_all() -> dict[str, SkillMeta]:
    """完整发现: 内置 skills/ + entry_points 扩展。"""
    discover_builtin_skills()
    discover_skills_from_entry_points()
    return get_registry()


def get_skill_docs() -> dict[str, str]:
    """读取所有已注册技能的 SKILL.md 内容，供 agent 学习。"""
    docs: dict[str, str] = {}
    for name, meta in get_registry().items():
        if meta.script_path:
            skill_md = meta.script_path.parent / "SKILL.md"
            if skill_md.exists():
                docs[name] = skill_md.read_text(encoding="utf-8")
    return docs


def _safe_load(py_file: Path, folder_name: str) -> None:
    try:
        mod_name = f"_kunlib_skill_{folder_name}_{py_file.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, py_file)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
    except Exception as e:
        print(f"[kunlib] Warning: failed to load {py_file}: {e}", file=sys.stderr)
```

---

## 5. `kunlib/cli.py`

```python name=kunlib/cli.py
"""KunLib CLI 入口。

    kunlib list
    kunlib run <skill> [skill args...]
    kunlib catalog
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from kunlib.registry import discover_all, KUNLIB_SKILLS_DIR
from kunlib.skill import get_registry

PYTHON = sys.executable


def main():
    top = argparse.ArgumentParser(prog="kunlib", description="KunLib — Genetic Breeding Skill Library")
    sub = top.add_subparsers(dest="command")

    sub.add_parser("list", help="List all registered skills")
    sub.add_parser("catalog", help="Generate catalog.json")

    run_p = sub.add_parser("run", help="Run a skill")
    run_p.add_argument("skill_name", help="Skill name (e.g. hiblup-ebv)")

    args, remaining = top.parse_known_args()

    discover_all()
    registry = get_registry()

    if args.command == "list":
        _cmd_list(registry)
    elif args.command == "catalog":
        from kunlib.catalog import generate_catalog
        print(f"Generated: {generate_catalog(registry)}")
    elif args.command == "run":
        _cmd_run(args.skill_name, remaining, registry)
    else:
        top.print_help()


def _cmd_list(registry):
    print(f"\n{'='*60}")
    print(f"  KunLib Skills  ({len(registry)} registered)")
    print(f"{'='*60}\n")
    for name, meta in sorted(registry.items()):
        demo = " [demo]" if meta.has_demo else ""
        ok = "OK" if meta.script_path and meta.script_path.exists() else "MISSING"
        print(f"  {meta.emoji} {name:30s} v{meta.version}{demo}  [{ok}]")
        print(f"     {meta.description}")
        print()
    print("  Run:    kunlib run <skill> --demo --output /tmp/out")
    print("  Direct: python skills/<skill>/<script>.py --demo --output /tmp/out\n")


def _cmd_run(skill_name: str, passthrough: list[str], registry):
    """subprocess 调用技能脚本，透传所有参数。"""
    meta = registry.get(skill_name)
    if not meta:
        print(f"Error: skill '{skill_name}' not found. Available: {', '.join(sorted(registry))}")
        sys.exit(1)
    if not meta.script_path or not meta.script_path.exists():
        print(f"Error: script not found for '{skill_name}'")
        sys.exit(1)
    cmd = [PYTHON, str(meta.script_path)] + passthrough
    sys.exit(subprocess.run(cmd, cwd=str(meta.script_path.parent)).returncode)


if __name__ == "__main__":
    main()
```

---

## 6. `kunlib/catalog.py`

```python name=kunlib/catalog.py
"""自动生成 catalog.json —— 零手动维护。"""
from __future__ import annotations

import json
from pathlib import Path
from kunlib.skill import SkillMeta
from kunlib.registry import KUNLIB_SKILLS_DIR


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
                    {"name": p.name, "type": p.type.__name__ if isinstance(p.type, type) else str(p.type),
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
```

---

## 7. `kunlib/agent_adapter.py`

```python name=kunlib/agent_adapter.py
"""Agent 适配器 —— kunbreed / OpenClaw / 任意 agent 通过此接口集成 kunlib。"""
from __future__ import annotations

import argparse
from typing import Any

from kunlib.registry import discover_all, get_skill_docs
from kunlib.skill import get_registry, SkillMeta
from kunlib.result import KunResult


class KunLibAdapter:
    """通用适配器。

    用法::

        adapter = KunLibAdapter()
        docs = adapter.get_skill_docs()           # SKILL.md 内容
        manifest = adapter.get_skill_manifest()    # 结构化清单
        result = adapter.run_skill("hiblup-ebv", {"demo": True, "output": "/tmp/out"})
    """

    def __init__(self):
        discover_all()
        self.registry = get_registry()

    def get_skill_manifest(self) -> list[dict[str, Any]]:
        return [
            {
                "name": m.name,
                "description": m.description,
                "trigger_keywords": m.trigger_keywords,
                "input_formats": m.input_formats,
                "has_demo": m.has_demo,
                "tags": m.tags,
                "params": [
                    {"name": p.name, "type": p.type.__name__ if isinstance(p.type, type) else str(p.type),
                     "required": p.required, "help": p.help, "is_flag": p.is_flag}
                    for p in m.params
                ],
            }
            for m in self.registry.values()
        ]

    def get_skill_docs(self) -> dict[str, str]:
        return get_skill_docs()

    def route(self, query: str) -> SkillMeta | None:
        query_lower = query.lower()
        best, best_score = None, 0
        for meta in self.registry.values():
            score = sum(1 for kw in meta.trigger_keywords if kw.lower() in query_lower)
            if score > best_score:
                best_score, best = score, meta
        return best

    def run_skill(self, skill_name: str, args_dict: dict[str, Any]) -> dict[str, Any]:
        meta = self.registry.get(skill_name)
        if not meta or not meta.entry_func:
            return {"error": f"Skill '{skill_name}' not found"}
        ns = argparse.Namespace(**args_dict)
        result = meta.entry_func(ns)
        if isinstance(result, KunResult):
            return result.to_dict()
        return {"error": "Skill did not return KunResult"}
```

---

## 8. `kunlib/common/__init__.py`

```python name=kunlib/common/__init__.py
"""KunLib common utilities — parsers, report, checksums, breeding helpers."""
```

---

## 9. `kunlib/common/report.py`

```python name=kunlib/common/report.py
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
```

---

## 10. `kunlib/common/checksums.py`

```python name=kunlib/common/checksums.py
"""文件校验。"""
from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(filepath: str | Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
```

---

## 11. `kunlib/common/parsers.py`

```python name=kunlib/common/parsers.py
"""通用数据解析器（VCF header, PLINK .fam, CSV 表型等）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def detect_format(filepath: str | Path) -> str:
    """根据扩展名和文件头推断数据格式。"""
    p = Path(filepath)
    suffixes = "".join(p.suffixes).lower()
    if ".vcf" in suffixes:
        return "vcf"
    if p.suffix.lower() == ".fam":
        return "plink-fam"
    if p.suffix.lower() in (".bed",):
        return "plink-bed"
    if p.suffix.lower() in (".csv", ".tsv"):
        return "tabular"
    return "unknown"


def read_csv_header(filepath: str | Path, sep: str = ",") -> list[str]:
    """读取 CSV/TSV 首行作为列名。"""
    with open(filepath, encoding="utf-8") as f:
        return [c.strip() for c in f.readline().strip().split(sep)]
```

---

## 12. `kunlib/common/breeding.py`

```python name=kunlib/common/breeding.py
"""育种专用工具函数（占位，后续扩展）。"""
from __future__ import annotations


def grm_from_genotypes(geno_matrix):
    """从基因型矩阵计算 G 矩阵（占位）。"""
    raise NotImplementedError("GRM computation to be implemented")


def selection_index(ebvs: dict[str, float], weights: dict[str, float]) -> float:
    """综合选择指数。"""
    return sum(ebvs.get(trait, 0.0) * w for trait, w in weights.items())
```

---

## 13. `templates/SKILL-TEMPLATE.md`

````markdown name=templates/SKILL-TEMPLATE.md
---
name: your-skill-name
description: >-
  One-line description of what this skill does.
version: 0.1.0
author: Your Name
tags: [tag1, tag2]
metadata:
  kunlib:
    requires:
      bins: [python3]
    emoji: "🧬"
    trigger_keywords:
      - keyword that routes to this skill
    chaining_partners: []
    input_formats:
      - csv
---

# 🧬 Skill Name

You are **[Skill Name]**, a KunLib skill for [domain].

## Why This Exists

- **Without it**: [painful manual process]
- **With it**: [automated outcome]

## Core Capabilities

1. **Capability 1**: Description
2. **Capability 2**: Description

## Input Formats

| Format | Extension | Required Fields |
|--------|-----------|-----------------|
| Format 1 | `.ext` | field1, field2 |

## CLI Reference

```bash
# Via kunlib
kunlib run your-skill-name --demo --output /tmp/demo

# Direct
python skills/your-skill-name/your_skill.py --demo --output /tmp/demo

# With real data
python skills/your-skill-name/your_skill.py --input <file> --output <dir>
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--input` | path | — | Input file or directory |
| `--output` | path | required | Output directory |
| `--demo` | flag | false | Run with synthetic data |

## Output Structure

```
output_dir/
├── report.md
├── result.json
├── tables/
│   └── results.csv
└── reproducibility/
    └── commands.sh
```

## Safety

- **Local-first**: All computation runs locally
- **Disclaimer**: Research tool only
- **Reproducibility**: Full command log
````

---

## 14. `AGENTS.md`

````markdown name=AGENTS.md
# AGENTS.md — KunLib Guide for AI Coding Agents

This guide is for AI coding agents (Codex, Copilot, Claude Code, Cursor, etc.)
working on the KunLib codebase, and for agents (like kunbreed) that want to
**add new skills** by converting user scripts into KunLib-compatible skills.

## Project Overview

KunLib is a genetic breeding analysis skill library. Each skill is a
self-contained module that performs a specific breeding/genetics analysis task.
Skills are registered via the `@skill` decorator from `kunlib` and can be
invoked via CLI, direct `python script.py`, or programmatically by an agent.

## Setup

```bash
git clone https://github.com/kzy599/kunlib.git && cd kunlib
pip install -e .
kunlib list
kunlib run <skill> --demo
```

## Commands

| Command | Purpose |
|---------|---------|
| `kunlib list` | List all registered skills |
| `kunlib run <skill> --demo` | Run skill with demo data |
| `kunlib run <skill> --input <path> --output <dir>` | Run with real data |
| `python skills/<name>/<script>.py --demo --output /tmp/out` | Direct execution |
| `kunlib catalog` | Regenerate `skills/catalog.json` |
| `pytest -v` | Run all tests |

## Project Structure

```
kunlib/
├── kunlib/              # SDK package
│   ├── __init__.py      # Exports: skill, Param, KunResult
│   ├── skill.py         # @skill decorator + SkillMeta + argparse builder
│   ├── result.py        # KunResult standard output
│   ├── registry.py      # Auto-discovery from skills/ directory
│   ├── cli.py           # CLI entry point
│   ├── catalog.py       # catalog.json generator
│   ├── agent_adapter.py # Agent integration interface
│   └── common/          # Shared utilities
├── skills/              # Skill library (one dir per skill)
│   ├── <skill-name>/
│   │   ├── SKILL.md     # Required: methodology doc for agents
│   │   ├── <script>.py  # Required: implementation with @skill
│   │   ├── demo/        # Encouraged: synthetic test data
│   │   └── tests/       # Encouraged: pytest tests
│   └── catalog.json     # Auto-generated
├── templates/
│   └── SKILL-TEMPLATE.md
└── AGENTS.md            # This file
```

## How a Skill Works

Every skill has two required files:

1. **SKILL.md** — Human/agent-readable methodology doc (hand-written)
2. **<script>.py** — Python implementation using `@skill` decorator

The script MUST:
- `from kunlib import skill, Param, KunResult`
- Use `@skill(...)` decorator on its main `run()` function
- Declare all CLI params via `Param(...)` in the decorator
- Return a `KunResult` from `run()`
- Have `if __name__ == "__main__": run.__kunlib_meta__.run_cli()`

## Skill Script Template

```python
#!/usr/bin/env python3
"""<Skill Name> — one-line description."""
from __future__ import annotations
import argparse
from pathlib import Path

from kunlib import skill, Param, KunResult

SKILL_DIR = Path(__file__).resolve().parent

@skill(
    name="your-skill-name",          # must match folder name
    version="0.1.0",
    description="What this skill does in one line",
    author="your-name",
    tags=["tag1", "tag2"],
    trigger_keywords=["keyword1", "keyword2"],
    emoji="🧬",
    params=[
        Param("input", help="Input file or directory"),
        Param("output", required=True, help="Output directory"),
        Param("demo", is_flag=True, help="Run with synthetic data"),
        # add more Param(...) as needed
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.demo:
        # load from SKILL_DIR / "demo" / ...
        mode = "demo"
    else:
        # load from args.input
        mode = "input"

    # ... your computation ...

    return KunResult(
        skill_name="your-skill-name",
        skill_version="0.1.0",
        mode=mode,
        output_dir=output_dir,
        summary={"key_metric": 42},
        tables=[output_dir / "tables" / "results.csv"],
        report_path=output_dir / "report.md",
    )

if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
```

---

## 🔧 Converting a User Script into a KunLib Skill

When a user gives you any functional script (Python, R wrapper, shell pipeline,
etc.) that has inputs, outputs, and parameters, follow this procedure to convert
it into a proper KunLib skill.

### Step 1: Analyze the Original Script

Identify from the user's script:
- **Inputs**: What files/directories does it read? What formats?
- **Outputs**: What files does it produce? Where?
- **Parameters**: What knobs can the user tune? Types, defaults?
- **Dependencies**: External binaries (Rscript, plink, samtools)? Python packages?
- **Core logic**: The actual computation (keep this unchanged as much as possible)

### Step 2: Create Skill Directory

```
skills/<skill-name>/
├── SKILL.md          # You must write this (see templates/SKILL-TEMPLATE.md)
├── <skill_name>.py   # Converted script
├── demo/             # At least one small synthetic input
└── tests/
    └── test_<skill_name>.py
```

Naming rules:
- Folder: lowercase-kebab (`hiblup-ebv`, not `HI_BLUP`)
- Python file: lowercase-underscore (`hiblup_ebv.py`)
- Skill name in `@skill()`: matches folder name exactly

### Step 3: Wrap the Script

Take the user's core logic and wrap it:

```python
from kunlib import skill, Param, KunResult

# 1. Move the user's core logic into a plain function
def compute_something(input_path, output_dir, param1, param2):
    # ... user's original code, minimally modified ...
    # ... writes output files to output_dir ...
    return {"n_results": 42}  # summary dict

# 2. Declare the skill with @skill decorator
@skill(
    name="skill-name",
    version="0.1.0",
    description="...",
    params=[
        Param("input", help="..."),
        Param("output", required=True, help="..."),
        Param("demo", is_flag=True, help="..."),
        Param("param1", type=int, default=10, help="..."),
        Param("param2", type=float, default=0.05, help="..."),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.demo:
        input_path = SKILL_DIR / "demo" / "sample_input.csv"
        mode = "demo"
    else:
        input_path = Path(args.input)
        mode = "input"

    # 3. Call the user's core logic
    summary = compute_something(
        input_path=input_path,
        output_dir=output_dir,
        param1=args.param1,
        param2=args.param2,
    )

    # 4. Return KunResult
    return KunResult(
        skill_name="skill-name",
        skill_version="0.1.0",
        mode=mode,
        output_dir=output_dir,
        summary=summary,
        report_path=output_dir / "report.md",
    )

if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
```

### Step 4: Conversion Rules

| Original Script Has | KunLib Conversion |
|---------------------|-------------------|
| `argparse` with `--input`/`--output` | Map to `Param("input", ...)` / `Param("output", required=True, ...)` |
| Hardcoded input path | Replace with `args.input` or `SKILL_DIR / "demo" / ...` |
| Hardcoded output path | Replace with `args.output` |
| `print()` results | Keep prints, but also `return KunResult(summary={...})` |
| Writes files to disk | Write to `output_dir`, list in `KunResult.tables`/`.figures` |
| R/shell subprocess | Keep as-is, use `subprocess.run(check=True)` |
| No demo mode | Add `Param("demo", is_flag=True)` + synthetic data in `demo/` |
| Magic numbers | Extract to `Param(...)` with sensible defaults |
| `sys.exit()` on error | Raise exceptions instead; let kunlib handle exit codes |
| Relative path imports | Use `SKILL_DIR = Path(__file__).resolve().parent` |

### Step 5: Write SKILL.md

Copy `templates/SKILL-TEMPLATE.md` and fill in every section. Key points:
- YAML frontmatter `name:` must match the folder name and `@skill(name=...)`
- Include real CLI examples that work
- Document every parameter in the Parameters table
- Show the exact output directory structure
- List all external dependencies (bins, R packages, Python packages)

### Step 6: Write Tests

```python
# tests/test_<skill_name>.py
from pathlib import Path
import subprocess, sys

def test_demo_mode(tmp_path):
    script = Path(__file__).resolve().parent.parent / "<skill_name>.py"
    result = subprocess.run(
        [sys.executable, str(script), "--demo", "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "result.json").exists()
```

### Step 7: Verify

```bash
# Does it run?
python skills/<name>/<script>.py --demo --output /tmp/test

# Does kunlib see it?
kunlib list

# Does kunlib run it?
kunlib run <name> --demo --output /tmp/test

# Do tests pass?
pytest skills/<name>/tests/ -v
```

## Safety Boundaries

1. **Local-first**: No data uploads without explicit consent
2. **Disclaimer**: Every result.json includes the KunLib disclaimer
3. **Reproducibility**: Skills should log commands to reproducibility/ dir
4. **No hallucinated science**: Parameters must trace to cited methods
````

---

## 15. `pyproject.toml`

```toml name=pyproject.toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "kunlib"
version = "0.1.0"
description = "Genetic breeding analysis skill library"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [{name = "kzy599"}]
keywords = ["breeding", "genetics", "bioinformatics", "genomic-selection"]

[project.scripts]
kunlib = "kunlib.cli:main"

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff"]

[tool.setuptools.packages.find]
include = ["kunlib*"]

[tool.pytest.ini_options]
pythonpath = ["."]
addopts = "--import-mode=importlib"
testpaths = ["tests"]
```

---

## 16. `tests/test_registry.py`

```python name=tests/test_registry.py
"""测试技能自动发现。"""
from kunlib.registry import discover_all, get_skill_docs
from kunlib.skill import get_registry


def test_discover_returns_dict():
    registry = discover_all()
    assert isinstance(registry, dict)


def test_get_skill_docs_returns_dict():
    discover_all()
    docs = get_skill_docs()
    assert isinstance(docs, dict)
```

---

## 17. `tests/test_result.py`

```python name=tests/test_result.py
"""测试 KunResult 序列化。"""
from pathlib import Path
from kunlib.result import KunResult


def test_to_dict():
    r = KunResult(skill_name="test", skill_version="0.0.1", summary={"x": 1})
    d = r.to_dict()
    assert d["skill"] == "test"
    assert d["summary"] == {"x": 1}
    assert "disclaimer" in d


def test_save(tmp_path):
    r = KunResult(skill_name="test", skill_version="0.0.1", output_dir=tmp_path)
    path = r.save()
    assert path.exists()
    assert path.name == "result.json"
```

---

## 18. `tests/test_skill.py`

```python name=tests/test_skill.py
"""测试 @skill 装饰器和 SkillMeta。"""
import argparse
from kunlib import skill, Param, KunResult


@skill(
    name="test-skill",
    version="0.0.1",
    description="A test skill",
    params=[
        Param("output", required=True, help="Output dir"),
        Param("demo", is_flag=True, help="Demo mode"),
        Param("count", type=int, default=5, help="Count"),
    ],
)
def _dummy_run(args: argparse.Namespace) -> KunResult:
    return KunResult(skill_name="test-skill", skill_version="0.0.1", summary={"count": args.count})


def test_decorator_registers():
    from kunlib.skill import get_registry
    assert "test-skill" in get_registry()


def test_meta_attached():
    assert hasattr(_dummy_run, "__kunlib_meta__")
    assert _dummy_run.__kunlib_meta__.name == "test-skill"


def test_build_parser():
    parser = _dummy_run.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x", "--demo", "--count", "10"])
    assert args.output == "/tmp/x"
    assert args.demo is True
    assert args.count == 10


def test_run_cli(tmp_path):
    result = _dummy_run.__kunlib_meta__.run_cli(["--output", str(tmp_path), "--count", "7"])
    assert result.summary["count"] == 7
```

---

## 19. `Makefile`

```makefile name=Makefile
.PHONY: test list catalog install

install:
	pip install -e ".[dev]"

test:
	pytest -v

list:
	kunlib list

catalog:
	kunlib catalog
```

---

## 20. `README.md`

````markdown name=README.md
# 🧬 KunLib — Genetic Breeding Analysis Skill Library

KunLib is a skill library for genetic breeding analysis tasks.
Each skill is a self-contained module with standardized input/output,
discoverable by AI agents (kunbreed, OpenClaw, etc.) via `SKILL.md`.

## Quick Start

```bash
pip install -e .
kunlib list
kunlib run <skill> --demo --output /tmp/out
```

## Direct Execution

Every skill script is independently runnable:

```bash
python skills/hiblup-ebv/hiblup_ebv.py --demo --output /tmp/out
```

## For AI Agents

```python
from kunlib.agent_adapter import KunLibAdapter

adapter = KunLibAdapter()
docs = adapter.get_skill_docs()       # Read SKILL.md for methodology
manifest = adapter.get_skill_manifest()  # Structured skill catalog
result = adapter.run_skill("hiblup-ebv", {"demo": True, "output": "/tmp/out"})
```

## Add a Skill

See [AGENTS.md](AGENTS.md) §"Converting a User Script into a KunLib Skill".

## License

MIT
````

---

## 文件清单总结

```
kunlib/
├── kunlib/
│   ├── __init__.py            # 文件 1
│   ├── skill.py               # 文件 2
│   ├── result.py              # 文件 3
│   ├── registry.py            # 文件 4
│   ├── cli.py                 # 文件 5
│   ├── catalog.py             # 文件 6
│   ├── agent_adapter.py       # 文件 7
│   └── common/
│       ├── __init__.py        # 文件 8
│       ├── report.py          # 文件 9
│       ├── checksums.py       # 文件 10
│       ├── parsers.py         # 文件 11
│       └── breeding.py        # 文件 12
├── skills/                    # (空，等你加技能)
├── templates/
│   └── SKILL-TEMPLATE.md      # 文件 13
├── AGENTS.md                  # 文件 14 (含技能添加 prompt)
├── pyproject.toml             # 文件 15
├── tests/
│   ├── test_registry.py       # 文件 16
│   ├── test_result.py         # 文件 17
│   └── test_skill.py          # 文件 18
├── Makefile                   # 文件 19
└── README.md                  # 文件 20
```

AGENTS.md 里的 **§"Converting a User Script into a KunLib Skill"** 就是你要的那个 prompt——任何 agent 读到这段指令后，就能把用户随便写的脚本改造成符合 kunlib 规范的技能。
