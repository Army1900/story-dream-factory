from __future__ import annotations
import json
from dataclasses import dataclass, asdict


@dataclass
class ActionProposal:
    """角色 Agent 产出的行动提案（过程数据，不持久化）。"""
    intent: str = ""
    action_type: str = "action"  # action/dialogue/conflict/move/wait
    target: str = ""
    expectation: str = ""
    dialogue: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ActionProposal:
        return cls(
            intent=d.get("intent", ""),
            action_type=d.get("action_type", "action"),
            target=d.get("target", ""),
            expectation=d.get("expectation", ""),
            dialogue=d.get("dialogue", ""),
        )

    @classmethod
    def from_llm_json(cls, raw: str) -> ActionProposal:
        """从 LLM 返回的 JSON 字符串解析。"""
        return cls.from_dict(json.loads(raw))
