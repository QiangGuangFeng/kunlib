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


# ---- kind 相关测试 ----

def test_default_kind_is_data():
    """未声明 kind 时默认为 'data'。"""
    assert _dummy_run.__kunlib_meta__.kind == "data"


def test_invalid_kind_raises():
    """声明无效 kind 时应抛出 ValueError。"""
    import pytest
    with pytest.raises(ValueError, match="Invalid skill kind"):
        @skill(name="test-invalid-kind", kind="unknown", params=[])
        def _bad(args):
            return KunResult(skill_name="test-invalid-kind", skill_version="0.0.1")


def test_generator_no_input_injected():
    """generator kind 不注入 --input。"""
    @skill(name="test-generator", kind="generator", params=[])
    def _gen(args):
        return KunResult(skill_name="test-generator", skill_version="0.0.1")

    parser = _gen.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x"])
    assert not hasattr(args, "input")


def test_generator_creates_full_dirs(tmp_path):
    """generator kind 创建完整标准目录。"""
    @skill(name="test-generator-dirs", kind="generator", params=[])
    def _gen(args):
        return KunResult(skill_name="test-generator-dirs", skill_version="0.0.1",
                         output_dir=args.output_dir)

    _gen.__kunlib_meta__.run_cli(["--output", str(tmp_path)])
    for d in ("work", "tables", "figures", "logs", "reproducibility"):
        assert (tmp_path / d).is_dir(), f"Missing dir: {d}"


def test_orchestrator_only_logs_dir(tmp_path):
    """orchestrator kind 只创建 logs/ 目录。"""
    @skill(name="test-orchestrator", kind="orchestrator", params=[])
    def _orch(args):
        assert args.work_dir is None
        assert args.tables_dir is None
        return KunResult(skill_name="test-orchestrator", skill_version="0.0.1",
                         output_dir=args.output_dir)

    _orch.__kunlib_meta__.run_cli(["--output", str(tmp_path)])
    assert (tmp_path / "logs").is_dir()
    assert not (tmp_path / "work").exists()
    assert not (tmp_path / "tables").exists()
    assert not (tmp_path / "figures").exists()


def test_validator_input_required():
    """validator kind 的 --input 是必需的。"""
    @skill(name="test-validator-req", kind="validator", params=[])
    def _val(args):
        return KunResult(skill_name="test-validator-req", skill_version="0.0.1")

    import pytest
    parser = _val.__kunlib_meta__.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--output", "/tmp/x"])  # 缺少 --input 应失败


def test_validator_creates_logs_and_tables(tmp_path):
    """validator kind 创建 logs/ 和 tables/ 目录。"""
    @skill(name="test-validator-dirs", kind="validator", params=[])
    def _val(args):
        return KunResult(skill_name="test-validator-dirs", skill_version="0.0.1",
                         output_dir=args.output_dir)

    _val.__kunlib_meta__.run_cli(["--output", str(tmp_path), "--input", str(tmp_path)])
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "tables").is_dir()
    assert not (tmp_path / "work").exists()
    assert not (tmp_path / "figures").exists()


def test_info_no_input_only_logs(tmp_path):
    """info kind 不注入 --input，只创建 logs/ 目录。"""
    @skill(name="test-info", kind="info", params=[])
    def _info(args):
        assert args.work_dir is None
        assert args.tables_dir is None
        return KunResult(skill_name="test-info", skill_version="0.0.1",
                         output_dir=args.output_dir)

    parser = _info.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x"])
    assert not hasattr(args, "input")

    _info.__kunlib_meta__.run_cli(["--output", str(tmp_path)])
    assert (tmp_path / "logs").is_dir()
    assert not (tmp_path / "work").exists()


def test_kind_in_catalog(tmp_path):
    """catalog.json 中包含 kind 字段。"""
    import json
    from kunlib.catalog import generate_catalog
    from kunlib.skill import get_registry

    path = generate_catalog(get_registry(), output_dir=tmp_path)
    catalog = json.loads(path.read_text())
    for entry in catalog["skills"]:
        assert "kind" in entry, f"Missing 'kind' in catalog entry for {entry['name']}"


def test_kind_in_manifest():
    """agent_adapter manifest 中包含 kind 字段。"""
    from kunlib.agent_adapter import KunLibAdapter
    adapter = KunLibAdapter()
    for entry in adapter.get_skill_manifest():
        assert "kind" in entry, f"Missing 'kind' in manifest entry for {entry['name']}"


# ---- prepare_env 测试 ----

def test_prepare_env_creates_dirs(tmp_path):
    """prepare_env() 应正确创建目录结构并注入 args 属性。"""
    import argparse
    from kunlib import skill, Param, KunResult

    @skill(name="test-prepare-env", kind="data", params=[])
    def _dummy(args):
        return KunResult(skill_name="test-prepare-env", skill_version="0.0.1")

    ns = argparse.Namespace(output=str(tmp_path))
    ns = _dummy.__kunlib_meta__.prepare_env(ns)
    assert ns.output_dir == tmp_path.resolve()
    assert ns.work_dir is not None and ns.work_dir.is_dir()
    assert ns.tables_dir is not None and ns.tables_dir.is_dir()
    assert ns.logs_dir is not None and ns.logs_dir.is_dir()


def test_adapter_run_skill_creates_dirs(tmp_path):
    """KunLibAdapter.run_skill() 应正确创建目录结构并输出 result.json。"""
    from kunlib.agent_adapter import KunLibAdapter
    adapter = KunLibAdapter()
    # test-skill 在本文件开头已注册
    result = adapter.run_skill("test-skill", {"output": str(tmp_path), "demo": True, "count": 3})
    assert "error" not in result
    assert (tmp_path / "result.json").exists()
    assert (tmp_path / "logs").is_dir()


# ---- input_schema 自动生成文件参数测试 ----

def test_input_schema_auto_generates_file_params():
    """input_schema 中的 IOField 应自动生成 --xxx-file CLI 参数。"""
    from kunlib import skill, Param, KunResult, IOField

    @skill(
        name="test-auto-input-params",
        kind="data",
        input_schema=[
            IOField(name="phe.csv", description="表型文件"),
            IOField(name="sel_id.csv", description="选择集ID"),
        ],
        params=[Param("demo", is_flag=True, help="Demo")],
    )
    def _auto(args):
        return KunResult(skill_name="test-auto-input-params", skill_version="0.0.1")

    parser = _auto.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x", "--input", "/data"])
    # 自动生成的参数应有默认值
    assert args.phe_file == "phe.csv"
    assert args.sel_id_file == "sel_id.csv"
    # 覆盖默认值
    args2 = parser.parse_args(["--output", "/tmp/x", "--input", "/data",
                                "--phe-file", "my_phe.csv"])
    assert args2.phe_file == "my_phe.csv"
    assert args2.sel_id_file == "sel_id.csv"  # 未覆盖的保持默认


def test_manual_param_silently_skipped_when_auto_generated():
    """如果开发者在 params 中声明了与 input_schema 自动生成同名的 Param，框架静默跳过。"""
    from kunlib import skill, Param, KunResult, IOField

    @skill(
        name="test-skip-dup-param",
        kind="data",
        input_schema=[IOField(name="phe.csv")],
        params=[
            Param("phe-file", default="old_phe.csv", help="should be skipped"),
        ],
    )
    def _dup(args):
        return KunResult(skill_name="test-skip-dup-param", skill_version="0.0.1")

    parser = _dup.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x", "--input", "/data"])
    # 应使用 input_schema 的默认值（phe.csv），不是 Param 的 default（old_phe.csv）
    assert args.phe_file == "phe.csv"


def test_generator_no_auto_input_params():
    """generator kind 不注入 --input，也不自动生成 input_schema 文件参数。"""
    from kunlib import skill, Param, KunResult, IOField

    @skill(
        name="test-gen-no-auto",
        kind="generator",
        input_schema=[],  # generator 通常没有 input_schema
        params=[],
    )
    def _gen(args):
        return KunResult(skill_name="test-gen-no-auto", skill_version="0.0.1")

    parser = _gen.__kunlib_meta__.build_parser()
    args = parser.parse_args(["--output", "/tmp/x"])
    assert not hasattr(args, "input")
