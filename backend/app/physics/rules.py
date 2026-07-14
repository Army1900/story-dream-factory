from __future__ import annotations

# 战斗伤害
DAMAGE_TABLE = {"light": 10, "moderate": 25, "severe": 50}

def compute_damage(current_health: int, severity: str = "moderate") -> int:
    """计算受伤后的生命值。"""
    dmg = DAMAGE_TABLE.get(severity, 25)
    return max(0, current_health - dmg)

# 关系变化
RELATIONSHIP_CHANGE = {
    "conflict": -15,       # 冲突降好感
    "dialogue": 5,         # 对话略升（默认）
    "cooperation": 20,     # 合作升好感
    "betrayal": -30,       # 背叛暴降
}

def update_relationship(current_affinity: float, action_type: str, positive: bool = False) -> float:
    """更新角色间关系数值。"""
    if action_type == "dialogue" and positive:
        delta = RELATIONSHIP_CHANGE["cooperation"]
    else:
        delta = RELATIONSHIP_CHANGE.get(action_type, 0)
    return max(-100.0, min(100.0, current_affinity + delta))
