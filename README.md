# Travel Agent Next

`travel-agent-next` 是智能旅行助手的新仓库版本，目标是在保留原有核心功能与 API 契约的前提下，去除 HelloAgents 依赖，并以 `FastAPI + Vue 3 + TypeScript + Ant Design Vue` 独立实现。

## 目录结构

- `backend/`: FastAPI 后端，负责行程生成、地图与 POI 接口、图片服务
- `frontend/`: Vue 3 前端，保留原有功能流程并完成视觉升级
- `docs/`: 设计说明、实施记录与问题报告

## 快速启动

后端：

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

默认访问地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

## 常用命令

```bash
# 后端测试
cd backend
uv run pytest

# 前端构建
cd frontend
npm run build

# 前端 E2E
cd frontend
npm run test:e2e
```

## 当前进度

- 后端 API 骨架与主要工作流已落地
- 前端页面与核心流程已完成迁移
- 首页与结果页已完成本轮视觉升级
