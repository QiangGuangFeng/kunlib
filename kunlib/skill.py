"""KunLib Skill SDK — 声明式技能注册框架。

开发者在技能主脚本中使用 @skill 装饰器即可完成:
  1. 元信息注册（name, tags, trigger_keywords, params...）
  2. argparse 自动构建（自动注入 --input / --output）
  3. 标准输出目录结构自动创建
  4. CLI 入口 (run_cli)
  5. 被 kunlib CLI / agent adapter 发现和调用
"""
from __future__ import annotations

import argparse
import functools
import inspect
import json
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable

from kunlib.result import KunResult


# 框架自动创建的标准子目录名
STANDARD_DIRS = ("work", "tables", "figures", "logs", "reproducibility")

# 框架保留的参数名，开发者在 params 中声明会被静默跳过
_RESERVED_PARAMS = {"input", "output"}

# 技能类型
SKILL_KINDS = ("data", "generator", "orchestrator", "validator", "info")

# 每种 kind 自动创建的子目录
KIND_DIRS: dict[str, tuple[str, ...]] = {
    "data":         ("work", "tables", "figures", "logs", "reproducibility"),
    "generator":    ("work", "tables", "figures", "logs", "reproducibility"),
    "orchestrator": ("logs",),
    "validator":    ("logs", "tables"),
    "info":         ("logs",),
}

# 每种 kind 的 --input 注入策略
KIND_INPUT: dict[str, dict[str, bool]] = {
    "data":         {"inject": True,  "required": False},
    "generator":    {"inject": False, "required": False},
    "orchestrator": {"inject": False, "required": False},
    "validator":    {"inject": True,  "required": True},
    "info":         {"inject": False, "required": False},
}


@dataclass
class Param:
    """技能参数声明。

    name 使用 kebab-case (e.g. "trait-pos")，与 CLI flag 一致。
    argparse 会自动将其转为 snake_case 属性 (args.trait_pos)。

    注意: "input" 和 "output" 由框架自动注入，不需要声明。
    """
    name: str
    type: type = str
    required: bool = False
    default: Any = None
    help: str = ""
    is_flag: bool = False


@dataclass
class SkillRequires:
    """技能依赖声明。"""
    bins: list[str] = field(default_factory=list)
    r_packages: list[str] = field(default_factory=list)
    python_packages: list[str] = field(default_factory=list)
    bioc_packages: list[str] = field(default_factory=list)


@dataclass
class IOField:
    """输入/输出文件声明。"""
    name: str                                                        # 文件名或 pattern
    format: str = ""                                                 # csv, vcf, bed, png 等
    required_fields: list[str] = field(default_factory=list)        # 必需字段/列名
    dir: str = ""                                                    # 输出子目录 (tables, figures 等)
    description: str = ""


def _iofield_to_flag(name: str) -> str:
    """IOField.name → CLI flag name (without --)

    规则: 去掉扩展名 → 下划线转连字符 → 加 '-file' 后缀

    Examples:
      "phe.csv"            → "phe-file"
      "geno.csv"           → "geno-file"
      "sel_id.csv"         → "sel-id-file"
      "id_index_sex.csv"   → "id-index-sex-file"
      "ped.csv"            → "ped-file"
    """
    stem = name.rsplit('.', 1)[0]        # "sel_id.csv" → "sel_id"
    kebab = stem.replace('_', '-')       # "sel_id" → "sel-id"
    return f"{kebab}-file"               # "sel-id" → "sel-id-file"


@dataclass
class SkillMeta:
    """技能元信息，由 @skill 装饰器自动填充。"""
    name: str
    kind: str = "data"
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    trigger_keywords: list[str] = field(default_factory=list)
    chaining_partners: list[str] = field(default_factory=list)
    input_formats: list[str] = field(default_factory=list)
    requires: SkillRequires = field(default_factory=SkillRequires)
    emoji: str = "🧬"
    params: list[Param] = field(default_factory=list)
    input_schema: list[IOField] = field(default_factory=list)
    output_schema: list[IOField] = field(default_factory=list)
    script_path: Path | None = None
    has_demo: bool = False
    entry_func: Callable | None = None

    @property
    def requires_bins(self) -> list[str]:
        """向后兼容：返回 requires.bins。"""
        return self.requires.bins

    def build_parser(self) -> argparse.ArgumentParser:
        """从 self.params 自动构建 ArgumentParser。

        框架自动注入:
          --output  输出目录（必需，所有 kind 均注入）
          --input   输入目录（根据 kind 决定是否注入及是否 required）

        根据 input_schema 自动生成 --xxx-file 参数（仅当 --input 被注入时）。
        """
        parser = argparse.ArgumentParser(
            prog=f"kunlib run {self.name}",
            description=self.description,
        )
        # ---- --output 永远必需 ----
        parser.add_argument("--output", required=True, help="Output directory (required)")

        # ---- --input 根据 kind 决定是否注入及是否 required ----
        input_cfg = KIND_INPUT[self.kind]
        if input_cfg["inject"]:
            parser.add_argument(
                "--input",
                required=input_cfg["required"],
                help="Input directory containing all required input files for this skill",
            )

        # ---- 根据 input_schema 自动生成 --xxx-file 参数 ----
        self._auto_input_params: set[str] = set()
        if input_cfg["inject"] and self.input_schema:
            for iof in self.input_schema:
                flag_name = _iofield_to_flag(iof.name)
                if flag_name in _RESERVED_PARAMS:
                    continue
                self._auto_input_params.add(flag_name)
                parser.add_argument(
                    f"--{flag_name}",
                    type=str,
                    default=iof.name,
                    help=f"Filename within --input directory: {iof.description}" if iof.description else f"Filename within --input directory (default: {iof.name})",
                )

        # ---- 技能自定义参数 ----
        for p in self.params:
            if p.name in _RESERVED_PARAMS:
                continue  # 由框架注入，跳过
            if p.name in self._auto_input_params:
                continue  # 由框架从 input_schema 自动生成，跳过开发者的重复声明
            flag = f"--{p.name}"
            if p.is_flag:
                parser.add_argument(flag, action="store_true", default=False, help=p.help)
            else:
                kw: dict[str, Any] = {"type": p.type, "help": p.help, "default": p.default}
                if p.required:
                    kw["required"] = True
                parser.add_argument(flag, **kw)
        return parser

    def prepare_env(self, args: argparse.Namespace) -> argparse.Namespace:
        """创建标准输出目录结构并注入 args.*_dir 属性。

        要求 args 中已有 args.output (str)。
        根据 self.kind 创建对应子目录，注入:
          args.output_dir, args.logs_dir, args.work_dir,
          args.tables_dir, args.figures_dir, args.repro_dir
        未创建的目录注入为 None。
        """
        output_dir = Path(args.output).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
          # resolve --input to absolute path (defense against cwd changes in subprocesses)
        if getattr(args, "input", None) is not None:
            args.input = str(Path(args.input).resolve())

        dirs: dict[str, Path] = {}
        for d in KIND_DIRS[self.kind]:
            p = output_dir / d
            p.mkdir(exist_ok=True)
            dirs[d] = p

        args.output_dir = output_dir
        args.logs_dir = dirs["logs"]
        args.work_dir    = dirs.get("work")
        args.tables_dir  = dirs.get("tables")
        args.figures_dir = dirs.get("figures")
        args.repro_dir   = dirs.get("reproducibility")
        return args

    def run_cli(self, argv: list[str] | None = None) -> KunResult:
        """解析命令行参数 → 准备标准目录 → 执行 entry_func → 保存结果。

        框架根据 kind 创建对应的输出目录结构:
          所有 kind 都保证:
            output/
            ├── logs/              运行日志
            └── result.json        框架自动写

          data / generator 额外创建:
            ├── work/              中间/临时文件
            ├── tables/            最终表格
            ├── figures/           最终图片
            └── reproducibility/   复现指令

          validator 额外创建:
            └── tables/            校验报告

        技能通过 args.output_dir / args.work_dir / args.tables_dir /
        args.figures_dir / args.logs_dir / args.repro_dir 访问这些目录。
        未创建的目录属性注入为 None。
        """
        parser = self.build_parser()
        args = parser.parse_args(argv)
        args = self.prepare_env(args)

        # ---- 执行技能 ----
        result = self.entry_func(args)

        # ---- 校验返回值 ----
        if not isinstance(result, KunResult):
            raise TypeError(
                f"[{self.name}] run() must return KunResult, got {type(result).__name__}"
            )

        # 自动补全 kind（技能可以不手动设置，框架从 meta 补上）
        if result.kind == "data" and self.kind != "data":
            result.kind = self.kind

        # 自动补全 output_dir
        if result.output_dir is None:
            result.output_dir = args.output_dir

        # ---- 保存 result.json + 打印摘要 ----
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
    kind: str = "data",
    version: str = "0.1.0",
    description: str = "",
    author: str = "",
    tags: list[str] | None = None,
    trigger_keywords: list[str] | None = None,
    chaining_partners: list[str] | None = None,
    input_formats: list[str] | None = None,
    requires_bins: list[str] | None = None,
    requires: SkillRequires | None = None,
    input_schema: list[IOField] | None = None,
    output_schema: list[IOField] | None = None,
    emoji: str = "🧬",
    params: list[Param] | None = None,
):
    """技能注册装饰器 —— 开发者唯一需要使用的接口。

    --input 和 --output 由框架自动注入，开发者只需声明技能特有的参数。

    用法::

        @skill(
            name="hiblup-ebv",
            version="0.1.0",
            description="GBLUP breeding values via HI-BLUP",
            params=[
                Param("demo", is_flag=True, help="Run with synthetic data"),
                Param("trait-pos", type=int, default=2, help="Trait column"),
            ],
        )
        def run(args: argparse.Namespace) -> KunResult:
            # 框架自动提供:
            #   args.input       输入目录路径（仅 data/validator kind）
            #   args.output      输出路径字符串
            #   args.output_dir  输出 Path 对象
            #   args.work_dir    中间文件目录
            #   args.tables_dir  最终表格目录
            #   args.figures_dir 最终图片目录
            #   args.logs_dir    日志目录
            #   args.repro_dir   复现指令目录
            ...

        if __name__ == "__main__":
            run.__kunlib_meta__.run_cli()
    """
    def decorator(func: Callable) -> Callable:
        if kind not in SKILL_KINDS:
            raise ValueError(f"Invalid skill kind '{kind}', must be one of {SKILL_KINDS}")

        # Merge requires_bins (legacy) into requires.bins
        effective_requires = requires if requires is not None else SkillRequires()
        if requires_bins:
            merged_bins = list(dict.fromkeys(effective_requires.bins + requires_bins))
            effective_requires = replace(effective_requires, bins=merged_bins)

        meta = SkillMeta(
            name=name,
            kind=kind,
            version=version,
            description=description,
            author=author,
            tags=tags or [],
            trigger_keywords=trigger_keywords or [],
            chaining_partners=chaining_partners or [],
            input_formats=input_formats or [],
            requires=effective_requires,
            emoji=emoji,
            params=params or [],
            input_schema=input_schema or [],
            output_schema=output_schema or [],
            script_path=Path(inspect.getfile(func)).resolve(),
            has_demo=any(p.name == "demo" and p.is_flag for p in (params or [])),
            entry_func=func,
        )
        _SKILL_REGISTRY[name] = meta

        @functools.wraps(func)
        def wrapper(*a, **kw):
            return func(*a, **kw)

        wrapper.__kunlib_meta__ = meta
        return wrapper

    return decorator
