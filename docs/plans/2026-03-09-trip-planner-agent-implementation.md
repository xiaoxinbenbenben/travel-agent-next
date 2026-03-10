# Trip Planner-Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 恢复最终 planner-agent 负责结构化排程，并让 service 只负责校验、补图、预算和兜底。

**Architecture:** 保留现有 TripWorkflow 的前置工具采集阶段，在尾部增加最终 planner 阶段。planner 接收 `TripRequest` 与工具结果摘要，输出结构化日程 JSON；service 负责校验并映射为 `TripPlan`，planner 不可用时回退到现有规则排程。

**Tech Stack:** Python, FastAPI, Pydantic, unittest, MiniAgent runtime

---

### Task 1: 为 planner 输出定义测试边界

**Files:**
- Modify: `backend/tests/unit/test_trip_workflow.py`
- Modify: `backend/tests/unit/test_trip_service.py`

**Step 1: Write the failing test**

- 为 workflow 增加测试，断言最终 planner 调用消息包含：
  - `free_text_input`
  - 前置工具结果摘要
  - planner 返回的结构化 JSON 被写入 `result.content`
- 为 service 增加测试，断言：
  - 优先使用 planner 的 `days[].attraction_poi_ids`
  - 优先使用 planner 的 `overall_suggestions`
  - planner 非法时回退规则排程

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_trip_workflow.py tests/unit/test_trip_service.py -q`

Expected: 与 planner 阶段相关的新增断言失败。

**Step 3: Write minimal implementation**

- 给 workflow 增加 planner 阶段与结果透传
- 给 service 增加 planner 结果解析与回退

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_trip_workflow.py tests/unit/test_trip_service.py -q`

Expected: PASS

### Task 2: 实现 planner prompt 与 workflow 末阶段

**Files:**
- Modify: `backend/app/agent/prompts.py`
- Modify: `backend/app/agent/workflows/trip_workflow.py`

**Step 1: Write the failing test**

- 断言 planner prompt 要求输出 JSON，而不是自由文本总结

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_trip_workflow.py -q`

Expected: FAIL

**Step 3: Write minimal implementation**

- 新增 planner prompt 模板
- workflow 将前置 traces 摘要 + request 信息组装为 planner 输入
- planner 阶段不要求工具调用，直接保留模型输出文本

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_trip_workflow.py -q`

Expected: PASS

### Task 3: 将 planner 输出映射到 TripPlan

**Files:**
- Modify: `backend/app/services/trip_service.py`
- Test: `backend/tests/unit/test_trip_service.py`

**Step 1: Write the failing test**

- 断言合法 planner JSON 能映射到：
  - `days[].attractions`
  - `days[].description`
  - `hotel`
  - `meals`
  - `overall_suggestions`

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_trip_service.py -q`

Expected: FAIL

**Step 3: Write minimal implementation**

- 从 traces 提取候选对象映射
- 解析 planner JSON
- 回填每天选中的 POI、酒店、餐饮
- 保留补图、预算、天气逻辑

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_trip_service.py -q`

Expected: PASS

### Task 4: 保留兜底规则，避免 planner 失效时 API 退化

**Files:**
- Modify: `backend/app/services/trip_service.py`
- Test: `backend/tests/unit/test_trip_service.py`

**Step 1: Write the failing test**

- 构造非法 planner 输出，断言仍能得到非空 `TripPlan`

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_trip_service.py -q`

Expected: FAIL

**Step 3: Write minimal implementation**

- 将当前主题分配逻辑下沉为 fallback
- planner 解析失败时走 fallback

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_trip_service.py -q`

Expected: PASS

### Task 5: 验证契约与真实接口

**Files:**
- Modify: `backend/tests/api/test_trip_api_contract.py`（仅在必要时）

**Step 1: Run automated verification**

Run: `uv run pytest tests/unit/test_trip_workflow.py tests/unit/test_trip_service.py tests/unit/test_photo_service.py tests/api/test_trip_api_contract.py -q`

Expected: PASS

**Step 2: Run real regression**

Run a real `/api/trip/plan` request with:

```json
{
  "city": "北京",
  "start_date": "2026-04-01",
  "end_date": "2026-04-03",
  "travel_days": 3,
  "transportation": "公共交通",
  "accommodation": "经济型酒店",
  "preferences": ["自然景观", "历史文化"],
  "free_text_input": "想去故宫，长城"
}
```

Expected:

- HTTP 200
- 结构仍兼容 `TripPlanResponse`
- `free_text_input` 对最终选点有可见影响
- planner 不再只是生成无效总结
