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
    requires:
      bins: [python3, Rscript]
      packages: [data.table]
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
| `--input` | path | — | Input directory containing CSV files |
| `--output` | path | required | Output directory |
| `--demo` | flag | false | Run with synthetic demo data |
| `--trait-pos` | int | 2 | Column index (1-based) of the target trait in `phe.csv` |

## Output Structure

```
output_dir/
├── report.md
├── result.json
├── phe_ebv.csv
├── sel_ebv.csv
├── ref_ebv.csv
└── reproducibility/
    └── commands.sh
```

## Safety

- **Local-first**: All computation runs locally via R
- **Disclaimer**: Research tool only — results must be validated by domain experts
- **Reproducibility**: Full command log in `reproducibility/commands.sh`
