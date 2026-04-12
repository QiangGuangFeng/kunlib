"""测试 @skill 装饰器和 SkillMeta。"""
import argparse
from kunlib import skill, Param, KunResult


@skill(
    name="test-skill",
    version="0.0.1",
    description="A test skill",
    params=[
        Param("output", required=True, help="Output dir"),
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


def test_build_parser():
    parser = _dummy_run.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x", "--demo", "--count", "10"])
    assert args.output == "/tmp/x"
    assert args.demo is True
    assert args.count == 10


def test_run_cli(tmp_path):
    result = _dummy_run.__kunlib_meta__.run_cli(["--output", str(tmp_path), "--count", "7"])
    assert result.summary["count"] == 7
