---
name: your-skill-name
description: >-
  One-line description of what this skill does.
version: 0.1.0
author: Your Name
tags: [tag1, tag2]
metadata:
  kunlib:
    kind: data  # data | generator | orchestrator | validator | info
    requires:
      bins: [python3]
      r_packages: []
      python_packages: []
      bioc_packages: []
    emoji: "🧬"
    trigger_keywords:
      - keyword that routes to this skill
    chaining_partners: []
    input_formats:
      - csv
    input_schema:       # data/validator kind 必填；generator/orchestrator/info kind 可省略
      - name: input.csv
        format: csv
        required_fields: [ID]
        description: 输入文件描述
    output_schema:      # 所有产出文件的 kind 都应声明；orchestrator/info kind 可省略
      - name: result.csv
        format: csv
        dir: tables
        description: 输出文件描述
---

# 🧬 Skill Name

You are **[Skill Name]**, a KunLib skill for [domain].

## Why This Exists

- **Without it**: [painful manual process]
- **With it**: [automated outcome]

## Core Capabilities

1. **Capability 1**: Description
2. **Capability 2**: Description

## Input Formats

> 根据 `kind` 调整此节。orchestrator/info 型可简化或删除此节。

| Format | Extension | Required Fields |
|--------|-----------|-----------------|
| Format 1 | `.ext` | field1, field2 |

## CLI Reference

```bash
# Via kunlib
kunlib run your-skill-name --demo --output /tmp/demo

# Direct
python skills/your-skill-name/your_skill.py --demo --output /tmp/demo

# With real data (data/validator kind)
python skills/your-skill-name/your_skill.py --input <dir> --output <dir>
```

## Parameters

> `--input` 和 `--output` 由框架根据 kind 自动注入，不需要在 `params=[]` 中声明。

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--input` | path | — | Input directory *(框架自动注入；仅 data=可选, validator=必需)* |
| `--output` | path | required | Output directory *(框架自动注入；所有 kind 必需)* |
| `--demo` | flag | false | Run with synthetic data |

## Dependencies

List every external dependency so users can install them before running the skill.

### System Binaries

| Binary | Version | Install Method | Notes |
|--------|---------|----------------|-------|
| `python3` | ≥ 3.9 | `conda install python=3.9` | Required by KunLib framework |

### R Packages

| Package | Version | Install Method | Notes |
|---------|---------|----------------|-------|
| — | — | — | *(remove this row and add entries if your skill uses R)* |

### Python Packages

| Package | Version | Install Method | Notes |
|---------|---------|----------------|-------|
| — | — | — | *(remove this row and add entries if your skill uses Python packages)* |

### Bioconductor Packages

| Package | Version | Install Method | Notes |
|---------|---------|----------------|-------|
| — | — | — | *(remove this row and add entries if your skill uses Bioconductor)* |

> **Install Method** should be one of:
>
> | Category | Example |
> |----------|---------|
> | conda / conda-forge / Bioconda | `conda install -c bioconda samtools` |
> | pip / PyPI | `pip install pandas` |
> | CRAN | `install.packages("data.table")` |
> | Bioconductor | `BiocManager::install("DESeq2")` |
> | GitHub (R) | `remotes::install_github("author/pkg")` — include full URL |
> | GitHub (CLI/C++) | `git clone https://github.com/... && make install` |
> | URL direct download | `wget https://example.com/tool-v1.0.tar.gz` |
> | System package manager | `apt install libhts-dev` / `brew install htslib` |
> | Manual download (licensed) | Provide official URL and note license restrictions |
>
> ⚠️ If a dependency requires **manual download due to licensing or commercial
> restrictions** (e.g., ASReml, FImpute, commercial chip annotation tools),
> clearly state this and provide the official download URL.

## Output Structure

> 根据 `kind` 选择对应的输出结构。

**data / generator:**

```
output_dir/
├── report.md
├── result.json
├── work/
├── tables/
│   └── results.csv
├── figures/
├── logs/
└── reproducibility/
    └── commands.sh
```

**validator:**

```
output_dir/
├── result.json
├── logs/
└── tables/
    └── validation_report.csv
```

**orchestrator:**

```
output_dir/
├── result.json
├── logs/
│   └── pipeline.log
├── 01_skill-a/
│   └── (sub-skill full output)
└── 02_skill-b/
    └── (sub-skill full output)
```

**info:**

```
output_dir/
├── result.json
└── logs/
    └── info.log
```

## Safety

- **Local-first**: All computation runs locally
- **Disclaimer**: Research tool only
- **Reproducibility**: Full command log
