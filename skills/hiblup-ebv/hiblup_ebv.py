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


def _generate_demo(output_dir: Path) -> Path:
    """Generate demo data using filegenerator.r."""
    demo_dir = output_dir / "demo_input"
    demo_dir.mkdir(parents=True, exist_ok=True)
    _run_r(RSCRIPT_DEMO, [str(demo_dir)], cwd=SKILL_DIR)
    return demo_dir


def _read_ebv_summary(output_dir: Path) -> dict:
    """Read EBV output files and produce summary statistics."""
    summary: dict = {}
    for name in ("phe_ebv.csv", "sel_ebv.csv", "ref_ebv.csv"):
        fpath = output_dir / name
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
        Param("input", help="Input directory containing phe.csv, geno.csv, sel_id.csv, ref_id.csv"),
        Param("output", required=True, help="Output directory"),
        Param("demo", is_flag=True, help="Run with synthetic demo data"),
        Param("trait-pos", type=int, default=2,
              help="Column index (1-based) of the target trait in phe.csv"),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    """Main pipeline for HI-BLUP EBV estimation."""
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    mode = "demo" if args.demo else "input"
    trait_pos = args.trait_pos

    # --- resolve input directory ---
    if args.demo:
        input_dir = _generate_demo(output_dir)
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

    # --- run HI-BLUP pipeline via R ---
    _run_r(
        RSCRIPT_HIBLUP,
        [str(input_dir), str(output_dir), str(trait_pos)],
        cwd=SKILL_DIR,
    )

    # --- collect results ---
    summary = _read_ebv_summary(output_dir)
    tables = [
        output_dir / f
        for f in ("phe_ebv.csv", "sel_ebv.csv", "ref_ebv.csv")
        if (output_dir / f).exists()
    ]

    # --- write report ---
    report_path = _write_report(output_dir, mode, summary)

    # --- write reproducibility ---
    repro_dir = output_dir / "reproducibility"
    repro_dir.mkdir(exist_ok=True)
    (repro_dir / "commands.sh").write_text(
        f"# Reproduce this analysis\n"
        f"Rscript --vanilla run_hiblup.r {input_dir} {output_dir} {trait_pos}\n",
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
