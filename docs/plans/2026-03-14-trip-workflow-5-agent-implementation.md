# Trip Workflow 5-Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `TripWorkflow` 从单 `MiniAgent` 多阶段调用改为 5 个具名 specialist agent 协同执行，并保持现有 API 与结果结构兼容。

**Architecture:** 复用现有 `MiniAgent` 运行时与 `ToolRegistry`，新增一层 specialist agent 封装表达景点、天气、酒店、餐饮与规划五类职责。`TripWorkflow` 只负责编排与兜底工具分发，`TripService` 负责实例化 5 个 agent 并维持既有回填、预算与降级逻辑。

**Tech Stack:** Python, FastAPI, unittest, Pydantic

---

### Task 1: 让测试先定义 5-agent 目标行为

**Files:**
- Modify: `backend/tests/unit/test_trip_workflow.py`
- Modify: `backend/tests/unit/test_agent_runtime.py`

1. 写失败测试，要求 workflow 接受 5 个独立 agent，并在 traces 中保留 `agent_name`
2. 运行目标测试，确认当前实现失败
3. 仅实现让这些测试通过所需的最小改动

### Task 2: 引入 specialist agent 封装

**Files:**
- Modify: `backend/app/agent/contracts.py`
- Modify: `backend/app/agent/runtime.py`
- Create: `backend/app/agent/specialists.py`
- Modify: `backend/app/agent/__init__.py`

1. 扩展 `ToolTrace` 支持 `agent_name`
2. 为 `MiniAgent` 增加 `name`
3. 新增 5 个 specialist agent 与工具子注册表构造

### Task 3: 改造 workflow 与 service 装配

**Files:**
- Modify: `backend/app/agent/workflows/trip_workflow.py`
- Modify: `backend/app/services/trip_service.py`
- Modify: `backend/tests/unit/test_trip_service.py`

1. 用 5 个 specialist agent 替换单 agent workflow
2. 保留现有 planner 上下文与规则回退逻辑
3. 运行相关单测，确认行为兼容
