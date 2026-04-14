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

## 🚀 Quick Start for External Developers

External developers can add a skill with minimal effort using the prompt template:

1. Fork this repo
2. Put your script in `skills/<skill-name>/`
3. Fill in the 3-line prompt from [`templates/ADD-SKILL-PROMPT.md`](templates/ADD-SKILL-PROMPT.md)
4. @copilot with the prompt — agent handles all the conversion

For the full manual conversion process, see the section below.

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
- **Fill in the `## Dependencies` section** (see below)

#### Dependency Documentation Convention

The YAML frontmatter `requires` block must classify dependencies:

```yaml
requires:
  bins: [python3, Rscript, plink]   # system binaries on PATH
  r_packages: [data.table]           # R packages
  python_packages: [pandas, numpy]   # Python packages
```

The `## Dependencies` section in SKILL.md must list **every** dependency with
its install method so users know exactly how to set up the environment. Use one
of these categories for Install Method:

| Category | Example |
|----------|---------|
| conda / pip | `conda install -c conda-forge plink` or `pip install pandas` |
| CRAN | `install.packages("data.table")` |
| Bioconductor | `BiocManager::install("GenomicRanges")` |
| GitHub | `remotes::install_github("user/repo")` — include full URL |
| Manual download | Provide download URL and note any license restrictions |

⚠️ If a dependency requires manual download due to licensing or commercial
restrictions (e.g., certain BLUP software, commercial chip annotation tools),
clearly state this in the Notes column with the official download URL.

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
