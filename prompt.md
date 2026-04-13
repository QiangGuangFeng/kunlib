在 main 上追加以下改动。这是一次性的综合改造，涉及 3 个核心设计变更：

1. **框架自动注入 `--input` / `--output`**，开发者不需要在 params 中声明
2. **框架自动创建标准输出目录结构**（`work/`、`tables/`、`figures/`、`logs/`、`reproducibility/`），技能直接用
3. **`KunResult.files` 改为 `dict[str, list[Path]]`** 灵活分类（已完成，保持不变）

---

## 文件 1：完整替换 `kunlib/skill.py`

```python
"""KunLib Skill SDK — 声明式技能注册框架。

开发者在技能主脚本中使用 @skill 装饰器即可完成:
  1. 元信息注册（name, tags, trigger_keywords, params...）
  2. argparse 自动构建（自动注入 --input / --output）
  3. 标准输出目录结构自动创建
  4. CLI 入口 (run_cli)
  5. 被 kunlib CLI / agent adapter 发现和调用
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


# 框架自动创建的标准子目录名
STANDARD_DIRS = ("work", "tables", "figures", "logs", "reproducibility")

# 框架保留的参数名，开发者在 params 中声明会被静默跳过
_RESERVED_PARAMS = {"input", "output"}


@dataclass
class Param:
    """技能参数声明。

    name 使用 kebab-case (e.g. "trait-pos")，与 CLI flag 一致。
    argparse 会自动将其转为 snake_case 属性 (args.trait_pos)。

    注意: "input" 和 "output" 由框架自动注入，不需要声明。
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
        """从 self.params 自动构建 ArgumentParser。

        框架自动注入:
          --input   输入文件或目录（可选，demo 模式下可省略）
          --output  输出目录（必需）
        """
        parser = argparse.ArgumentParser(
            prog=f"kunlib run {self.name}",
            description=self.description,
        )
        # ---- 框架强制参数 ----
        parser.add_argument("--input", help="Input file or directory")
        parser.add_argument("--output", required=True, help="Output directory (required)")

        # ---- 技能自定义参数 ----
        for p in self.params:
            if p.name in _RESERVED_PARAMS:
                continue  # 由框架注入，跳过
            flag = f"--{p.name}"
            if p.is_flag:
                parser.add_argument(flag, action="store_true", default=False, help=p.help)
            else:
                kw: dict[str, Any] = {"type": p.type, "help": p.help, "default": p.default}
                if p.required:
                    kw["required"] = True
                parser.add_argument(flag, **kw)
        return parser

    def run_cli(self, argv: list[str] | None = None) -> KunResult:
        """解析命令行参数 → 准备标准目录 → 执行 entry_func → 保存结果。

        框架自动创建标准输出目录结构:
          output/
          ├── work/              中间/临时文件
          ├── tables/            最终表格
          ├── figures/           最终图片
          ├── logs/              运行日志
          ├── reproducibility/   复现指令
          └── result.json        框架自动写

        技能通过 args.output_dir / args.work_dir / args.tables_dir /
        args.figures_dir / args.logs_dir / args.repro_dir 访问这些目录。
        """
        parser = self.build_parser()
        args = parser.parse_args(argv)

        # ---- 创建标准目录结构并注入到 args ----
        output_dir = Path(args.output).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        dirs = {}
        for d in STANDARD_DIRS:
            p = output_dir / d
            p.mkdir(exist_ok=True)
            dirs[d] = p

        args.output_dir = output_dir
        args.work_dir = dirs["work"]
        args.tables_dir = dirs["tables"]
        args.figures_dir = dirs["figures"]
        args.logs_dir = dirs["logs"]
        args.repro_dir = dirs["reproducibility"]

        # ---- 执行技能 ----
        result = self.entry_func(args)

        # ---- 校验返回值 ----
        if not isinstance(result, KunResult):
            raise TypeError(
                f"[{self.name}] run() must return KunResult, got {type(result).__name__}"
            )

        # 自动补全 output_dir
        if result.output_dir is None:
            result.output_dir = output_dir

        # ---- 保存 result.json + 打印摘要 ----
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

    --input 和 --output 由框架自动注入，开发者只需声明技能特有的参数。

    用法::

        @skill(
            name="hiblup-ebv",
            version="0.1.0",
            description="GBLUP breeding values via HI-BLUP",
            params=[
                Param("demo", is_flag=True, help="Run with synthetic data"),
                Param("trait-pos", type=int, default=2, help="Trait column"),
            ],
        )
        def run(args: argparse.Namespace) -> KunResult:
            # 框架自动提供:
            #   args.input       输入路径（可选）
            #   args.output      输出路径字符串
            #   args.output_dir  输出 Path 对象
            #   args.work_dir    中间文件目录
            #   args.tables_dir  最终表格目录
            #   args.figures_dir 最终图片目录
            #   args.logs_dir    日志目录
            #   args.repro_dir   复现指令目录
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
            has_demo=any(p.name == "demo" and p.is_flag for p in (params or [])),
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

## 文件 2：完整替换 `skills/hiblup-ebv/hiblup_ebv.py`

关键改动：
- 从 `params` 中删除 `Param("input", ...)` 和 `Param("output", ...)`
- 使用框架注入的 `args.work_dir`、`args.tables_dir`、`args.repro_dir`
- R 脚本在 `work_dir` 中运行，最终结果复制到 `tables_dir`

```python
"""HI-BLUP EBV — Estimate breeding values using GBLUP via HI-BLUP."""
from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from pathlib import Path

from kunlib import skill, Param, KunResult
from kunlib.common.report import generate_report_header, generate_report_footer
from kunlib.common.checksums import sha256_file

SKILL_DIR = Path(__file__).resolve().parent
RSCRIPT_DEMO = SKILL_DIR / "filegenerator.r"
RSCRIPT_HIBLUP = SKILL_DIR / "run_hiblup.r"

REQUIRED_FILES = ["phe.csv", "geno.csv", "sel_id.csv", "ref_id.csv"]


def _check_bins() -> dict[str, str | None]:
    """Check availability of required external binaries."""
    bins: dict[str, str | None] = {}
    for name in ("Rscript",):
        bins[name] = shutil.which(name)
    return bins


def _run_r(script: Path, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run an R script via Rscript."""
    cmd = ["Rscript", "--vanilla", str(script)] + args
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=True)


def _validate_input(input_dir: Path) -> list[str]:
    """Return list of missing required files."""
    return [f for f in REQUIRED_FILES if not (input_dir / f).exists()]


def _generate_demo(work_dir: Path) -> Path:
    """Generate demo data into work_dir using filegenerator.r."""
    _run_r(RSCRIPT_DEMO, [str(work_dir)], cwd=SKILL_DIR)
    return work_dir


def _read_ebv_summary(work_dir: Path) -> dict:
    """Read EBV output files from work_dir and produce summary statistics."""
    summary: dict = {}
    for name in ("phe_ebv.csv", "sel_ebv.csv", "ref_ebv.csv"):
        fpath = work_dir / name
        if fpath.exists():
            with open(fpath, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            stats: dict = {"n_rows": len(rows)}
            if rows and "EBV" in rows[0]:
                ebvs = [float(r["EBV"]) for r in rows if r.get("EBV")]
                if ebvs:
                    stats["mean_ebv"] = round(sum(ebvs) / len(ebvs), 4)
                    stats["min_ebv"] = round(min(ebvs), 4)
                    stats["max_ebv"] = round(max(ebvs), 4)
            summary[name] = stats
    return summary


def _write_report(output_dir: Path, mode: str, summary: dict) -> Path:
    """Write KunLib-style report.md."""
    report_path = output_dir / "report.md"
    header = generate_report_header(
        title="HI-BLUP EBV Report",
        skill_name="hiblup-ebv",
        skill_version="0.1.0",
        extra={"Mode": mode},
    )
    body_lines = ["## Summary\n"]
    for fname, stats in summary.items():
        body_lines.append(f"### {fname}\n")
        for k, v in stats.items():
            body_lines.append(f"- **{k}**: {v}")
        body_lines.append("")
    footer = generate_report_footer()
    report_path.write_text(
        header + "\n".join(body_lines) + footer, encoding="utf-8"
    )
    return report_path


@skill(
    name="hiblup-ebv",
    version="0.1.0",
    description="Estimate breeding values (EBV) using GBLUP via HI-BLUP",
    author="kzy599",
    tags=[
        "animal-breeding", "gblup", "ebv", "hiblup",
        "quantitative-genetics", "genomic-selection",
    ],
    trigger_keywords=[
        "gblup", "ebv", "breeding value", "hiblup",
        "genomic selection", "estimate ebv",
        "估计育种值", "基因组选择",
    ],
    chaining_partners=["kinship-matrix", "gwas-prs"],
    input_formats=["csv-dir (phe.csv + geno.csv + sel_id.csv + ref_id.csv)"],
    requires_bins=["python3", "Rscript"],
    emoji="🐄",
    params=[
        # --input 和 --output 由框架自动注入，不需要声明
        Param("demo", is_flag=True, help="Run with synthetic demo data"),
        Param("trait-pos", type=int, default=2,
              help="Column index (1-based) of the target trait in phe.csv"),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    """Main pipeline for HI-BLUP EBV estimation.

    框架自动提供的目录:
      args.output_dir   总输出目录
      args.work_dir     中间文件 (R 脚本在这里跑)
      args.tables_dir   最终表格
      args.figures_dir   最终图片
      args.logs_dir     日志
      args.repro_dir    复现指令
    """
    output_dir = args.output_dir
    work_dir = args.work_dir
    tables_dir = args.tables_dir
    repro_dir = args.repro_dir

    mode = "demo" if args.demo else "input"
    trait_pos = args.trait_pos

    # --- resolve input directory ---
    if args.demo:
        input_dir = _generate_demo(work_dir)
    else:
        if not args.input:
            raise SystemExit("Error: --input is required when not using --demo")
        input_dir = Path(args.input)

    # --- validate inputs ---
    missing = _validate_input(input_dir)
    if missing:
        raise SystemExit(
            f"Error: missing required files in {input_dir}: {', '.join(missing)}"
        )

    # --- run HI-BLUP pipeline via R (中间文件全部在 work_dir) ---
    _run_r(
        RSCRIPT_HIBLUP,
        [str(input_dir), str(work_dir), str(trait_pos)],
        cwd=SKILL_DIR,
    )

    # --- collect summary from work_dir ---
    summary = _read_ebv_summary(work_dir)

    # --- copy final results from work_dir to tables_dir ---
    tables = []
    for name in ("phe_ebv.csv", "sel_ebv.csv", "ref_ebv.csv"):
        src = work_dir / name
        if src.exists():
            dst = tables_dir / name
            shutil.copy2(src, dst)
            tables.append(dst)

    # --- write report ---
    report_path = _write_report(output_dir, mode, summary)

    # --- write reproducibility ---
    (repro_dir / "commands.sh").write_text(
        f"# Reproduce this analysis\n"
        f"Rscript --vanilla run_hiblup.r {input_dir} {work_dir} {trait_pos}\n",
        encoding="utf-8",
    )

    # --- checksums ---
    checksums = {t.name: sha256_file(t) for t in tables}

    return KunResult(
        skill_name="hiblup-ebv",
        skill_version="0.1.0",
        mode=mode,
        output_dir=output_dir,
        summary=summary,
        data={"checksums": checksums, "trait_pos": trait_pos},
        files={"tables": tables},
        report_path=report_path,
    )


if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
```

---

## 文件 3：完整替换 `tests/test_skill.py`

```python
"""测试 @skill 装饰器和 SkillMeta。"""
import argparse
from kunlib import skill, Param, KunResult


@skill(
    name="test-skill",
    version="0.0.1",
    description="A test skill",
    params=[
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


def test_build_parser_has_input_output():
    """框架自动注入 --input 和 --output。"""
    parser = _dummy_run.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x", "--input", "/data", "--demo", "--count", "10"])
    assert args.output == "/tmp/x"
    assert args.input == "/data"
    assert args.demo is True
    assert args.count == 10


def test_output_is_required():
    """--output 是必需的。"""
    parser = _dummy_run.__kunlib_meta__.build_parser()
    import pytest
    with pytest.raises(SystemExit):
        parser.parse_args(["--count", "10"])  # 没有 --output 应该失败


def test_reserved_params_skipped():
    """开发者在 params 中声明 input/output 不会导致 argparse 重复。"""
    @skill(
        name="test-reserved",
        version="0.0.1",
        params=[
            Param("input", help="should be skipped"),
            Param("output", required=True, help="should be skipped"),
            Param("extra", type=int, default=1, help="custom param"),
        ],
    )
    def _dummy(args):
        return KunResult(skill_name="test-reserved", skill_version="0.0.1")

    parser = _dummy.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x", "--extra", "42"])
    assert args.output == "/tmp/x"
    assert args.extra == 42


def test_run_cli_creates_standard_dirs(tmp_path):
    """run_cli 自动创建标准目录结构。"""
    result = _dummy_run.__kunlib_meta__.run_cli(["--output", str(tmp_path), "--count", "7"])
    assert result.summary["count"] == 7
    # 框架应自动创建标准子目录
    for d in ("work", "tables", "figures", "logs", "reproducibility"):
        assert (tmp_path / d).is_dir(), f"Missing standard dir: {d}"
    # result.json 应自动写入
    assert (tmp_path / "result.json").exists()


def test_run_cli_rejects_non_kunresult(tmp_path):
    """run() 不返回 KunResult 时应抛出 TypeError。"""
    @skill(name="test-bad-return", version="0.0.1", params=[])
    def _bad(args):
        return {"not": "a KunResult"}

    import pytest
    with pytest.raises(TypeError, match="must return KunResult"):
        _bad.__kunlib_meta__.run_cli(["--output", str(tmp_path)])
```

---

## 文件 4：完整替换 `tests/test_result.py`

```python
"""测试 KunResult 序列化。"""
from pathlib import Path
from kunlib.result import KunResult


def test_to_dict():
    r = KunResult(skill_name="test", skill_version="0.0.1", summary={"x": 1})
    d = r.to_dict()
    assert d["skill"] == "test"
    assert d["summary"] == {"x": 1}
    assert "disclaimer" in d
    assert "files" in d
    assert isinstance(d["files"], dict)


def test_to_dict_with_files(tmp_path):
    t1 = tmp_path / "tables" / "a.csv"
    t1.parent.mkdir()
    t1.write_text("x")
    f1 = tmp_path / "figures" / "plot.png"
    f1.parent.mkdir()
    f1.write_text("x")

    r = KunResult(
        skill_name="test",
        skill_version="0.0.1",
        output_dir=tmp_path,
        files={
            "tables": [t1],
            "figures": [f1],
        },
    )
    d = r.to_dict()
    assert d["files"]["tables"] == ["tables/a.csv"]
    assert d["files"]["figures"] == ["figures/plot.png"]


def test_save(tmp_path):
    r = KunResult(skill_name="test", skill_version="0.0.1", output_dir=tmp_path)
    path = r.save()
    assert path.exists()
    assert path.name == "result.json"
```

---

## 文件 5：完整替换 `tests/test_hiblup_ebv.py`

```python
"""Tests for hiblup-ebv skill."""
import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the skill module (folder name contains a hyphen, so normal import fails)
# ---------------------------------------------------------------------------
_SKILL_PY = Path(__file__).resolve().parent.parent / "skills" / "hiblup-ebv" / "hiblup_ebv.py"
_spec = importlib.util.spec_from_file_location("hiblup_ebv", _SKILL_PY)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export key names for convenience
_run = _mod.run
_validate_input = _mod._validate_input
_REQUIRED_FILES = _mod.REQUIRED_FILES
_SKILL_DIR = _mod.SKILL_DIR


# ---------------------------------------------------------------------------
# Registration & metadata
# ---------------------------------------------------------------------------
class TestRegistration:
    def test_skill_registered(self):
        from kunlib.skill import get_registry
        assert "hiblup-ebv" in get_registry()

    def test_meta_name(self):
        assert _run.__kunlib_meta__.name == "hiblup-ebv"

    def test_meta_version(self):
        assert _run.__kunlib_meta__.version == "0.1.0"

    def test_meta_emoji(self):
        assert _run.__kunlib_meta__.emoji == "🐄"

    def test_meta_author(self):
        assert _run.__kunlib_meta__.author == "kzy599"

    def test_has_demo_flag(self):
        assert _run.__kunlib_meta__.has_demo is True


# ---------------------------------------------------------------------------
# CLI parser — --input and --output auto-injected by framework
# ---------------------------------------------------------------------------
class TestParser:
    def test_parse_demo(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--demo"])
        assert args.output == "/tmp/x"
        assert args.demo is True

    def test_has_input_flag(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--input", "/data"])
        assert args.input == "/data"

    def test_parse_trait_pos(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--trait-pos", "3"])
        assert args.trait_pos == 3

    def test_default_trait_pos(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.trait_pos == 2


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
class TestValidation:
    def test_missing_all(self, tmp_path):
        missing = _validate_input(tmp_path)
        assert set(missing) == set(_REQUIRED_FILES)

    def test_complete(self, tmp_path):
        for f in _REQUIRED_FILES:
            (tmp_path / f).write_text("ID\n1\n")
        assert _validate_input(tmp_path) == []

    def test_partial(self, tmp_path):
        (tmp_path / "phe.csv").write_text("ID\n1\n")
        missing = _validate_input(tmp_path)
        assert "phe.csv" not in missing
        assert len(missing) == 3


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------
class TestFiles:
    def test_skill_md_exists(self):
        assert (_SKILL_DIR / "SKILL.md").exists()

    def test_filegenerator_r_exists(self):
        assert (_SKILL_DIR / "filegenerator.r").exists()

    def test_run_hiblup_r_exists(self):
        assert (_SKILL_DIR / "run_hiblup.r").exists()


# ---------------------------------------------------------------------------
# Discovery integration
# ---------------------------------------------------------------------------
class TestDiscovery:
    def test_discover_finds_skill(self):
        from kunlib.registry import discover_all
        registry = discover_all()
        assert "hiblup-ebv" in registry

    def test_skill_docs_include_skill(self):
        from kunlib.registry import discover_all, get_skill_docs
        discover_all()
        docs = get_skill_docs()
        assert "hiblup-ebv" in docs
        assert "KunLib" in docs["hiblup-ebv"]
```

---

## 文件 6：完整替换 `AGENTS.md`

````markdown
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
kunlib run <skill> --demo --output /tmp/out
```

## Commands

| Command | Purpose |
|---------|---------|
| `kunlib list` | List all registered skills |
| `kunlib run <skill> --demo --output /tmp/out` | Run skill with demo data |
| `kunlib run <skill> --input <path> --output <dir>` | Run with real data |
| `python skills/<name>/<script>.py --demo --output /tmp/out` | Direct execution |
| `kunlib catalog` | Regenerate `skills/catalog.json` |
| `pytest -v` | Run all tests |

## Project Structure

```
kunlib/
├── kunlib/              # SDK package
│   ├── __init__.py      # Exports: skill, Param, KunResult
│   ├── skill.py         # @skill decorator + SkillMeta + auto dir setup
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
- Only declare skill-specific params (`--input`/`--output` auto-injected by framework)
- Return a `KunResult` from `run()`
- Have `if __name__ == "__main__": run.__kunlib_meta__.run_cli()`

## Framework Auto-Injected Features

### Auto parameters

`--input` and `--output` are **automatically injected** by the framework. Do NOT
declare them in `params=[...]`. `--output` is always required.

### Auto directory structure

When `run_cli()` is called, the framework creates the following directories
under `--output` **before** calling `run()`:

```
output/
├── work/              # Intermediate/temp files (R workdir, PLINK outputs, etc.)
├── tables/            # Final tabular results
├── figures/           # Final plots/images
├── logs/              # Run logs
├── reproducibility/   # Commands to reproduce
└── result.json        # Auto-written by framework after run() returns
```

These are injected into `args` and accessible as:

| `args` attribute | Path | Purpose |
|------------------|------|---------|
| `args.output_dir` | `output/` | Top-level output dir (Path object) |
| `args.work_dir` | `output/work/` | Intermediate files |
| `args.tables_dir` | `output/tables/` | Final tables |
| `args.figures_dir` | `output/figures/` | Final figures |
| `args.logs_dir` | `output/logs/` | Logs |
| `args.repro_dir` | `output/reproducibility/` | Reproducibility |

### Auto result.json

`result.json` is written automatically by the framework after `run()` returns.
The skill does NOT need to call `result.save()`.

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
        # --input and --output are auto-injected, do NOT list here
        Param("demo", is_flag=True, help="Run with synthetic data"),
        # add more Param(...) as needed
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    # Framework provides: args.output_dir, args.work_dir, args.tables_dir,
    #                     args.figures_dir, args.logs_dir, args.repro_dir

    if args.demo:
        # generate or load demo data into args.work_dir
        mode = "demo"
    else:
        # load from args.input
        mode = "input"

    # ... your computation, write intermediate files to args.work_dir ...
    # ... copy final tables to args.tables_dir ...
    # ... copy final figures to args.figures_dir ...

    return KunResult(
        skill_name="your-skill-name",
        skill_version="0.1.0",
        mode=mode,
        output_dir=args.output_dir,
        summary={"key_metric": 42},
        files={
            "tables": [args.tables_dir / "results.csv"],
            "figures": [args.figures_dir / "plot.png"],
        },
        report_path=args.output_dir / "report.md",
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
def compute_something(input_path, work_dir, tables_dir, param1, param2):
    # ... user's original code, minimally modified ...
    # ... write intermediate files to work_dir ...
    # ... copy final results to tables_dir ...
    return {"n_results": 42}  # summary dict

# 2. Declare the skill with @skill decorator
@skill(
    name="skill-name",
    version="0.1.0",
    description="...",
    params=[
        # --input and --output auto-injected, do NOT list
        Param("demo", is_flag=True, help="..."),
        Param("param1", type=int, default=10, help="..."),
        Param("param2", type=float, default=0.05, help="..."),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    if args.demo:
        input_path = SKILL_DIR / "demo" / "sample_input.csv"
        mode = "demo"
    else:
        input_path = Path(args.input)
        mode = "input"

    # 3. Call the user's core logic with framework dirs
    summary = compute_something(
        input_path=input_path,
        work_dir=args.work_dir,
        tables_dir=args.tables_dir,
        param1=args.param1,
        param2=args.param2,
    )

    # 4. Return KunResult
    return KunResult(
        skill_name="skill-name",
        skill_version="0.1.0",
        mode=mode,
        output_dir=args.output_dir,
        summary=summary,
        files={"tables": [args.tables_dir / "output.csv"]},
        report_path=args.output_dir / "report.md",
    )

if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
```

### Step 4: Conversion Rules

| Original Script Has | KunLib Conversion |
|---------------------|-------------------|
| `argparse` with `--input`/`--output` | Remove — framework auto-injects them |
| Hardcoded input path | Replace with `args.input` or `SKILL_DIR / "demo" / ...` |
| Hardcoded output path | Replace with `args.tables_dir` / `args.figures_dir` |
| Intermediate files | Write to `args.work_dir` |
| `print()` results | Keep prints, but also `return KunResult(summary={...})` |
| Writes files to disk | Final → `tables_dir`/`figures_dir`, temp → `work_dir` |
| R/shell subprocess | Keep as-is, set `cwd=args.work_dir` |
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
    # Framework auto-creates these dirs
    assert (tmp_path / "work").is_dir()
    assert (tmp_path / "tables").is_dir()
```

### Step 7: Verify

```bash
# Does it run?
python skills/<name>/<script>.py --demo --output /tmp/test

# Does kunlib see it?
kunlib list

# Does kunlib run it?
kunlib run <name> --demo --output /tmp/test

# Standard dirs created?
ls /tmp/test/
# → work/  tables/  figures/  logs/  reproducibility/  result.json  report.md

# Do tests pass?
pytest tests/ -v
```

## Safety Boundaries

1. **Local-first**: No data uploads without explicit consent
2. **Disclaimer**: Every result.json includes the KunLib disclaimer
3. **Reproducibility**: Skills should log commands to `args.repro_dir`
4. **No hallucinated science**: Parameters must trace to cited methods
````

---

## 要求

- 所有测试必须通过 (`pytest -v`)
- `--input` 和 `--output` 由框架注入，开发者在 params 里写了也不报错（静默跳过）
- `run_cli()` 在调用 `entry_func(args)` 之前创建 `work/`、`tables/`、`figures/`、`logs/`、`reproducibility/` 五个子目录，并注入到 `args`
- `run()` 返回非 `KunResult` 时 `run_cli()` 抛 `TypeError`
- `result.json` 由框架在 `run()` 返回后自动写入，技能不需要调用 `result.save()`
- hiblup_ebv.py 的 R 脚本在 `args.work_dir` 中运行，最终结果复制到 `args.tables_dir`
- `kunlib/__init__.py` 不需要改动
- `kunlib/result.py` 已经是 `files: dict[str, list[Path]]` 不需要改动
- `kunlib/agent_adapter.py` 和 `kunlib/catalog.py` 中如果引用了旧的 `tables`/`figures` 字段需要同步更新为 `files`
