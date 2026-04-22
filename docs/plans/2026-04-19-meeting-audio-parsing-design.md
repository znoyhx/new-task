# 会议音频解析功能设计

## 1. 功能定位

会议音频解析不是一个独立产品，而是 EvidenceFlow Agent 主链路的输入增强层。

它的目标不是“做一个通用录音转写工具”，而是让用户可以直接上传组会音频，在本地完成转写与结构化切分，然后无缝进入已有的：

- 周进展提取
- 导师 idea 捕获
- 下周研究计划生成
- 推荐阅读生成
- 可选证据核验
- briefing / deliverable 生成

这件事在 PRD 中本来就是 MVP 范围，因为产品目标已经明确写了“支持导入会议录音或 transcript”。当前计划的问题不是方向错误，而是实现计划对音频链路拆得太粗，只写到了“audio second”，没有把文件上传、本地转写、错误处理、可追溯性和 UI 状态拆成可执行任务。

## 2. 设计目标与边界

### 2.1 P0 目标

- 支持从前端上传会议音频文件，而不只是传本地 `audio_path`
- 后端将原始音频保存到本地工作区，不上传第三方转写服务
- 使用本地转写方案完成音频到 transcript 的转换
- 产出带时间戳的 transcript chunks，直接复用现有下游服务
- 在 UI 中展示明确的“上传 -> 本地转写 -> transcript parsing -> 后续抽取”阶段
- 转写失败、空结果、格式不支持时给出明确错误，而不是静默失败

### 2.2 非目标

- 第一版不做实时会议 bot
- 第一版不做流式转写
- 第一版不承诺准确的多说话人 diarization
- 第一版不做音频剪辑器、播放器波形、逐词字幕编辑器
- 第一版不引入必须联网或付费的转写服务

## 3. 用户流

### 3.1 导入流

1. 用户在 Meeting Processing Page 选择输入类型：
   - transcript
   - audio
2. 如果选择 audio，则上传本地音频文件
3. 前端显示文件名、大小和处理中阶段
4. 后端保存原始音频并执行本地转写
5. 后端把转写结果标准化成 `ParsedTranscript`
6. 页面进入审阅态，用户可以看到 transcript 时间线
7. 用户继续运行 review 流程，生成周进展、idea、计划、阅读和交付物

### 3.2 失败流

- 文件格式不支持：在上传阶段直接失败
- 音频文件为空或损坏：在转写阶段失败
- 本地转写后没有可用文本：在 transcript parsing 前失败
- 长音频超出限制：在服务端校验阶段失败

错误必须以内联卡片显示，遵守 UI spec 中的错误态要求，不使用浏览器弹窗。

## 4. 后端设计

### 4.1 API 设计

保留现有 `POST /api/meetings/import` 用于 JSON 方式的 transcript / `audio_path` 导入，新增专门的浏览器上传端点：

- `POST /api/meetings/import-audio`

建议使用 `multipart/form-data`：

- `file`: 音频文件
- `meeting_title`: 可选
- `language_hint`: 可选，默认自动

这样可以避免把现有 JSON 导入接口改成混合协议，降低对已有测试和前端调用的破坏。

### 4.2 存储设计

每次音频导入在本地创建独立目录：

```text
data/local_db/meetings/{meeting_id}/
  meeting.json
  source/
    original.<ext>
  transcript.txt
  transcript_chunks.json
  transcription_metadata.json
```

其中：

- `source/original.<ext>` 保存原始音频
- `transcript.txt` 保存转写出的纯文本
- `transcript_chunks.json` 保存切分后的 chunk
- `transcription_metadata.json` 保存转写后端、语言提示、耗时、警告信息

### 4.3 schema 扩展建议

在 `MeetingRecord` 中补充以下字段：

- `audio_filename`
- `audio_content_type`
- `audio_size_bytes`
- `transcription_backend`
- `transcription_language`
- `transcription_status`
- `transcription_warning_messages`

如果不想让 `MeetingRecord` 过重，也可以新增一个 `TranscriptionMetadata` schema 并用文件持久化。MVP 更建议新增 metadata 文件，减少对既有 meeting schema 的耦合修改。

### 4.4 服务边界

建议沿用现有边界，不新增大范围重构：

- `backend/api/meetings.py`
  - 新增上传接口
- `backend/services/transcription_service.py`
  - 增加 `import_uploaded_audio(...)`
  - 负责保存文件、调用转写 adapter、落盘 transcript 和 metadata
- `backend/adapters/whisper_adapter.py`
  - 真正实现本地转写
  - 统一输出 `text + segments`
- `backend/services/transcript_parser_service.py`
  - 继续只负责 transcript 标准化，不耦合文件上传

这个分层满足约束文档中“所有外部能力通过 adapter 封装”的要求。

## 5. 转写与切分策略

### 5.1 支持格式

P0 建议支持：

- `.mp3`
- `.wav`
- `.m4a`
- `.mp4`
- `.webm`

服务端应基于扩展名和 MIME type 双重校验，但不要只依赖前端 accept。

### 5.2 本地转写后端

默认后端继续使用文档既定方案：

- `faster-whisper`

保留 `whisper.cpp` 作为可切换 backend，但不要求在第一轮同时完成双实现。MVP 只要 adapter 边界可切换即可。

### 5.3 分段规则

转写 adapter 返回的 segment 至少包含：

- `text`
- `start`
- `end`

如果转写后端提供更多字段，可以额外接收：

- `avg_logprob`
- `no_speech_prob`
- `language`

然后在 `TranscriptionService` 中映射为 `TranscriptChunk`。

### 5.4 说话人策略

第一版不要把“精确说话人识别”绑定到音频解析是否可用。

P0 策略：

- 如果转写后端返回 speaker，则直接保留
- 如果没有 speaker，则写入 `Unknown`
- 下游 agent 允许基于文本内容推断角色，但音频解析层本身不伪造姓名

这样能避免为了 diarization 引入额外重型依赖，符合当前约束。

## 6. 前端设计

### 6.1 入口变化

在现有 Meeting Processing Page 的上传面板中加入输入类型切换：

- `Transcript`
- `Audio`

当选择 `Audio` 时：

- 隐藏 transcript 大文本框
- 显示音频文件选择器
- 显示支持格式说明
- 显示本地转写提示文案

### 6.2 阶段态变化

如果本次导入是音频，则处理中阶段调整为：

1. audio upload
2. local transcription
3. transcript parsing
4. progress extraction
5. idea capture
6. evidence retrieval
7. plan generation

如果本次导入是 transcript，则保留较短链路。

### 6.3 审阅态

音频导入完成后，仍然要落到和 transcript 一致的审阅界面：

- transcript timeline
- student progress
- advisor ideas
- right-column action plan / evidence / deliverables

这样能保持 UI spec 里的主链路一致，不需要为了音频输入另开一套页面。

## 7. 测试与验证策略

### 7.1 本地测试

至少补齐：

- `whisper_adapter` 输出标准化测试
- `transcription_service` 音频导入测试
- `meetings API` 的 multipart 上传测试
- 音频导入后生成 `ParsedTranscript` 的集成测试

### 7.2 音频样例

演示和测试不能使用私有组会录音。应使用：

- 自行录制的公开可提交样例
- 或合成 / 清洗后的短音频样例

并在 `data/samples/` 下同时提供：

- 样例音频
- 对应期望 transcript 摘要

### 7.3 live test 要求

转写本身是本地能力，不需要 DeepSeek live test。

但一旦音频导入链路触发了 agent 输出，就必须在音频输入场景下至少跑一次真实 DeepSeek 验证，例如：

- `audio -> import -> review`
- 验证 progress extraction / idea capture / research plan 可以基于音频转写结果正常工作

换句话说：

- 本地转写能力靠本地测试验收
- 音频驱动的 agent 主链路靠 DeepSeek live test 验收

## 8. 风险与取舍

### 8.1 已知风险

- 中文组会、多人插话、口语缩写会降低转写质量
- 没有 diarization 时，下游按学生拆分可能变差
- 长音频会让处理时延明显上升

### 8.2 本轮取舍

第一版优先完成：

- 音频可上传
- 本地可转写
- transcript 可进入既有主链路
- 失败态清晰

暂不追求：

- 精准说话人分离
- 音频回放对齐
- 高级编辑器能力

## 9. 对 implementation plan 的落点

建议不要重排已存在的任务编号，避免和前面阶段执行记录冲突。

推荐增量方式：

- 在 Task 3 后新增 `Task 3A: Implement Meeting Audio Parsing and Upload Flow`
- 在 Task 9 中补充音频导入 UI
- 在 Task 10 中补充样例音频和音频端到端验证

这样既符合当前产品文档，也能保持已有任务 6/7/8/9/10 的历史引用稳定。
