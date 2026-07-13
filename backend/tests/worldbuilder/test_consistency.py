from app.worldbuilder.consistency import check_consistency, ConsistencyResult

def test_no_issues_on_empty():
    result = check_consistency({})
    assert result.ok
    assert len(result.issues) == 0

def test_rule_contradiction_detected():
    result = check_consistency({"rules": ["魔法可以复活死者", "魔法不可复活死者"]})
    assert not result.ok
    assert any("复活" in i for i in result.issues)

def test_too_few_rules_warns():
    result = check_consistency({"rules": ["只有一条规则"]})
    assert any("至少3条" in i for i in result.warnings)

def test_character_goal_conflict_detected():
    result = check_consistency({
        "characters": [
            {"name":"A","goal":"杀死B"},
            {"name":"B","goal":"杀死A"},
        ]
    })
    # 直接冲突目标是好的张力，不是矛盾——应该是 warning 不是 error
    assert result.ok  # 张力不是错误
    assert any("张力" in w or "冲突" in w for w in result.warnings)

def test_too_few_locations_warns():
    result = check_consistency({"locations": ["只有一个地点"]})
    assert any("至少3个" in i for i in result.warnings)

def test_visual_style_missing_warns():
    result = check_consistency({})
    assert any("视觉风格" in i for i in result.warnings)
