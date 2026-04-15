#!/usr/bin/env python3
"""Pedigree Analysis — Aquaculture pedigree analysis via visPedigree."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from kunlib import skill, Param, KunResult, SkillRequires, IOField
from kunlib.common.report import generate_report_header, generate_report_footer
from kunlib.common.checksums import sha256_file

SKILL_DIR = Path(__file__).resolve().parent
RSCRIPT_DEMO = SKILL_DIR / "generate_demo.r"
RSCRIPT_MAIN = SKILL_DIR / "run_pedigree.r"

VALID_TASKS = {"stats", "inbreeding", "interval", "diversity", "ancestry", "matrix", "visual"}
DEFAULT_TASKS = "stats,inbreeding,visual"


# --------------------------------------------------------------------------- #
# Helper: run R script
# --------------------------------------------------------------------------- #
def _run_r(
    script: Path,
    r_args: list[str],
    cwd: Path,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    run_env = None
    if env:
        run_env = {**os.environ, **env}
    cmd = ["Rscript", "--vanilla", str(script)] + r_args
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, check=True, env=run_env
    )


# --------------------------------------------------------------------------- #
# Helper: check required bins
# --------------------------------------------------------------------------- #
def _check_bins() -> dict[str, str | None]:
    return {"Rscript": shutil.which("Rscript")}


# --------------------------------------------------------------------------- #
# Helper: validate pedigree CSV (minimal check)
# --------------------------------------------------------------------------- #
def _validate_pedigree(filepath: Path) -> dict:
    """Check file exists and has at least 3 columns. Return basic stats."""
    with open(filepath, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None or len(header) < 3:
            raise ValueError(
                f"Pedigree file must have ≥ 3 columns (Ind, Sire, Dam), "
                f"got {len(header) if header else 0}"
            )
        rows = list(reader)
    return {
        "n_rows": len(rows),
        "n_cols": len(header),
        "columns": header,
    }


# --------------------------------------------------------------------------- #
# Helper: parse tasks argument
# --------------------------------------------------------------------------- #
def _resolve_tasks(tasks_str: str) -> set[str]:
    raw = {t.strip().lower() for t in tasks_str.split(",") if t.strip()}
    if "all" in raw:
        return set(VALID_TASKS)
    invalid = raw - VALID_TASKS
    if invalid:
        raise ValueError(
            f"Unknown task(s): {sorted(invalid)}. Valid: {sorted(VALID_TASKS)}"
        )
    return raw


# --------------------------------------------------------------------------- #
# Helper: extract JSON summary from R stdout
# --------------------------------------------------------------------------- #
def _parse_r_summary(stdout: str) -> dict:
    m = re.search(
        r"===KUNLIB_JSON_BEGIN===\s*(.*?)\s*===KUNLIB_JSON_END===",
        stdout,
        re.DOTALL,
    )
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return {}
    return {}


# --------------------------------------------------------------------------- #
# Helper: collect output files
# --------------------------------------------------------------------------- #
def _collect_files(tables_dir: Path, figures_dir: Path) -> dict[str, list[Path]]:
    tables = sorted(tables_dir.glob("*.csv"))
    figures = sorted(figures_dir.glob("*"))
    figures = [f for f in figures if f.suffix.lower() in {".png", ".pdf"}]
    return {"tables": tables, "figures": figures}


# --------------------------------------------------------------------------- #
# Helper: write report.md
# --------------------------------------------------------------------------- #
def _write_report(
    output_dir: Path,
    mode: str,
    r_summary: dict,
    pedigree_info: dict,
) -> Path:
    report_path = output_dir / "report.md"
    header = generate_report_header(
        title="Pedigree Analysis Report",
        skill_name="pedigree-analysis",
        skill_version="0.1.0",
        extra={"Mode": mode},
    )

    lines = [
        "## Pedigree Overview\n",
        f"- **Records in input**: {pedigree_info.get('n_rows', 'N/A')}",
        f"- **Columns**: {', '.join(pedigree_info.get('columns', []))}",
        "",
    ]

    if r_summary:
        lines += [
            "## Analysis Summary\n",
            f"- **Individuals (after tidying)**: {r_summary.get('n_individuals', 'N/A')}",
            f"- **Founders**: {r_summary.get('n_founders', 'N/A')}",
            f"- **Generations**: {r_summary.get('n_generations', 'N/A')}",
            "",
        ]

        executed = r_summary.get("tasks_executed", [])
        skipped = r_summary.get("tasks_skipped", [])
        if executed:
            lines.append(f"**Modules completed**: {', '.join(executed)}\n")
        if skipped:
            lines.append("**Modules skipped**:\n")
            for s in skipped:
                lines.append(f"  - {s}")
        lines.append("")

        if "inbreeding" in r_summary:
            ib = r_summary["inbreeding"]
            lines += [
                "### Inbreeding\n",
                f"- **Mean F**: {ib.get('mean_f', 'N/A')}",
                f"- **Max F**: {ib.get('max_f', 'N/A')}",
                f"- **Inbred individuals (F > 0)**: {ib.get('n_inbred', 'N/A')}",
                "",
            ]

        if "diversity" in r_summary:
            div = r_summary["diversity"]
            lines += [
                "### Genetic Diversity\n",
                f"- **Ne (Coancestry)**: {div.get('NeCoancestry', 'N/A')}",
                f"- **Ne (Inbreeding)**: {div.get('NeInbreeding', 'N/A')}",
                f"- **Effective founders (fe)**: {div.get('fe', 'N/A')}",
                f"- **Effective ancestors (fa)**: {div.get('fa', 'N/A')}",
                f"- **Gene Diversity**: {div.get('GeneDiv', 'N/A')}",
                "",
            ]

    footer = generate_report_footer()
    report_path.write_text(header + "\n".join(lines) + footer, encoding="utf-8")
    return report_path


# --------------------------------------------------------------------------- #
# @skill
# --------------------------------------------------------------------------- #
@skill(
    name="pedigree-analysis",
    version="0.1.0",
    description=(
        "Aquaculture pedigree analysis: tidying, statistics, inbreeding, "
        "diversity, generation intervals, ancestry tracing, relationship "
        "matrices, and pedigree visualization via visPedigree."
    ),
    author="luansheng",
    tags=[
        "pedigree", "aquaculture", "animal-breeding", "inbreeding",
        "genetic-diversity", "relationship-matrix", "visualization",
        "visPedigree", "effective-population-size",
    ],
    trigger_keywords=[
        "pedigree analysis", "系谱分析", "近交系数", "遗传多样性",
        "有效群体大小", "系谱图", "关系矩阵", "世代间隔",
        "inbreeding coefficient", "kinship", "effective population size",
        "pedigree visualization", "ancestor contribution", "blood line",
    ],
    chaining_partners=["lagm-mating", "hiblup-ebv"],
    input_formats=["csv (Ind/Sire/Dam + optional Year/Sex/Line columns)"],
    requires=SkillRequires(
        bins=["python3", "Rscript"],
        r_packages=["visPedigree", "data.table", "jsonlite"],
    ),
    input_schema=[
        IOField(
            name="pedigree.csv",
            format="csv",
            required_fields=["Ind", "Sire", "Dam"],
            description=(
                "系谱文件（默认名 pedigree.csv，可通过 --pedfile 指定其他文件名）："
                "前3列必须按顺序为个体ID、父本ID、母本ID（列名任意）。"
                "缺失亲本用 NA/0/*。可附加 Year、Sex、Line 等列。"
                "文件须位于 --input 指定的输入目录中。"
            ),
        ),
    ],
    output_schema=[
        IOField(name="tidyped.csv", dir="tables", description="标准化系谱（始终输出）"),
        IOField(name="pedstats_summary.csv", dir="tables", description="群体结构统计"),
        IOField(name="inbreeding.csv", dir="tables", description="个体近交系数"),
        IOField(name="diversity_summary.csv", dir="tables", description="遗传多样性摘要"),
        IOField(name="pedigree.pdf", dir="figures", description="系谱图"),
        IOField(name="matrix_heatmap.png", dir="figures", description="关系矩阵热图"),
    ],
    emoji="🐟",
    params=[
        Param("demo", is_flag=True, help="使用合成水产系谱运行（约4560个个体，5代）"),
        Param("pedfile", default="pedigree.csv", help="输入目录中的系谱 CSV 文件名（默认: pedigree.csv）"),
        Param(
            "tasks",
            default=DEFAULT_TASKS,
            help=(
                "逗号分隔的分析模块：stats, inbreeding, interval, diversity, "
                "ancestry, matrix, visual, all。默认: stats,inbreeding,visual"
            ),
        ),
        Param("cand", default=None, help="候选个体 ID（逗号分隔），为空则分析全部"),
        Param("trace", default="up", help="候选追溯方向：up / down / all"),
        Param("tracegen", type=int, default=None, help="追溯代数，为空则全追溯"),
        Param("timevar", default=None, help="时间列名（如 Year），interval 模块必需"),
        Param("foundervar", default=None, help="血统标记列名（如 Line），ancestry 模块必需"),
        Param("reference", default=None, help="diversity 模块参考个体 ID（逗号分隔），默认取最新世代"),
        Param("top", type=int, default=20, help="diversity 模块显示 Top N 奠基者/祖先"),
        Param("mat-method", default="A", help="关系矩阵类型：A / D / AA / Ainv / Dinv / AAinv"),
        Param("mat-compact", is_flag=True, help="矩阵计算启用全同胞压缩（加速大系谱）"),
        Param("export-matrix", is_flag=True, help="导出完整关系矩阵 CSV（默认仅输出摘要+热图）"),
        Param("compact", is_flag=True, help="visped 全同胞压缩显示"),
        Param("highlight", default=None, help="visped 高亮个体 ID"),
        Param("vis-trace", default="up", help="visped 追溯方向（up / down / all）"),
        Param("showf", is_flag=True, help="visped 在节点显示近交系数"),
        Param("fig-format", default="pdf", help="系谱图格式：pdf（推荐大系谱）或 png"),
        Param("fig-width", type=int, default=12, help="图形宽度（英寸，仅 png 有效）"),
        Param("fig-height", type=int, default=10, help="图形高度（英寸，仅 png 有效）"),
        Param(
            "inbreed-breaks",
            default="0.0625,0.125,0.25",
            help="近交分级阈值（逗号分隔，如 0.0625,0.125,0.25）",
        ),
        Param("threads", type=int, default=0, help="矩阵计算线程数（0=自动）"),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    """Pedigree analysis pipeline. Calls generate_demo.r or run_pedigree.r via Rscript."""

    output_dir = args.output_dir
    work_dir   = args.work_dir
    tables_dir = args.tables_dir
    figures_dir = args.figures_dir
    repro_dir  = args.repro_dir

    mode = "demo" if args.demo else "input"

    # ---- Check Rscript availability ----
    bins = _check_bins()
    if bins["Rscript"] is None:
        raise RuntimeError("Rscript not found on PATH. Install R ≥ 4.2.")

    # ---- Resolve tasks ----
    tasks_set = _resolve_tasks(args.tasks)
    tasks_str = ",".join(sorted(tasks_set))

    # ---- Resolve input file ----
    if args.demo:
        _run_r(RSCRIPT_DEMO, ["--output", str(work_dir)], cwd=SKILL_DIR)
        input_path = work_dir / "demo_ped.csv"
    else:
        if not args.input:
            raise ValueError("--input is required when not using --demo")
        input_dir = Path(args.input)
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        if not input_dir.is_dir():
            raise NotADirectoryError(f"--input must be a directory, got: {input_dir}")
        input_path = input_dir / args.pedfile
        if not input_path.exists():
            raise FileNotFoundError(
                f"Pedigree file not found: {input_path} "
                f"(use --pedfile to specify a different filename)"
            )
        if not input_path.is_file():
            raise ValueError(f"Expected a file at: {input_path}")

    # ---- Validate pedigree ----
    pedigree_info = _validate_pedigree(input_path)

    # ---- Build R arguments ----
    r_args: list[str] = [
        "--input-file",  str(input_path),
        "--tables-dir",  str(tables_dir),
        "--figures-dir", str(figures_dir),
        "--work-dir",    str(work_dir),
        "--tasks",       tasks_str,
        "--trace",       args.trace,
        "--mat-method",  args.mat_method,
        "--fig-format",  args.fig_format,
        "--fig-width",   str(args.fig_width),
        "--fig-height",  str(args.fig_height),
        "--inbreed-breaks", args.inbreed_breaks,
        "--top",         str(args.top),
        "--threads",     str(args.threads),
        "--vis-trace",   args.vis_trace,
    ]

    # Optional string args
    for flag, value in [
        ("--cand",       args.cand),
        ("--timevar",    args.timevar),
        ("--foundervar", args.foundervar),
        ("--reference",  args.reference),
        ("--highlight",  args.highlight),
    ]:
        if value is not None:
            r_args += [flag, str(value)]

    if args.tracegen is not None:
        r_args += ["--tracegen", str(args.tracegen)]

    # Boolean flags
    for flag, enabled in [
        ("--mat-compact",    args.mat_compact),
        ("--export-matrix",  args.export_matrix),
        ("--compact",        args.compact),
        ("--showf",          args.showf),
    ]:
        if enabled:
            r_args.append(flag)

    # ---- Run main R pipeline ----
    result = _run_r(RSCRIPT_MAIN, r_args, cwd=work_dir)
    r_summary = _parse_r_summary(result.stdout)

    # ---- Collect output files ----
    files = _collect_files(tables_dir, figures_dir)

    # ---- Write report ----
    report_path = _write_report(output_dir, mode, r_summary, pedigree_info)

    # ---- Write reproducibility script ----
    repro_lines = ["#!/bin/bash", "# Reproduce this pedigree analysis", ""]
    if mode == "demo":
        repro_lines.append(
            f"Rscript --vanilla {RSCRIPT_DEMO} --output {work_dir}"
        )
    repro_lines.append(f"Rscript --vanilla {RSCRIPT_MAIN} \\")
    i = 0
    while i < len(r_args):
        arg = r_args[i]
        bool_flags = {"--mat-compact", "--export-matrix", "--compact", "--showf"}
        if arg in bool_flags:
            repro_lines.append(f"  {arg} \\")
            i += 1
        elif i + 1 < len(r_args):
            repro_lines.append(f"  {arg} {r_args[i + 1]} \\")
            i += 2
        else:
            repro_lines.append(f"  {arg} \\")
            i += 1
    if repro_lines[-1].endswith(" \\"):
        repro_lines[-1] = repro_lines[-1][:-2]
    (repro_dir / "commands.sh").write_text("\n".join(repro_lines) + "\n", encoding="utf-8")

    # ---- Checksums ----
    checksums = {f.name: sha256_file(f) for flist in files.values() for f in flist}

    # ---- Build summary ----
    summary: dict = {
        "n_input_rows": pedigree_info["n_rows"],
        "tasks_requested": sorted(tasks_set),
    }
    if r_summary:
        summary["n_individuals"]  = r_summary.get("n_individuals")
        summary["n_founders"]     = r_summary.get("n_founders")
        summary["n_generations"]  = r_summary.get("n_generations")
        summary["tasks_executed"] = r_summary.get("tasks_executed", [])
        summary["tasks_skipped"]  = r_summary.get("tasks_skipped", [])
        if "inbreeding" in r_summary:
            summary["inbreeding"] = r_summary["inbreeding"]
        if "diversity" in r_summary:
            summary["diversity"] = r_summary["diversity"]

    return KunResult(
        skill_name="pedigree-analysis",
        skill_version="0.1.0",
        mode=mode,
        output_dir=output_dir,
        summary=summary,
        data={"checksums": checksums, "r_stdout": result.stdout[-2000:]},
        files=files,
        report_path=report_path,
    )


if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
