# Backend

## 运行环境
- Python `>=3.10`
- 依赖管理：`uv`

## 安装依赖
```bash
cd backend
uv sync
```

## 关键环境变量
- `HOST` / `PORT`: 服务监听地址与端口。
- `AMAP_API_KEY`: 高德服务密钥（必填）。
- `AMAP_MCP_COMMAND`: MCP 服务启动命令，默认 `uvx amap-mcp-server`。
- `AMAP_MCP_MOCK`: `true/false`，默认 `true`（本地 mock 模式）。
- `LLM_API_KEY` / `LLM_MODEL_ID` / `LLM_BASE_URL` / `LLM_TIMEOUT`: LLM 客户端配置。
- `UNSPLASH_ACCESS_KEY` / `UNSPLASH_SECRET_KEY`: 景点图片服务配置。

## 启动服务
```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 测试
```bash
cd backend
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

## 说明
- `backend/.env`、`backend/.env.example` 已加入 Git 忽略规则，避免误提交密钥。
- 当前 `AmapMCPClient` 提供 mock 与 MCP stdio 两种模式；`AMAP_MCP_MOCK=false` 时走 `AMAP_MCP_COMMAND` 启动的 MCP 服务。
