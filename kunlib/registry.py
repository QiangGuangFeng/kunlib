"""KunLib 技能自动发现 —— 扫描 skills/ 目录加载 @skill 装饰器。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from kunlib.skill import SkillMeta, get_registry

# kunlib 自带的 skills/ 目录
KUNLIB_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def discover_builtin_skills() -> dict[str, SkillMeta]:
    """扫描 kunlib 仓库自带的 skills/ 目录。"""
    return discover_skills_from_directory(KUNLIB_SKILLS_DIR)


def discover_skills_from_directory(skills_dir: Path) -> dict[str, SkillMeta]:
    """扫描指定目录：每个含 SKILL.md 的子目录视为技能。

    加载其中的 .py 文件会触发 @skill 装饰器执行，
    从而自动注册到全局 _SKILL_REGISTRY。
    """
    skills_dir = Path(skills_dir)
    if not skills_dir.exists():
        return get_registry()

    for folder in sorted(skills_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith((".", "_")):
            continue
        if not (folder / "SKILL.md").exists():
            continue
        for py_file in folder.glob("*.py"):
            if py_file.name.startswith("test_") or py_file.name == "__init__.py":
                continue
            _safe_load(py_file, folder.name)

    return get_registry()


def discover_skills_from_entry_points() -> dict[str, SkillMeta]:
    """通过 Python entry_points 发现第三方扩展技能。"""
    if sys.version_info >= (3, 12):
        from importlib.metadata import entry_points
        eps = entry_points(group="kunlib.skills")
    else:
        from importlib.metadata import entry_points
        all_eps = entry_points()
        eps = all_eps.get("kunlib.skills", [])

    for ep in eps:
        try:
            ep.load()
        except Exception as e:
            print(f"[kunlib] Warning: failed to load skill '{ep.name}': {e}", file=sys.stderr)

    return get_registry()


def discover_all() -> dict[str, SkillMeta]:
    """完整发现: 内置 skills/ + entry_points 扩展。"""
    discover_builtin_skills()
    discover_skills_from_entry_points()
    return get_registry()


def get_skill_docs() -> dict[str, str]:
    """读取所有已注册技能的 SKILL.md 内容，供 agent 学习。"""
    docs: dict[str, str] = {}
    for name, meta in get_registry().items():
        if meta.script_path:
            skill_md = meta.script_path.parent / "SKILL.md"
            if skill_md.exists():
                docs[name] = skill_md.read_text(encoding="utf-8")
    return docs


def _safe_load(py_file: Path, folder_name: str) -> None:
    try:
        mod_name = f"_kunlib_skill_{folder_name}_{py_file.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, py_file)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
    except Exception as e:
        print(f"[kunlib] Warning: failed to load {py_file}: {e}", file=sys.stderr)
