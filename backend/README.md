# Story Dream Factory — Backend

## 安装

需要 Python 3.11+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
cd backend
uv sync
cp .env.example .env  # 按需填写密钥
```

## 运行测试

```bash
uv run pytest
```

## 启动开发服务器

```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

## M1 地基已实现

- 领域模型（World/WorldTemplate/Location/Character/Relationship/Event/Memory/ImageAsset/DirectorDirective）
- SQLite 持久化（仓储模式）+ 图像文件存储
- 基础 API：`GET /health`、`World CRUD /worlds`
- LLM 网关（httpx + 分层路由 + fallback + 结构化输出）
- 生图网关（风格锚注入 + 种子 + provider 抽象）

### 手动验证网关（需密钥）

```bash
.venv/Scripts/python.exe scripts/check_llm.py
.venv/Scripts/python.exe scripts/check_imagegen.py
```

## M2 世界构建助手已实现

- 7 阶段对话状态机（愿景→世界观→规则→地点→角色→开场→定稿）
- 3 个预设模板（奇幻/赛博/仙侠）
- 对话核心（LLM 回复 + 结构化数据提取 + 阶段推进/回退）
- 矛盾检测（规则矛盾/数量不足/张力检查）
- 健康检查（定稿体检）
- 视觉锚定（风格参考图 + 角色定义图）
- API：创建会话 / 发消息 / 进度 / 回退 / 定稿产出 World
  - `POST /worlds/builder/session`（可选 `template_index`）
  - `POST /worlds/builder/session/{id}/message`
  - `GET /worlds/builder/session/{id}/progress`
  - `POST /worlds/builder/session/{id}/go-back`
  - `POST /worlds/builder/session/{id}/finalize`（写 World + Character + Location 到 DB，返回健康报告）

## M3 单角色模拟已实现

- ActionProposal 行动提案（intent/action_type/target/expectation/dialogue）
- CharacterAgent（感知→决策→LLM 结构化提案，错误降级为 wait）
- Narrator 叙述者（提案→文学叙述 Event，错误降级模板）
- Simulator 模拟引擎（单角色 tick：决策→叙述→推进时钟→事件历史）
- API：`POST /worlds/{id}/simulate/start`、`POST /step`、`GET /status`
