from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ConsistencyResult:
    issues: list[str] = field(default_factory=list)      # 错误（必须修）
    warnings: list[str] = field(default_factory=list)     # 警告（建议修）

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0


def check_consistency(collected: dict) -> ConsistencyResult:
    result = ConsistencyResult()

    rules = collected.get("rules", [])
    if isinstance(rules, list):
        # 检测矛盾规则（关键词相反）
        _check_rule_contradictions(rules, result)
        if len(rules) < 3:
            result.warnings.append(f"世界规则建议至少3条，当前{len(rules)}条")

    characters = collected.get("characters", [])
    if isinstance(characters, list):
        if len(characters) >= 2:
            result.warnings.append("检测到多个角色，确认角色间有足够张力")
        elif len(characters) < 2:
            result.warnings.append("角色建议至少2个")

    locations = collected.get("locations", [])
    if isinstance(locations, list) and len(locations) < 3:
        result.warnings.append(f"地点建议至少3个，当前{len(locations)}个")

    if not collected.get("visual_style"):
        result.warnings.append("视觉风格锚尚未确定")

    if not collected.get("vision"):
        result.warnings.append("愿景尚未确定")

    return result


_OPPOSITES = [
    ("可以", "不可"), ("能", "不能"), ("会", "不会"),
    ("必须", "禁止"), ("允许", "禁止"),
]

def _check_rule_contradictions(rules: list[str], result: ConsistencyResult) -> None:
    for i, r1 in enumerate(rules):
        for r2 in rules[i+1:]:
            for pos, neg in _OPPOSITES:
                if pos in r1 and neg in r2 and _share_keyword(r1, r2):
                    result.issues.append(f"规则可能矛盾：「{r1}」vs「{r2}」")
                elif neg in r1 and pos in r2 and _share_keyword(r1, r2):
                    result.issues.append(f"规则可能矛盾：「{r1}」vs「{r2}」")

def _share_keyword(r1: str, r2: str) -> bool:
    """两条规则是否有共同关键词（简单：共享 >=2 个汉字片段）。"""
    common = set(r1) & set(r2)
    return len(common) >= 3
