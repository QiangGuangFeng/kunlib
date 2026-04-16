---
name: pedigree-analysis
description: >-
  水产动物家系育种系谱分析：系谱整理、群体统计、近交系数、遗传多样性、
  世代间隔、血统比例、关系矩阵及系谱可视化，基于 visPedigree 包。
kind: data
version: 0.1.0
author: luansheng
license: GPL-3.0
tags:
  - pedigree
  - aquaculture
  - animal-breeding
  - inbreeding
  - genetic-diversity
  - relationship-matrix
  - visualization
  - visPedigree
  - effective-population-size
metadata:
  kunlib:
    requires:
      bins: [Rscript]
      r_packages: [visPedigree, data.table, jsonlite]
      python_packages: []
      bioc_packages: []
    emoji: "🐟"
    trigger_keywords:
      - pedigree analysis
      - 系谱分析
      - 近交系数
      - 遗传多样性
      - 有效群体大小
      - 系谱图
      - 关系矩阵
      - 世代间隔
      - inbreeding coefficient
      - kinship
      - effective population size
      - pedigree visualization
      - ancestor contribution
      - blood line
    chaining_partners:
      - lagm-mating
      - hiblup-ebv
    input_formats:
      - csv (Ind/Sire/Dam + optional Year/Sex/Line columns)
    input_schema:
      - name: pedigree.csv
        format: csv
        required_fields: [Ind, Sire, Dam]
        description: >-
          系谱文件：前3列必须按顺序为个体ID、父本ID、母本ID（列名任意）。
          缺失亲本用 NA/0/*。可附加 Year、Sex、Line 等列。
    output_schema:
      - name: tidyped.csv
        format: csv
        dir: tables
        description: 标准化后的系谱（始终输出）
      - name: pedstats_summary.csv
        format: csv
        dir: tables
        description: 群体结构统计（stats 模块）
      - name: inbreeding.csv
        format: csv
        dir: tables
        description: 个体近交系数（inbreeding 模块）
      - name: diversity_summary.csv
        format: csv
        dir: tables
        description: 遗传多样性摘要（diversity 模块）
      - name: pedigree.pdf
        format: pdf
        dir: figures
        description: 系谱图（visual 模块）
      - name: ecg_plot.png
        format: png
        dir: figures
        description: 等价完全世代直方图（stats 模块）
      - name: matrix_heatmap.png
        format: png
        dir: figures
        description: 关系矩阵热图（matrix 模块）
---

# 🐟 Pedigree Analysis

You are **Pedigree Analysis**, a KunLib skill for comprehensive aquaculture pedigree analysis powered by [visPedigree](https://github.com/luansheng/visPedigree).

## Why This Exists

- **Without it**: Breeders must manually run multiple R functions, manage intermediate objects, and write custom output code.
- **With it**: A single CLI call covers the full pipeline — from raw pedigree CSV to tidied data, statistics, inbreeding coefficients, diversity indices, generation intervals, ancestry proportions, relationship matrices, and publication-ready figures.

## Core Capabilities

1. **Pedigree Standardisation**: `tidyped()` — handles missing parents, detects loops, assigns generations, supports selfing and bisexual parents.
2. **Population Statistics**: `pedstats()` — group size, founder counts, equivalent complete generations (ECG), ECG histogram.
3. **Inbreeding Analysis**: `inbreed()` + `pedfclass()` — individual-level Wright's F coefficients and severity classification.
4. **Generation Intervals**: `pedgenint()` — SS/SD/DS/DD four-pathway generation intervals from a time column (e.g., `Year`).
5. **Genetic Diversity**: `pediv()` — effective population size (Ne), effective founders (fe), effective ancestors (fa), gene diversity, founder/ancestor contribution tables.
6. **Ancestry Tracing**: `pedancestry()` — proportion of each founder group (e.g., Line) in every individual.
7. **Relationship Matrices**: `pedmat()` — Additive (A), Dominance (D), AA epistatic matrices and their inverses; compact mode for large pedigrees.
8. **Pedigree Visualisation**: `visped()` — hierarchical PDF/PNG graph with compact full-sib nodes, ancestry tracing, and inbreeding display.

## Input Format

`--input` 是 KunLib 框架注入的**输入目录**。系谱 CSV 文件须放在该目录中，默认文件名为 `pedigree.csv`，也可通过 `--pedigree-file` 指定其他文件名。

| Item | Requirement |
|------|-------------|
| `--input` | 输入目录（KunLib 框架注入） |
| 默认文件名 | `pedigree.csv`（可通过 `--pedigree-file` 覆盖） |
| Column order | Col 1 = Individual ID, Col 2 = Sire ID, Col 3 = Dam ID |
| Column names | Any (standardised internally) |
| Missing parents | `NA`, `0`, or `*` |
| Extra columns | `Year`, `Sex`, `Line`, `Batch`, etc. — passed through automatically |
| Encoding | UTF-8 |

## CLI Reference

```bash
# Default tasks (stats + inbreeding + visual) with synthetic demo data
kunlib run pedigree-analysis --demo --output /tmp/ped_demo

# Direct execution (demo)
python skills/pedigree-analysis/pedigree_analysis.py --demo --output /tmp/ped_demo

# All modules with real data — default pedfile name (pedigree.csv)
kunlib run pedigree-analysis \
  --input /path/to/input_dir \
  --tasks all \
  --timevar Year \
  --foundervar Line \
  --output /tmp/ped_all

# Custom pedfile name (e.g., shrimp_2024.csv inside input_dir)
kunlib run pedigree-analysis \
  --input /path/to/input_dir \
  --pedigree-file shrimp_2024.csv \
  --tasks all \
  --timevar Year \
  --foundervar Line \
  --output /tmp/ped_all

# Specific modules with candidate tracing
python skills/pedigree-analysis/pedigree_analysis.py \
  --input /path/to/input_dir \
  --tasks stats,inbreeding,visual \
  --cand "G5_F01_001,G5_F01_002" \
  --trace up --tracegen 3 \
  --compact --showf \
  --output /tmp/ped_cand

# Relationship matrix (optional full export)
python skills/pedigree-analysis/pedigree_analysis.py \
  --input /path/to/input_dir \
  --tasks matrix \
  --mat-method A --mat-compact --export-matrix \
  --output /tmp/ped_matrix

# Generation interval
python skills/pedigree-analysis/pedigree_analysis.py \
  --input /path/to/input_dir \
  --tasks interval \
  --timevar Year \
  --output /tmp/ped_interval
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--input` | path | — | 输入目录 *(KunLib 框架自动注入)* |
| `--output` | path | required | 输出目录 *(KunLib 框架自动注入)* |
| `--demo` | flag | false | 使用合成水产系谱（5代 × 30家系 × 30个体，含近交） |
| `--pedigree-file` | str | `pedigree.csv` | 输入目录中的系谱 CSV 文件名 *(由 `input_schema` 自动生成)* |
| `--tasks` | str | `stats,inbreeding,visual` | 逗号分隔的分析模块；`all` 运行全部7个模块 |
| `--cand` | str | — | 候选个体 ID（逗号分隔），为空则分析全部 |
| `--trace` | str | `up` | 候选追溯方向：`up` / `down` / `all` |
| `--tracegen` | int | — | 追溯代数；为空则全追溯 |
| `--timevar` | str | — | 时间列名（如 `Year`），`interval` 模块必需 |
| `--foundervar` | str | — | 血统标记列名（如 `Line`），`ancestry` 模块必需 |
| `--reference` | str | — | 多样性分析参考个体 ID（逗号分隔）；默认取最新世代 |
| `--top` | int | `20` | `diversity` 模块显示 Top N 奠基者/祖先 |
| `--mat-method` | str | `A` | 关系矩阵类型：`A` / `D` / `AA` / `Ainv` / `Dinv` / `AAinv` |
| `--mat-compact` | flag | false | 矩阵计算启用全同胞压缩（加速大系谱） |
| `--export-matrix` | flag | false | 导出完整关系矩阵 CSV（默认仅热图） |
| `--compact` | flag | false | `visped` 全同胞压缩显示 |
| `--highlight` | str | — | `visped` 高亮个体 ID |
| `--vis-trace` | str | `up` | `visped` 追溯高亮方向 |
| `--showf` | flag | false | `visped` 节点显示近交系数 |
| `--fig-format` | str | `pdf` | 系谱图格式：`pdf`（矢量，推荐大系谱）或 `png` |
| `--fig-width` | int | `12` | 图形宽度（英寸，仅 `png` 有效） |
| `--fig-height` | int | `10` | 图形高度（英寸，仅 `png` 有效） |
| `--inbreed-breaks` | str | `0.0625,0.125,0.25` | 近交分级阈值（逗号分隔） |
| `--threads` | int | `0` | 矩阵计算线程数（0 = 自动） |

## Module Reference

| Module | Trigger | Key Outputs | Pre-requisite |
|--------|---------|-------------|---------------|
| `stats` | always available | `pedstats_summary.csv`, `pedstats_ecg.csv`, `subpopulation.csv`, `ecg_plot.png` | — |
| `inbreeding` | always available | `inbreeding.csv`, `inbreeding_class.csv` | — |
| `interval` | requires `--timevar` | `gen_intervals.csv` | Time column in pedigree |
| `diversity` | always available | `diversity_summary.csv`, `founder_contrib.csv`, `ancestor_contrib.csv` | — |
| `ancestry` | requires `--foundervar` | `ancestry_proportions.csv` | Founder-group column in pedigree |
| `matrix` | always available | `matrix_summary.csv`, `matrix_heatmap.png` (+ optional `amat.csv`) | — |
| `visual` | always available | `pedigree.pdf` or `pedigree.png` | — |

> `interval` and `ancestry` modules are silently skipped if their required column is absent — no error is raised.

## Methodology

### Pedigree Standardisation (`tidyped`)
- Detects duplicate IDs and pedigree loops
- Adds missing founders as unlinked individuals
- Assigns virtual generations (top-down by default)
- Infers sex from pedigree structure if `Sex` column absent

### Inbreeding (`inbreed`)
- Algorithm: Sargolzaei & Iwaisaki (2005) — LAP bucket method, C++ via Rcpp/RcppArmadillo
- Scales to > 1 million individuals

### Generation Intervals (`pedgenint`)
- Four gametic pathways: SS, SD, DS, DD
- Numeric `Year` treated as mid-year date automatically

### Genetic Diversity (`pediv`)
- $f_e = \frac{1}{\sum_{k} q_k^2}$ (effective founders)
- $f_a$ via Boichard et al. (1997) marginal contributions
- Gene Diversity $= 1 - \bar{f}$ (mean kinship among reference individuals)

### Relationship Matrices (`pedmat`)
- **A**: Henderson (1976) tabular method
- **D**: Cockerham (1954) method
- **AA**: Hadamard product $A \odot A$
- Compact mode collapses full-sib families → dramatically reduces memory for aquaculture pedigrees with large full-sib groups

## Dependencies

### System Binaries

| Binary | Version | Install Method | Notes |
|--------|---------|----------------|-------|
| `Rscript` | ≥ 4.2 (建议 4.4+) | `conda install -c conda-forge r-base` | R 脚本运行环境 |

### R Packages

| Package | Version | Install Method | Notes |
|---------|---------|----------------|-------|
| `visPedigree` | ≥ 1.8.0 | `install.packages("visPedigree")` | 核心系谱分析包（CRAN 稳定版） |
| `data.table` | — | `install.packages("data.table")` | 高性能表格操作 |
| `jsonlite` | — | `install.packages("jsonlite")` | R→Python JSON 通信 |
| `igraph` | — | 随 visPedigree 自动安装 | 系谱图布局（间接依赖） |
| `lattice` | — | R 内置包 | vismat 返回 trellis 对象（间接依赖） |

### Python Packages

*(此技能不需要额外的 Python 包，仅用标准库)*

### Bioconductor Packages

*(此技能不需要 Bioconductor 包)*

## Output Structure

```
output_dir/
├── report.md
├── result.json
├── work/
│   └── demo_ped.csv              # demo 模式下的合成系谱
├── tables/
│   ├── tidyped.csv               # 始终输出
│   ├── pedstats_summary.csv      # stats
│   ├── pedstats_ecg.csv          # stats
│   ├── subpopulation.csv         # stats
│   ├── inbreeding.csv            # inbreeding
│   ├── inbreeding_class.csv      # inbreeding
│   ├── gen_intervals.csv         # interval
│   ├── diversity_summary.csv     # diversity
│   ├── founder_contrib.csv       # diversity
│   ├── ancestor_contrib.csv      # diversity
│   ├── ancestry_proportions.csv  # ancestry
│   ├── matrix_summary.csv        # matrix
│   └── amat.csv                  # matrix (--export-matrix only)
├── figures/
│   ├── pedigree.pdf              # visual (default)
│   ├── ecg_plot.png              # stats
│   └── matrix_heatmap.png        # matrix
├── logs/
└── reproducibility/
    └── commands.sh
```

## Safety

- **Local-first**: All computation runs locally; no data is uploaded
- **Disclaimer**: Research tool only — validate results with domain experts before use in production breeding programs
- **Reproducibility**: Full command log in `reproducibility/commands.sh`
- **Graceful degradation**: Modules lacking required inputs are silently skipped and logged in `result.json`

## References

1. Luan, S. (2026). visPedigree: Tidying, Analysis, and Fast Visualization of Animal and Plant Pedigrees. R package v1.8.1. https://github.com/luansheng/visPedigree
2. Wright, S. (1922). Coefficients of inbreeding and relationship. *American Naturalist*, 56, 330–338.
3. Sargolzaei, M., & Iwaisaki, H. (2005). A fast algorithm for computing inbreeding coefficients in large populations. *Journal of Animal Breeding and Genetics*, 122(5), 325–331.
4. Boichard, D., Maignel, L., & Verrier, E. (1997). The value of using probabilities of gene origin to measure genetic variability in a population. *Genetics Selection Evolution*, 29(1), 5.
5. Henderson, C. R. (1976). A simple method for computing the inverse of a numerator relationship matrix. *Biometrics*, 32(1), 69–83.
