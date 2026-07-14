from __future__ import annotations
import json
from app.worldbuilder.session import BuilderSession
from app.worldbuilder.stages import STAGES


class ConversationService:
    """处理导演消息 → LLM 回复 + 结构化数据提取 + 阶段推进。"""

    def __init__(self, llm_gateway):
        self.llm = llm_gateway

    async def process_message(self, session: BuilderSession, user_message: str) -> str:
        session.add_message("user", user_message)

        # 检查阶段控制指令
        lowered = user_message.lower().strip()
        if any(kw in lowered for kw in ["完成", "下一步", "next", "进入下一步"]):
            session.advance()
            stage = STAGES[session.current_stage]
            reply = f"进入「{stage['title']}」阶段。{stage['prompt_hint']}"
            session.add_message("assistant", reply)
            return reply
        if any(kw in lowered for kw in ["回到上一步", "返回", "back", "上一步"]):
            session.go_back()
            stage = STAGES[session.current_stage]
            reply = f"回到「{stage['title']}」阶段。{stage['prompt_hint']}"
            session.add_message("assistant", reply)
            return reply

        # 构建 LLM prompt
        stage = STAGES[session.current_stage]
        system_prompt = self._build_system_prompt(session)
        messages = [{"role": "system", "content": system_prompt}] + session.messages[-10:]

        # LLM 回复
        reply = await self.llm.complete(messages=messages)
        session.add_message("assistant", reply)

        # 结构化数据提取
        try:
            extracted = await self.llm.complete_json(
                messages=[{"role": "system", "content": f"从以下对话提取「{stage['title']}」阶段的结构化数据，输出 JSON。"},
                          {"role": "user", "content": f"用户说：{user_message}\n助手说：{reply}"}]
            )
            if extracted:
                session.collect(session.current_stage, extracted)
        except Exception:
            pass  # 提取失败不阻塞对话

        return reply

    def _build_system_prompt(self, session: BuilderSession) -> str:
        stage = STAGES[session.current_stage]
        return (
            f"你是「故事梦工厂」的世界构建助手。当前在「{stage['title']}」阶段。\n"
            f"本阶段需要覆盖：{', '.join(stage['checklist'])}\n"
            f"引导导演描述，补充追问未覆盖的维度。\n"
            f"已有的世界数据：{json.dumps(session.collected, ensure_ascii=False, default=str)}\n"
            f"回复简洁有引导性。当导演说「完成」时进入下一步。"
        )
