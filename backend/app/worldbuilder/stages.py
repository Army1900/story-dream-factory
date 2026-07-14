STAGE_ORDER = ["vision","setting","rules","locations","characters","inciting","finalize"]

STAGES = {
    "vision":     {"title":"愿景","checklist":["类型与基调","规模","视觉风格"],"prompt_hint":"你想讲一个什么样的故事？"},
    "setting":    {"title":"世界观","checklist":["时代","世界设定","核心矛盾"],"prompt_hint":"这个世界从何而来？核心矛盾是什么？"},
    "rules":      {"title":"规则","checklist":["世界法则(至少3条)","力量体系边界"],"prompt_hint":"这个世界遵循什么规则？"},
    "locations":  {"title":"地点","checklist":["关键地点(至少3个)","连通关系"],"prompt_hint":"故事发生在哪里？"},
    "characters": {"title":"角色","checklist":["角色(至少2个)","性格/目标","角色间张力","角色定义图"],"prompt_hint":"谁来登场？"},
    "inciting":   {"title":"开场","checklist":["初始态势","引爆事件"],"prompt_hint":"从哪个瞬间开始？"},
    "finalize":   {"title":"定稿","checklist":["健康检查","视觉锚确认","开拍"],"prompt_hint":"准备好开拍了吗？"},
}

def next_stage(current: str) -> str | None:
    idx = STAGE_ORDER.index(current)
    return STAGE_ORDER[idx+1] if idx < len(STAGE_ORDER)-1 else None

def prev_stage(current: str) -> str | None:
    idx = STAGE_ORDER.index(current)
    return STAGE_ORDER[idx-1] if idx > 0 else None
