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
uv run uvicorn app.main:app --reload
```
