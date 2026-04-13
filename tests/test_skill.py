"""测试 @skill 装饰器和 SkillMeta。"""
import argparse
from kunlib import skill, Param, KunResult


@skill(
    name="test-skill",
    version="0.0.1",
    description="A test skill",
    params=[
        Param("demo", is_flag=True, help="Demo mode"),
        Param("count", type=int, default=5, help="Count"),
    ],
)
def _dummy_run(args: argparse.Namespace) -> KunResult:
    return KunResult(skill_name="test-skill", skill_version="0.0.1", summary={"count": args.count})


def test_decorator_registers():
    from kunlib.skill import get_registry
    assert "test-skill" in get_registry()


def test_meta_attached():
    assert hasattr(_dummy_run, "__kunlib_meta__")
    assert _dummy_run.__kunlib_meta__.name == "test-skill"


def test_build_parser_has_input_output():
    """框架自动注入 --input 和 --output。"""
    parser = _dummy_run.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x", "--input", "/data", "--demo", "--count", "10"])
    assert args.output == "/tmp/x"
    assert args.input == "/data"
    assert args.demo is True
    assert args.count == 10


def test_output_is_required():
    """--output 是必需的。"""
    parser = _dummy_run.__kunlib_meta__.build_parser()
    import pytest
    with pytest.raises(SystemExit):
        parser.parse_args(["--count", "10"])  # 没有 --output 应该失败


def test_reserved_params_skipped():
    """开发者在 params 中声明 input/output 不会导致 argparse 重复。"""
    @skill(
        name="test-reserved",
        version="0.0.1",
        params=[
            Param("input", help="should be skipped"),
            Param("output", required=True, help="should be skipped"),
            Param("extra", type=int, default=1, help="custom param"),
        ],
    )
    def _dummy(args):
        return KunResult(skill_name="test-reserved", skill_version="0.0.1")

    parser = _dummy.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x", "--extra", "42"])
    assert args.output == "/tmp/x"
    assert args.extra == 42


def test_run_cli_creates_standard_dirs(tmp_path):
    """run_cli 自动创建标准目录结构。"""
    result = _dummy_run.__kunlib_meta__.run_cli(["--output", str(tmp_path), "--count", "7"])
    assert result.summary["count"] == 7
    # 框架应自动创建标准子目录
    for d in ("work", "tables", "figures", "logs", "reproducibility"):
        assert (tmp_path / d).is_dir(), f"Missing standard dir: {d}"
    # result.json 应自动写入
    assert (tmp_path / "result.json").exists()


def test_run_cli_rejects_non_kunresult(tmp_path):
    """run() 不返回 KunResult 时应抛出 TypeError。"""
    @skill(name="test-bad-return", version="0.0.1", params=[])
    def _bad(args):
        return {"not": "a KunResult"}

    import pytest
    with pytest.raises(TypeError, match="must return KunResult"):
        _bad.__kunlib_meta__.run_cli(["--output", str(tmp_path)])
