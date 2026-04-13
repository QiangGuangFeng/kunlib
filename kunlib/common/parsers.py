"""通用数据解析器（VCF header, PLINK .fam, CSV 表型等）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def detect_format(filepath: str | Path) -> str:
    """根据扩展名和文件头推断数据格式。"""
    p = Path(filepath)
    suffixes = "".join(p.suffixes).lower()
    if ".vcf" in suffixes:
        return "vcf"
    if p.suffix.lower() == ".fam":
        return "plink-fam"
    if p.suffix.lower() in (".bed",):
        return "plink-bed"
    if p.suffix.lower() in (".csv", ".tsv"):
        return "tabular"
    return "unknown"


def read_csv_header(filepath: str | Path, sep: str = ",") -> list[str]:
    """读取 CSV/TSV 首行作为列名。"""
    with open(filepath, encoding="utf-8") as f:
        return [c.strip() for c in f.readline().strip().split(sep)]
