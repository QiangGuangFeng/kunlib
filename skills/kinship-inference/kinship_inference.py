"""Kinship Inference — SNP QC + COLONY pedigree reconstruction via PLINK & COLONY."""
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
RSCRIPT_KINSHIP = SKILL_DIR / "run_kinship.R"

REQUIRED_FILES = ["SampleInfo.csv"]


def _check_bins() -> dict[str, str | None]:
    """Check availability of required external binaries."""
    bins: dict[str, str | None] = {}
    for name in ("Rscript", "plink"):
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


def _read_pipeline_summary(work_dir: Path) -> dict:
    """Read pipeline_summary.csv written by the R script."""
    summary: dict = {}
    fpath = work_dir / "pipeline_summary.csv"
    if fpath.exists():
        with open(fpath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get("metric", row.get("key", ""))
                val = row.get("value", "")
                # Try to convert to int
                try:
                    summary[key] = int(val)
                except (ValueError, TypeError):
                    summary[key] = val
    return summary


def _write_report(
    output_dir: Path, mode: str, summary: dict,
) -> Path:
    """Write KunLib-style report.md."""
    report_path = output_dir / "report.md"
    header = generate_report_header(
        title="Kinship Inference Report",
        skill_name="kinship-inference",
        skill_version="0.1.0",
        extra={"Mode": mode},
    )
    body_lines = [
        "## Pipeline Summary\n",
        f"- **Target SNPs**: {summary.get('n_target_snps', 'N/A')}",
        f"- **SNP chip files**: {summary.get('n_snp_chips', 'N/A')}",
        f"- **Merged samples**: {summary.get('n_samples_merged', 'N/A')}",
        f"- **Loci after QC**: {summary.get('n_loci_after_qc', 'N/A')}",
        f"- **Offspring**: {summary.get('n_offspring', 'N/A')}",
        f"- **Sires**: {summary.get('n_sires', 'N/A')}",
        f"- **Dams**: {summary.get('n_dams', 'N/A')}",
        f"- **Project name**: {summary.get('project_name', 'N/A')}",
        "",
        "## Output Files\n",
        "- `colony.dat` — COLONY input file for pedigree reconstruction",
        "- `SNP012Plink.*` — PLINK QC output files",
        "- `Plink.log` — PLINK log file",
        "",
    ]
    footer = generate_report_footer()
    report_path.write_text(
        header + "\n".join(body_lines) + footer, encoding="utf-8",
    )
    return report_path


@skill(
    name="kinship-inference",
    kind="data",
    version="0.1.0",
    description="基于高通量 SNP 芯片基因分型数据，经 PLINK 质控，构建 COLONY 输入文件，采用全似然法进行家系重建与亲缘关系推断",
    author="QGF",
    tags=[
        "animal-breeding", "kinship", "pedigree-reconstruction",
        "colony", "plink", "snp-qc", "parentage-assignment",
    ],
    trigger_keywords=[
        "kinship inference", "pedigree reconstruction", "colony",
        "parentage", "family reconstruction", "亲缘关系推断",
        "家系重建", "亲本鉴定", "亲缘推断",
    ],
    chaining_partners=["hiblup-ebv", "lagm-mating"],
    input_formats=["csv.gz (SNP chip genotype)", "csv (SampleInfo)", "txt (SNP list)"],
    requires=SkillRequires(
        bins=["python3", "Rscript", "plink"],
        r_packages=["data.table", "magrittr", "xfun", "glue", "stringi"],
    ),
    input_schema=[
        IOField(
            name="snp_offspring.csv", format="csv",
            required_fields=["ID", "chrom", "position", "ref"],
            description="子代 SNP 芯片基因型文件（行=SNP，列=ID/chrom/position/ref/个体；可为 .csv.gz）",
        ),
        IOField(
            name="snp_parent_tag.csv", format="csv",
            required_fields=["ID", "chrom", "position", "ref"],
            description="亲本/靶标 SNP 芯片基因型文件（行=SNP，列=ID/chrom/position/ref/个体；可为 .csv.gz）",
        ),
        IOField(
            name="SampleInfo.csv", format="csv",
            required_fields=["GenotypeID", "Class"],
            description="样本类别信息：Class 列含 Tag、Offspring、Sire、Dam 因子",
        ),
        IOField(
            name="snp_list.txt", format="txt",
            description="目标 SNP 列表，无表头，每行一个 SNP 名称",
        ),
    ],
    output_schema=[
        IOField(name="colony.dat", dir="tables", description="COLONY 软件输入文件"),
        IOField(name="Plink.log", dir="tables", description="PLINK 质控日志"),
        IOField(name="SNP012Plink.snplist", dir="tables", description="QC 后保留的 SNP 列表"),
    ],
    emoji="🔬",
    params=[
        # --input and --output are auto-injected by framework
        # --snp-offspring-file, --snp-parent-tag-file, --SampleInfo-file, --1K位点-file
        # are auto-generated from input_schema
        Param("demo", is_flag=True, help="使用 demo/ 目录中的合成数据运行"),
        Param("snp-files", type=str, default="",
              help="SNP 芯片文件名列表（逗号分隔），覆盖 input_schema 默认值。"
                   "如 'snp_offspring.csv.gz,snp_parent_tag.csv.gz'"),
        Param("project-name", type=str, default="KinshipInference",
              help="项目名称，写入 colony.dat"),
        Param("output-file-name", type=str, default="KinshipInference",
              help="COLONY 输出文件名前缀"),
        Param("seed", type=int, default=1234, help="随机种子"),
        Param("update-allele-freq", type=int, default=0,
              help="是否更新等位基因频率: 0=否, 1=是"),
        Param("species-type", type=int, default=2,
              help="物种类型: 2=二性, 1=单性"),
        Param("inbreeding", type=int, default=0,
              help="是否存在近交: 0=不存在, 1=存在"),
        Param("ploidy-type", type=int, default=0,
              help="倍性类型: 0=二倍体, 1=单倍体"),
        Param("mating-system", type=str, default="0 0",
              help="交配系统: '父本 母本'，0=多配, 1=单配"),
        Param("clone-inference", type=int, default=0,
              help="是否进行克隆推断: 0=不进行, 1=进行"),
        Param("scale-full-sibship", type=int, default=1,
              help="是否缩放全同胞关系: 0=不缩放, 1=缩放"),
        Param("sibship-prior", type=int, default=0,
              help="同胞关系先验: 0=无, 1=弱, 2=中等, 3=强, 4=Ne最优"),
        Param("pop-allele-freq", type=int, default=0,
              help="是否已知群体基因频率: 0=未知, 1=已知"),
        Param("run-num", type=int, default=1, help="COLONY 运行次数"),
        Param("run-length", type=int, default=2,
              help="运行长度: 1=短, 2=中等, 3=长, 4=非常长"),
        Param("monitor-method", type=int, default=1,
              help="监控方法: 0=迭代次数, 1=时间（秒）"),
        Param("monitor-interval", type=int, default=1000,
              help="监控间隔（迭代次数或秒）"),
        Param("system-version", type=int, default=0,
              help="系统版本: 0=DOS/Linux, 1=Windows"),
        Param("inference-method", type=int, default=1,
              help="推断方法: 0=PLS, 1=Full Likelihood, 2=FPLS"),
        Param("precision-level", type=int, default=2,
              help="精度水平: 0=低, 1=中, 2=高, 3=非常高"),
        Param("n-threads", type=int, default=45, help="COLONY 并行线程数"),
        Param("male-cand-prob", type=float, default=0.5,
              help="父本候选包含概率"),
        Param("female-cand-prob", type=float, default=0.5,
              help="母本候选包含概率"),
        Param("marker-type", type=int, default=0,
              help="标记类型: 0=SNP/SSR, 1=RAPD/AFLP等"),
        Param("dropout-rate", type=float, default=0.001,
              help="等位基因丢失率"),
        Param("error-rate", type=float, default=0.05,
              help="基因分型错误率"),
        Param("run-colony", is_flag=True,
              help="生成 colony.dat 后自动运行 COLONY（需 mpirun + colony 已安装）"),
        Param("colony-bin", type=str, default="colony2p.ifort.impi2018.out",
              help="COLONY 可执行文件路径或名称"),
        Param("mpirun-bin", type=str, default="mpirun",
              help="mpirun 可执行文件路径"),
    ],
)
def run(args: argparse.Namespace) -> KunResult:
    """Main pipeline for kinship inference via PLINK QC + COLONY.

    框架自动提供的目录:
      args.output_dir   总输出目录
      args.work_dir     中间文件 (R 脚本在这里跑)
      args.tables_dir   最终表格
      args.figures_dir  最终图片
      args.logs_dir     日志
      args.repro_dir    复现指令
    """
    output_dir = args.output_dir
    work_dir = args.work_dir
    tables_dir = args.tables_dir
    logs_dir = args.logs_dir
    repro_dir = args.repro_dir

    mode = "demo" if args.demo else "input"

    # --- Resolve input directory ---
    if args.demo:
        input_dir = SKILL_DIR / "demo"
    else:
        if not args.input:
            raise SystemExit("Error: --input is required when not using --demo")
        input_dir = Path(args.input)

    # --- Determine SNP file list ---
    snp_files_str = args.snp_files
    if not snp_files_str:
        if args.demo:
            # Use demo files
            snp_files_str = "ZZ2024G06_off_gt1556.csv.gz,All.GT_ZZG06_par_tag_55K_213.csv.gz"
        else:
            # Use the auto-generated input_schema file params
            snp_files_str = f"{args.snp_offspring_file},{args.snp_parent_tag_file}"

    # --- Determine other input files ---
    sample_info_file = args.SampleInfo_file
    snp_list_file = args.snp_list_file
    if args.demo:
        # Demo files use original Chinese filenames
        if sample_info_file == "SampleInfo.csv":
            pass  # Same default
        if snp_list_file == "snp_list.txt":
            snp_list_file = "1K位点.txt"

    # --- Validate required files ---
    snp_file_list = [f.strip() for f in snp_files_str.split(",") if f.strip()]
    required = [sample_info_file, snp_list_file] + snp_file_list
    missing = _validate_input(input_dir, required)
    if missing:
        raise SystemExit(
            f"Error: missing required files in {input_dir}: {', '.join(missing)}"
        )

    # --- Set demo-specific defaults ---
    project_name = args.project_name
    output_file_name = args.output_file_name
    if args.demo and project_name == "KinshipInference":
        project_name = "DemoKinshipInference"
        output_file_name = "DemoKinshipInference"

    # --- Build R arguments ---
    r_args = [
        "--snp-files", snp_files_str,
        "--snp-list-file", snp_list_file,
        "--sample-info-file", sample_info_file,
        "--input-dir", str(input_dir),
        "--work-dir", str(work_dir),
        "--tables-dir", str(tables_dir),
        "--project-name", project_name,
        "--output-file-name", output_file_name,
        "--seed", str(args.seed),
        "--update-allele-freq", str(args.update_allele_freq),
        "--species-type", str(args.species_type),
        "--inbreeding", str(args.inbreeding),
        "--ploidy-type", str(args.ploidy_type),
        "--mating-system", args.mating_system,
        "--clone-inference", str(args.clone_inference),
        "--scale-full-sibship", str(args.scale_full_sibship),
        "--sibship-prior", str(args.sibship_prior),
        "--pop-allele-freq", str(args.pop_allele_freq),
        "--run-num", str(args.run_num),
        "--run-length", str(args.run_length),
        "--monitor-method", str(args.monitor_method),
        "--monitor-interval", str(args.monitor_interval),
        "--system-version", str(args.system_version),
        "--inference-method", str(args.inference_method),
        "--precision-level", str(args.precision_level),
        "--male-cand-prob", str(args.male_cand_prob),
        "--female-cand-prob", str(args.female_cand_prob),
        "--marker-type", str(args.marker_type),
        "--dropout-rate", str(args.dropout_rate),
        "--error-rate", str(args.error_rate),
    ]

    # --- Run R pipeline ---
    try:
        result = _run_r(RSCRIPT_KINSHIP, r_args, cwd=work_dir)
        # Write R stdout/stderr to logs
        if result.stdout:
            (logs_dir / "r_stdout.log").write_text(result.stdout, encoding="utf-8")
        if result.stderr:
            (logs_dir / "r_stderr.log").write_text(result.stderr, encoding="utf-8")
    except subprocess.CalledProcessError as e:
        # Write error logs
        (logs_dir / "r_stdout.log").write_text(e.stdout or "", encoding="utf-8")
        (logs_dir / "r_stderr.log").write_text(e.stderr or "", encoding="utf-8")
        raise SystemExit(
            f"Error: R pipeline failed (exit code {e.returncode}).\n"
            f"See {logs_dir / 'r_stderr.log'} for details.\n"
            f"stderr: {(e.stderr or '')[:500]}"
        )

    # --- Optionally run COLONY ---
    colony_status = "skipped"
    if args.run_colony:
        colony_dat = work_dir / "colony.dat"
        if colony_dat.exists():
            colony_cmd = [
                args.mpirun_bin, "-np", str(args.n_threads),
                args.colony_bin, f"IFN:{colony_dat}",
            ]
            try:
                colony_result = subprocess.run(
                    colony_cmd, cwd=str(work_dir),
                    capture_output=True, text=True, check=True,
                )
                colony_status = "success"
                (logs_dir / "colony_stdout.log").write_text(
                    colony_result.stdout or "", encoding="utf-8",
                )
                (logs_dir / "colony_stderr.log").write_text(
                    colony_result.stderr or "", encoding="utf-8",
                )
            except subprocess.CalledProcessError as e:
                colony_status = "failed"
                (logs_dir / "colony_stdout.log").write_text(
                    e.stdout or "", encoding="utf-8",
                )
                (logs_dir / "colony_stderr.log").write_text(
                    e.stderr or "", encoding="utf-8",
                )
            except FileNotFoundError:
                colony_status = "not_found"
                (logs_dir / "colony_stderr.log").write_text(
                    f"COLONY binary not found: {args.colony_bin}\n"
                    f"mpirun binary: {args.mpirun_bin}\n",
                    encoding="utf-8",
                )

    # --- Read pipeline summary ---
    summary = _read_pipeline_summary(work_dir)
    summary["colony_run_status"] = colony_status

    # --- Collect output files ---
    tables = []
    for name in ("colony.dat", "Plink.log", "SNP012Plink.snplist"):
        fpath = tables_dir / name
        if fpath.exists():
            tables.append(fpath)

    logs = []
    for name in ("r_stdout.log", "r_stderr.log"):
        fpath = logs_dir / name
        if fpath.exists():
            logs.append(fpath)

    # --- Write report ---
    report_path = _write_report(output_dir, mode, summary)

    # --- Write reproducibility ---
    repro_lines = [
        "# Reproduce this analysis",
        "Rscript --vanilla run_kinship.R \\",
    ]
    i = 0
    while i < len(r_args):
        arg = r_args[i]
        if i + 1 < len(r_args):
            repro_lines.append(f"  {arg} '{r_args[i+1]}' \\")
            i += 2
        else:
            repro_lines.append(f"  {arg} \\")
            i += 1
    # Remove trailing backslash from last line
    if repro_lines[-1].endswith(" \\"):
        repro_lines[-1] = repro_lines[-1][:-2]
    if args.run_colony:
        repro_lines.append("")
        repro_lines.append("# Run COLONY")
        repro_lines.append(
            f"{args.mpirun_bin} -np {args.n_threads} {args.colony_bin} IFN:colony.dat"
        )
    (repro_dir / "commands.sh").write_text(
        "\n".join(repro_lines) + "\n", encoding="utf-8",
    )

    # --- Checksums ---
    checksums = {t.name: sha256_file(t) for t in tables}

    return KunResult(
        skill_name="kinship-inference",
        skill_version="0.1.0",
        mode=mode,
        output_dir=output_dir,
        summary=summary,
        data={"checksums": checksums},
        files={"tables": tables, "logs": logs},
        report_path=report_path,
    )


if __name__ == "__main__":
    run.__kunlib_meta__.run_cli()
