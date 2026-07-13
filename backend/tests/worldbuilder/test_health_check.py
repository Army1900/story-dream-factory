from app.worldbuilder.health_check import run_health_check, HealthReport

def test_healthy_world():
    collected = {
        "vision": {"type": "奇幻"},
        "rules": ["魔法稀有", "暴力通缉", "誓言约束"],
        "locations": ["镇", "城", "林"],
        "characters": [{"name": "A"}, {"name": "B"}],
        "visual_style": {"art_style": "油画"},
    }
    report = run_health_check(collected)
    assert report.passed
    assert len(report.errors) == 0

def test_missing_rules_fails():
    report = run_health_check({"rules": ["只有一条"]})
    assert not report.passed
    assert any("规则" in e for e in report.errors)

def test_missing_characters_fails():
    report = run_health_check({"rules": ["a","b","c"], "characters": []})
    assert not report.passed

def test_missing_visual_style_warns():
    report = run_health_check({
        "rules": ["a","b","c"], "locations": ["x","y","z"],
        "characters": [{"name":"A"},{"name":"B"}],
    })
    assert report.passed  # warning 不阻塞
    assert any("视觉" in w for w in report.warnings)

def test_report_has_checklist():
    report = run_health_check({})
    assert len(report.checklist) >= 5
    for item in report.checklist:
        assert "name" in item
        assert "status" in item  # "pass" | "warn" | "fail"
