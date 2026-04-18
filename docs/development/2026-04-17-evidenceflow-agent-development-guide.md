# 证据流 Agent 开发文档

## 1. 推荐技术路线

推荐采用以下分层：

- 前端：`Next.js + React + TypeScript`
- 后端：`FastAPI + Python`
- Agent 编排：后端自定义 orchestration，必要时引入轻量 workflow
- 模型：`DeepSeek Chat`
- 本地转写：`faster-whisper` 或 `whisper.cpp`
- 数据库：`SQLite`
- 本地向量库：`LanceDB`
- Embeddings：`fastembed` 或 `sentence-transformers`

该路线的目标是：最小付费依赖、低部署复杂度、便于比赛演示。

## 1.1 Subagent 使用规则

- 在以下情况允许并建议启用 subagent：
  - 任务可明确拆分为多个互不重叠的子任务
  - 某个子任务不阻塞当前主链路，可并行推进
  - 需要一个子任务专门负责验证、整理或独立实现某个模块
- 不应启用 subagent 的情况：
  - 当前下一步严格依赖该任务结果
  - 子任务写入范围与主任务或其他子任务高度重叠
  - 只是为了“更快”而把一个本来很小的任务拆散
- Subagent 输出必须满足：
  - 明确负责文件范围
  - 不修改未授权区域
  - 返回可验证结果
  - 若涉及 agent 功能，仍需真实请求 DeepSeek 完成 live test
- 多个 subagent 并行时，必须保证写入集合互斥，避免同时修改同一文件或同一模块。

## 2. 推荐仓库结构

```text
docs/
  product/
  development/
  plans/
frontend/
  src/app/
  src/components/
  src/lib/
backend/
  app.py
  api/
  agents/
  services/
  adapters/
  memory/
  models/
  schemas/
  storage/
  tests/
data/
  samples/
  local_db/
```

## 3. 后端模块划分

### 3.1 agents/

- `orchestrator_agent.py`
- `memory_agent.py`
- `planning_agent.py`
- `reading_agent.py`
- `evidence_agent.py`

### 3.2 services/

- `transcription_service.py`
- `transcript_parser_service.py`
- `progress_extraction_service.py`
- `idea_capture_service.py`
- `research_plan_service.py`
- `reading_recommendation_service.py`
- `evidence_retrieval_service.py`
- `claim_verification_service.py`
- `briefing_service.py`

### 3.3 adapters/

- `deepseek_client.py`
- `openalex_adapter.py`
- `arxiv_adapter.py`
- `semantic_scholar_adapter.py`
- `whisper_adapter.py`

## 4. 核心数据模型

### 4.1 Project

- `id`
- `name`
- `description`
- `domain`
- `created_at`

### 4.2 Meeting

- `id`
- `project_id`
- `title`
- `audio_path`
- `transcript_path`
- `summary`
- `created_at`

### 4.3 StudentProgress

- `id`
- `meeting_id`
- `student_name`
- `completed_work`
- `current_result`
- `blockers`
- `risks`

### 4.4 ResearchIdea

- `id`
- `meeting_id`
- `student_name`
- `idea_text`
- `suggested_by`
- `expected_validation`
- `status`

### 4.5 ReadingRecommendation

- `id`
- `meeting_id`
- `idea_id`
- `student_name`
- `title`
- `source_url`
- `reason`
- `priority`

### 4.6 Claim

- `id`
- `meeting_id`
- `idea_id`
- `text`
- `speaker`
- `timestamp_start`
- `timestamp_end`
- `status` (`supported` / `contradicted` / `needs_verification`)

### 4.7 EvidenceCard

- `id`
- `claim_id`
- `source_title`
- `source_url`
- `source_type`
- `stance`
- `snippet`
- `score`

### 4.8 ActionItem

- `id`
- `meeting_id`
- `student_name`
- `title`
- `owner`
- `deadline`
- `priority`
- `status`
- `dependency_note`

## 5. 核心流程

### 流程 A：会议处理

1. 上传音频或 transcript
2. 如果是音频，执行本地转写
3. 结构化切分 transcript
4. 按学生维度提取周进展、结果、阻塞点、风险
5. 捕获导师新 idea，并转成研究假设与下周动作
6. 基于新 idea 和当前阻塞点生成推荐阅读
7. 在必要时对关键 claim 和新 idea 进入证据检索与核验
8. 生成会议摘要、下周计划与交付物
9. 写入项目记忆

### 流程 B：会前 briefing

1. 读取项目记忆
2. 汇总学生上周承诺与实际完成情况
3. 拉取未完成 action item 和导师历史建议
4. 生成风险、阻塞、建议议程和本周最该追问的问题
5. 输出 briefing 文档

## 6. API 设计建议

- `POST /api/projects`
- `GET /api/projects/{id}`
- `POST /api/meetings/import`
- `POST /api/meetings/{id}/process`
- `GET /api/meetings/{id}/progress`
- `GET /api/meetings/{id}/ideas`
- `GET /api/meetings/{id}/reading-list`
- `GET /api/meetings/{id}/claims`
- `GET /api/meetings/{id}/action-items`
- `POST /api/claims/{id}/verify`
- `GET /api/projects/{id}/briefing`
- `GET /api/projects/{id}/memory`
- `POST /api/deliverables/generate`

## 7. Prompt 约定

- 所有结构化抽取必须要求 JSON 输出。
- 所有 claim 分类必须包含置信标签。
- 所有 idea 落地结果必须包含：
  - `next_actions`
  - `recommended_reading`
  - `validation_metrics`
- 推荐阅读结果必须包含：
  - `title`
  - `reason`
  - `priority`
  - `source_url`
- 所有引用结果必须附带 `source_title + source_url + snippet`。
- 无证据时禁止强行给出肯定判断。

## 8. 测试策略

- 单元测试：
  - transcript 切分
  - 周进展抽取
  - idea 捕获
  - 下周计划生成
  - 推荐阅读生成
  - claim schema 校验
  - evidence card 组装
- 集成测试：
  - 上传 transcript -> 生成周进展和 action items
  - idea -> 生成推荐阅读与行动计划
  - idea -> 在需要时检索证据 -> 输出 verdict
  - project memory -> briefing 生成
- 演示测试：
  - 固定样例项目
  - 固定 transcript
  - 固定输出断言

## 8.1 Agent 功能真实模型验证规则

- 所有 agent 相关功能必须同时具备：
  - 本地单元 / 集成测试
  - 一次真实 `DeepSeek` 请求验证
- 真实验证不能被 mock、recorded fixture 或静态 JSON 替代。
- 真实验证的最低要求：
  - 使用当前 `.env` 中配置的 `DEEPSEEK_API_KEY`
  - 向 `DEEPSEEK_BASE_URL` 发送真实请求
  - 验证返回结果满足预期结构，而不是只验证 HTTP 200
- 建议为每个 agent 功能准备一个最小 live test：
  - `live_progress_extraction_test`
  - `live_idea_capture_test`
  - `live_research_plan_test`
  - `live_reading_recommendation_test`
  - `live_claim_verification_test`
- 所有 live test 在执行后都需要记录：
  - 输入样例
  - 请求时间
  - 返回摘要
  - 是否满足 schema

说明：

- 单元测试负责快速回归。
- live DeepSeek test 负责确认 agent 真实可用。
- 两者缺一不可。

## 8.2 Subagent 协作验证规则

- 如果开发过程中启用了 subagent，则主线程必须在合并结果前完成一次人工复核。
- 复核内容至少包括：
  - 文件范围是否符合约束
  - 功能是否与当前阶段目标一致
  - 是否补齐本地测试
  - 若为 agent 功能，是否完成真实 DeepSeek 请求验证
- subagent 返回的代码不能因为“已完成”而跳过主线程最终测试。
- 最终交付以主线程验证结果为准，而不是以 subagent 自述为准。

## 9. 比赛版本建议

- 优先做“稳定可跑的主链路”，再做可视化增强。
- transcript 回跳、知识地图、导师质询属于高展示功能，可作为第二阶段。
- 比赛现场必须准备离线样例，避免外部检索失败影响 demo。
- 样例 transcript 必须覆盖“学生汇报 -> 导师给 idea -> 生成下周计划”的完整链路。
