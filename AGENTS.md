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
| `kunlib run <skill> --input <dir> --output <dir>` | Run with real data (input is a directory) |
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
- `from kunlib import skill, Param, KunResult, SkillRequires, IOField`
- Use `@skill(...)` decorator on its main `run()` function
- Declare `kind=` in `@skill()` — default is `"data"`, see §Skill Kinds for all types
- Only declare skill-specific params (`--input`/`--output` auto-injected by framework based on kind)
- For `data`/`validator` kind: `--input` is always a **directory path**; declare file-name params (e.g. `--phe-file`) separately to specify which files within the directory to read
- Declare `input_schema=[IOField(...)]` for every required input file (data/validator kind)
- Declare `output_schema=[IOField(...)]` for every output file the skill produces
- Declare `requires=SkillRequires(bins=[...], r_packages=[...], ...)` for all dependencies
- Return a `KunResult` from `run()`
- Have `if __name__ == "__main__": run.__kunlib_meta__.run_cli()`

## Framework Auto-Injected Features

### Auto parameters

`--output` (output directory) is **always** automatically injected by the framework and is **always required**.

`--input` (input directory) injection depends on `kind`:
- **Injected and optional**: `kind="data"` — skill can fall back to `--demo` mode when `--input` is omitted
- **Injected and required**: `kind="validator"` — must validate input data, so `--input` is mandatory
- **Not injected**: `kind="generator"`, `kind="orchestrator"`, `kind="info"` — passing `--input` on CLI will cause an argparse error

`--input` is always a **directory path**, not a file path. Skills declare file-name params (e.g. `--phe-file`, `--geno-file`) to specify which files within `--input` to read. This design ensures traceability: when chaining skills, set the previous skill's output directory as the next skill's `--input`.

Do NOT declare `--input` or `--output` in `params=[...]` — the framework injects them automatically.

### Auto directory structure

When `run_cli()` is called, the framework creates directories under `--output`
**based on the skill's `kind`** before calling `run()`:

**All kinds** (always created):
- `output/logs/` — Run logs
- `output/result.json` — Auto-written by framework after `run()` returns

**`data` and `generator` kind** (additionally created):
- `output/work/` — Intermediate/temp files
- `output/tables/` — Final tabular results
- `output/figures/` — Final plots/images
- `output/reproducibility/` — Commands to reproduce

**`validator` kind** (additionally created):
- `output/tables/` — Validation reports

**`orchestrator` and `info` kind**: Only `logs/` and `result.json`.

These are injected into `args`:

| `args` attribute | `data`/`generator` | `validator` | `orchestrator`/`info` |
|------------------|-------------------|-------------|----------------------|
| `args.output_dir` | `Path` ✅ | `Path` ✅ | `Path` ✅ |
| `args.logs_dir` | `Path` ✅ | `Path` ✅ | `Path` ✅ |
| `args.work_dir` | `Path` ✅ | `None` ❌ | `None` ❌ |
| `args.tables_dir` | `Path` ✅ | `Path` ✅ | `None` ❌ |
| `args.figures_dir` | `Path` ✅ | `None` ❌ | `None` ❌ |
| `args.repro_dir` | `Path` ✅ | `None` ❌ | `None` ❌ |

⚠️ **`None` means the directory was NOT created.** Accessing `None / "file.csv"` will raise `TypeError`. Skills must check before use, or simply use the correct `kind` for their purpose.

### Auto result.json

`result.json` is written automatically by the framework after `run()` returns.
The skill does NOT need to call `result.save()`.

## Skill Kinds — 技能类型声明

每个技能通过 `@skill(kind=...)` 声明类型。`--output` **对所有类型都是必需的**，
框架保证每次执行都会产出 `result.json` + `logs/`，使 agent 可追踪任何技能的执行状态。

### 类型总览

| kind | `--input` | 创建的子目录 | 用途 |
|------|-----------|-------------|------|
| `data` (默认) | 注入，可选（输入目录） | work/ tables/ figures/ logs/ reproducibility/ | 读数据→算→出结果 |
| `generator` | 不注入 | work/ tables/ figures/ logs/ reproducibility/ | 凭空生成数据 |
| `orchestrator` | 不注入 | logs/ 仅此 | 编排多个技能的调用链 |
| `validator` | 注入，**必需**（输入目录） | logs/ tables/ | 校验输入数据合规性 |
| `info` | 不注入 | logs/ 仅此 | 查询环境/版本/配置信息 |

### 规则

1. **所有类型都必须 `return KunResult(...)`** — 这是框架的核心契约
2. **所有类型的 `result.json` 都由框架自动写** — 技能不需要手动调用 `result.save()`
3. **`kind` 未声明时默认为 `"data"`** — 向后兼容现有技能
4. **`args.work_dir` 等目录在未创建的 kind 下为 `None`** — 技能使用前应检查，或直接选择正确的 kind
5. **`--input` 永远是目录路径** — 技能内的具体文件名（如 `phe.csv`, `geno.csv`）通过技能自己的 Param 声明（如 `--phe-file`、`--geno-file`），技能代码中通过 `Path(args.input) / args.phe_file` 拼接。这样设计是为了输入可追溯，agent 在上下游串联技能时，只需指定前一个技能的输出目录作为下一个技能的 `--input`
6. **所有类型都应在 `logs/` 中记录关键执行信息** — 至少包含：执行了什么、开始/结束时间、成功/失败状态。对于 orchestrator 还应记录调用了哪些子技能

### Orchestrator 编排型约定

编排型技能本身不做数据计算，它的职责是按顺序调用其他技能并记录流程状态。

**目录约定（推荐，非框架强制）**：在 `output/` 下为每个子技能创建编号子目录：

    output/                          ← 编排技能的 --output
    ├── result.json                  ← 编排技能自己的结果（记录流程状态）
    ├── logs/
    │   └── pipeline.log             ← 记录调用了哪些技能、每步状态
    ├── 01_hiblup-ebv/               ← 子技能1的完整输出
    │   ├── result.json
    │   ├── work/ tables/ figures/ ...
    └── 02_lagm-mating/              ← 子技能2的完整输出
        ├── result.json
        ├── work/ tables/ figures/ ...

**logs/ 最低要求**：记录调用了哪个子技能、每步的开始/结束时间、每步的 status (success/failed)、每步的输出目录路径。

**result.json summary 约定**：

    {
      "skill": "breeding-pipeline",
      "kind": "orchestrator",
      "summary": {
        "steps": [
          {"step": 1, "skill": "hiblup-ebv", "status": "success", "output": "01_hiblup-ebv/"},
          {"step": 2, "skill": "lagm-mating", "status": "success", "output": "02_lagm-mating/"}
        ],
        "total_steps": 2,
        "completed": 2,
        "failed": 0
      }
    }

## Skill Script Templates — 按 kind 分类

Agent 注册技能时，根据 kind 选择对应的模板。**必须严格按照模板中的 `@skill()` 参数和 `run()` 函数结构来写。**

### Template: `kind="data"`（默认，数据处理型）

```python
#!/usr/bin/env python3
"""<Skill Name> — one-line description."""
from __future__ import annotations
import argparse
from pathlib import Path

from kunlib import skill, Param, KunResult, SkillRequires, IOField

SKILL_DIR = Path(__file__).resolve().parent

@skill(
    name="your-skill-name",          # must match folder name
    kind="data",
    version="0.1.0",
    description="What this skill does in one line",
    author="your-name",
    tags=["tag1", "tag2"],
    trigger_keywords=["keyword1", "keyword2"],
    emoji="🧬",
    requires=SkillRequires(bins=["python3"], r_packages=[], python_packages=[]),
    input_schema=[
        IOField(name="input.csv", format="csv", required_fields=["ID"], description="..."),
    ],
    output_schema=[
        IOField(name="result.csv", format="csv", dir="tables", description="..."),
    ],
    params=[
        # --input and --output are auto-injected, do NOT list here
        Param("demo", is_flag=True, help="Run with synthetic data"),
        Param("input-file", default="input.csv", help="Filename within --input directory"),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    # Available for data kind:
    #   args.input       → input directory path (str, optional)
    #   args.output_dir  → Path ✅    args.logs_dir    → Path ✅
    #   args.work_dir    → Path ✅    args.tables_dir  → Path ✅
    #   args.figures_dir → Path ✅    args.repro_dir   → Path ✅

    if args.demo:
        input_dir = args.work_dir  # generate demo data here
        mode = "demo"
    else:
        input_dir = Path(args.input)
        mode = "input"

    input_path = input_dir / args.input_file

    # ... your computation ...
    # ... write intermediate files to args.work_dir ...
    # ... write final tables to args.tables_dir ...

    return KunResult(
        skill_name="your-skill-name",
        skill_version="0.1.0",
        mode=mode,
        output_dir=args.output_dir,
        summary={"key_metric": 42},
        files={"tables": [args.tables_dir / "result.csv"]},
        report_path=args.output_dir / "report.md",
    )

if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
```

### Template: `kind="generator"`（生成型）

```python
#!/usr/bin/env python3
"""<Generator Name> — generate synthetic data."""
from __future__ import annotations
import argparse
from pathlib import Path

from kunlib import skill, Param, KunResult, SkillRequires, IOField

SKILL_DIR = Path(__file__).resolve().parent

@skill(
    name="your-generator-name",
    kind="generator",
    version="0.1.0",
    description="Generate synthetic data for ...",
    author="your-name",
    tags=["simulation", "demo-data"],
    trigger_keywords=["simulate", "generate"],
    emoji="🎲",
    requires=SkillRequires(bins=["python3"]),
    # generator has NO input_schema — it generates data from nothing
    output_schema=[
        IOField(name="synthetic_data.csv", format="csv", dir="tables", description="..."),
    ],
    params=[
        Param("n-samples", type=int, default=100, help="Number of samples to generate"),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    # Available for generator kind:
    #   NO args.input — passing --input on CLI will cause argparse error
    #   args.output_dir  → Path ✅    args.logs_dir    → Path ✅
    #   args.work_dir    → Path ✅    args.tables_dir  → Path ✅
    #   args.figures_dir → Path ✅    args.repro_dir   → Path ✅

    # ... generate synthetic data ...
    out_file = args.tables_dir / "synthetic_data.csv"
    # ... write to out_file ...

    return KunResult(
        skill_name="your-generator-name",
        skill_version="0.1.0",
        mode="generate",
        output_dir=args.output_dir,
        summary={"n_samples": args.n_samples},
        files={"tables": [out_file]},
    )

if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
```

### Template: `kind="orchestrator"`（编排型）

```python
#!/usr/bin/env python3
"""<Pipeline Name> — orchestrate multiple skills."""
from __future__ import annotations
import argparse
import datetime
import subprocess
import sys
from pathlib import Path

from kunlib import skill, Param, KunResult

SKILL_DIR = Path(__file__).resolve().parent

@skill(
    name="your-pipeline-name",
    kind="orchestrator",
    version="0.1.0",
    description="Run skill-A then skill-B pipeline",
    author="your-name",
    tags=["pipeline", "workflow"],
    trigger_keywords=["pipeline", "workflow"],
    chaining_partners=["skill-a", "skill-b"],
    emoji="🔗",
    # orchestrator typically has NO input_schema/output_schema
    # its "outputs" are the sub-skill output directories
    params=[
        Param("demo", is_flag=True, help="Run all steps with demo data"),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    # Available for orchestrator kind:
    #   NO args.input — not injected
    #   args.output_dir → Path ✅    args.logs_dir → Path ✅
    #   args.work_dir   → None ❌    args.tables_dir  → None ❌
    #   args.figures_dir→ None ❌    args.repro_dir   → None ❌

    log_lines = []
    steps = []

    def log(msg):
        line = f"[{datetime.datetime.now().isoformat()}] {msg}"
        log_lines.append(line)
        print(line)

    # Step 1: run skill-a
    log("Step 1/2: running skill-a")
    step1_out = args.output_dir / "01_skill-a"
    step1_out.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "kunlib.cli", "run", "skill-a",
           "--output", str(step1_out)]
    if args.demo:
        cmd.append("--demo")
    result1 = subprocess.run(cmd, capture_output=True, text=True)
    status1 = "success" if result1.returncode == 0 else "failed"
    log(f"Step 1/2: skill-a {status1}")
    steps.append({"step": 1, "skill": "skill-a", "status": status1,
                   "output": "01_skill-a/"})

    # Step 2: run skill-b, using step 1's output as input
    log("Step 2/2: running skill-b")
    step2_out = args.output_dir / "02_skill-b"
    step2_out.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "kunlib.cli", "run", "skill-b",
           "--input", str(step1_out / "tables"),
           "--output", str(step2_out)]
    result2 = subprocess.run(cmd, capture_output=True, text=True)
    status2 = "success" if result2.returncode == 0 else "failed"
    log(f"Step 2/2: skill-b {status2}")
    steps.append({"step": 2, "skill": "skill-b", "status": status2,
                   "output": "02_skill-b/"})

    # Write pipeline log
    (args.logs_dir / "pipeline.log").write_text("\n".join(log_lines), encoding="utf-8")

    completed = sum(1 for s in steps if s["status"] == "success")
    failed = sum(1 for s in steps if s["status"] == "failed")

    return KunResult(
        skill_name="your-pipeline-name",
        skill_version="0.1.0",
        mode="demo" if args.demo else "pipeline",
        output_dir=args.output_dir,
        summary={"steps": steps, "total_steps": len(steps),
                 "completed": completed, "failed": failed},
        files={"logs": [args.logs_dir / "pipeline.log"]},
    )

if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
```

### Template: `kind="validator"`（验证型）

```python
#!/usr/bin/env python3
"""<Validator Name> — validate input data."""
from __future__ import annotations
import argparse
import csv
from pathlib import Path

from kunlib import skill, Param, KunResult, SkillRequires, IOField

SKILL_DIR = Path(__file__).resolve().parent

@skill(
    name="your-validator-name",
    kind="validator",
    version="0.1.0",
    description="Validate input files for ...",
    author="your-name",
    tags=["validation", "quality-check"],
    trigger_keywords=["validate", "check", "校验"],
    emoji="✅",
    requires=SkillRequires(bins=["python3"]),
    input_schema=[
        IOField(name="data.csv", format="csv", required_fields=["ID"], description="..."),
    ],
    output_schema=[
        IOField(name="validation_report.csv", format="csv", dir="tables", description="..."),
    ],
    params=[
        # --input is auto-injected and REQUIRED for validator kind
        Param("strict", is_flag=True, help="Fail on warnings"),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    # Available for validator kind:
    #   args.input      → input directory path (str, REQUIRED)
    #   args.output_dir → Path ✅    args.logs_dir   → Path ✅
    #   args.tables_dir → Path ✅
    #   args.work_dir   → None ❌    args.figures_dir→ None ❌
    #   args.repro_dir  → None ❌

    input_dir = Path(args.input)
    checks = []

    # ... run validation checks ...
    # checks.append({"file": "data.csv", "check": "exists", "pass": True})

    all_passed = all(c["pass"] for c in checks)

    # Write validation report
    report_path = args.tables_dir / "validation_report.csv"
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "check", "pass", "message"])
        writer.writeheader()
        writer.writerows(checks)

    return KunResult(
        skill_name="your-validator-name",
        skill_version="0.1.0",
        mode="input",
        output_dir=args.output_dir,
        summary={"valid": all_passed, "checks_passed": sum(1 for c in checks if c["pass"]),
                 "checks_failed": sum(1 for c in checks if not c["pass"])},
        files={"tables": [report_path]},
    )

if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
```

### Template: `kind="info"`（信息型）

```python
#!/usr/bin/env python3
"""<Info Name> — query environment or reference information."""
from __future__ import annotations
import argparse
import shutil
from pathlib import Path

from kunlib import skill, Param, KunResult

SKILL_DIR = Path(__file__).resolve().parent

@skill(
    name="your-info-name",
    kind="info",
    version="0.1.0",
    description="Check environment or provide reference information",
    author="your-name",
    tags=["info", "environment"],
    trigger_keywords=["check env", "环境检查"],
    emoji="ℹ️",
    # info kind typically has NO input_schema/output_schema
    params=[],
)
def run(args: argparse.Namespace) -> KunResult:
    # Available for info kind:
    #   NO args.input — not injected
    #   args.output_dir → Path ✅    args.logs_dir → Path ✅
    #   args.work_dir   → None ❌    args.tables_dir  → None ❌
    #   args.figures_dir→ None ❌    args.repro_dir   → None ❌

    # ... gather information ...
    info = {}
    for bin_name in ["python3", "Rscript", "plink"]:
        path = shutil.which(bin_name)
        info[bin_name] = str(path) if path else "not found"

    # Write info log
    log_lines = [f"{k}: {v}" for k, v in info.items()]
    (args.logs_dir / "env_check.log").write_text("\n".join(log_lines), encoding="utf-8")

    return KunResult(
        skill_name="your-info-name",
        skill_version="0.1.0",
        mode="info",
        output_dir=args.output_dir,
        summary=info,
        files={"logs": [args.logs_dir / "env_check.log"]},
    )

if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
```

---

## 🚀 Quick Start for External Developers

External developers can add a skill with minimal effort using the prompt template:

1. Fork this repo
2. Put your script in `skills/<skill-name>/`
3. Fill in the 7-item prompt from [`templates/ADD-SKILL-PROMPT.md`](templates/ADD-SKILL-PROMPT.md)
4. @copilot with the prompt — agent handles all the conversion

For the full manual conversion process, see the section below.

---

## 🔧 Converting a User Script into a KunLib Skill

When a user gives you any functional script (Python, R wrapper, shell pipeline,
etc.) that has inputs, outputs, and parameters, follow this procedure to convert
it into a proper KunLib skill.

### Step 1: Analyze the Original Script

Identify from the user's script:
- **Skill kind**: Is this a data-processing, generator, orchestrator, validator, or info skill? Determine the `kind` first — it affects which template to use, which directories are available, and whether `--input` is injected.
- **Inputs**: What files/directories does it read? What formats?
- **Outputs**: What files does it produce? Where?
- **Parameters**: What knobs can the user tune? Types, defaults?
- **Dependencies**: External binaries (Rscript, plink, samtools)? Python packages?
- **Core logic**: The actual computation (keep this unchanged as much as possible)

#### Agent 必须从用户处确认的信息（不可仅靠推理）

| 信息 | 为什么不能推理 |
|------|---------------|
| 依赖安装方式 | `subprocess.run("hiblup")` 只告诉你命令名，不告诉你怎么装 |
| 参数默认值的领域合理性 | `trait_pos=4` 是否合理，只有用户知道 |
| 输入文件字段含义 | `geno.csv` 是 0/1/2 编码还是 A/B 编码，脚本里不一定写明 |
| 许可证限制 | hiblup 需要手动下载，这是法律/商业信息不是技术信息 |

如果用户提供的信息不足，agent 应主动追问上述关键项，而不是猜测。

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

Choose the template from §Skill Script Templates that matches the determined `kind`, then:

1. Move the user's core logic into a plain function
2. Fill in the `@skill(...)` decorator with all required fields: `name`, `kind`, `version`, `description`, `author`, `tags`, `trigger_keywords`, `requires`, `input_schema` (if applicable), `output_schema`, `params`
3. Wire the `run()` function following the chosen template's structure
4. Ensure `--input` is treated as a directory (for data/validator kind), with individual filenames declared as Param

See §Skill Script Templates for complete code templates for each kind.

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
| No `kind` declaration | Add `kind="data"` (or the appropriate kind) to `@skill()` — agent must determine the correct kind based on script behavior |
| No `input_schema` / `output_schema` | Add `input_schema=[IOField(...)]` and `output_schema=[IOField(...)]` — document every input and output file |
| No `requires=SkillRequires(...)` | Add `requires=SkillRequires(bins=[...], r_packages=[...], ...)` — list all dependencies |
| Script is a pure workflow description | Use `kind="orchestrator"` — no computation, just call other skills in sequence |
| Script only checks/validates data | Use `kind="validator"` — `--input` will be required, output is a validation report |

### Step 5: Write SKILL.md

Copy `templates/SKILL-TEMPLATE.md` and fill in every section. Key points:
- YAML frontmatter `name:` must match the folder name and `@skill(name=...)`
- YAML frontmatter must include `kind:` field matching the `@skill(kind=...)` value
- YAML frontmatter must include `input_schema:` and `output_schema:` sections
- Include real CLI examples that work
- Document every parameter in the Parameters table
- Show the exact output directory structure
- **Fill in the `## Dependencies` section** (see below)

#### Dependency Documentation Convention

The YAML frontmatter `requires` block must classify dependencies:

```yaml
requires:
  bins: [python3, Rscript, plink]   # system binaries on PATH
  r_packages: [data.table]           # R packages
  python_packages: [pandas, numpy]   # Python packages
  bioc_packages: [GenomicRanges]     # Bioconductor packages
```

The `## Dependencies` section in SKILL.md must list **every** dependency with
its install method so users know exactly how to set up the environment. Use one
of these categories for Install Method:

| Category | Example |
|----------|---------|
| conda / conda-forge / Bioconda | `conda install -c bioconda samtools` |
| pip / PyPI | `pip install pandas` |
| CRAN | `install.packages("data.table")` |
| Bioconductor | `BiocManager::install("DESeq2")` |
| GitHub (R) | `remotes::install_github("author/pkg")` — include full URL |
| GitHub (CLI/C++) | `git clone https://github.com/... && make install` |
| URL direct download | `wget https://example.com/tool-v1.0.tar.gz` |
| System package manager | `apt install libhts-dev` / `brew install htslib` |
| Manual download (licensed) | Provide official URL and note license restrictions |

⚠️ If a dependency requires manual download due to licensing or commercial
restrictions (e.g., ASReml, FImpute, commercial chip annotation tools),
clearly state this in the Notes column with the official download URL.

### Step 6: Write Tests

Tests should verify the skill runs correctly based on its `kind`. Use the
appropriate assertions for each kind's available directories.

**For `data` kind** (with `--demo`):

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
    # data kind creates all dirs
    assert (tmp_path / "work").is_dir()
    assert (tmp_path / "tables").is_dir()
    assert (tmp_path / "figures").is_dir()
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "reproducibility").is_dir()
```

**For `generator` kind**:

```python
def test_generate(tmp_path):
    script = Path(__file__).resolve().parent.parent / "<skill_name>.py"
    result = subprocess.run(
        [sys.executable, str(script), "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "result.json").exists()
    # generator kind creates same dirs as data
    assert (tmp_path / "tables").is_dir()
```

**For `validator` kind** (requires `--input`):

```python
def test_validate(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    # ... create minimal test input files in input_dir ...
    output_dir = tmp_path / "output"
    script = Path(__file__).resolve().parent.parent / "<skill_name>.py"
    result = subprocess.run(
        [sys.executable, str(script), "--input", str(input_dir), "--output", str(output_dir)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert (output_dir / "result.json").exists()
    # validator kind creates logs/ and tables/ only
    assert (output_dir / "tables").is_dir()
    assert (output_dir / "logs").is_dir()
```

**For `orchestrator` kind**:

```python
def test_pipeline_demo(tmp_path):
    script = Path(__file__).resolve().parent.parent / "<skill_name>.py"
    result = subprocess.run(
        [sys.executable, str(script), "--demo", "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "result.json").exists()
    # orchestrator kind only creates logs/
    assert (tmp_path / "logs").is_dir()
```

**For `info` kind**:

```python
def test_info(tmp_path):
    script = Path(__file__).resolve().parent.parent / "<skill_name>.py"
    result = subprocess.run(
        [sys.executable, str(script), "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "result.json").exists()
    # info kind only creates logs/
    assert (tmp_path / "logs").is_dir()
```

### Step 7: Verify

```bash
# Does it run?
python skills/<name>/<script>.py --demo --output /tmp/test

# Does kunlib see it?
kunlib list

# Does kunlib run it?
kunlib run <name> --demo --output /tmp/test

# Check output structure matches kind
ls /tmp/test/
# data/generator → work/ tables/ figures/ logs/ reproducibility/ result.json
# validator      → logs/ tables/ result.json
# orchestrator   → logs/ result.json 01_xxx/ 02_xxx/
# info           → logs/ result.json

# Do tests pass?
pytest tests/ -v
```

## Safety Boundaries

1. **Local-first**: No data uploads without explicit consent
2. **Disclaimer**: Every result.json includes the KunLib disclaimer
3. **Reproducibility**: Skills should log commands to `args.repro_dir`
4. **No hallucinated science**: Parameters must trace to cited methods
