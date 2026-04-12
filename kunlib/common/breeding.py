"""育种专用工具函数（占位，后续扩展）。"""
from __future__ import annotations


def grm_from_genotypes(geno_matrix):
    """从基因型矩阵计算 G 矩阵（占位）。"""
    raise NotImplementedError("GRM computation to be implemented")


def selection_index(ebvs: dict[str, float], weights: dict[str, float]) -> float:
    """综合选择指数。"""
    return sum(ebvs.get(trait, 0.0) * w for trait, w in weights.items())
