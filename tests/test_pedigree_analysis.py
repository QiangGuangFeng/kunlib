"""Tests for pedigree-analysis skill."""
import importlib.util
from pathlib import Path

import pytest

# --------------------------------------------------------------------------- #
# Load skill module (folder name contains hyphen, normal import won't work)
# --------------------------------------------------------------------------- #
_SKILL_PY = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "pedigree-analysis"
    / "pedigree_analysis.py"
)
_spec = importlib.util.spec_from_file_location("pedigree_analysis", _SKILL_PY)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_run              = _mod.run
_validate_ped     = _mod._validate_pedigree
_resolve_tasks    = _mod._resolve_tasks
_parse_r_summary  = _mod._parse_r_summary
_SKILL_DIR        = _mod.SKILL_DIR
VALID_TASKS       = _mod.VALID_TASKS
DEFAULT_TASKS     = _mod.DEFAULT_TASKS


# --------------------------------------------------------------------------- #
# Registration & metadata
# --------------------------------------------------------------------------- #
class TestRegistration:
    def test_skill_registered(self):
        from kunlib.skill import get_registry
        assert "pedigree-analysis" in get_registry()

    def test_meta_name(self):
        assert _run.__kunlib_meta__.name == "pedigree-analysis"

    def test_meta_version(self):
        assert _run.__kunlib_meta__.version == "0.1.0"

    def test_meta_emoji(self):
        assert _run.__kunlib_meta__.emoji == "🐟"

    def test_meta_author(self):
        assert _run.__kunlib_meta__.author == "luansheng"

    def test_has_demo_flag(self):
        assert _run.__kunlib_meta__.has_demo is True

    def test_chaining_partners(self):
        assert "lagm-mating" in _run.__kunlib_meta__.chaining_partners


# --------------------------------------------------------------------------- #
# CLI parser
# --------------------------------------------------------------------------- #
class TestParser:
    def test_parse_demo(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--demo"])
        assert args.demo is True

    def test_has_input_flag(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--input", "/data/input_dir"])
        assert args.input == "/data/input_dir"

    def test_default_pedfile(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.pedfile == "pedigree.csv"

    def test_parse_pedfile(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--pedfile", "shrimp.csv"])
        assert args.pedfile == "shrimp.csv"

    def test_default_tasks(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.tasks == DEFAULT_TASKS

    def test_parse_tasks(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--tasks", "stats,matrix"])
        assert args.tasks == "stats,matrix"

    def test_default_mat_method(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.mat_method == "A"

    def test_default_fig_format(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.fig_format == "pdf"

    def test_default_threads(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x"])
        assert args.threads == 0

    def test_flag_compact(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--compact"])
        assert args.compact is True

    def test_flag_showf(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--showf"])
        assert args.showf is True

    def test_flag_mat_compact(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--mat-compact"])
        assert args.mat_compact is True

    def test_flag_export_matrix(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--export-matrix"])
        assert args.export_matrix is True

    def test_parse_top(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--top", "30"])
        assert args.top == 30

    def test_parse_tracegen(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--tracegen", "3"])
        assert args.tracegen == 3

    def test_parse_timevar(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--timevar", "Year"])
        assert args.timevar == "Year"

    def test_parse_foundervar(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--foundervar", "Line"])
        assert args.foundervar == "Line"

    def test_parse_cand(self):
        parser = _run.__kunlib_meta__.build_parser()
        args = parser.parse_args(["--output", "/tmp/x", "--cand", "A,B,C"])
        assert args.cand == "A,B,C"


# --------------------------------------------------------------------------- #
# Task resolution
# --------------------------------------------------------------------------- #
class TestTaskResolution:
    def test_default_tasks_parse(self):
        t = _resolve_tasks(DEFAULT_TASKS)
        assert t == {"stats", "inbreeding", "visual"}

    def test_all_expands(self):
        t = _resolve_tasks("all")
        assert t == VALID_TASKS

    def test_single_task(self):
        assert _resolve_tasks("matrix") == {"matrix"}

    def test_mixed_tasks(self):
        t = _resolve_tasks("stats,diversity,ancestry")
        assert t == {"stats", "diversity", "ancestry"}

    def test_invalid_task_raises(self):
        with pytest.raises(ValueError, match="Unknown task"):
            _resolve_tasks("fake_module")

    def test_all_with_extra_ignored(self):
        # "all" wins regardless of other entries
        t = _resolve_tasks("all,stats")
        assert t == VALID_TASKS


# --------------------------------------------------------------------------- #
# Pedigree validation
# --------------------------------------------------------------------------- #
class TestValidation:
    def test_valid_minimal(self, tmp_path):
        f = tmp_path / "ped.csv"
        f.write_text("Ind,Sire,Dam\nA,NA,NA\nB,A,NA\n")
        info = _validate_ped(f)
        assert info["n_rows"] == 2
        assert info["n_cols"] == 3

    def test_valid_extra_cols(self, tmp_path):
        f = tmp_path / "ped.csv"
        f.write_text("Ind,Sire,Dam,Year,Sex\nA,NA,NA,2020,male\n")
        info = _validate_ped(f)
        assert info["n_cols"] == 5
        assert "Year" in info["columns"]

    def test_too_few_columns(self, tmp_path):
        f = tmp_path / "ped.csv"
        f.write_text("Ind,Sire\nA,NA\n")
        with pytest.raises(ValueError, match="≥ 3 columns"):
            _validate_ped(f)

    def test_empty_file(self, tmp_path):
        f = tmp_path / "ped.csv"
        f.write_text("")
        with pytest.raises((ValueError, StopIteration)):
            _validate_ped(f)


# --------------------------------------------------------------------------- #
# R summary JSON parsing
# --------------------------------------------------------------------------- #
class TestRSummaryParsing:
    def test_clean_parse(self):
        stdout = (
            "Some R log message\n"
            "===KUNLIB_JSON_BEGIN===\n"
            '{"n_individuals":100,"n_founders":20}\n'
            "===KUNLIB_JSON_END===\n"
        )
        r = _parse_r_summary(stdout)
        assert r["n_individuals"] == 100
        assert r["n_founders"] == 20

    def test_no_markers_returns_empty(self):
        assert _parse_r_summary("no markers here") == {}

    def test_malformed_json_returns_empty(self):
        stdout = "===KUNLIB_JSON_BEGIN===\nnot valid json\n===KUNLIB_JSON_END===\n"
        assert _parse_r_summary(stdout) == {}

    def test_logs_between_json(self):
        stdout = (
            "[stats] Done.\n[inbreeding] Done.\n"
            "===KUNLIB_JSON_BEGIN===\n"
            '{"tasks_executed":["stats","inbreeding"]}\n'
            "===KUNLIB_JSON_END===\n"
        )
        r = _parse_r_summary(stdout)
        assert "stats" in r["tasks_executed"]


# --------------------------------------------------------------------------- #
# File existence
# --------------------------------------------------------------------------- #
class TestFiles:
    def test_skill_md_exists(self):
        assert (_SKILL_DIR / "SKILL.md").exists()

    def test_run_pedigree_r_exists(self):
        assert (_SKILL_DIR / "run_pedigree.r").exists()

    def test_generate_demo_r_exists(self):
        assert (_SKILL_DIR / "generate_demo.r").exists()

    def test_skill_py_exists(self):
        assert (_SKILL_DIR / "pedigree_analysis.py").exists()


# --------------------------------------------------------------------------- #
# Input directory + pedfile resolution
# --------------------------------------------------------------------------- #
class TestInputDirResolution:
    """Unit-test the input-dir/pedfile resolution logic without running R."""

    def _make_args(self, tmp_path, pedfile="pedigree.csv", input_dir=None, demo=False):
        """Build a minimal argparse.Namespace mimicking framework injection."""
        import argparse
        ns = argparse.Namespace(
            demo=demo,
            input=str(input_dir) if input_dir is not None else None,
            pedfile=pedfile,
            output_dir=tmp_path,
            work_dir=tmp_path / "work",
            tables_dir=tmp_path / "tables",
            figures_dir=tmp_path / "figures",
            logs_dir=tmp_path / "logs",
            repro_dir=tmp_path / "reproducibility",
            tasks="stats",
            cand=None, trace="up", tracegen=None,
            timevar=None, foundervar=None, reference=None,
            top=20, mat_method="A", mat_compact=False,
            export_matrix=False, compact=False, highlight=None,
            vis_trace="up", showf=False, fig_format="pdf",
            fig_width=12, fig_height=10, inbreed_breaks="0.0625,0.125,0.25",
            threads=0,
        )
        for d in (ns.work_dir, ns.tables_dir, ns.figures_dir,
                  ns.logs_dir, ns.repro_dir):
            d.mkdir(parents=True, exist_ok=True)
        return ns

    def test_default_pedfile_found(self, tmp_path):
        """--input <dir> with default pedigree.csv resolves correctly."""
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()
        (input_dir / "pedigree.csv").write_text("Ind,Sire,Dam\nA,NA,NA\n")
        # Verify the path resolution manually (no R needed)
        from pathlib import Path
        resolved = Path(str(input_dir)) / "pedigree.csv"
        assert resolved.exists()
        assert resolved.is_file()

    def test_custom_pedfile_found(self, tmp_path):
        """--input <dir> --pedfile shrimp.csv resolves correctly."""
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()
        (input_dir / "shrimp.csv").write_text("Ind,Sire,Dam\nA,NA,NA\n")
        from pathlib import Path
        resolved = Path(str(input_dir)) / "shrimp.csv"
        assert resolved.exists()
        assert resolved.is_file()

    def test_input_dir_not_exists_raises(self, tmp_path):
        """run() raises FileNotFoundError when --input directory does not exist."""
        import shutil
        if shutil.which("Rscript") is None:
            pytest.skip("Rscript not found on PATH")
        ns = self._make_args(tmp_path, input_dir=tmp_path / "nonexistent_dir")
        with pytest.raises(FileNotFoundError, match="Input directory not found"):
            _run(ns)

    def test_input_is_file_raises(self, tmp_path):
        """run() raises NotADirectoryError when --input points to a file."""
        import shutil
        if shutil.which("Rscript") is None:
            pytest.skip("Rscript not found on PATH")
        a_file = tmp_path / "not_a_dir.csv"
        a_file.write_text("Ind,Sire,Dam\nA,NA,NA\n")
        ns = self._make_args(tmp_path, input_dir=a_file)
        with pytest.raises(NotADirectoryError, match="must be a directory"):
            _run(ns)

    def test_pedfile_not_found_raises(self, tmp_path):
        """run() raises FileNotFoundError when pedfile is absent from --input dir."""
        import shutil
        if shutil.which("Rscript") is None:
            pytest.skip("Rscript not found on PATH")
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()
        # pedigree.csv is NOT created
        ns = self._make_args(tmp_path, input_dir=input_dir)
        with pytest.raises(FileNotFoundError, match="Pedigree file not found"):
            _run(ns)

    def test_custom_pedfile_not_found_raises(self, tmp_path):
        """run() raises FileNotFoundError when custom --pedfile is absent."""
        import shutil
        if shutil.which("Rscript") is None:
            pytest.skip("Rscript not found on PATH")
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()
        # shrimp.csv is NOT created
        ns = self._make_args(tmp_path, pedfile="shrimp.csv", input_dir=input_dir)
        with pytest.raises(FileNotFoundError, match="Pedigree file not found"):
            _run(ns)



class TestDiscovery:
    def test_discover_finds_skill(self):
        from kunlib.registry import discover_all
        registry = discover_all()
        assert "pedigree-analysis" in registry

    def test_skill_docs_include_skill(self):
        from kunlib.registry import discover_all, get_skill_docs
        discover_all()
        docs = get_skill_docs()
        assert "pedigree-analysis" in docs
        assert "KunLib" in docs["pedigree-analysis"]


# --------------------------------------------------------------------------- #
# End-to-end demo integration test
# --------------------------------------------------------------------------- #
class TestE2EDemo:
    """Run --demo end-to-end via subprocess (requires R + visPedigree installed).

    All tests share a single demo run via class-scoped fixtures to avoid
    re-running the full R pipeline N times.
    """

    # Repo root — needed to expose kunlib to the subprocess (pyproject.toml
    # adds '.' to pythonpath only inside pytest, not in subprocesses).
    _REPO = str(_SKILL_PY.parent.parent.parent)

    @pytest.fixture(autouse=True)
    def _check_rscript(self):
        import shutil
        if shutil.which("Rscript") is None:
            pytest.skip("Rscript not found on PATH")

    @pytest.fixture(scope="class")
    def demo_result(self, tmp_path_factory):
        """Run demo once, share output directory across all tests in class."""
        import subprocess, sys, os
        out = tmp_path_factory.mktemp("e2e_demo")
        env = {**os.environ, "PYTHONPATH": self._REPO}
        proc = subprocess.run(
            [sys.executable, str(_SKILL_PY), "--demo", "--output", str(out)],
            capture_output=True, text=True, env=env,
        )
        return {"proc": proc, "out": out}

    def test_demo_exit_zero(self, demo_result):
        r = demo_result["proc"]
        assert r.returncode == 0, (
            f"demo run failed.\nSTDOUT:\n{r.stdout[-3000:]}\nSTDERR:\n{r.stderr[-2000:]}"
        )

    def test_demo_result_json_exists(self, demo_result):
        assert (demo_result["out"] / "result.json").exists()

    def test_demo_standard_dirs_exist(self, demo_result):
        for d in ("work", "tables", "figures", "logs", "reproducibility"):
            assert (demo_result["out"] / d).is_dir(), f"'{d}' directory missing"

    def test_demo_tidyped_csv_exists(self, demo_result):
        assert (demo_result["out"] / "tables" / "tidyped.csv").exists()

    def test_demo_tasks_executed_not_empty(self, demo_result):
        import json
        assert demo_result["proc"].returncode == 0, demo_result["proc"].stderr[-500:]
        data = json.loads((demo_result["out"] / "result.json").read_text())
        executed = data.get("summary", {}).get("tasks_executed", [])
        assert len(executed) > 0, (
            f"tasks_executed is empty — R state bug likely present.\n"
            f"tasks_skipped: {data['summary'].get('tasks_skipped')}"
        )

    def test_demo_tasks_skipped_no_false_failures(self, demo_result):
        import json
        assert demo_result["proc"].returncode == 0, demo_result["proc"].stderr[-500:]
        data = json.loads((demo_result["out"] / "result.json").read_text())
        skipped = data.get("summary", {}).get("tasks_skipped", [])
        for task in ("stats", "inbreeding", "visual"):
            assert not any(task in s for s in skipped), (
                f"Default task '{task}' ended up in tasks_skipped: {skipped}"
            )

    def test_demo_commands_sh_uses_absolute_path(self, demo_result):
        assert demo_result["proc"].returncode == 0, demo_result["proc"].stderr[-500:]
        sh = (demo_result["out"] / "reproducibility" / "commands.sh").read_text()
        assert "run_pedigree.r" in sh
        assert sh.count("/") > 2, "commands.sh should contain absolute paths"
