"""Tests for lagm-mating skill."""
import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the skill module (folder name contains a hyphen, so normal import fails)
# ---------------------------------------------------------------------------
_SKILL_PY = Path(__file__).resolve().parent.parent / "skills" / "lagm-mating" / "lagm_mating.py"
_spec = importlib.util.spec_from_file_location("lagm_mating", _SKILL_PY)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export key names for convenience
_run = _mod.run
_validate_input = _mod._validate_input
_validate_id_index_sex = _mod._validate_id_index_sex
_REQUIRED_FILES = _mod.REQUIRED_FILES
_SKILL_DIR = _mod.SKILL_DIR


# ---------------------------------------------------------------------------
# Registration & metadata
# ---------------------------------------------------------------------------
class TestRegistration:
    def test_skill_registered(self):
        from kunlib.skill import get_registry
        assert "lagm-mating" in get_registry()

    def test_meta_name(self):
        assert _run.__kunlib_meta__.name == "lagm-mating"

    def test_meta_version(self):
        assert _run.__kunlib_meta__.version == "0.1.0"

    def test_meta_emoji(self):
        assert _run.__kunlib_meta__.emoji == "🐄"

    def test_meta_author(self):
        assert _run.__kunlib_meta__.author == "kzy599"

    def test_has_demo_flag(self):
        assert _run.__kunlib_meta__.has_demo is True


# ---------------------------------------------------------------------------
# CLI parser — --input and --output auto-injected by framework
# ---------------------------------------------------------------------------
class TestParser:
    def test_parse_demo(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--demo"])
        assert args.output == "/tmp/x"
        assert args.demo is True

    def test_has_input_flag(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--input", "/data"])
        assert args.input == "/data"

    def test_default_t(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.t == 3

    def test_parse_t(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--t", "5"])
        assert args.t == 5

    def test_default_n_crosses(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.n_crosses == 30

    def test_parse_n_crosses(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--n-crosses", "50"])
        assert args.n_crosses == 50

    def test_default_male_contribution_min(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.male_contribution_min == 2

    def test_default_male_contribution_max(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.male_contribution_max == 2

    def test_default_female_contribution_min(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.female_contribution_min == 1

    def test_default_female_contribution_max(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.female_contribution_max == 1

    def test_default_diversity_mode(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.diversity_mode == "genomic"

    def test_parse_diversity_mode(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--diversity-mode", "relationship"])
        assert args.diversity_mode == "relationship"

    def test_default_use_ped(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.use_ped is False

    def test_parse_use_ped(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--use-ped"])
        assert args.use_ped is True

    def test_default_n_iter(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.n_iter == 30000

    def test_default_n_pop(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.n_pop == 100

    def test_default_n_threads(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.n_threads == 8

    def test_default_swap_prob(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.swap_prob == 0.2

    def test_default_init_prob(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.init_prob == 0.8

    def test_default_cooling_rate(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.cooling_rate == 0.998

    def test_default_stop_window(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.stop_window == 2000

    def test_default_stop_eps(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.stop_eps == 1e-8

    def test_parse_id_index_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--id-index-sex-file", "my.csv"])
        assert args.id_index_sex_file == "my.csv"

    def test_default_id_index_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.id_index_sex_file == "id_index_sex.csv"

    def test_parse_geno_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--geno-file", "g.csv"])
        assert args.geno_file == "g.csv"

    def test_default_geno_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.geno_file == "geno.csv"

    def test_parse_ped_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--ped-file", "p.csv"])
        assert args.ped_file == "p.csv"

    def test_default_ped_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.ped_file == "ped.csv"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
class TestValidation:
    def test_missing_all(self, tmp_path):
        missing = _validate_input(tmp_path)
        assert set(missing) == set(_REQUIRED_FILES)

    def test_complete(self, tmp_path):
        for f in _REQUIRED_FILES:
            (tmp_path / f).write_text("ID,col2,col3\n1,0.5,M\n")
        assert _validate_input(tmp_path) == []

    def test_partial(self, tmp_path):
        (tmp_path / "id_index_sex.csv").write_text("ID,selindex,sex\n1,0.5,M\n")
        missing = _validate_input(tmp_path)
        assert "id_index_sex.csv" not in missing
        assert len(missing) == 1

    def test_validate_id_index_sex_valid(self, tmp_path):
        fpath = tmp_path / "id_index_sex.csv"
        fpath.write_text("ID,selindex,sex\n1,1.5,M\n2,2.0,F\n3,0.8,M\n")
        stats = _validate_id_index_sex(fpath)
        assert stats["n_candidates"] == 3
        assert stats["n_males"] == 2
        assert stats["n_females"] == 1

    def test_validate_id_index_sex_too_few_columns(self, tmp_path):
        fpath = tmp_path / "id_index_sex.csv"
        fpath.write_text("ID,selindex\n1,1.5\n")
        with pytest.raises(ValueError, match="at least 3 columns"):
            _validate_id_index_sex(fpath)


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------
class TestFiles:
    def test_skill_md_exists(self):
        assert (_SKILL_DIR / "SKILL.md").exists()

    def test_run_lagm_r_exists(self):
        assert (_SKILL_DIR / "run_lagm.r").exists()

    def test_generate_demo_r_exists(self):
        assert (_SKILL_DIR / "generate_demo.r").exists()

    def test_demogenerator_r_exists(self):
        assert (_SKILL_DIR / "demogenerator.r").exists()


# ---------------------------------------------------------------------------
# Discovery integration
# ---------------------------------------------------------------------------
class TestDiscovery:
    def test_discover_finds_skill(self):
        from kunlib.registry import discover_all
        registry = discover_all()
        assert "lagm-mating" in registry

    def test_skill_docs_include_skill(self):
        from kunlib.registry import discover_all, get_skill_docs
        discover_all()
        docs = get_skill_docs()
        assert "lagm-mating" in docs
        assert "KunLib" in docs["lagm-mating"]
