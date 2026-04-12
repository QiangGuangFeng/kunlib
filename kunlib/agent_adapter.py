"""Agent 适配器 —— kunbreed / OpenClaw / 任意 agent 通过此接口集成 kunlib。"""
from __future__ import annotations

import argparse
from typing import Any

from kunlib.registry import discover_all, get_skill_docs
from kunlib.skill import get_registry, SkillMeta
from kunlib.result import KunResult


class KunLibAdapter:
    """通用适配器。

    用法::

        adapter = KunLibAdapter()
        docs = adapter.get_skill_docs()           # SKILL.md 内容
        manifest = adapter.get_skill_manifest()    # 结构化清单
        result = adapter.run_skill("hiblup-ebv", {"demo": True, "output": "/tmp/out"})
    """

    def __init__(self):
        discover_all()
        self.registry = get_registry()

    def get_skill_manifest(self) -> list[dict[str, Any]]:
        return [
            {
                "name": m.name,
                "description": m.description,
                "trigger_keywords": m.trigger_keywords,
                "input_formats": m.input_formats,
                "has_demo": m.has_demo,
                "tags": m.tags,
                "params": [
                    {"name": p.name, "type": p.type.__name__ if isinstance(p.type, type) else str(p.type),
                     "required": p.required, "help": p.help, "is_flag": p.is_flag}
                    for p in m.params
                ],
            }
            for m in self.registry.values()
        ]

    def get_skill_docs(self) -> dict[str, str]:
        return get_skill_docs()

    def route(self, query: str) -> SkillMeta | None:
        query_lower = query.lower()
        best, best_score = None, 0
        for meta in self.registry.values():
            score = sum(1 for kw in meta.trigger_keywords if kw.lower() in query_lower)
            if score > best_score:
                best_score, best = score, meta
        return best

    def run_skill(self, skill_name: str, args_dict: dict[str, Any]) -> dict[str, Any]:
        meta = self.registry.get(skill_name)
        if not meta or not meta.entry_func:
            return {"error": f"Skill '{skill_name}' not found"}
        ns = argparse.Namespace(**args_dict)
        result = meta.entry_func(ns)
        if isinstance(result, KunResult):
            return result.to_dict()
        return {"error": "Skill did not return KunResult"}
