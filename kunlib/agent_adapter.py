"""Agent 适配器 —— kunbreed / OpenClaw / 任意 agent 通过此接口集成 kunlib。"""
from __future__ import annotations

import argparse
import shutil
from typing import Any

from kunlib.catalog import _param_type_name
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
        deps = adapter.check_skill_deps("hiblup-ebv")  # 依赖检查
    """

    def __init__(self):
        discover_all()
        self.registry = get_registry()

    def get_skill_manifest(self) -> list[dict[str, Any]]:
        return [
            {
                "name": m.name,
                "kind": m.kind,
                "description": m.description,
                "trigger_keywords": m.trigger_keywords,
                "input_formats": m.input_formats,
                "has_demo": m.has_demo,
                "tags": m.tags,
                "requires": {
                    "bins": m.requires.bins,
                    "r_packages": m.requires.r_packages,
                    "python_packages": m.requires.python_packages,
                    "bioc_packages": m.requires.bioc_packages,
                },
                "input_schema": [
                    {
                        "name": f.name,
                        "format": f.format,
                        "required_fields": f.required_fields,
                        "dir": f.dir,
                        "description": f.description,
                    }
                    for f in m.input_schema
                ],
                "output_schema": [
                    {
                        "name": f.name,
                        "format": f.format,
                        "required_fields": f.required_fields,
                        "dir": f.dir,
                        "description": f.description,
                    }
                    for f in m.output_schema
                ],
                "params": [
                    {"name": p.name, "type": _param_type_name(p),
                     "required": p.required, "help": p.help, "is_flag": p.is_flag}
                    for p in m.params
                ],
            }
            for m in self.registry.values()
        ]

    def get_skill_docs(self) -> dict[str, str]:
        return get_skill_docs()

    def check_skill_deps(self, skill_name: str) -> dict[str, Any]:
        """检查技能所需依赖是否已安装。"""
        meta = self.registry.get(skill_name)
        if not meta:
            return {"error": f"Skill '{skill_name}' not found"}

        result: dict[str, Any] = {
            "bins": {},
            "summary": {"total": 0, "found": 0, "missing": 0},
        }

        for bin_name in meta.requires.bins:
            found = shutil.which(bin_name) is not None
            result["bins"][bin_name] = found
            result["summary"]["total"] += 1
            if found:
                result["summary"]["found"] += 1
            else:
                result["summary"]["missing"] += 1

        return result

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

        if "output" not in args_dict:
            return {"error": "'output' is required in args_dict"}

        ns = argparse.Namespace(**args_dict)
        ns = meta.prepare_env(ns)
        result = meta.entry_func(ns)

        if isinstance(result, KunResult):
            if result.kind == "data" and meta.kind != "data":
                result.kind = meta.kind
            if result.output_dir is None:
                result.output_dir = ns.output_dir
            result.save()
            return result.to_dict()
        return {"error": "Skill did not return KunResult"}
