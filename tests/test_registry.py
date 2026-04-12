"""测试技能自动发现。"""
from kunlib.registry import discover_all, get_skill_docs
from kunlib.skill import get_registry


def test_discover_returns_dict():
    registry = discover_all()
    assert isinstance(registry, dict)


def test_get_skill_docs_returns_dict():
    discover_all()
    docs = get_skill_docs()
    assert isinstance(docs, dict)
