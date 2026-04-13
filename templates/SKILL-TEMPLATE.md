---
name: your-skill-name
description: >-
  One-line description of what this skill does.
version: 0.1.0
author: Your Name
tags: [tag1, tag2]
metadata:
  kunlib:
    requires:
      bins: [python3]
    emoji: "🧬"
    trigger_keywords:
      - keyword that routes to this skill
    chaining_partners: []
    input_formats:
      - csv
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

| Format | Extension | Required Fields |
|--------|-----------|-----------------|
| Format 1 | `.ext` | field1, field2 |

## CLI Reference

```bash
# Via kunlib
kunlib run your-skill-name --demo --output /tmp/demo

# Direct
python skills/your-skill-name/your_skill.py --demo --output /tmp/demo

# With real data
python skills/your-skill-name/your_skill.py --input <file> --output <dir>
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--input` | path | — | Input file or directory |
| `--output` | path | required | Output directory |
| `--demo` | flag | false | Run with synthetic data |

## Output Structure

```
output_dir/
├── report.md
├── result.json
├── tables/
│   └── results.csv
└── reproducibility/
    └── commands.sh
```

## Safety

- **Local-first**: All computation runs locally
- **Disclaimer**: Research tool only
- **Reproducibility**: Full command log
