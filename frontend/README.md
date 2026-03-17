# Frontend

前端使用 `Vue 3 + TypeScript + Ant Design Vue` 实现，保留旧版核心功能流程，并完成本轮视觉升级。

## 安装与启动

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

默认访问地址：`http://localhost:5173`

## 环境变量

- `VITE_API_BASE_URL`: 后端服务地址
- `VITE_AMAP_API_KEY`: 高德 Web JS API Key
- `VITE_AMAP_SECURITY_JS_CODE`: 高德安全密钥

请将真实配置写入 `frontend/.env`，仓库中仅提交 `frontend/.env.example`。

## 常用命令

```bash
cd frontend
npm run build
npm run test:e2e
```

## 说明

- 页面流程保持为首页填写、结果页展示/编辑/导出
- 结果页不再从前端额外补发 `/api/poi/photo` 请求
