"""测试 KunResult 序列化。"""
from pathlib import Path
from kunlib.result import KunResult


def test_to_dict():
    r = KunResult(skill_name="test", skill_version="0.0.1", summary={"x": 1})
    d = r.to_dict()
    assert d["skill"] == "test"
    assert d["summary"] == {"x": 1}
    assert "disclaimer" in d


def test_save(tmp_path):
    r = KunResult(skill_name="test", skill_version="0.0.1", output_dir=tmp_path)
    path = r.save()
    assert path.exists()
    assert path.name == "result.json"
