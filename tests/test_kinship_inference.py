"""Tests for kinship-inference skill."""
import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the skill module (folder name contains a hyphen, so normal import fails)
# ---------------------------------------------------------------------------
_SKILL_PY = Path(__file__).resolve().parent.parent / "skills" / "kinship-inference" / "kinship_inference.py"
_spec = importlib.util.spec_from_file_location("kinship_inference", _SKILL_PY)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export key names for convenience
_run = _mod.run
_validate_input = _mod._validate_input
_read_pipeline_summary = _mod._read_pipeline_summary
_REQUIRED_FILES = _mod.REQUIRED_FILES
_SKILL_DIR = _mod.SKILL_DIR


# ---------------------------------------------------------------------------
# Registration & metadata
# ---------------------------------------------------------------------------
class TestRegistration:
    def test_skill_registered(self):
        from kunlib.skill import get_registry
        assert "kinship-inference" in get_registry()

    def test_meta_name(self):
        assert _run.__kunlib_meta__.name == "kinship-inference"

    def test_meta_kind(self):
        assert _run.__kunlib_meta__.kind == "data"

    def test_meta_version(self):
        assert _run.__kunlib_meta__.version == "0.1.0"

    def test_meta_emoji(self):
        assert _run.__kunlib_meta__.emoji == "🔬"

    def test_meta_author(self):
        assert _run.__kunlib_meta__.author == "QGF"

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

    def test_parse_project_name(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--project-name", "TestProject"])
        assert args.project_name == "TestProject"

    def test_default_project_name(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.project_name == "KinshipInference"

    def test_parse_seed(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--seed", "42"])
        assert args.seed == 42

    def test_default_seed(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.seed == 1234

    def test_parse_species_type(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--species-type", "1"])
        assert args.species_type == 1

    def test_default_species_type(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.species_type == 2

    def test_parse_mating_system(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--mating-system", "1 1"])
        assert args.mating_system == "1 1"

    def test_default_mating_system(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.mating_system == "0 0"

    def test_parse_inference_method(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--inference-method", "2"])
        assert args.inference_method == 2

    def test_default_inference_method(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.inference_method == 1

    def test_parse_precision_level(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--precision-level", "3"])
        assert args.precision_level == 3

    def test_default_precision_level(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.precision_level == 2

    def test_parse_n_threads(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--n-threads", "8"])
        assert args.n_threads == 8

    def test_default_n_threads(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.n_threads == 45

    def test_parse_run_colony(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--run-colony"])
        assert args.run_colony is True

    def test_default_run_colony(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.run_colony is False

    def test_parse_snp_files(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--snp-files", "a.csv.gz,b.csv.gz"])
        assert args.snp_files == "a.csv.gz,b.csv.gz"

    def test_default_snp_files(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.snp_files == ""

    # Test auto-generated input_schema file params
    def test_parse_snp_offspring_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--snp-offspring-file", "my_off.csv"])
        assert args.snp_offspring_file == "my_off.csv"

    def test_default_snp_offspring_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.snp_offspring_file == "snp_offspring.csv"

    def test_parse_snp_parent_tag_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--snp-parent-tag-file", "parents.csv"])
        assert args.snp_parent_tag_file == "parents.csv"

    def test_default_snp_parent_tag_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.snp_parent_tag_file == "snp_parent_tag.csv"

    def test_parse_sample_info_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--SampleInfo-file", "info.csv"])
        assert args.SampleInfo_file == "info.csv"

    def test_default_sample_info_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.SampleInfo_file == "SampleInfo.csv"

    def test_parse_snp_list_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--snp-list-file", "my_snps.txt"])
        assert args.snp_list_file == "my_snps.txt"

    def test_default_snp_list_file(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.snp_list_file == "snp_list.txt"

    def test_parse_male_cand_prob(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--male-cand-prob", "0.8"])
        assert args.male_cand_prob == 0.8

    def test_default_male_cand_prob(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.male_cand_prob == 0.5

    def test_parse_dropout_rate(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--dropout-rate", "0.01"])
        assert args.dropout_rate == 0.01

    def test_default_dropout_rate(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.dropout_rate == 0.001

    def test_parse_error_rate(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--error-rate", "0.1"])
        assert args.error_rate == 0.1

    def test_default_error_rate(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.error_rate == 0.05


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
class TestValidation:
    def test_missing_all(self, tmp_path):
        missing = _validate_input(tmp_path)
        assert set(missing) == set(_REQUIRED_FILES)

    def test_complete(self, tmp_path):
        for f in _REQUIRED_FILES:
            (tmp_path / f).write_text("GenotypeID,Class\nID1,Offspring\n")
        assert _validate_input(tmp_path) == []

    def test_partial(self, tmp_path):
        (tmp_path / "SampleInfo.csv").write_text("GenotypeID,Class\nID1,Offspring\n")
        missing = _validate_input(tmp_path)
        assert "SampleInfo.csv" not in missing
        assert len(missing) == 0

    def test_custom_file_list(self, tmp_path):
        missing = _validate_input(tmp_path, ["a.csv", "b.csv"])
        assert set(missing) == {"a.csv", "b.csv"}

    def test_custom_file_partial(self, tmp_path):
        (tmp_path / "a.csv").write_text("data")
        missing = _validate_input(tmp_path, ["a.csv", "b.csv"])
        assert missing == ["b.csv"]


# ---------------------------------------------------------------------------
# Pipeline summary reading
# ---------------------------------------------------------------------------
class TestPipelineSummary:
    def test_read_summary_exists(self, tmp_path):
        summary_file = tmp_path / "pipeline_summary.csv"
        summary_file.write_text(
            "metric,value\nn_target_snps,1140\nn_offspring,100\nproject_name,Test\n"
        )
        result = _read_pipeline_summary(tmp_path)
        assert result["n_target_snps"] == 1140
        assert result["n_offspring"] == 100
        assert result["project_name"] == "Test"

    def test_read_summary_legacy_key_column(self, tmp_path):
        summary_file = tmp_path / "pipeline_summary.csv"
        summary_file.write_text(
            "key,value\nn_target_snps,1140\nn_offspring,100\nproject_name,Test\n"
        )
        result = _read_pipeline_summary(tmp_path)
        assert result["n_target_snps"] == 1140
        assert result["n_offspring"] == 100
        assert result["project_name"] == "Test"

    def test_read_summary_missing(self, tmp_path):
        result = _read_pipeline_summary(tmp_path)
        assert result == {}


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------
class TestFiles:
    def test_skill_md_exists(self):
        assert (_SKILL_DIR / "SKILL.md").exists()

    def test_functions_colony_r_exists(self):
        assert (_SKILL_DIR / "functions_colony.R").exists()

    def test_run_kinship_r_exists(self):
        assert (_SKILL_DIR / "run_kinship.R").exists()

    def test_demo_dir_exists(self):
        assert (_SKILL_DIR / "demo").is_dir()

    def test_demo_sample_info_exists(self):
        assert (_SKILL_DIR / "demo" / "SampleInfo.csv").exists()

    def test_demo_snp_list_exists(self):
        assert (_SKILL_DIR / "demo" / "1K位点.txt").exists()


# ---------------------------------------------------------------------------
# Discovery integration
# ---------------------------------------------------------------------------
class TestDiscovery:
    def test_discover_finds_skill(self):
        from kunlib.registry import discover_all
        registry = discover_all()
        assert "kinship-inference" in registry

    def test_skill_docs_include_skill(self):
        from kunlib.registry import discover_all, get_skill_docs
        discover_all()
        docs = get_skill_docs()
        assert "kinship-inference" in docs
        assert "KunLib" in docs["kinship-inference"]
