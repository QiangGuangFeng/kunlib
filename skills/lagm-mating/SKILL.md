---
name: lagm-mating
description: >-
  根据候选个体信息（ID、选择指数、性别）及基因型/系谱数据，
  通过 lagm::lagm_plan() 约束优化生成兼顾遗传增益与多样性的配种方案。
version: 0.1.0
author: kzy599
license: MIT
tags: [animal-breeding, mating-plan, optimal-contribution, genetic-diversity, lagm, quantitative-genetics]
metadata:
  kunlib:
    kind: data
    requires:
      bins: [python3, Rscript]
      r_packages: [data.table, remotes, visPedigree, lagm, AlphaSimR]
      python_packages: []
      bioc_packages: []
    emoji: "🐄"
    trigger_keywords:
      - mating plan
      - lagm
      - optimal mating
      - genetic diversity
      - 配种方案
      - 最优交配
      - 遗传多样性
      - 配种计划
    chaining_partners:
      - hiblup-ebv
      - kinship-matrix
    input_formats:
      - csv-dir (id_index_sex.csv + geno.csv + optional ped.csv)
    input_schema:
      - name: id_index_sex.csv
        format: csv
        required_fields: [ID, selindex, sex]
        description: 候选个体信息，第1列ID，第2列选择指数，第3列性别(M/F)
      - name: geno.csv
        format: csv
        required_fields: [ID]
        description: 基因型矩阵，第1列ID，其余列为SNP标记(0/1/2编码)
      - name: ped.csv
        format: csv
        required_fields: [ID, sire, dam]
        description: 系谱文件（可选，use_ped=TRUE且diversity_mode!='genomic'时使用）
    output_schema:
      - name: mating_plan.csv
        format: csv
        dir: tables
        description: 配种方案主结果，包含母本、父本、配对与目标函数相关字段
---

# 🐄 LAGM Mating

You are **LAGM Mating**, a KunLib skill for generating optimal mating plans that balance genetic gain and diversity.

## Why This Exists

- **Without it**: Breeders must manually design mating plans, risking inbreeding accumulation and suboptimal genetic progress.
- **With it**: Automated constrained optimization via `lagm::lagm_plan()` produces mating plans that maximize selection response while controlling diversity loss across future generations.

## Core Capabilities

1. **Constrained mating optimization**: Balance selection index (genetic gain) against diversity preservation
2. **Multiple diversity modes**: Genomic (raw genotype), relationship matrix (G-matrix from genotype), or pedigree-based (A-matrix via `visPedigree`)
3. **Flexible contribution constraints**: Control min/max contribution per sire and dam
4. **Look-ahead optimization**: Multi-generation lookahead for long-term genetic planning
5. **Heuristic search**: Simulated annealing with configurable cooling, early stopping, and population-based search

## Methodology

- Core function: `lagm::lagm_plan()` performs constrained optimization of mating allocations
- Objective: Maximize weighted selection index (EBV/genetic gain) while maintaining genetic diversity
- Diversity matrix sources:
  - **Genomic mode** (`diversity_mode="genomic"`): Uses raw genotype matrix directly
  - **Relationship mode** (`diversity_mode="relationship"`, `use_ped=FALSE`): Constructs G-matrix from genotypes via VanRaden method
  - **Pedigree mode** (`diversity_mode="relationship"`, `use_ped=TRUE`): Uses pedigree-based A-matrix via `visPedigree::pedmat()`
- Search: Population-based simulated annealing with configurable swap probability, initial heuristic ratio, cooling rate, and early stopping

## Input Formats

| Format | Extension | Required Fields | Notes |
|--------|-----------|-----------------|-------|
| Candidate info | `.csv` | Col1=ID, Col2=selindex, Col3=sex(M/F) | Column order enforced, header names flexible |
| Genotype | `.csv` | Col1=ID, remaining=SNP(0/1/2) | Column order enforced, header names flexible |
| Pedigree | `.csv` | Col1=ID, Col2=sire, Col3=dam | Optional; column order enforced |

> **Important**: ID values must be strictly aligned across `id_index_sex.csv`, `geno.csv`, and `ped.csv`.

## CLI Reference

```bash
# Via kunlib CLI
kunlib run lagm-mating --demo --output /tmp/lagm_demo
kunlib run lagm-mating --input /path/to/data --output /tmp/lagm_out

# Direct execution
python skills/lagm-mating/lagm_mating.py --demo --output /tmp/lagm_demo
python skills/lagm-mating/lagm_mating.py --input /path/to/data --output /tmp/lagm_out

# With custom parameters
python skills/lagm-mating/lagm_mating.py \
  --input /path/to/data --output /tmp/lagm_out \
  --n-crosses 50 --t 5 --diversity-mode relationship --n-iter 50000
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--input` | path | — | 输入文件目录 *(框架自动注入)* |
| `--output` | path | required | 输出目录 *(框架自动注入)* |
| `--demo` | flag | false | 使用 generate_demo.r 生成合成数据并运行 |
| `--id-index-sex-file` | str | `id_index_sex.csv` | 候选个体信息文件名 *(框架根据 input_schema 自动生成)* |
| `--geno-file` | str | `geno.csv` | 基因型文件名 *(框架根据 input_schema 自动生成)* |
| `--ped-file` | str | `ped.csv` | 系谱文件名（可选） *(框架根据 input_schema 自动生成)* |
| `--t` | int | `3` | 前瞻代数 (lookahead generations) |
| `--n-crosses` | int | `30` | 目标配对数 |
| `--male-contribution-min` | int | `2` | 每个公本最少贡献次数 |
| `--male-contribution-max` | int | `2` | 每个公本最多贡献次数 |
| `--female-contribution-min` | int | `1` | 每个母本最少贡献次数 |
| `--female-contribution-max` | int | `1` | 每个母本最多贡献次数 |
| `--diversity-mode` | str | `genomic` | 多样性模式: `genomic` 或 `relationship` |
| `--use-ped` | flag | false | 使用系谱关系矩阵 |
| `--n-iter` | int | `30000` | 优化迭代次数 |
| `--n-pop` | int | `100` | 种群/候选方案规模 |
| `--n-threads` | int | `8` | 并行线程数 |
| `--swap-prob` | float | `0.2` | 交换概率 |
| `--init-prob` | float | `0.8` | 初始启发式比例 |
| `--cooling-rate` | float | `0.998` | 退火降温速率 |
| `--stop-window` | int | `2000` | 早停窗口 |
| `--stop-eps` | float | `1e-8` | 早停精度阈值 |

## Dependencies

### System Binaries

| Binary | Version | Install Method | Notes |
|--------|---------|----------------|-------|
| `python3` | ≥ 3.10 | `conda install python=3.10` | KunLib 框架需要 |
| `Rscript` | ≥ 4.2 (建议 4.5+) | `conda install -c conda-forge r-base` | R 脚本运行环境 |

### R Packages

| Package | Version | Install Method | Notes |
|---------|---------|----------------|-------|
| `data.table` | — | `install.packages("data.table")` | 高性能数据读写 |
| `remotes` | — | `install.packages("remotes")` | 安装 GitHub 包所需 |
| `visPedigree` | — | `remotes::install_github("luansheng/visPedigree")` | 系谱矩阵计算（pedigree模式需要） |
| `lagm` | — | `remotes::install_github("kzy599/LAGM", subdir = "lagmRcpp")` | ⚠️ 核心配种优化包；GitHub: https://github.com/kzy599/LAGM ；如仓库不可访问请联系 kangziyi1998@163.com 获取手动安装包 |
| `AlphaSimR` | — | `install.packages("AlphaSimR")` | 仅 demo 模式需要（生成合成数据） |

### Python Packages

*(此技能不需要额外的 Python 包)*

### Bioconductor Packages

*(此技能不需要 Bioconductor 包)*

## Output Structure

```
output_dir/
├── report.md
├── result.json
├── work/                  # 中间文件
├── tables/
│   └── mating_plan.csv    # 配种方案主结果
├── figures/
├── logs/
└── reproducibility/
    └── commands.sh
```

## Safety

- **Local-first**: All computation runs locally via R
- **Disclaimer**: Research tool only — results must be validated by domain experts
- **Reproducibility**: Full command log in `reproducibility/commands.sh`
