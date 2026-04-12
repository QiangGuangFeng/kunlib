"""KunLib Skill SDK — 声明式技能注册框架。

开发者在技能主脚本中使用 @skill 装饰器即可完成:
  1. 元信息注册（name, tags, trigger_keywords, params...）
  2. argparse 自动构建
  3. CLI 入口 (run_cli)
  4. 被 kunlib CLI / agent adapter 发现和调用
"""
from __future__ import annotations

import argparse
import functools
import inspect
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from kunlib.result import KunResult


@dataclass
class Param:
    """技能参数声明。

    name 使用 kebab-case (e.g. "trait-pos")，与 CLI flag 一致。
    argparse 会自动将其转为 snake_case 属性 (args.trait_pos)。
    """
    name: str
    type: type = str
    required: bool = False
    default: Any = None
    help: str = ""
    is_flag: bool = False


@dataclass
class SkillMeta:
    """技能元信息，由 @skill 装饰器自动填充。"""
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    trigger_keywords: list[str] = field(default_factory=list)
    chaining_partners: list[str] = field(default_factory=list)
    input_formats: list[str] = field(default_factory=list)
    requires_bins: list[str] = field(default_factory=list)
    emoji: str = "🧬"
    params: list[Param] = field(default_factory=list)
    script_path: Path | None = None
    has_demo: bool = False
    entry_func: Callable | None = None

    def build_parser(self) -> argparse.ArgumentParser:
        """从 self.params 自动构建 ArgumentParser。"""
        parser = argparse.ArgumentParser(
            prog=f"kunlib run {self.name}",
            description=self.description,
        )
        for p in self.params:
            flag = f"--{p.name}"
            if p.is_flag:
                parser.add_argument(flag, action="store_true", default=False, help=p.help)
            else:
                kw: dict[str, Any] = {"type": p.type, "help": p.help, "default": p.default}
                if p.required:
                    kw["required"] = True
                parser.add_argument(flag, **kw)
        return parser

    def run_cli(self, argv: list[str] | None = None) -> KunResult | None:
        """解析命令行参数 → 执行 entry_func → 保存并打印结果。

        脚本的 if __name__ == "__main__" 直接调用此方法即可。
        argv=None 时读 sys.argv，测试时可传入自定义参数列表。
        """
        parser = self.build_parser()
        args = parser.parse_args(argv)
        result = self.entry_func(args)
        if isinstance(result, KunResult):
            result.save()
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return result


# --------------------------------------------------------------------------- #
# Global registry
# --------------------------------------------------------------------------- #

_SKILL_REGISTRY: dict[str, SkillMeta] = {}


def get_registry() -> dict[str, SkillMeta]:
    """返回当前进程中所有已注册的技能。"""
    return _SKILL_REGISTRY


def skill(
    name: str,
    *,
    version: str = "0.1.0",
    description: str = "",
    author: str = "",
    tags: list[str] | None = None,
    trigger_keywords: list[str] | None = None,
    chaining_partners: list[str] | None = None,
    input_formats: list[str] | None = None,
    requires_bins: list[str] | None = None,
    emoji: str = "🧬",
    params: list[Param] | None = None,
):
    """技能注册装饰器 —— 开发者唯一需要使用的接口。

    用法::

        @skill(
            name="hiblup-ebv",
            version="0.1.0",
            description="GBLUP breeding values via HI-BLUP",
            params=[
                Param("input", help="Input directory"),
                Param("output", required=True, help="Output directory"),
                Param("demo", is_flag=True, help="Run with synthetic data"),
            ],
        )
        def run(args: argparse.Namespace) -> KunResult:
            ...

        if __name__ == "__main__":
            run.__kunlib_meta__.run_cli()
    """
    def decorator(func: Callable) -> Callable:
        meta = SkillMeta(
            name=name,
            version=version,
            description=description,
            author=author,
            tags=tags or [],
            trigger_keywords=trigger_keywords or [],
            chaining_partners=chaining_partners or [],
            input_formats=input_formats or [],
            requires_bins=requires_bins or [],
            emoji=emoji,
            params=params or [],
            script_path=Path(inspect.getfile(func)).resolve(),
            has_demo=any(p.name == "demo" for p in (params or [])),
            entry_func=func,
        )
        _SKILL_REGISTRY[name] = meta

        @functools.wraps(func)
        def wrapper(*a, **kw):
            return func(*a, **kw)

        wrapper.__kunlib_meta__ = meta
        return wrapper

    return decorator
