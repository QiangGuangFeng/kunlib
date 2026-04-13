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
