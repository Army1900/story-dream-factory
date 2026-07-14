from app.physics.engine import PhysicsEngine, ResolvedAction
from app.agents.proposal import ActionProposal

def test_move_action_updates_location():
    engine = PhysicsEngine()
    proposal = ActionProposal(intent="去酒馆", action_type="move", target="酒馆")
    resolved = engine.resolve(proposal, character_state={"location_id": "营地"}, world_rules=[])
    assert resolved.success
    assert resolved.new_state["location_id"] == "酒馆"

def test_dialogue_passes_through():
    engine = PhysicsEngine()
    proposal = ActionProposal(intent="质问", action_type="dialogue", target="贝拉", dialogue="你骗了我。")
    resolved = engine.resolve(proposal, character_state={"location_id": "酒馆"}, world_rules=[])
    assert resolved.success
    assert resolved.new_state["location_id"] == "酒馆"  # 位置不变

def test_conflict_deals_damage():
    engine = PhysicsEngine()
    proposal = ActionProposal(intent="攻击", action_type="conflict", target="敌人")
    resolved = engine.resolve(proposal, character_state={"location_id": "战场", "health": 100}, world_rules=[])
    assert resolved.success
    assert resolved.new_state["health"] < 100  # 受伤

def test_wait_does_nothing():
    engine = PhysicsEngine()
    proposal = ActionProposal(intent="等待", action_type="wait")
    resolved = engine.resolve(proposal, character_state={"location_id": "酒馆", "health": 80}, world_rules=[])
    assert resolved.success
    assert resolved.new_state == {"location_id": "酒馆", "health": 80}

def test_rule_blocks_action():
    engine = PhysicsEngine()
    proposal = ActionProposal(intent="施法", action_type="action", target="复活死者")
    resolved = engine.resolve(proposal, character_state={}, world_rules=["魔法不可复活死者"])
    assert not resolved.success
    assert "违反" in resolved.reason or "不可" in resolved.reason
