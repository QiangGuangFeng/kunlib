"""HI-BLUP EBV — Estimate breeding values using GBLUP via HI-BLUP."""
from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from pathlib import Path

from kunlib import skill, Param, KunResult, SkillRequires, IOField
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


def _run_r(
    script: Path, args: list[str], cwd: Path, env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run an R script via Rscript."""
    import os

    run_env = None
    if env:
        run_env = {**os.environ, **env}
    cmd = ["Rscript", "--vanilla", str(script)] + args
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=True, env=run_env)


def _resolve_input_paths(
    input_dir: Path, phe_file: str, geno_file: str, sel_file: str, ref_file: str,
) -> tuple[Path, Path, Path, Path]:
    """Resolve input file paths within the input directory."""
    return (
        input_dir / phe_file,
        input_dir / geno_file,
        input_dir / sel_file,
        input_dir / ref_file,
    )


def _validate_input(input_dir: Path, filenames: list[str] | None = None) -> list[str]:
    """Return list of missing required files."""
    names = filenames if filenames is not None else REQUIRED_FILES
    return [f for f in names if not (input_dir / f).exists()]


def _generate_demo(work_dir: Path, env: dict | None = None) -> Path:
    """Generate demo data into work_dir using filegenerator.r."""
    _run_r(RSCRIPT_DEMO, ["--output", str(work_dir)], cwd=SKILL_DIR, env=env)
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
    kind="data",
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
    requires=SkillRequires(
        bins=["python3", "Rscript", "plink", "hiblup"],
        r_packages=["data.table"],
    ),
    input_schema=[
        IOField(name="phe.csv", format="csv", required_fields=["ID"], description="表型文件"),
        IOField(name="geno.csv", format="csv", required_fields=["ID"], description="0/1/2基因型矩阵"),
        IOField(name="sel_id.csv", format="csv", required_fields=["ID"], description="选择集 ID"),
        IOField(name="ref_id.csv", format="csv", required_fields=["ID"], description="参考集 ID"),
    ],
    output_schema=[
        IOField(name="phe_ebv.csv", dir="tables", description="全部个体EBV"),
        IOField(name="sel_ebv.csv", dir="tables", description="选择集EBV"),
        IOField(name="ref_ebv.csv", dir="tables", description="参考集EBV"),
    ],
    emoji="🐄",
    params=[
        # --input 和 --output 由框架自动注入，不需要声明
        # --phe-file, --geno-file, --sel-id-file, --ref-id-file 由框架根据 input_schema 自动生成
        Param("demo", is_flag=True, help="使用 filegenerator.r 生成合成数据并运行"),
        Param("trait-pos", type=int, default=4, help="hiblup 表型列位置 (1-based)"),
        Param("threads", type=int, default=32, help="hiblup/plink 线程数"),
        Param("plink-format", is_flag=True, help="基因型文件已是 plink 格式时启用"),
        Param("fast-demo", is_flag=True, help="测试专用: mock demo 加速"),
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
    threads = args.threads

    # --- build env for fast-demo / mock ---
    extra_env: dict[str, str] = {}
    if args.fast_demo:
        extra_env["HIBLUP_EBV_FAST_DEMO"] = "1"
        extra_env["HIBLUP_EBV_MOCK"] = "1"

    # --- resolve input directory ---
    if args.demo:
        input_dir = _generate_demo(work_dir, env=extra_env or None)
    else:
        if not args.input:
            raise SystemExit("Error: --input is required when not using --demo")
        input_dir = Path(args.input)

    # --- resolve individual input files ---
    phe_path, geno_path, sel_path, ref_path = _resolve_input_paths(
        input_dir, args.phe_file, args.geno_file, args.sel_id_file, args.ref_id_file,
    )

    # --- validate inputs ---
    required = [args.phe_file, args.geno_file, args.sel_id_file, args.ref_id_file]
    missing = _validate_input(input_dir, required)
    if missing:
        raise SystemExit(
            f"Error: missing required files in {input_dir}: {', '.join(missing)}"
        )

    # --- run HI-BLUP pipeline via R (中间文件全部在 work_dir) ---
    r_args = [
        "--phe-file", str(phe_path),
        "--geno-file", str(geno_path),
        "--sel-id", str(sel_path),
        "--ref-id", str(ref_path),
        "--trait-pos", str(trait_pos),
        "--threads", str(threads),
        "--workdir", str(work_dir),
    ]
    if args.plink_format:
        r_args.append("--plink-format")

    _run_r(RSCRIPT_HIBLUP, r_args, cwd=SKILL_DIR, env=extra_env or None)

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
    repro_lines = [
        "# Reproduce this analysis",
        "Rscript --vanilla run_hiblup.r \\",
        f"  --phe-file {phe_path} \\",
        f"  --geno-file {geno_path} \\",
        f"  --sel-id {sel_path} \\",
        f"  --ref-id {ref_path} \\",
        f"  --trait-pos {trait_pos} \\",
        f"  --threads {threads} \\",
        f"  --workdir {work_dir}",
    ]
    if args.plink_format:
        repro_lines[-1] += " \\"
        repro_lines.append("  --plink-format")
    (repro_dir / "commands.sh").write_text(
        "\n".join(repro_lines) + "\n", encoding="utf-8",
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
