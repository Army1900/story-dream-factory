from __future__ import annotations
from app.worldbuilder.stages import STAGES, STAGE_ORDER, next_stage, prev_stage


class BuilderSession:
    """世界构建会话状态机：7 阶段 + 已收集数据 + 清单进度。"""

    def __init__(self, template: dict | None = None):
        self.current_stage: str = "vision"
        self.stage_index: int = 0
        self.collected: dict = {}
        self.messages: list[dict] = []
        self.world_name: str = ""
        if template:
            self._apply_template(template)

    def _apply_template(self, tpl: dict) -> None:
        if tpl.get("rules_draft"):
            self.collected["rules"] = list(tpl["rules_draft"])
        if tpl.get("visual_style_draft"):
            self.collected["visual_style"] = dict(tpl["visual_style_draft"])
        if tpl.get("locations_draft"):
            self.collected["locations"] = list(tpl["locations_draft"])
        self.world_name = tpl.get("name", "")

    def advance(self) -> str | None:
        nxt = next_stage(self.current_stage)
        if nxt is None:
            return None
        self.current_stage = nxt
        self.stage_index = STAGE_ORDER.index(nxt)
        return nxt

    def go_back(self) -> str:
        prv = prev_stage(self.current_stage)
        if prv:
            self.current_stage = prv
            self.stage_index = STAGE_ORDER.index(prv)
        return self.current_stage

    def go_to(self, stage: str) -> None:
        if stage in STAGE_ORDER:
            self.current_stage = stage
            self.stage_index = STAGE_ORDER.index(stage)

    def collect(self, stage: str, data: dict) -> None:
        if stage not in self.collected or not isinstance(self.collected[stage], dict):
            self.collected[stage] = {}
        if isinstance(data, dict):
            self.collected[stage].update(data)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def checklist_progress(self) -> dict:
        result = {}
        for key in STAGE_ORDER:
            stage_def = STAGES[key]
            items = stage_def["checklist"]
            covered = 0
            stage_data = self.collected.get(key, {})
            # 简易覆盖检测：checklist 关键词在 collected 中有对应 key
            mapping = {
                "类型与基调": "type" in stage_data or "tone" in stage_data,
                "视觉风格": "visual_style" in self.collected or "visual_style" in stage_data,
                "核心矛盾": "conflict" in stage_data,
                "世界法则(至少3条)": isinstance(self.collected.get("rules"), list) and len(self.collected.get("rules", [])) >= 3,
                "关键地点(至少3个)": isinstance(self.collected.get("locations"), list) and len(self.collected.get("locations", [])) >= 3,
                "角色(至少2个)": isinstance(self.collected.get("characters"), list) and len(self.collected.get("characters", [])) >= 2,
                "引爆事件": "inciting_event" in self.collected or "inciting_event" in stage_data,
            }
            for item in items:
                if mapping.get(item, False):
                    covered += 1
            result[key] = {"covered": covered, "total": len(items)}
        return result

    def to_dict(self) -> dict:
        return {
            "current_stage": self.current_stage,
            "stage_index": self.stage_index,
            "collected": self.collected,
            "messages": self.messages,
            "world_name": self.world_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BuilderSession:
        s = cls(template=None)
        s.current_stage = data.get("current_stage", "vision")
        s.stage_index = data.get("stage_index", 0)
        s.collected = data.get("collected", {})
        s.messages = data.get("messages", [])
        s.world_name = data.get("world_name", "")
        return s
