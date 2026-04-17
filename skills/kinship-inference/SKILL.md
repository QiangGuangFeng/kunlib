---
name: kinship-inference
description: >-
  基于高通量 SNP 芯片基因分型数据，经 PLINK 进行严格质量控制，构建符合 COLONY
  软件规范的输入文件，进而采用全似然法进行家系重建与亲缘关系推断。
version: 0.1.0
author: QGF
license: MIT
tags: [animal-breeding, kinship, pedigree-reconstruction, colony, plink, snp-qc, parentage-assignment]
metadata:
  kunlib:
    kind: data
    requires:
      bins: [python3, Rscript, plink]
      r_packages: [data.table, magrittr, xfun, glue, stringi]
      python_packages: []
      bioc_packages: []
    emoji: "🔬"
    trigger_keywords:
      - kinship inference
      - pedigree reconstruction
      - colony
      - parentage
      - family reconstruction
      - 亲缘关系推断
      - 家系重建
      - 亲本鉴定
      - 亲缘推断
    chaining_partners:
      - hiblup-ebv
      - lagm-mating
    input_formats:
      - csv.gz (SNP chip genotype)
      - csv (SampleInfo)
      - txt (SNP list)
    input_schema:
      - name: snp_offspring.csv
        format: csv
        required_fields: [ID, chrom, position, ref]
        description: 子代 SNP 芯片基因型文件（行=SNP，列=ID/chrom/position/ref/个体；可为 .csv.gz）
      - name: snp_parent_tag.csv
        format: csv
        required_fields: [ID, chrom, position, ref]
        description: 亲本/靶标 SNP 芯片基因型文件（行=SNP，列=ID/chrom/position/ref/个体；可为 .csv.gz）
      - name: SampleInfo.csv
        format: csv
        required_fields: [GenotypeID, Class]
        description: 样本类别信息，Class 列含 Tag、Offspring、Sire、Dam 因子
      - name: snp_list.txt
        format: txt
        description: 目标 SNP 列表，无表头，每行一个 SNP 名称
    output_schema:
      - name: colony.dat
        format: dat
        dir: tables
        description: COLONY 软件输入文件
      - name: Plink.log
        format: log
        dir: tables
        description: PLINK 质控日志
      - name: SNP012Plink.snplist
        format: txt
        dir: tables
        description: QC 后保留的 SNP 列表
---

# 🔬 Kinship Inference

You are **Kinship Inference**, a KunLib skill for pedigree reconstruction and kinship inference using SNP chip genotyping data, PLINK quality control, and the COLONY full-likelihood method.

## Why This Exists

- **Without it**: Researchers must manually extract SNPs from chip data, convert genotype formats, run PLINK QC, classify individuals by sample info, and carefully construct COLONY input files — a multi-step error-prone process.
- **With it**: A single command automates the entire pipeline from raw SNP chip files to a ready-to-run COLONY input file, with full quality control and reproducibility.

## Core Capabilities

1. **Multi-chip merging**: Merge genotype data from multiple SNP chip files based on a target SNP list
2. **PLINK QC**: Automated quality control (MAF, call rate, genotype call rate) via PLINK
3. **Sample classification**: Automatic classification of offspring, sires, dams, and tag individuals from SampleInfo
4. **COLONY input generation**: Construct `colony.dat` with all required parameters for full-likelihood pedigree reconstruction
5. **Optional COLONY execution**: Run COLONY via MPI for parallel computation (when `--run-colony` is specified)

## Methodology

1. **SNP extraction**: Read target SNP list → extract matching SNPs from each chip file
2. **Chip merging**: Merge extracted genotypes across chip files by SNP ID
3. **Format conversion**: Convert merged genotypes to PLINK ped/map format (`GT2PedMap`)
4. **PLINK QC**: Run PLINK with `--maf 0.05 --mind 0.20 --geno 0.10 --snps-only --freq --recode --allow-extra-chr`
5. **Genotype tidying**: Convert allele codes (A→1, C→2, G→3, T→4) for COLONY compatibility
6. **Individual classification**: Use SampleInfo to identify offspring (including Tag individuals), sires, and dams
7. **COLONY file generation**: Write `colony.dat` with marker error rates, offspring/parent genotypes, and all COLONY parameters
8. **Optional COLONY run**: Execute COLONY via `mpirun` for pedigree reconstruction

### References

- Purcell S, et al. (2007). PLINK: a tool set for whole-genome association and population-based linkage analyses. *American Journal of Human Genetics*, 81(3):559-575.
- Jones OR, Wang J (2010). COLONY: a program for parentage and sibship inference from multilocus genotype data. *Molecular Ecology Resources*, 10(3):551-555.

## Input Formats

| Format | Extension | Required Fields | Notes |
|--------|-----------|-----------------|-------|
| SNP chip genotype | `.csv` / `.csv.gz` | ID, chrom, position, ref, \<individual columns\> | 行=SNP位点，列=ID/染色体/位置/参考等位基因/个体基因型；可提供多个芯片文件 |
| Sample info | `.csv` | GenotypeID, Class | Class 列含 Tag、Offspring、Sire、Dam 因子 |
| SNP list | `.txt` | 无表头 | 每行一个目标 SNP 名称（如 `NW_020868289.1_207791`） |

> **Important**: GenotypeID values in SampleInfo.csv must match column names in the SNP chip files.

## CLI Reference

```bash
# Via kunlib CLI (demo mode)
kunlib run kinship-inference --demo --output /tmp/kinship_demo

# Direct execution (demo mode)
python skills/kinship-inference/kinship_inference.py --demo --output /tmp/kinship_demo

# With real data
python skills/kinship-inference/kinship_inference.py \
  --input /path/to/data \
  --output /tmp/kinship_out \
  --snp-files "chip1.csv.gz,chip2.csv.gz" \
  --snp-list-file snp_list.txt \
  --SampleInfo-file SampleInfo.csv

# With custom COLONY parameters
python skills/kinship-inference/kinship_inference.py \
  --input /path/to/data \
  --output /tmp/kinship_out \
  --snp-files "chip1.csv.gz,chip2.csv.gz" \
  --project-name MyProject \
  --mating-system "1 1" \
  --inference-method 1 \
  --precision-level 2

# Run COLONY after generating colony.dat
python skills/kinship-inference/kinship_inference.py \
  --input /path/to/data \
  --output /tmp/kinship_out \
  --snp-files "chip1.csv.gz,chip2.csv.gz" \
  --run-colony --n-threads 45
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--input` | path | — | 输入文件目录 *(框架自动注入)* |
| `--output` | path | required | 输出目录 *(框架自动注入)* |
| `--demo` | flag | false | 使用 demo/ 目录中的合成数据运行 |
| `--snp-offspring-file` | str | `snp_offspring.csv` | 子代芯片文件名 *(框架根据 input_schema 自动生成)* |
| `--snp-parent-tag-file` | str | `snp_parent_tag.csv` | 亲本芯片文件名 *(框架根据 input_schema 自动生成)* |
| `--SampleInfo-file` | str | `SampleInfo.csv` | 样本信息文件名 *(框架根据 input_schema 自动生成)* |
| `--snp-list-file` | str | `snp_list.txt` | 目标 SNP 列表文件名 *(框架根据 input_schema 自动生成)* |
| `--snp-files` | str | — | SNP 芯片文件名列表（逗号分隔），覆盖默认值 |
| `--project-name` | str | `KinshipInference` | 写入 colony.dat 的项目名称 |
| `--output-file-name` | str | `KinshipInference` | COLONY 输出文件名前缀 |
| `--seed` | int | `1234` | 随机种子 |
| `--update-allele-freq` | int | `0` | 是否更新等位基因频率: 0=否, 1=是 |
| `--species-type` | int | `2` | 物种类型: 2=二性, 1=单性 |
| `--inbreeding` | int | `0` | 是否存在近交: 0=不存在, 1=存在 |
| `--ploidy-type` | int | `0` | 倍性类型: 0=二倍体, 1=单倍体 |
| `--mating-system` | str | `"0 0"` | 交配系统: "父本 母本"，0=多配, 1=单配 |
| `--clone-inference` | int | `0` | 是否进行克隆推断: 0=不进行, 1=进行 |
| `--scale-full-sibship` | int | `1` | 是否缩放全同胞关系: 0=不缩放, 1=缩放 |
| `--sibship-prior` | int | `0` | 同胞关系先验: 0=无, 1=弱, 2=中等, 3=强, 4=Ne最优 |
| `--pop-allele-freq` | int | `0` | 群体基因频率: 0=未知, 1=已知 |
| `--run-num` | int | `1` | COLONY 运行次数 |
| `--run-length` | int | `2` | 运行长度: 1=短, 2=中等, 3=长, 4=非常长 |
| `--monitor-method` | int | `1` | 监控方法: 0=迭代次数, 1=时间（秒） |
| `--monitor-interval` | int | `1000` | 监控间隔（迭代次数或秒） |
| `--system-version` | int | `0` | 系统版本: 0=DOS/Linux, 1=Windows |
| `--inference-method` | int | `1` | 推断方法: 0=PLS, 1=Full Likelihood, 2=FPLS |
| `--precision-level` | int | `2` | 精度水平: 0=低, 1=中, 2=高, 3=非常高 |
| `--n-threads` | int | `45` | COLONY 并行线程数 |
| `--male-cand-prob` | float | `0.5` | 父本候选包含概率 |
| `--female-cand-prob` | float | `0.5` | 母本候选包含概率 |
| `--marker-type` | int | `0` | 标记类型: 0=SNP/SSR, 1=RAPD/AFLP |
| `--dropout-rate` | float | `0.001` | 等位基因丢失率 |
| `--error-rate` | float | `0.05` | 基因分型错误率 |
| `--run-colony` | flag | false | 生成 colony.dat 后自动运行 COLONY |
| `--colony-bin` | str | `colony2p.ifort.impi2018.out` | COLONY 可执行文件路径 |
| `--mpirun-bin` | str | `mpirun` | mpirun 可执行文件路径 |

## Dependencies

### System Binaries

| Binary | Version | Install Method | Notes |
|--------|---------|----------------|-------|
| `python3` | ≥ 3.9 | `conda install python=3.9` | KunLib 框架需要 |
| `Rscript` | ≥ 4.0 | `conda install -c conda-forge r-base` | R 脚本运行环境 |
| `plink` | 1.9 | `conda install -c bioconda plink` | 基因型格式转换与质控 |
| `mpirun` | — | Intel MPI: 服务器上已安装 | ⚠️ 仅 `--run-colony` 模式需要 |
| `colony2p.ifort.impi2018.out` | 2.0+ | Manual download from COLONY official website | ⚠️ 仅 `--run-colony` 模式需要；需手动下载安装，请参阅 https://www.zsl.org/about-us/resources/software/colony |

### R Packages

| Package | Version | Install Method | Notes |
|---------|---------|----------------|-------|
| `data.table` | — | `install.packages("data.table")` | 高性能数据读写 |
| `magrittr` | — | `install.packages("magrittr")` | 管道操作符 |
| `xfun` | — | `install.packages("xfun")` | 平台检测（is_windows/is_linux） |
| `glue` | — | `install.packages("glue")` | 字符串模板 |
| `stringi` | — | `install.packages("stringi")` | 字符串替换（等位基因编码转换） |

### Python Packages

*(此技能不需要额外的 Python 包)*

### Bioconductor Packages

*(此技能不需要 Bioconductor 包)*

## Output Structure

```
output_dir/
├── report.md
├── result.json
├── work/                      # R 脚本中间文件
│   ├── GenoIndPlink.ped       # PLINK 输入 ped 文件
│   ├── GenoIndPlink.map       # PLINK 输入 map 文件
│   ├── SNP012Plink.*          # PLINK QC 输出（ped/map/snplist/frq/...）
│   ├── Plink.log              # PLINK 运行日志
│   ├── colony.dat             # COLONY 输入文件
│   └── pipeline_summary.csv   # 流程摘要
├── tables/
│   ├── colony.dat             # COLONY 输入文件（副本）
│   ├── SNP012Plink.*          # QC 结果文件（副本）
│   └── Plink.log              # PLINK 日志（副本）
├── figures/
├── logs/
│   ├── r_stdout.log           # R 脚本标准输出
│   └── r_stderr.log           # R 脚本标准错误
└── reproducibility/
    └── commands.sh            # 复现命令
```

## Safety

- **Local-first**: All computation runs locally via R and PLINK
- **Disclaimer**: Research tool only — results must be validated by domain experts
- **Reproducibility**: Full command log in `reproducibility/commands.sh`
- **COLONY optional**: COLONY 运行步骤为可选（`--run-colony`），默认仅生成输入文件
