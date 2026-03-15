# Trip Workflow Concurrency Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 TripWorkflow 的前置 specialist agent 检索阶段改为并发执行，同时仅在 MCP 连接初始化阶段增加保护，避免首次建连竞态。

**Architecture:** 保持现有 5-agent 结构不变，把景点、天气、酒店与餐饮检索任务组装为 `asyncio.gather(...)` 并发执行，最后统一汇总给 PlannerAgent。MCP stdio 客户端只对 `connect()` 增加一次性初始化锁，不对 `call_tool()` 做全局串行保护，以保留工具调用并发能力。

**Tech Stack:** Python, asyncio, FastAPI, unittest

---

### Task 1: 用测试定义并发行为

**Files:**
- Modify: `backend/tests/unit/test_trip_workflow.py`
- Modify: `backend/tests/unit/test_mcp_stdio_client.py`

1. 写失败测试，验证前置 specialist agent 会发生重叠执行
2. 写失败测试，验证并发 `connect()` 只初始化一次底层 client
3. 运行目标测试并确认当前实现失败

### Task 2: 最小实现 workflow 并发化

**Files:**
- Modify: `backend/app/agent/workflows/trip_workflow.py`

1. 将景点、天气、酒店、餐饮前置阶段改为并发任务
2. 保持 planner 阶段串行
3. 保持 traces 合并顺序稳定，避免影响后续 planner 上下文构造

### Task 3: 为 MCP connect 增加初始化保护

**Files:**
- Modify: `backend/app/integrations/mcp/stdio_client.py`

1. 给 `connect()` 增加异步锁
2. 仅保护首次 `_client` 初始化，不改变 `call_tool()` 并发策略
3. 运行后端测试验证无回归
