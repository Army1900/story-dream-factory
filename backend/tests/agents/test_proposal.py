from app.agents.proposal import ActionProposal

def test_proposal_basic():
    p = ActionProposal(intent="质问贝拉", action_type="dialogue", target="贝拉", expectation="逼出真相", dialogue="你骗了我。")
    assert p.intent == "质问贝拉"
    assert p.action_type == "dialogue"
    assert p.target == "贝拉"

def test_proposal_optional_fields():
    p = ActionProposal(intent="等待", action_type="wait", target="", expectation="", dialogue="")
    assert p.action_type == "wait"

def test_proposal_to_dict():
    p = ActionProposal(intent="移动", action_type="move", target="酒馆", expectation="到达", dialogue="")
    d = p.to_dict()
    assert d["intent"] == "移动"
    assert d["action_type"] == "move"

def test_proposal_from_dict():
    d = {"intent":"攻击","action_type":"conflict","target":"敌人","expectation":"击败","dialogue":""}
    p = ActionProposal.from_dict(d)
    assert p.intent == "攻击"
    assert p.action_type == "conflict"

def test_proposal_from_llm_json():
    raw = '{"intent": "说服", "action_type": "dialogue", "target": "守卫", "expectation": "放行", "dialogue": "让我过去。"}'
    p = ActionProposal.from_llm_json(raw)
    assert p.target == "守卫"
