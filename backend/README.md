# Backend

后端使用 `FastAPI` 实现，负责行程生成、地图能力、POI 查询与图片相关接口。

## 环境要求

- Python `>=3.10`
- `uv`

## 安装与启动

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务默认地址：`http://localhost:8000`

## 关键环境变量

- `LLM_API_KEY`、`LLM_MODEL_ID`、`LLM_BASE_URL`、`LLM_TIMEOUT`
- `AMAP_API_KEY`
- `UNSPLASH_ACCESS_KEY`、`UNSPLASH_SECRET_KEY`
- `HOST`、`PORT`
- `CORS_ORIGINS`

请将真实配置写入 `backend/.env`，仓库中仅提交 `backend/.env.example`。

## 主要接口

- `GET /health`
- `POST /api/trip/plan`
- `GET /api/map/*`
- `GET /api/poi/*`

## 测试

```bash
cd backend
uv run pytest
```
