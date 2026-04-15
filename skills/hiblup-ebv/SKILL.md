---
name: hiblup-ebv
description: >-
  Estimate breeding values (EBV) using GBLUP via HI-BLUP from phenotype and genotype tables,
  with a local R backend and KunLib-compatible report outputs.
version: 0.1.0
author: kzy599
license: MIT
tags: [animal-breeding, gblup, ebv, hiblup, quantitative-genetics, genomic-selection]
metadata:
  kunlib:
    kind: data
    requires:
      bins: [python3, Rscript, plink, hiblup]
      r_packages: [data.table]
      python_packages: []
      bioc_packages: []
    emoji: "🐄"
    trigger_keywords:
      - gblup
      - ebv
      - breeding value
      - hiblup
      - genomic selection
      - estimate ebv
      - 估计育种值
      - 基因组选择
    chaining_partners:
      - kinship-matrix
      - gwas-prs
    input_formats:
      - csv-dir (phe.csv + geno.csv + sel_id.csv + ref_id.csv)
    input_schema:
      - name: phe.csv
        format: csv
        required_fields: [ID]
        description: 表型文件，第1列ID，目标性状列由 --trait-pos 指定
      - name: geno.csv
        format: csv
        required_fields: [ID]
        description: 基因型矩阵，第1列ID，其余列为SNP标记(0/1/2编码)
      - name: sel_id.csv
        format: csv
        required_fields: [ID]
        description: 选择集个体ID列表
      - name: ref_id.csv
        format: csv
        required_fields: [ID]
        description: 参考集个体ID列表
    output_schema:
      - name: phe_ebv.csv
        format: csv
        dir: tables
        description: 全部个体的EBV估计结果
      - name: sel_ebv.csv
        format: csv
        dir: tables
        description: 选择集个体的EBV估计结果
      - name: ref_ebv.csv
        format: csv
        dir: tables
        description: 参考集个体的EBV估计结果
---

# 🐄 HI-BLUP EBV

You are **HI-BLUP EBV**, a KunLib skill for estimating genomic breeding values using GBLUP (HI-BLUP backend).

## Core Capabilities

1. Build genomic relationship matrix (VanRaden method 1) from genotype CSV
2. Solve mixed-model equations (Henderson's MME) for GBLUP
3. Estimate EBV and write `phe_ebv.csv`, `sel_ebv.csv`, `ref_ebv.csv`
4. Produce KunLib-style `report.md`, `result.json`, and reproducibility files

## Input Formats

| Format | Extension | Required Fields | Example |
|---|---|---|---|
| Phenotype | `.csv` | `ID` and trait column position (`--trait-pos`) | `phe.csv` |
| Genotype | `.csv` | first column `ID`, remaining marker columns coded as 0/1/2 | `geno.csv` |
| Selection IDs | `.csv` | `ID` | `sel_id.csv` |
| Reference IDs | `.csv` | `ID` | `ref_id.csv` |

## Workflow

1. Validate required files
2. Optionally generate demo input (`filegenerator.r`)
3. Run R thin wrapper (`run_hiblup.r`) to execute PLINK + HI-BLUP steps
4. Collect EBV tables and generate report artifacts

## CLI Reference

```bash
# Via kunlib CLI
kunlib run hiblup-ebv --demo --output /tmp/hiblup_demo
kunlib run hiblup-ebv --input /path/to/data --output /tmp/hiblup_out

# Direct execution
python skills/hiblup-ebv/hiblup_ebv.py --demo --output /tmp/hiblup_demo
python skills/hiblup-ebv/hiblup_ebv.py --input /path/to/data --output /tmp/hiblup_out --trait-pos 3
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--input` | path | — | Input directory containing CSV files *(framework-injected)* |
| `--output` | path | required | Output directory *(framework-injected)* |
| `--demo` | flag | false | 使用 filegenerator.r 生成合成数据并运行 |
| `--phe-file` | str | `phe.csv` | 输入目录中的表型文件名 *(框架根据 input_schema 自动生成)* |
| `--geno-file` | str | `geno.csv` | 输入目录中的基因型文件名 *(框架根据 input_schema 自动生成)* |
| `--sel-id-file` | str | `sel_id.csv` | 输入目录中的选择集 ID 文件名 *(框架根据 input_schema 自动生成)* |
| `--ref-id-file` | str | `ref_id.csv` | 输入目录中的参考集 ID 文件名 *(框架根据 input_schema 自动生成)* |
| `--trait-pos` | int | 4 | hiblup 表型列位置 (1-based) |
| `--threads` | int | 32 | hiblup/plink 线程数 |
| `--plink-format` | flag | false | 基因型文件已是 plink 格式时启用 |
| `--fast-demo` | flag | false | 测试专用: mock demo 加速 |

## Dependencies

### System Binaries

| Binary | Version | Install Method | Notes |
|--------|---------|----------------|-------|
| `python3` | ≥ 3.9 | `conda install python=3.9` | KunLib 框架需要 |
| `Rscript` | ≥ 4.0 | `conda install -c conda-forge r-base` | R 脚本运行环境 |
| `plink` | 1.9 | `conda install -c bioconda plink` | 基因型格式转换 |
| `hiblup` | — | Manual download from official website| ⚠️ 需用户自行下载安装，请参阅官网说明 |

### R Packages

| Package | Version | Install Method | Notes |
|---------|---------|----------------|-------|
| `data.table` | — | `install.packages("data.table")` 或 `conda install -c conda-forge r-data.table` | 高性能数据读写 |

### Python Packages

*(此技能不需要额外的 Python 包)*

### Bioconductor Packages

*(此技能不需要 Bioconductor 包)*

## Output Structure

```
output_dir/
├── report.md
├── result.json
├── work/                  # R 脚本中间文件（含原始 EBV 输出）
├── tables/
│   ├── phe_ebv.csv        # 全部个体 EBV
│   ├── sel_ebv.csv        # 选择集 EBV
│   └── ref_ebv.csv        # 参考集 EBV
├── figures/
├── logs/
└── reproducibility/
    └── commands.sh
```

## Safety

- **Local-first**: All computation runs locally via R
- **Disclaimer**: Research tool only — results must be validated by domain experts
- **Reproducibility**: Full command log in `reproducibility/commands.sh`
