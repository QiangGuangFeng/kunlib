"""KunLib CLI 入口。

    kunlib list
    kunlib run <skill> [skill args...]
    kunlib catalog
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from kunlib.registry import discover_all, KUNLIB_SKILLS_DIR
from kunlib.skill import get_registry

PYTHON = sys.executable


def main():
    top = argparse.ArgumentParser(prog="kunlib", description="KunLib — Genetic Breeding Skill Library")
    sub = top.add_subparsers(dest="command")

    sub.add_parser("list", help="List all registered skills")
    sub.add_parser("catalog", help="Generate catalog.json")

    run_p = sub.add_parser("run", help="Run a skill")
    run_p.add_argument("skill_name", help="Skill name (e.g. hiblup-ebv)")

    args, remaining = top.parse_known_args()

    discover_all()
    registry = get_registry()

    if args.command == "list":
        _cmd_list(registry)
    elif args.command == "catalog":
        from kunlib.catalog import generate_catalog
        print(f"Generated: {generate_catalog(registry)}")
    elif args.command == "run":
        _cmd_run(args.skill_name, remaining, registry)
    else:
        top.print_help()


def _cmd_list(registry):
    print(f"\n{'='*60}")
    print(f"  KunLib Skills  ({len(registry)} registered)")
    print(f"{'='*60}\n")
    for name, meta in sorted(registry.items()):
        demo = " [demo]" if meta.has_demo else ""
        ok = "OK" if meta.script_path and meta.script_path.exists() else "MISSING"
        print(f"  {meta.emoji} {name:30s} v{meta.version}{demo}  [{ok}]")
        print(f"     {meta.description}")
        print()
    print("  Run:    kunlib run <skill> --demo --output /tmp/out")
    print("  Direct: python skills/<skill>/<script>.py --demo --output /tmp/out\n")


def _cmd_run(skill_name: str, passthrough: list[str], registry):
    """subprocess 调用技能脚本，透传所有参数。"""
    meta = registry.get(skill_name)
    if not meta:
        print(f"Error: skill '{skill_name}' not found. Available: {', '.join(sorted(registry))}")
        sys.exit(1)
    if not meta.script_path or not meta.script_path.exists():
        print(f"Error: script not found for '{skill_name}'")
        sys.exit(1)
    cmd = [PYTHON, str(meta.script_path)] + passthrough
    sys.exit(subprocess.run(cmd, cwd=str(meta.script_path.parent)).returncode)


if __name__ == "__main__":
    main()
