"""Tests for hiblup-ebv skill."""
import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the skill module (folder name contains a hyphen, so normal import fails)
# ---------------------------------------------------------------------------
_SKILL_PY = Path(__file__).resolve().parent.parent / "skills" / "hiblup-ebv" / "hiblup_ebv.py"
_spec = importlib.util.spec_from_file_location("hiblup_ebv", _SKILL_PY)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export key names for convenience
_run = _mod.run
_validate_input = _mod._validate_input
_REQUIRED_FILES = _mod.REQUIRED_FILES
_SKILL_DIR = _mod.SKILL_DIR


# ---------------------------------------------------------------------------
# Registration & metadata
# ---------------------------------------------------------------------------
class TestRegistration:
    def test_skill_registered(self):
        from kunlib.skill import get_registry
        assert "hiblup-ebv" in get_registry()

    def test_meta_name(self):
        assert _run.__kunlib_meta__.name == "hiblup-ebv"

    def test_meta_version(self):
        assert _run.__kunlib_meta__.version == "0.1.0"

    def test_meta_emoji(self):
        assert _run.__kunlib_meta__.emoji == "🐄"

    def test_meta_author(self):
        assert _run.__kunlib_meta__.author == "kzy599"

    def test_has_demo_flag(self):
        assert _run.__kunlib_meta__.has_demo is True


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------
class TestParser:
    def test_parse_demo(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--demo"])
        assert args.output == "/tmp/x"
        assert args.demo is True

    def test_parse_trait_pos(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--trait-pos", "3"])
        assert args.trait_pos == 3

    def test_default_trait_pos(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.trait_pos == 2


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
class TestValidation:
    def test_missing_all(self, tmp_path):
        missing = _validate_input(tmp_path)
        assert set(missing) == set(_REQUIRED_FILES)

    def test_complete(self, tmp_path):
        for f in _REQUIRED_FILES:
            (tmp_path / f).write_text("ID\n1\n")
        assert _validate_input(tmp_path) == []

    def test_partial(self, tmp_path):
        (tmp_path / "phe.csv").write_text("ID\n1\n")
        missing = _validate_input(tmp_path)
        assert "phe.csv" not in missing
        assert len(missing) == 3


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------
class TestFiles:
    def test_skill_md_exists(self):
        assert (_SKILL_DIR / "SKILL.md").exists()

    def test_filegenerator_r_exists(self):
        assert (_SKILL_DIR / "filegenerator.r").exists()

    def test_run_hiblup_r_exists(self):
        assert (_SKILL_DIR / "run_hiblup.r").exists()


# ---------------------------------------------------------------------------
# Discovery integration
# ---------------------------------------------------------------------------
class TestDiscovery:
    def test_discover_finds_skill(self):
        from kunlib.registry import discover_all
        registry = discover_all()
        assert "hiblup-ebv" in registry

    def test_skill_docs_include_skill(self):
        from kunlib.registry import discover_all, get_skill_docs
        discover_all()
        docs = get_skill_docs()
        assert "hiblup-ebv" in docs
        assert "KunLib" in docs["hiblup-ebv"]
