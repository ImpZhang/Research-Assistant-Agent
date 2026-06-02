# SuperMew 科研助手需求拆解文档

版本：v0.1  
日期：2026-05-28  
状态：架构升级规划稿  
目标项目：`/home/zhangwz/SuperMew-main`

## 1. 文档目标

本文档用于把 SuperMew 从当前的「文档问答 RAG」升级为「基于文献证据的科研 idea 助手」所需的产品目标、用户场景、功能边界、模块拆分、迭代优先级和验收标准梳理清楚。

本文档回答的问题是：

- SuperMew 最终要解决什么问题？
- 当前项目和目标形态之间差在哪里？
- 需要新增哪些能力？
- 每个能力的输入、输出、交互方式和验收标准是什么？
- 哪些功能先做，哪些功能后做？

技术架构、技术选型和实现方案见配套文档：

- `docs/research_assistant_technical_design.md`

## 2. 背景与现状

### 2.1 当前项目现状

当前 SuperMew 已具备一个相对完整的 RAG 应用骨架：

- FastAPI 后端。
- Vue 3 CDN 单页前端。
- 文档上传与管理。
- PDF/Word 文档解析。
- 三级滑动窗口分块。
- Milvus/Milvus Lite 向量存储。
- dense embedding + BM25 sparse embedding。
- hybrid retrieve + rerank。
- Step-back / HyDE 查询扩展。
- LangGraph RAG 流程。
- SSE 流式输出。
- RAG trace 前端可视化。
- 会话历史保存。
- 离线 RAG 评测脚本。

这说明项目已经不是空壳 demo。但当前核心价值仍集中在「如何检索对 chunk」和「如何回答文档问题」，还没有进入真正科研助手的核心场景。

### 2.2 当前主要问题

当前系统的主要瓶颈不是「没有 RAG」，而是：

1. **知识表示太低层**
   - 当前主要存储 chunk。
   - 系统不知道一篇论文的研究问题、方法、贡献、数据集、指标、局限和未来工作。
   - 系统回答时依赖检索到的文本片段，而不是依赖结构化的论文理解。

2. **检索逻辑存在 hard-coded 调题痕迹**
   - `backend/rag_utils.py` 中有大量针对具体论文、问题短语和 root chunk id 的加分逻辑。
   - 这有利于小评测集，但不利于扩展到新领域、新论文和真实科研任务。

3. **缺少科研工作流**
   - 当前用户主要能「问文档问题」。
   - 不能系统地完成「读论文 -> 找 gap -> 生成 idea -> 审稿人批评 -> 实验设计」。

4. **缺少 idea 管理**
   - idea 不是一等对象。
   - 没有 idea 的证据、评分、版本、审稿反馈、实验计划和状态流转。

5. **外部文献发现能力不足**
   - 当前主要依赖用户上传文献。
   - 还不能自动检索最新相关工作、查引用、查代码实现、管理 Zotero 文献库。

## 3. 产品定位

### 3.1 一句话定位

SuperMew 是一个 **基于论文证据的科研 idea 工作流助手**。

它不是普通聊天机器人，也不是单纯 RAG 问答系统，而是帮助研究者完成：

```text
文献理解 -> 研究空白发现 -> idea 生成 -> idea 批判 -> 实验设计 -> proposal 雏形
```

### 3.2 核心价值主张

SuperMew 应该做到：

- 能读懂论文结构，而不只是检索文本。
- 能从多篇论文中发现研究空白。
- 能生成有证据支撑的科研 idea。
- 能模拟审稿人提前攻击 idea。
- 能把 idea 转成可执行实验计划。
- 能长期记住用户的研究方向、资源限制和偏好。

### 3.3 不做什么

短期内不追求：

- 变成通用办公助手。
- 变成大而全的 AutoGPT。
- 一开始就自动完成整篇论文写作。
- 一开始就接入复杂多 agent 框架。
- 一开始就上完整 GraphRAG/Neo4j/DeerFlow。

项目核心应先聚焦科研链路，避免工具越接越多但主线变散。

## 4. 用户画像与核心场景

### 4.1 目标用户

第一阶段主要服务以下用户：

1. **研究生/博士生**
   - 需要快速理解一个方向。
   - 需要从已有论文中找到可做的题。
   - 需要判断 idea 是否有 novelty。

2. **科研初学者**
   - 有方向但不知道如何提出研究问题。
   - 需要把「灵感」变成可检验的实验计划。

3. **已有项目方向的研究者**
   - 已经有一批论文。
   - 希望系统帮忙整理 related work、找 gap、构造 proposal。

4. **开发者本人**
   - 当前项目知识库以图像地理定位、视觉语言模型、RAG 检索为主。
   - 需要从现有文献出发，形成更像科研项目的系统。

### 4.2 核心使用场景

#### 场景 A：上传一批论文，系统自动建立文献库

用户上传 5-50 篇论文，系统自动：

- 解析 PDF。
- 识别章节。
- 生成论文卡片。
- 提取 claim、method、dataset、metric、result、limitation、future work。
- 生成 evidence 对象。
- 建立向量索引和轻量关系图。

#### 场景 B：问一个文献问题

用户问：

```text
GeoCLIP 和 GeoRanker 的核心区别是什么？
```

系统应输出：

- 直接答案。
- 对比维度。
- 每个结论的证据。
- 相关论文和页码。
- 如证据不足，明确说明不足。

#### 场景 C：找研究空白

用户问：

```text
基于这些地理定位论文，有哪些值得做的 research gap？
```

系统应输出多个 gap：

- gap 描述。
- 支撑证据。
- 涉及论文。
- 为什么重要。
- 为什么目前没解决。
- 可行性初评。
- 可衍生 idea。

#### 场景 D：生成科研 idea

用户选择一个 gap 后，系统生成 idea：

- 研究问题。
- 核心假设。
- 方法草图。
- 和已有工作的区别。
- 数据集。
- baseline。
- metric。
- 风险。
- 投稿方向。
- 证据引用。

#### 场景 E：模拟审稿人

用户要求：

```text
以 NeurIPS/CVPR 审稿人视角批评这个 idea。
```

系统应输出：

- novelty 风险。
- technical depth 风险。
- experiment 风险。
- baseline 风险。
- claim 风险。
- rebuttal 建议。
- idea 修改建议。

#### 场景 F：转成实验计划

系统从 idea 生成：

- 实验目标。
- 数据集选择。
- baseline 列表。
- ablation 表。
- evaluation metrics。
- 预期结果表格。
- 实验优先级。
- 失败后的 fallback plan。

## 5. 总体能力地图

SuperMew 升级后的能力分为六大域：

```text
1. 文献摄入与结构化
2. 证据检索与问答
3. 多论文对比与知识图谱
4. Research gap 挖掘
5. Idea 生成、评分与审稿
6. 实验设计与长期科研记忆
```

## 6. 功能需求拆解

## 6.1 文献摄入与结构化

### 6.1.1 论文上传

当前已有基础上传能力，需要增强：

输入：

- PDF。
- Word 文档。
- 后续支持 arXiv URL、DOI、Semantic Scholar paper id、Zotero item。

输出：

- 原始文件。
- 文档解析结果。
- 章节结构。
- chunk。
- evidence。
- paper card。

验收标准：

- 上传论文后系统能在文献库中显示。
- 能看到论文标题、作者、年份、venue、摘要。
- 能看到论文结构化字段。
- 解析失败时给出明确错误原因。

### 6.1.2 章节识别

需要识别常见论文章节：

- Abstract。
- Introduction。
- Related Work。
- Method。
- Experiment。
- Results。
- Discussion。
- Limitations。
- Conclusion。
- References。
- Appendix。

输入：

- 论文全文文本。
- 页码信息。

输出：

```json
{
  "section_id": "sec_method_001",
  "paper_id": "paper_xxx",
  "title": "Method",
  "level": 1,
  "page_start": 3,
  "page_end": 5,
  "text_span": "...",
  "section_type": "method"
}
```

验收标准：

- 对常见论文能粗略识别主要章节。
- 章节识别错误不阻断上传。
- chunk 保留 section_id 和 section_type。

### 6.1.3 Paper Card 抽取

Paper Card 是科研助手的基础对象。

字段：

```text
paper_id
title
authors
year
venue
domain
task
problem
motivation
main_contributions
method_summary
datasets
metrics
baselines
key_results
limitations
future_work
keywords
open_questions
```

每个字段都需要尽量附带 evidence：

```json
{
  "claim": "The paper proposes an image-to-GPS retrieval approach.",
  "evidence_ids": ["ev_001", "ev_002"],
  "confidence": 0.86
}
```

验收标准：

- 每篇论文生成一个 card。
- card 中关键字段能在原文中找到对应 evidence。
- 用户可以查看 card 原始证据。
- 抽取失败字段允许为空，但要记录缺失原因。

### 6.1.4 Evidence 对象

Evidence 是比 chunk 更高级的证据单位。

字段：

```text
evidence_id
paper_id
section_id
chunk_id
page_number
evidence_type
text
summary
supports
confidence
```

evidence_type 可选：

```text
problem
motivation
claim
method
dataset
metric
result
limitation
future_work
citation
definition
comparison
```

验收标准：

- 问答、gap、idea、review 输出中的关键判断都能追溯到 evidence。
- evidence 可以被向量检索。
- evidence 可以被结构化过滤。

## 6.2 证据检索与问答

### 6.2.1 查询意图识别

系统需要识别用户问题类型：

```text
fact_lookup
paper_summary
paper_comparison
method_explanation
experiment_analysis
limitation_query
gap_query
idea_generation
idea_review
experiment_design
general_chat
```

验收标准：

- 普通聊天不强行走复杂 RAG。
- 文献问题走 evidence 检索。
- gap/idea/review 类问题进入对应工作流。
- 长流程必须以 job 形式暴露状态，并支持取消 pending/running job、重试 failed/canceled job，避免研究工作台或外部 agent 只能盲等。

### 6.2.2 Evidence-first 检索

当前是：

```text
query -> chunk
```

目标是：

```text
query -> evidence -> related paper card -> related chunks -> answer
```

检索流程：

1. 意图识别。
2. query rewrite。
3. evidence vector retrieval。
4. metadata filter。
5. rerank。
6. graph neighbor expansion。
7. answer synthesis。

验收标准：

- 回答中至少列出关键证据来源。
- 证据不足时明确说明。
- 同一问题能返回更稳定的 evidence，而不是依赖 hard-coded root chunk bonus。

### 6.2.3 多论文对比问答

支持问题：

- A 和 B 的方法区别是什么？
- 哪些论文用了同一数据集？
- 哪些论文解决的是同一个 problem？
- 哪些论文的 limitation 相似？

输出格式：

```text
结论摘要
对比表格
关键差异
证据来源
不确定项
```

验收标准：

- 能自动选择多篇 paper card。
- 输出中包含结构化对比表。
- 每个关键差异至少有一个 evidence。

## 6.3 文献对比矩阵

### 6.3.1 方向级文献矩阵

输入：

- 用户选择一批论文。
- 或输入一个研究方向。

输出：

```text
Paper
Problem
Method
Dataset
Metric
Key Result
Limitation
Future Work
Possible Gap
```

验收标准：

- 可以导出 Markdown。
- 支持按字段排序和筛选。
- 矩阵中的单元格可以点开证据。

### 6.3.2 方法流派聚类

系统应能把论文按路线归类：

```text
classification-based
retrieval-based
contrastive learning
vision-language model
reranking
human reasoning / MLLM
```

验收标准：

- 聚类结果可解释。
- 每个 cluster 有代表论文、共同假设、优点和局限。

## 6.4 Research Gap Miner

### 6.4.1 Gap 来源

系统从以下来源挖 gap：

- limitation。
- future work。
- 不同论文之间的矛盾。
- 数据集/场景覆盖不足。
- metric 不一致。
- baseline 不完整。
- 真实场景与 benchmark 的差距。
- 新模型能力和旧任务设定之间的错位。

### 6.4.2 Gap 对象

字段：

```text
gap_id
title
description
gap_type
source_papers
evidence_ids
why_important
why_unsolved
possible_approaches
feasibility
novelty_potential
risk
related_ideas
```

gap_type：

```text
method_gap
dataset_gap
evaluation_gap
application_gap
theory_gap
robustness_gap
efficiency_gap
multimodal_gap
reproducibility_gap
```

验收标准：

- 每个 gap 至少有 2 条证据，除非来自单篇论文的明确 limitation。
- gap 不是简单复述 future work，而要解释「为什么这是研究机会」。
- gap 能进一步生成 idea。

### 6.4.3 Gap 输出格式

示例：

```text
Gap: 全球图像地理定位中的候选生成与人类推理缺少统一评估

证据：
- Paper A 指出 retrieval candidate 在全球规模下成本高。
- Paper B 使用 MLLM reasoning 但缺少和 retrieval pipeline 的系统对比。

为什么重要：
- 当前方法把视觉检索、文本地理知识、人类推理分开评估。

可能研究问题：
- 能否构建一个统一框架，让模型在候选生成、候选排序和推理解释之间共享地理证据？
```

## 6.5 Idea Generator

### 6.5.1 Idea 生成输入

输入可以来自：

- 一个 gap。
- 一组论文。
- 一个用户方向。
- 一个用户草稿。
- 一个失败实验。
- 一个审稿意见。

### 6.5.2 Idea 对象

字段：

```text
idea_id
title
research_question
core_hypothesis
motivation
related_gaps
related_papers
evidence_ids
method_sketch
expected_contribution
novelty_argument
datasets
baselines
metrics
experiment_plan_summary
risks
resource_requirements
target_venues
status
version
created_at
updated_at
```

### 6.5.3 Idea 质量要求

一个合格 idea 必须具备：

- 明确研究问题。
- 可检验假设。
- 和已有工作的差异。
- 可执行实验路径。
- 支撑证据。
- 风险说明。

不合格 idea：

- 只是「把 A 和 B 结合」。
- 没有实验验证方式。
- 没有和已有工作的差异。
- claim 太大但证据弱。
- 完全依赖模型幻想。

每个进入 shortlist 的 idea 应进一步生成 related-work matrix：

- 列出最相似的本地 evidence、gap、idea 和 literature search 结果。
- 说明 overlap score、shared terms、relevance 和 differentiator。
- 记录 checked sources 和 missing searches，避免把未检索当作 novelty。
- 支持 Markdown 导出，用于 proposal、组会和导师 review。

进入 proposal 阶段的 idea 需要生成 proposal draft：

- 自动汇总 abstract、problem statement、novelty claim、method 和 experiment plan。
- 引用最新或指定的 related-work matrix，说明 related-work positioning。
- 输出 risk mitigation 与 30/60/90 天 milestone。
- 保存为可复查 artifact，而不是一次性聊天回答。

proposal draft 需要支持 readiness review：

- 给出 advisor-style decision 和 readiness score。
- 列出 strengths、concerns、required revisions 和 missing evidence。
- 把 review 结果保存并导出 Markdown，形成下一轮 refinement 输入。

readiness review 之后需要 proposal revision：

- 读取指定或最新 review 的 required revisions。
- 生成 revised abstract、novelty statement、related-work summary、experiment summary 和 risk mitigation。
- 保留 applied revisions 与 missing-evidence actions，形成可比较的 revision checkpoint。

proposal revision 之后需要进入 task backlog：

- 将 applied revisions、missing evidence 和 milestones 拆成研究任务。
- 每个任务需要 status、priority、due phase、source id 和 owner id。
- 支持查询、推进状态和后续看板扩展。

任务执行需要 event log：

- 创建任务时记录 created event。
- 更新任务状态、优先级或描述时记录 task_updated event。
- 支持手动追加 progress、blocker、decision、evidence 等事件。
- 后续 task board 和 agent executor 应基于 event history 判断真实进展。

任务需要支持 board snapshot：

- 固化某一时刻的 task ids、status summary、priority summary 和 next actions。
- 支持 Markdown 导出，用于组会汇报或个人周报。
- 后续可接提醒、MCP task 工具或自动执行器。

实验计划之后需要支持 experiment run：

- 将 experiment plan 的一次执行保存为 run artifact。
- run 需要记录 status、task id、dataset snapshot、parameters、metric results、artifact links、conclusion 和 notes。
- run 创建和更新时应写入关联 task 的 event log，避免实验结果只存在聊天记录或本地文件名里。
- run 需要支持 Markdown 导出，用于实验日志、组会和论文复现实验记录。

实验运行之后需要支持 experiment analysis：

- 自动把 run metrics、status、conclusion 和 artifact 完整性转成科研判断。
- analysis 需要输出 decision、confidence、metric interpretation、key findings、concerns 和 next actions。
- analysis 创建时应写入关联 task 的 event log，让“为什么继续/修改/补证据”有记录。
- analysis 需要支持 Markdown 导出，用于组会决策、导师沟通和后续 proposal revision。
- analysis 的 next actions 需要能一键生成下一轮 research tasks，让实验结论进入执行队列。

idea 需要支持 decision memo：

- 记录 pursue、revise、park、reject 等阶段性决策。
- 自动汇总 latest feedback、novelty check、review、experiment analysis、open tasks 作为 source artifacts。
- 保存 rationale、evidence ids、risk register 和 next commitments。
- next commitments 需要能一键生成下一轮 research tasks，让决策进入执行队列。
- 支持 Markdown 导出，并进入 GraphRAG-lite，避免“为什么选/不选这个方向”只留在聊天记录中。

idea 需要支持 assumption audit：

- 显式列出核心假设、为什么重要、验证信号、风险等级和当前状态。
- 自动汇总 latest experiment plan、novelty check、proposal review、experiment analysis、related-work matrix 作为 source artifacts。
- 至少覆盖 core hypothesis、novelty differentiation、evidence sufficiency、evaluation validity 和 resource feasibility。
- 支持 Markdown 导出，并进入 GraphRAG-lite，避免“这个方向必须满足什么条件才值得继续”停留在隐含判断里。

idea 需要支持 evidence ledger：

- 将 core hypothesis、novelty argument、expected contribution、proposal draft sections 等压成 claim-level ledger。
- 自动连接 idea 已挂载的 evidence ids，并标注每个 claim 的 support level、supporting evidence ids 和 next validation。
- 自动汇总 novelty collision signals、proposal review concerns、experiment analysis concerns、related-work missing searches 和 assumption audit 高风险项，形成 counterevidence、missing evidence 与 risk register。
- 输出 coverage score、decision hint、Markdown export，并进入 idea lineage、progress、research packet、idea bundle 和 advisor brief。
- 在 GraphRAG-lite 中写入 `idea_has_evidence_ledger`、`evidence_ledger_tracks_claim`、`evidence_supports_claim` 边，方便后续 MCP/agent 查询“某个科研主张由哪些证据支撑”。

proposal、review、revision、experiment run、experiment analysis、task 和 task snapshot 都需要进入 GraphRAG-lite：

- idea 可以追踪到 proposal draft。
- proposal draft 可以追踪到 review 和 revision。
- revision 可以追踪到 research tasks。
- experiment plan 可以追踪到具体 experiment run。
- experiment run 可以追踪到 experiment analysis。
- research task 可以追踪到支撑它的 experiment run。
- research task 可以追踪到基于实验结果生成的 analysis。
- experiment analysis 可以追踪到它生成的 follow-up tasks。
- idea 可以追踪到 decision memo。
- decision memo 可以追踪到它生成的 follow-up tasks。
- idea 可以追踪到 assumption audit。
- idea 可以追踪到 evidence ledger。
- evidence ledger 可以追踪到 claim，evidence 可以追踪到它支持的 claim。
- task snapshot 可以追踪到当时的任务集合。

系统需要提供 idea lineage：

- 一次性返回 idea 的 related work、proposal、review、revision、experiment run、experiment analysis、decision memo、assumption audit、evidence ledger、task、snapshot。
- 返回 graph edge summary，说明研究对象之间的演化关系。
- 支持 Markdown 导出，用于科研日志、导师沟通和 MCP 上下文。

系统需要提供 idea progress summary：

- 聚合 artifact counts、latest artifacts、task summary、experiment summary、blockers 和 recommended next step。
- 用于前端 dashboard、MCP tool 和自动 planner 判断一个研究方向当前卡在哪里。
- Markdown 导出必须包含可追踪 task id，方便组会和周报直接引用。

系统需要提供 idea research packet：

- 聚合 latest artifacts、open tasks、graph edge summary 和 Markdown context。
- 必须包含 latest decision memo、assumption audit 与 evidence ledger 的摘要入口。
- 用于导师讨论、MCP tool 或外部 planner 的第一段上下文，而不是让调用方自己拼多个端点。

系统需要提供 idea readiness scoring：

- 综合 evidence、novelty、proposal review、experiment analysis、decision memo、assumption audit、evidence ledger 和 task health。
- 输出总分、决策标签、score breakdown、blockers 和 Markdown report。
- 用于判断一个 idea 是否 ready_for_execution，还是需要 targeted work、park 或 reject。

系统需要提供 idea quality gate：

- 综合 novelty refresh、readiness、proposal review、experiment analysis、decision memo、assumption audit、evidence ledger 和 task health。
- 输出 gate score、advance/revise/de-risk/park/reject 决策、required evidence、blocking risks、recommended actions 和 Markdown report。
- 用于回答“这个 idea 现在是否值得继续投入实验/写作资源”，比 readiness 更接近 go/no-go 决策。

系统需要支持 quality gate task generation：quality gate 产出的 recommended actions 需要能一键转成 `owner_type=idea_quality_gate`、`due_phase=quality_gate_follow_up` 的任务，并写入 `quality_gate_creates_task` 图边。这样 go/no-go 判断不会停在报告里，而能直接进入去风险行动。

系统需要提供 project readiness overview：

- 对最近 idea 逐个计算 readiness summary。
- 输出 average readiness、decision counts、top ready ideas 和 needs-work ideas。
- 用于选题组合管理和 dashboard 首页判断哪些方向值得继续投入。

系统需要提供 project quality gate overview：

- 对最近 idea 逐个运行 quality gate summary。
- 输出 average gate score、decision counts、advance candidates、de-risk candidates、revision candidates 和 parked/rejected ideas。
- 用于回答“当前组合里哪些 idea 可以继续投入、哪些必须先补 novelty/evidence/experiment/decision 证据”，比 readiness overview 更接近 portfolio 级 go/no-go 判断。

project quality gate overview 需要能一键转成 task board 任务：从 de-risk/revision/指定 decision candidates 的 top actions 创建 `owner_type=idea_quality_gate`、`due_phase=quality_gate_follow_up` 的任务。这样 portfolio 级判断可以直接落到多个 idea 的行动队列。

系统需要提供 project progress overview：

- 聚合全部 idea status、open tasks、blocked tasks、recent experiment analyses 和 recommended actions。
- 用于快速判断整个科研项目今天应该推进什么，而不是逐个点开 idea。
- 后续 MCP/agent planner 应优先读取 overview，再进入具体 idea progress。

系统需要提供 project triage brief：

- 聚合 progress overview、project readiness overview、project quality gate overview 和 opportunity radar。
- 输出 recommended focus、risk focus、next actions 和 Markdown brief。
- 需要提供 `text/markdown` 导出入口，方便导师沟通、备份和外部 agent/MCP 工具直接消费。
- 用于回答“今天/本轮到底先做哪几件事”，作为人类工作台和外部 agent/MCP planner 的第一跳入口。

project triage brief 需要能一键转成 task board 任务：从 next actions 和 risk focus 创建 `owner_type=project_triage`、`due_phase=triage_follow_up` 的项目级任务，并写入 `project_triage_creates_task` 图边。这样每日 triage 结果能直接进入执行队列。

系统需要提供 persisted project triage snapshot：把某一次 project triage brief 固化为可追溯 artifact，保存 summary、recommended focus、risk focus、next actions、source task ids 和 Markdown export。snapshot 需要支持创建、列表、详情和 Markdown 导出，避免“今天为什么先做这些事”的判断被后续任务状态覆盖。

project triage snapshots 需要支持 comparison：输入 baseline snapshot 和 candidate snapshot，输出 readiness、quality、task、opportunity 等指标 delta，以及 recommended focus、risk focus、next actions 的 added/removed/kept 列表和 Markdown report。它用于日/周复盘和导师沟通，回答“这一轮判断相比上一轮到底变了什么”。

project triage snapshot comparison 需要能一键转成 task board 任务：从 added next actions、added risks 和 added focus 创建 `owner_type=project_triage_comparison`、`due_phase=triage_change_follow_up` 的项目级任务，并写入 `project_triage_comparison_creates_task` 图边。这样“本轮新增变化 -> 需要处理的任务”形成闭环。

系统需要提供 research opportunity radar：

- 聚合 profile-aware ranking、idea readiness、open/blocked tasks 和 readiness blockers。
- 输出 top opportunities、risk watchlist、recommended sequence 和 Markdown report。
- 用于回答“今天最值得推进哪个 idea、为什么现在推进、第一步做什么”，而不是只给静态排名或静态 readiness 分数。

opportunity radar 需要能一键转成 task board 任务：从 top opportunities 的 next actions 创建 `owner_type=opportunity_radar`、`due_phase=opportunity_follow_up` 的任务，并写入 `opportunity_radar_creates_task` 图边。这样“机会判断 -> 行动建议 -> 任务推进”形成闭环。

系统需要提供 project handoff bundle export：把 triage brief、persisted triage snapshots、latest triage snapshot comparison、progress overview、readiness overview、quality gate overview、opportunity radar、recent task board、advisor briefs、research plans、plan progress reports 和 JSON metadata 打包成 zip，用于项目级备份、导师沟通和外部 agent/MCP 接手。

系统需要支持 readiness blocker task generation：readiness 评分产出的 blockers 不能只停留在报告里，应能一键转成 task board 任务，并带上 readiness_score、decision、owner_type=idea_readiness、due_phase=readiness_follow_up 和图边 `idea_readiness_creates_task`，保证“评分 -> 阻塞项 -> 可执行任务”闭环。

系统需要支持 novelty refresh：研究者应能对任意 idea 重新运行 local/external literature collision search，指定 query override 和 limit，并把结果保存为 `completed_external_novelty_refresh` 类型的 novelty check。这样 idea 进入 proposal 或执行计划前，可以按最新问题表述重新检查撞车风险。

novelty check 需要能一键转成 task board 任务：把 recommended actions 写入 `owner_type=novelty_check`、`due_phase=novelty_follow_up` 的任务，并通过 `novelty_check_creates_task` 图边连接。这样撞车风险、外部搜索缺口和 novelty claim 修改不会只停留在报告里。

Workbench 需要提供最小可用 task board：能按当前 idea 和状态读取任务，选择任务，并把任务更新为 doing、done 或 blocked。所有操作必须走同一套 `/research/tasks` API，避免前端维护第二份任务状态。

系统需要提供 idea activity timeline：按时间聚合 proposal、experiment、decision、assumption audit、evidence ledger、research plan 和 task event，返回结构化 events 与 Markdown 日志，用于导师汇报、handoff 和后续 agent 接手时快速理解一个 idea 的历史。

系统需要提供 advisor brief：

- 将选定 idea 或项目级状态固化成 Markdown brief。
- brief 需要包含 idea 列表、最近实验判断、高优先级开放任务和 discussion prompts。
- brief 需要包含相关 research execution plans、plan task progress、readiness signals、evidence ledger signals、triage signals 和 latest triage snapshot comparison。
- brief 需要持久化，避免组会/导师沟通时报告内容被后续任务状态改变。

### 6.5.4 Idea 输出模板

```text
Title:

Research Question:

Core Hypothesis:

Motivation:

Evidence:

Difference from Prior Work:

Method Sketch:

Datasets:

Baselines:

Metrics:

Expected Contribution:

Main Risks:

First Experiment:

Target Venues:
```

## 6.6 Idea Scorer

### 6.6.1 评分维度

每个 idea 评分：

```text
novelty: 1-5
feasibility: 1-5
impact: 1-5
evidence_support: 1-5
experimental_verifiability: 1-5
resource_cost: 1-5
publication_potential: 1-5
overall_score: 1-5
```

### 6.6.2 评分解释

每个分数必须给出：

- 为什么给这个分。
- 主要风险。
- 如何提升分数。
- 依赖哪些证据。

验收标准：

- 评分不是只有数字。
- 对高风险 idea 能明确指出问题。
- 能给出改进路径。

## 6.7 Reviewer Simulator

### 6.7.1 审稿角色

支持多个审稿视角：

```text
Novelty Reviewer
Method Reviewer
Experiment Reviewer
Domain Expert
Skeptical Area Chair
Engineering Feasibility Reviewer
```

### 6.7.2 输出内容

每个 reviewer 输出：

```text
主要质疑
严重程度
证据依据
可能导致拒稿的原因
如何修改 idea
需要补充的实验
```

### 6.7.3 汇总决策

系统给出最终建议：

```text
Accept as promising
Revise
High risk
Not recommended
```

验收标准：

- 批评不能泛泛而谈。
- 必须指出具体 novelty/experiment/baseline 问题。
- 必须给出修改建议。

## 6.8 Experiment Designer

### 6.8.1 实验计划对象

字段：

```text
experiment_plan_id
idea_id
objective
hypothesis
datasets
baselines
metrics
main_experiment
ablation_studies
robustness_tests
efficiency_tests
expected_tables
failure_modes
fallback_plan
compute_requirements
timeline
```

### 6.8.2 输出内容

```text
实验目标
实验设置
数据集选择理由
baseline 选择理由
metric 选择理由
主实验表格
消融实验表格
鲁棒性实验
失败风险
最小可行实验 MVP
```

验收标准：

- 每个 idea 至少能生成一个 MVP 实验。
- baseline 不应只列强模型，还要列直接相关方法。
- 实验计划能区分「必须做」和「加分项」。

## 6.9 Research Memory

### 6.9.1 用户长期记忆

记住：

- 用户研究方向。
- 已上传论文。
- 读过的论文。
- 收藏的 idea。
- 否掉的 idea。
- 资源条件。
- 偏好的方法。
- 目标会议。

### 6.9.2 记忆使用原则

- 不把短期聊天当长期偏好。
- 重要记忆要可查看、可删除。
- idea 生成时使用用户资源约束。

验收标准：

- 同一个用户多次使用后，idea 更贴近其方向。
- 用户可以查看当前系统记住了什么。

## 6.10 外部文献发现

后续通过 MCP 或 API 接入：

- arXiv。
- Semantic Scholar。
- Zotero。
- GitHub。
- 浏览器搜索。

短期不作为核心依赖。当前外部 literature search adapter 至少需要支持 OpenAlex、arXiv 与 Semantic Scholar，并且必须可通过环境变量关闭，保证本地测试和无外网环境仍可运行。

在正式接 MCP server 之前，系统必须先暴露一个轻量 tool manifest，列出稳定 tool name、HTTP method/path、输入/输出 schema 名称、是否有写入副作用。这样 DeerFlow、MCP 或自研 planner 后续可以读取同一份能力契约，而不是把路由和 prompt 写死在外部编排层。

tool manifest 之上需要提供轻量 HTTP tool bridge spec：把 path 参数、JSON body、multipart 上传、输出模型、side effect、read-only/destructive hint 统一成可被 MCP adapter、DeerFlow node 或外部 planner 消费的结构。正式 MCP server 后续只包装这层 spec，不重复维护工具清单。

HTTP tool bridge spec 之上需要提供一个 dependency-light 的 stdio MCP-to-HTTP bridge 脚本：启动时读取 `/research/tools/mcp-spec`，实现 `initialize`、`tools/list` 和 `tools/call`，把 MCP tool call 翻译成 FastAPI HTTP 调用。该脚本必须把 spec 作为唯一工具事实源，不允许维护第二份 route/tool 清单；需要覆盖 path 参数编码、JSON body、multipart 文件上传和 zip bundle 的 base64 文本返回。

MCP bridge 需要提供最小托管控制：支持 read-only mode、allow/deny tool filters、环境变量配置和 health-check JSON 输出。外部客户端初次接入时应能只暴露只读工具或明确 allowlist，避免把 cancel/update/create 类写操作默认交给未知客户端。

系统需要保存研究者画像/项目约束：包括 primary domains、active research questions、target venues、methodological preferences、resource constraints、risk tolerance、negative preferences 和 ranking weights。ranking、advisor brief、后续 planner 应优先读取这份画像，避免生成“看起来不错但不适合当前资源和投稿目标”的 idea。

系统需要提供 research execution plan snapshot：把 profile、ranked ideas、open/blocked tasks 聚合成 7/14/30 天行动计划，包含 phases、task ids、success checks、source ids 和 Markdown 导出。它回答“接下来一到两周具体做什么”，而不是只输出静态报告。

execution plan 需要能一键转成 task board 任务：每个 plan action 至少包含 owner_type、owner_id、source_id、priority、due_phase 和 created event，并写入 research_plan_creates_task 图边，保证计划不会停留在静态文档。plan 与 plan task 必须进入 idea progress、idea lineage、research packet 和 idea bundle，形成“计划 -> 任务 -> 进展”的闭环。

research execution plan 需要提供 progress report：按 plan 读取生成的 tasks，统计 task_count、open/blocked/done、completion_ratio、phase/status/priority breakdown 和 next plan tasks，并导出 Markdown，避免计划只创建任务但没有后续推进反馈。

验收标准：

- 能通过关键词找相关论文。
- 能检查 idea 是否可能撞车。
- 能把外部论文加入本地文献库。

## 7. 前端信息架构

当前聊天页保留，但新增科研工作台。

### 7.1 主要页面

```text
1. Chat
2. Papers
3. Paper Cards
4. Evidence Search
5. Gap Map
6. Idea Lab
7. Review Board
8. Experiment Plans
9. Settings
```

### 7.2 Papers 页面

功能：

- 上传文献。
- 查看解析状态。
- 查看 paper card。
- 查看 evidence 数量。
- 重新抽取。
- 删除文献。

### 7.3 Gap Map 页面

功能：

- 选择论文集合。
- 生成 gaps。
- 按类型筛选。
- 查看 gap 证据。
- 从 gap 生成 idea。

### 7.4 Idea Lab 页面

功能：

- idea 列表。
- idea 详情。
- idea 评分。
- idea 版本。
- reviewer 反馈。
- 生成实验计划。

### 7.5 Experiment Plans 页面

功能：

- 查看实验计划。
- 导出 Markdown。
- 标记优先级。
- 标记完成状态。

## 8. 关键用户流程

### 8.1 上传论文到生成 Paper Card

```text
上传 PDF
-> 文本解析
-> 章节识别
-> chunk 切分
-> evidence 抽取
-> paper card 抽取
-> 向量索引
-> 关系图写入
-> 前端展示结果
```

### 8.2 从文献库生成 idea

```text
选择研究方向/论文集合
-> 抽取 limitations/future work
-> 聚类相似问题
-> 生成 research gaps
-> 对 gap 评分
-> 生成 ideas
-> 对 ideas 评分
-> reviewer 批评
-> 生成实验计划
```

### 8.3 用户已有 idea 的增强流程

```text
用户输入 idea 草稿
-> 系统查找相关论文
-> 系统找相似/冲突工作
-> novelty 检查
-> reviewer 批评
-> 修改建议
-> 实验计划
```

## 9. 数据对象状态流转

### 9.1 Paper 状态

```text
uploaded
parsed
chunked
indexed
card_extracted
failed
```

### 9.2 Gap 状态

```text
generated
reviewed
promising
rejected
converted_to_idea
```

### 9.3 Idea 状态

```text
draft
scored
reviewed
revised
experiment_planned
active
archived
rejected
```

### 9.4 Experiment 状态

```text
planned
ready
running
completed
failed
revised
```

## 10. 权限与安全需求

第一阶段可以保持单用户/本地用户模型，但架构上预留：

- user_id。
- project_id。
- paper ownership。
- idea ownership。
- private/public 标记。

短期不做复杂权限系统，避免拖慢核心能力。

## 11. 非功能需求

### 11.1 可解释性

所有重要输出必须能追溯证据：

- 问答结论。
- gap。
- idea。
- reviewer 批评。
- 实验建议。

### 11.2 稳定性

- 文档解析失败不影响已有文献。
- 单个字段抽取失败不影响整个 paper card。
- 模型 API 失败要有重试和失败记录。

### 11.3 可扩展性

- 能从 8 篇论文扩展到 50-200 篇。
- evidence schema 和 graph schema 应支持新字段。

### 11.4 可观测性

保留并扩展当前 RAG trace：

- 检索路径。
- 使用的 paper card。
- 使用的 evidence。
- graph expansion。
- idea generation steps。
- reviewer steps。

### 11.5 成本控制

- Paper Card 抽取要缓存。
- Gap 和 idea 生成可复用已有抽取结果。
- 外部文献搜索按需触发。

## 12. MVP 范围

### 12.1 MVP 必做

第一版必须包含：

1. Paper Card 抽取。
2. Evidence 对象。
3. 文献对比矩阵。
4. Gap Miner。
5. Idea Generator。
6. Idea Scorer。
7. Reviewer Simulator。
8. Experiment Designer。
9. Markdown 导出。

### 12.2 MVP 不做

第一版不做：

- 多用户登录注册。
- 完整 GraphRAG 框架。
- DeerFlow 迁移。
- 复杂图数据库。
- 自动跑实验。
- 自动写完整论文。
- 大规模外部爬虫。

## 13. 迭代路线

### Phase 0：整理现有项目

目标：

- 不破坏现有 RAG。
- 新增 `research_assistant` 模块。
- 建立 docs 和 schema。

任务：

- 新建需求与技术文档。
- 明确数据对象。
- 给当前 hard-coded RAG 逻辑打标，后续逐步替换。

### Phase 1：Paper Card 与 Evidence

目标：

- 让系统从 chunk 检索升级为论文结构理解。

任务：

- 新增 paper/evidence schema。
- 上传后生成 paper card。
- evidence 写入存储。
- 前端展示 paper card。

验收：

- 现有 8 篇论文都能生成 paper card。
- 至少 problem/method/contribution/dataset/result/limitation 能抽取。

### Phase 2：Gap Miner

目标：

- 从一批论文生成 research gaps。

任务：

- limitation 聚类。
- future work 聚类。
- 多论文差异分析。
- gap 评分。

验收：

- 对 geolocation 文献库生成不少于 5 个可解释 gap。
- 每个 gap 有 evidence。

### Phase 3：Idea Lab

目标：

- 从 gap 生成 idea，并管理 idea。

任务：

- idea generator。
- idea scorer。
- idea storage。
- idea markdown export。
- idea artifact bundle export。

验收：

- 每个 gap 能生成 2-3 个 idea。
- idea 有评分和证据。

### Phase 4：Reviewer 与实验设计

目标：

- 让 idea 能被批判和落地。

任务：

- reviewer simulator。
- experiment designer。
- idea revision loop。

验收：

- 每个 idea 能生成审稿意见和实验计划。
- 能区分必须实验和加分实验。

### Phase 5：GraphRAG-lite

目标：

- 建立轻量研究知识图。

任务：

- Paper/Claim/Method/Dataset/Metric/Result/Limitation/FutureWork/Idea 关系存储。
- 图邻居扩展。
- graph-assisted retrieval。

验收：

- 能查询「哪些 idea address 某个 limitation」。
- 能查询「哪些论文共享 dataset/method」。

### Phase 6：外部工具与 MCP

目标：

- 接入外部文献生态。

任务：

- arXiv。
- Semantic Scholar。
- Zotero。
- GitHub。
- 浏览器搜索。

验收：

- 能为 idea 自动检索外部相似工作。
- 能把外部论文加入文献库。

## 14. 成功指标

### 14.1 产品指标

- 用户上传论文后能快速得到 paper card。
- 用户能从一组论文得到可解释 gap。
- 用户能得到可执行 idea，而不是泛泛建议。
- 用户能看到 idea 的风险和实验计划。

### 14.2 工程指标

- Paper Card 生成成功率 >= 85%。
- Evidence 字段可追溯率 >= 80%。
- Gap 至少 80% 有明确 evidence。
- Idea 至少 80% 包含 research question、hypothesis、method、experiment。
- 现有 RAG 问答能力不回退。

### 14.3 评测指标

保留现有 RAG 指标：

- hit@1。
- hit@5。
- recall@5。
- MRR。
- nDCG。

新增科研助手指标：

- paper_card_field_coverage。
- evidence_support_rate。
- gap_evidence_rate。
- idea_completeness_rate。
- reviewer_actionability_score。
- experiment_plan_completeness_rate。

## 15. 风险与应对

### 15.1 抽取质量不稳定

风险：

- LLM 抽取字段不完整或不一致。

应对：

- 使用结构化输出。
- 分章节抽取。
- 每个字段保留 evidence。
- 支持重新抽取。

### 15.2 成本升高

风险：

- 上传多篇论文时 LLM 调用成本高。

应对：

- 缓存 paper card。
- 增量抽取。
- 先抽关键章节。
- 用户按需触发 gap/idea。

### 15.3 idea 幻觉

风险：

- 系统生成看似新颖但无证据的 idea。

应对：

- idea 必须绑定 evidence。
- reviewer 检查 novelty。
- 外部文献搜索后置验证。

### 15.4 项目复杂度失控

风险：

- 同时上 GraphRAG、MCP、DeerFlow、复杂前端会拖慢主线。

应对：

- 第一阶段只做内部工作流。
- GraphRAG-lite 先用轻量 schema。
- MCP 放到 Phase 6。
- 不迁移 DeerFlow。

## 16. 最终目标形态

最终 SuperMew 应该成为一个科研工作台：

```text
用户上传/导入文献
-> 系统自动理解论文
-> 系统整理方向结构
-> 系统发现 research gap
-> 系统生成多个 idea
-> 系统批判 idea
-> 系统设计实验
-> 用户选择并迭代
```

最终输出不只是答案，而是：

- 文献地图。
- gap 地图。
- idea 池。
- reviewer 报告。
- 实验计划。
- proposal 雏形。

一句话总结：

> SuperMew 的升级方向不是「更复杂的 RAG」，而是「以 RAG 为底座、以结构化文献理解为核心、以 idea 工作流为产品主线的科研助手」。
