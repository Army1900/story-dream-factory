from __future__ import annotations
from dataclasses import dataclass, field
from app.agents.proposal import ActionProposal
from app.physics.rules import compute_damage


@dataclass
class ResolvedAction:
    """物理引擎裁决后的行动结果。"""
    proposal: ActionProposal
    success: bool = True
    reason: str = ""
    new_state: dict = field(default_factory=dict)
    effects: dict = field(default_factory=dict)  # 副作用（关系变化等）


class PhysicsEngine:
    """确定性物理引擎：裁决 ActionProposal，不调 LLM。"""

    def resolve(self, proposal: ActionProposal, character_state: dict, world_rules: list[str]) -> ResolvedAction:
        # 检查规则约束
        blocked = self._check_rules(proposal, world_rules)
        if blocked:
            return ResolvedAction(proposal=proposal, success=False, reason=blocked, new_state=dict(character_state))

        atype = proposal.action_type
        new_state = dict(character_state)

        if atype == "move":
            new_state["location_id"] = proposal.target
        elif atype == "conflict":
            dmg = compute_damage(new_state.get("health", 100))
            new_state["health"] = dmg
        elif atype == "dialogue":
            pass  # 对白不改变物理状态
        elif atype == "wait":
            pass
        # action（通用）：不改变物理状态

        return ResolvedAction(proposal=proposal, success=True, reason="ok", new_state=new_state)

    def _check_rules(self, proposal: ActionProposal, rules: list[str]) -> str:
        """检查行动是否违反世界规则。返回空串=通过，否则返回违反原因。"""
        intent_lower = (proposal.intent + proposal.target).lower()
        for rule in rules:
            rule_lower = rule.lower()
            # 简单关键词匹配：如果规则含"不可X"且行动含"X"
            if "不可" in rule or "禁止" in rule:
                # 提取被禁止的关键词
                for marker in ("不可", "禁止"):
                    if marker in rule:
                        idx = rule.index(marker) + len(marker)
                        keyword = rule[idx:].strip()
                        if keyword and keyword in intent_lower:
                            return f"违反世界规则：「{rule}」"
        return ""
