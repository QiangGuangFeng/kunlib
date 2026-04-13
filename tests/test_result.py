"""测试 KunResult 序列化。"""
from pathlib import Path
from kunlib.result import KunResult


def test_to_dict():
    r = KunResult(skill_name="test", skill_version="0.0.1", summary={"x": 1})
    d = r.to_dict()
    assert d["skill"] == "test"
    assert d["summary"] == {"x": 1}
    assert "disclaimer" in d
    assert "files" in d
    assert isinstance(d["files"], dict)


def test_to_dict_with_files(tmp_path):
    t1 = tmp_path / "tables" / "a.csv"
    t1.parent.mkdir()
    t1.write_text("x")
    f1 = tmp_path / "figures" / "plot.png"
    f1.parent.mkdir()
    f1.write_text("x")

    r = KunResult(
        skill_name="test",
        skill_version="0.0.1",
        output_dir=tmp_path,
        files={
            "tables": [t1],
            "figures": [f1],
        },
    )
    d = r.to_dict()
    assert d["files"]["tables"] == ["tables/a.csv"]
    assert d["files"]["figures"] == ["figures/plot.png"]


def test_save(tmp_path):
    r = KunResult(skill_name="test", skill_version="0.0.1", output_dir=tmp_path)
    path = r.save()
    assert path.exists()
    assert path.name == "result.json"
