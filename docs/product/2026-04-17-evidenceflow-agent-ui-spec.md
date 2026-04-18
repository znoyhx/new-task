# 证据流 Agent UI/UX 设计规格

## 1. 设计目标

- 目标平台：Web，桌面端优先，最小化移动端适配。
- 目标感受：专业、克制、可信、研究感强，不做后台管理系统风格。
- 目标问题：在高信息密度下保持清晰层级，让用户快速完成“导入 -> 理解 -> 计划 -> 导出”。

## 2. 视觉方向

推荐方向：`Research Cockpit`

- 气质：学术工具 + 产品级桌面应用
- 关键词：calm, precise, evidence-driven, structured
- 避免：纯灰白后台、花哨渐变、强营销感、卡片堆砌

### 推荐风格参考

- 信息层级像 `Linear`
- 阅读体验像 `Perplexity`
- 长内容处理像 `Notion`

## 3. 布局原则

采用 `三栏布局`，保持稳定视觉习惯：

- 左栏：项目与组会导航
- 中栏：本次组会主内容流
- 右栏：行动与证据决策面板

### 栅格

- 画布宽度：`1440px` 设计基准
- 主内容最大宽度：`1280px`
- 三栏比例：
  - 左栏 `240px`
  - 中栏 `1fr`
  - 右栏 `360px`
- 页面外边距：`24px`
- 卡片间距：`16px`

### 层级原则

- 中栏永远承载“阅读和理解”
- 右栏永远承载“决策和输出”
- 左栏永远承载“上下文和切换”

## 4. 信息架构

### 4.1 一级导航

- Dashboard
- Meetings
- Students
- Evidence
- Briefings
- Memory

### 4.2 Dashboard 页面模块

中栏顺序：

- 本次组会概览
- 学生周进展卡片流
- 导师新 idea 卡片流
- Transcript 时间线

右栏顺序：

- 下周研究计划
- Action Items
- 推荐阅读
- 风险与阻塞
- 参考依据
- 导出区

### 4.3 Meeting Detail 页面模块

- Header：组会标题、日期、学生、处理状态
- Tab：
  - Summary
  - Progress
  - Ideas
  - Claims
  - Transcript

## 5. 页面设计

### 5.1 Dashboard

作用：快速看清“本周发生了什么、下周该做什么”。

必须有：

- 顶部项目切换器
- 本次组会摘要区
- 每位学生的周进展摘要
- 导师 idea 列表
- 右侧固定输出区

视觉重点：

- 顶部摘要区采用更高权重卡片
- 学生卡片和 idea 卡片统一宽度，不要不同形状混排
- 右栏固定吸附，始终可见
- 右栏的“下周计划”与“推荐阅读”权重高于“参考依据”

### 5.2 Meeting Processing Page

作用：导入会议并完成一次处理。

页面分 3 步：

1. 上传音频或 transcript
2. 处理中状态流
3. 结果审阅与确认

处理中必须展示：

- transcript parsing
- progress extraction
- idea capture
- evidence retrieval
- plan generation

不要只转圈，要展示明确阶段。

### 5.3 Student Research View

作用：看单个学生的研究脉络。

模块：

- 本周目标 vs 实际完成
- 历史导师建议
- 历史实验记录
- 当前主要风险
- 推荐下周计划

这个页面要更像“研究档案”，而不是任务列表。

## 6. 核心组件

### 6.1 Student Progress Card

字段：

- 学生名
- 本周完成项
- 当前结果
- 阻塞点
- 风险等级
- 下一步建议

状态色仅用于风险：

- low
- medium
- high

### 6.2 Advisor Idea Card

字段：

- idea 标题
- 原始建议摘要
- 建议实验动作
- 推荐阅读
- 验证指标
- 当前证据状态

必须有“加入下周计划”按钮。

### 6.3 Evidence Card

字段：

- 结论 / idea
- stance：support / contradict / needs verification
- source title
- source snippet
- source link
- confidence

这是辅助可信感组件。必须像“证据”，不能像普通标签，但视觉权重低于行动计划。

### 6.4 Action Plan Panel

字段：

- 本周目标
- 下周动作
- owner
- due date
- success metrics

右栏中必须优先显示，不可埋太深。

### 6.5 Reading Recommendation Card

字段：

- 论文标题
- 推荐原因
- 建议阅读优先级
- 来源链接

这个组件要比 Evidence Card 更靠近学生任务心智，语气必须是“先看什么、为什么看”。

## 7. 设计系统

### 7.1 色板

建议采用冷中性色 + 单一强调色：

```text
bg.canvas = #F5F7FA
bg.surface = #FFFFFF
bg.subtle = #EEF2F6
text.primary = #17202A
text.secondary = #51606F
text.muted = #7B8794
border.default = #D9E1E8
brand.primary = #2156F3
brand.soft = #E7EEFF
success = #1E8E5A
warning = #B7791F
danger = #C0392B
info = #1F6FEB
```

### 7.2 字体

不建议默认系统 UI 风格。推荐：

- 标题：`IBM Plex Sans` 或 `Manrope`
- 正文：`Inter` 或 `Source Sans 3`
- 代码 / transcript 时间戳：`IBM Plex Mono`

推荐组合：

- `IBM Plex Sans + Source Sans 3 + IBM Plex Mono`

### 7.3 字号层级

```text
display = 32/40 semibold
h1 = 24/32 semibold
h2 = 20/28 semibold
h3 = 16/24 semibold
body = 14/22 regular
small = 12/18 regular
label = 11/16 medium uppercase
```

### 7.4 间距

```text
4, 8, 12, 16, 20, 24, 32, 40
```

### 7.5 圆角与阴影

```text
radius.sm = 8
radius.md = 12
radius.lg = 16
shadow.sm = 0 1px 2px rgba(16,24,40,0.06)
shadow.md = 0 8px 24px rgba(16,24,40,0.08)
```

## 8. 交互规则

### 8.1 Loading

- 所有长操作必须显示阶段，不允许纯 spinner
- transcript 和 evidence 区域使用 skeleton
- 右栏计划区在生成前显示空态引导

### 8.2 Empty

需要覆盖：

- 无组会数据
- 无证据结果
- 无学生历史记录
- 无下周计划

空态文案要有行动导向，例如：

- `Upload a meeting transcript to generate the first research plan.`

### 8.3 Error

- 上传失败
- 转写失败
- 检索失败
- DeepSeek 响应失败

错误展示采用内联错误卡片，不用浏览器弹窗。

### 8.4 可追溯交互

- 点击 evidence card 可定位到 source
- 点击 claim 可高亮 transcript 对应片段
- 点击 action item 可展开来源解释

## 9. 无障碍要求

- 对比度至少满足 WCAG AA
- 所有按钮和 Tab 可键盘访问
- 焦点态必须明显，不可只改边框 1px
- Transcript 时间线必须支持键盘导航
- 颜色不能是唯一信息来源，风险和证据状态必须同时用图标或文案表达

## 10. 实现建议

### 10.1 前端组件建议

- `AppShell`
- `SidebarNav`
- `TopProjectSwitcher`
- `MeetingSummaryHeader`
- `StudentProgressCard`
- `AdvisorIdeaCard`
- `EvidenceCard`
- `TranscriptTimeline`
- `ActionPlanPanel`
- `ExportPanel`

### 10.2 页面建议

- `frontend/src/app/page.tsx`：Dashboard
- `frontend/src/app/meetings/[id]/page.tsx`：Meeting detail
- `frontend/src/app/students/[id]/page.tsx`：Student research view

### 10.3 状态管理

前端状态建议分离：

- UI state：Tab、drawer、selection
- Data state：meeting result、ideas、evidence、briefing

不要把整个页面做成一个超大组件。

## 11. 验收标准

- 第一眼看上去像“研究工作台”，不是后台管理系统
- 主链路在单屏内可理解，不需要来回跳页面
- 证据卡片和下周计划区有明确视觉重点
- 下周计划与推荐阅读区必须比证据区更有视觉重点
- 空态、加载态、错误态完整
- 桌面端 1440px 下布局稳定，移动端至少能堆叠阅读
