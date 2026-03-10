# Trip Planner-Agent Design

**目标**

恢复 `planner-agent` 作为最终排程决策核心，同时保留现有前置工具采集链路与 `TripPlan` API 契约不变。

**问题定义**

当前实现中，`TripWorkflow` 只负责采集景点、天气、酒店和餐饮的工具结果，最终的每日排程由 `trip_service.py` 内部规则完成。这导致：

- `free_text_input` 没有进入最终规划决策主链路
- `planner-agent` 名义存在，但不再承担核心排程职责
- service 里逐步堆积了主题打分与分配规则，职责偏重

**设计原则**

- `planner-agent` 负责“选谁进计划、每天怎么排、总体建议怎么写”
- service 负责“收集候选、校验 planner 输出、补图、预算、兜底”
- 保持 `/api/trip/plan` 请求与响应结构兼容
- planner 输出必须是结构化 JSON，不接受仅自然语言总结
- planner 失败时必须稳定回退到规则排程

**目标架构**

1. 前置采集阶段：
   - 继续按 `preferences` 搜景点
   - 继续查天气、酒店、餐饮
   - 返回 `tool_traces`
2. 候选归一化阶段：
   - service 将 traces 转为 attraction / hotel / meal / weather 候选
   - 生成 planner 所需的轻量上下文
3. 最终 planner 阶段：
   - 输入 `TripRequest + tool_traces 摘要 + free_text_input`
   - 输出结构化 `day assignment JSON`
4. Service 收尾阶段：
   - 校验 planner JSON
   - 回填完整对象到 `TripPlan`
   - 对最终入选景点补图
   - 重算预算
   - planner 不可用时回退规则排程

**Planner 输出 Schema**

planner 不直接输出完整 `TripPlan`，而是输出一个更小、更易校验的结构：

```json
{
  "days": [
    {
      "day_index": 0,
      "theme": "自然景观",
      "description": "第1天建议以自然景观为主，并优先安排长城。",
      "attraction_poi_ids": ["poi-1", "poi-2", "poi-3"],
      "meal_names": {
        "breakfast": "北京早餐铺",
        "lunch": "北京午餐馆",
        "dinner": "北京晚餐店"
      },
      "hotel_name": "北京中心酒店"
    }
  ],
  "overall_suggestions": "..."
}
```

约束：

- `day_index` 必须覆盖现有天数范围
- `attraction_poi_ids` 优先使用 POI ID，便于 service 精确回填
- `meal_names` / `hotel_name` 允许缺省，缺省时 service 保留已有兜底值
- `overall_suggestions` 优先使用 planner 输出；缺失时 service 规则补齐

**free_text_input 的位置**

`free_text_input` 不再在 service 中被硬编码成规则，而是与候选结果一起输入 planner。这样它可以自然表达：

- 明确点名的景点偏好
- 天气要求
- 预算倾向
- 节奏偏好
- 避坑描述

这些偏好由 planner 在已有候选池中做最终取舍，而不是由 service 维护越来越复杂的本地规则。

**失败与兜底**

以下情况回退到规则排程：

- planner 未返回合法 JSON
- planner 缺失 `days`
- planner 输出的 `day_index` 非法
- planner 选择的 `poi_id` 全部无法映射
- LLM 调用失败

回退规则保留当前主题分配能力，确保 API 稳定可用。

**测试策略**

- `TripWorkflow` 单测：
  - 确认最终 planner 阶段收到前置 traces 和 `free_text_input`
  - 确认 planner 阶段不再触发额外工具调用
- `TripService` 单测：
  - planner 返回结构化 JSON 时，按 planner 结果落盘
  - planner 输出非法时，回退到规则排程
  - `overall_suggestions` 优先使用 planner 输出
- API 契约测试：
  - 保持 `/api/trip/plan` 结构兼容
- 真实接口回归：
  - 用真实环境打同一 payload
  - 核对 `free_text_input` 在结果里体现为选点偏置，而非仅出现在 summary
