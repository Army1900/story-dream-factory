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
