"""LAGM Mating — Optimal mating plan via lagm::lagm_plan()."""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
from pathlib import Path

from kunlib import skill, Param, KunResult, SkillRequires, IOField
from kunlib.common.report import generate_report_header, generate_report_footer
from kunlib.common.checksums import sha256_file

SKILL_DIR = Path(__file__).resolve().parent
RSCRIPT_LAGM = SKILL_DIR / "run_lagm.r"
RSCRIPT_DEMO = SKILL_DIR / "generate_demo.r"

REQUIRED_FILES = ["id_index_sex.csv", "geno.csv"]


def _check_bins() -> dict[str, str | None]:
    """Check availability of required external binaries."""
    bins: dict[str, str | None] = {}
    for name in ("Rscript",):
        bins[name] = shutil.which(name)
    return bins


def _run_r(
    script: Path, args: list[str], cwd: Path, env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run an R script via Rscript."""
    run_env = None
    if env:
        run_env = {**os.environ, **env}
    cmd = ["Rscript", "--vanilla", str(script)] + args
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=True, env=run_env)


def _validate_input(input_dir: Path, filenames: list[str] | None = None) -> list[str]:
    """Return list of missing required files."""
    names = filenames if filenames is not None else REQUIRED_FILES
    return [f for f in names if not (input_dir / f).exists()]


def _validate_id_index_sex(filepath: Path) -> dict:
    """Validate id_index_sex.csv structure and return summary stats."""
    with open(filepath, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None or len(header) < 3:
            raise ValueError(
                f"id_index_sex file must have at least 3 columns (ID, selindex, sex), "
                f"got {len(header) if header else 0} columns"
            )
        rows = list(reader)

    n_total = len(rows)
    n_male = sum(1 for r in rows if len(r) >= 3 and r[2].strip().upper() == "M")
    n_female = sum(1 for r in rows if len(r) >= 3 and r[2].strip().upper() == "F")
    return {"n_candidates": n_total, "n_males": n_male, "n_females": n_female}


def _generate_demo(work_dir: Path, env: dict | None = None) -> Path:
    """Generate demo data into work_dir using generate_demo.r."""
    _run_r(RSCRIPT_DEMO, ["--output", str(work_dir)], cwd=SKILL_DIR, env=env)
    return work_dir


def _read_mating_plan_summary(tables_dir: Path) -> dict:
    """Read mating_plan.csv and produce summary statistics."""
    fpath = tables_dir / "mating_plan.csv"
    summary: dict = {}
    if fpath.exists():
        with open(fpath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        summary["n_crosses"] = len(rows)
    return summary


def _write_report(
    output_dir: Path, mode: str, summary: dict, input_summary: dict,
) -> Path:
    """Write KunLib-style report.md."""
    report_path = output_dir / "report.md"
    header = generate_report_header(
        title="LAGM Mating Plan Report",
        skill_name="lagm-mating",
        skill_version="0.1.0",
        extra={"Mode": mode},
    )
    body_lines = [
        "## Input Summary\n",
        f"- **Total candidates**: {input_summary.get('n_candidates', 'N/A')}",
        f"- **Males**: {input_summary.get('n_males', 'N/A')}",
        f"- **Females**: {input_summary.get('n_females', 'N/A')}",
        "",
        "## Mating Plan Summary\n",
    ]
    for k, v in summary.items():
        body_lines.append(f"- **{k}**: {v}")
    body_lines.append("")
    footer = generate_report_footer()
    report_path.write_text(
        header + "\n".join(body_lines) + footer, encoding="utf-8",
    )
    return report_path


@skill(
    name="lagm-mating",
    kind="data",
    version="0.1.0",
    description="Generate optimal mating plans balancing genetic gain and diversity via lagm::lagm_plan()",
    author="kzy599",
    tags=[
        "animal-breeding", "mating-plan", "optimal-contribution",
        "genetic-diversity", "lagm", "quantitative-genetics",
    ],
    trigger_keywords=[
        "mating plan", "lagm", "optimal mating",
        "genetic diversity", "配种方案", "最优交配",
        "遗传多样性", "配种计划",
    ],
    chaining_partners=["hiblup-ebv", "kinship-matrix"],
    input_formats=["csv-dir (id_index_sex.csv + geno.csv + optional ped.csv)"],
    requires=SkillRequires(
        bins=["python3", "Rscript"],
        r_packages=["data.table", "remotes"],
    ),
    input_schema=[
        IOField(
            name="id_index_sex.csv", format="csv",
            required_fields=["ID", "selindex", "sex"],
            description="候选个体信息：第1列ID，第2列选择指数，第3列性别(M/F)",
        ),
        IOField(
            name="geno.csv", format="csv",
            required_fields=["ID"],
            description="基因型矩阵：第1列ID，其余列为SNP标记(0/1/2编码)",
        ),
        IOField(
            name="ped.csv", format="csv",
            required_fields=["ID", "sire", "dam"],
            description="系谱文件（可选，use_ped=TRUE且diversity_mode!='genomic'时使用）",
        ),
    ],
    output_schema=[
        IOField(name="mating_plan.csv", dir="tables", description="配种方案主结果"),
    ],
    emoji="🐄",
    params=[
        Param("demo", is_flag=True, help="使用 generate_demo.r 生成合成数据并运行"),
        Param("id-index-file", default="id_index_sex.csv",
              help="输入目录中的候选个体信息文件名"),
        Param("geno-file", default="geno.csv",
              help="输入目录中的基因型文件名"),
        Param("ped-file", default="ped.csv",
              help="输入目录中的系谱文件名（可选）"),
        Param("t", type=int, default=3,
              help="前瞻代数 (lookahead generations)"),
        Param("n-crosses", type=int, default=30,
              help="目标配对数"),
        Param("male-contribution-min", type=int, default=2,
              help="每个公本最少贡献次数"),
        Param("male-contribution-max", type=int, default=2,
              help="每个公本最多贡献次数"),
        Param("female-contribution-min", type=int, default=1,
              help="每个母本最少贡献次数"),
        Param("female-contribution-max", type=int, default=1,
              help="每个母本最多贡献次数"),
        Param("diversity-mode", default="genomic",
              help="多样性模式: 'genomic' 或 'relationship'"),
        Param("use-ped", is_flag=True,
              help="使用系谱关系矩阵（需配合 diversity_mode != 'genomic'）"),
        Param("n-iter", type=int, default=30000,
              help="优化迭代次数"),
        Param("n-pop", type=int, default=100,
              help="种群/候选方案规模"),
        Param("n-threads", type=int, default=8,
              help="并行线程数"),
        Param("swap-prob", type=float, default=0.2,
              help="交换概率 (启发式搜索参数)"),
        Param("init-prob", type=float, default=0.8,
              help="初始方案中启发式比例 (80%启发式 + 20%随机)"),
        Param("cooling-rate", type=float, default=0.998,
              help="退火降温速率"),
        Param("stop-window", type=int, default=2000,
              help="早停窗口 (连续无改善次数)"),
        Param("stop-eps", type=float, default=1e-8,
              help="早停精度阈值"),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    """Main pipeline for LAGM mating plan optimization.

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

    # --- resolve input directory ---
    if args.demo:
        input_dir = _generate_demo(work_dir)
    else:
        if not args.input:
            raise SystemExit("Error: --input is required when not using --demo")
        input_dir = Path(args.input)

    # --- resolve individual input files ---
    id_index_path = input_dir / args.id_index_file
    geno_path = input_dir / args.geno_file
    ped_path = input_dir / args.ped_file

    # --- validate required inputs ---
    required = [args.id_index_file, args.geno_file]
    missing = _validate_input(input_dir, required)
    if missing:
        raise SystemExit(
            f"Error: missing required files in {input_dir}: {', '.join(missing)}"
        )

    # --- validate id_index_sex structure ---
    input_summary = _validate_id_index_sex(id_index_path)

    # --- build R arguments ---
    r_args = [
        "--id-index-file", str(id_index_path),
        "--geno-file", str(geno_path),
        "--workdir", str(work_dir),
        "--tables-dir", str(tables_dir),
        "--t", str(args.t),
        "--n-crosses", str(args.n_crosses),
        "--male-contribution-min", str(args.male_contribution_min),
        "--male-contribution-max", str(args.male_contribution_max),
        "--female-contribution-min", str(args.female_contribution_min),
        "--female-contribution-max", str(args.female_contribution_max),
        "--diversity-mode", args.diversity_mode,
        "--n-iter", str(args.n_iter),
        "--n-pop", str(args.n_pop),
        "--n-threads", str(args.n_threads),
        "--swap-prob", str(args.swap_prob),
        "--init-prob", str(args.init_prob),
        "--cooling-rate", str(args.cooling_rate),
        "--stop-window", str(args.stop_window),
        "--stop-eps", str(args.stop_eps),
    ]

    if args.use_ped:
        r_args.append("--use-ped")
        r_args.extend(["--ped-file", str(ped_path)])

    # --- run lagm pipeline via R ---
    _run_r(RSCRIPT_LAGM, r_args, cwd=work_dir)

    # --- collect summary ---
    summary = _read_mating_plan_summary(tables_dir)
    summary.update(input_summary)

    # --- collect output files ---
    tables = []
    mating_plan_path = tables_dir / "mating_plan.csv"
    if mating_plan_path.exists():
        tables.append(mating_plan_path)

    # --- write report ---
    report_path = _write_report(output_dir, mode, summary, input_summary)

    # --- write reproducibility ---
    repro_lines = [
        "# Reproduce this analysis",
        "Rscript --vanilla run_lagm.r \\",
    ]
    i = 0
    while i < len(r_args):
        arg = r_args[i]
        # Boolean flags have no following value
        if arg == "--use-ped":
            repro_lines.append(f"  {arg} \\")
            i += 1
        elif i + 1 < len(r_args):
            repro_lines.append(f"  {arg} {r_args[i+1]} \\")
            i += 2
        else:
            repro_lines.append(f"  {arg} \\")
            i += 1
    # Remove trailing backslash from last line
    if repro_lines[-1].endswith(" \\"):
        repro_lines[-1] = repro_lines[-1][:-2]
    (repro_dir / "commands.sh").write_text(
        "\n".join(repro_lines) + "\n", encoding="utf-8",
    )

    # --- checksums ---
    checksums = {t.name: sha256_file(t) for t in tables}

    return KunResult(
        skill_name="lagm-mating",
        skill_version="0.1.0",
        mode=mode,
        output_dir=output_dir,
        summary=summary,
        data={"checksums": checksums},
        files={"tables": tables},
        report_path=report_path,
    )


if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
