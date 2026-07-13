from __future__ import annotations
from dataclasses import dataclass, field
from app.worldbuilder.consistency import check_consistency


@dataclass
class HealthReport:
    checklist: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def run_health_check(collected: dict) -> HealthReport:
    report = HealthReport()

    # 1. 规则
    rules = collected.get("rules", [])
    rules_ok = isinstance(rules, list) and len(rules) >= 3
    report.checklist.append({"name": "世界规则 ≥3 条", "status": "pass" if rules_ok else "fail"})
    if not rules_ok:
        report.errors.append(f"世界规则不足3条（当前{len(rules) if isinstance(rules,list) else 0}）")

    # 2. 角色
    chars = collected.get("characters", [])
    chars_ok = isinstance(chars, list) and len(chars) >= 2
    report.checklist.append({"name": "角色 ≥2 个", "status": "pass" if chars_ok else "fail"})
    if not chars_ok:
        report.errors.append("角色不足2个")

    # 3. 地点
    locs = collected.get("locations", [])
    locs_ok = isinstance(locs, list) and len(locs) >= 3
    report.checklist.append({"name": "地点 ≥3 个", "status": "pass" if locs_ok else "warn"})
    if not locs_ok:
        report.warnings.append("地点不足3个")

    # 4. 矛盾检测
    cons = check_consistency(collected)
    cons_ok = cons.ok
    report.checklist.append({"name": "无规则矛盾", "status": "pass" if cons_ok else "fail"})
    report.errors.extend(cons.issues)

    # 5. 视觉风格
    vs = collected.get("visual_style", {})
    vs_ok = bool(vs)
    report.checklist.append({"name": "视觉风格锚已定", "status": "pass" if vs_ok else "warn"})
    if not vs_ok:
        report.warnings.append("视觉风格锚未确定")

    # 6. 引爆事件
    inciting = collected.get("inciting") or collected.get("inciting_event")
    report.checklist.append({"name": "引爆事件已设", "status": "pass" if inciting else "warn"})
    if not inciting:
        report.warnings.append("引爆事件未设置")

    return report
