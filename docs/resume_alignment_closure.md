# 简历描述与项目闭环对齐说明

本文档用于约束 Research Assistant Agent 后续迭代：目标不是继续堆新概念，而是让代码、文档、Demo 和简历表述保持一致，形成一个能讲清楚、能复现、能闭环的本地科研 Agent 项目。

## 一句话定位

Research Assistant Agent 是一个面向科研论文阅读与 Proposal 构建的本地可部署科研 Agent 工作流系统。它围绕论文解析、证据检索、方案生成、质量审查和产物追溯建立工程闭环，重点解决检索难评估、输出难复现、产物难追溯的问题。

## 简历表述边界

简历可以围绕以下三条主线展开：

1. 科研工作流架构设计
2. 证据检索评测闭环
3. 产物回放与质量门控

不要在没有可复现报告支撑时写死论文数量、问题数量或指标数值。论文数量、hard question 数量、Hit@8、MRR 等指标应在扩充论文集并运行评测脚本后再填写。

推荐写法：

```text
基于真实论文与高难 query-evidence 评测集验证检索链路，输出 Hit@8、MRR、miss cases 与失败归因；评测规模和指标以可复现报告为准。
```

如果要写具体数字，必须能对应到本地报告或提交产物：

```text
data/evaluation/.../realistic_quality_report.json
data/evaluation/.../realistic_quality_report.md
outputs/evaluations/.../real_paper_eval_*.json
```

## 项目闭环目标

项目闭环只围绕六层能力，不额外发散：

```text
文档与证据层
  -> 检索与评测层
  -> 工作流编排层
  -> 运行可观测层
  -> 产物溯源层
  -> 质量门控层
```

这六层共同支撑简历里的三个 bullet。

## 1. 文档与证据层

目标：把论文变成可检索、可引用、可追溯的结构化对象。

核心对象：

- `Paper`
- `PaperSection`
- `Chunk`
- `Evidence`

当前闭环要求：

- 支持 PDF / TXT / MD 上传。
- 能识别章节并保存 `PaperSection`。
- 每个 section 生成 parent chunk。
- section 内生成 child chunks。
- evidence 记录保留来源、摘要、支持关系和置信度。
- 表格、图注、实验结果类信号应尽量抽取为 evidence。

可讲重点：

```text
我没有把 PDF 简单切成固定窗口，而是先识别章节，再组织 parent-child chunk 和 evidence，使后续检索、引用和产物追溯有结构化基础。
```

验证入口：

```bash
bash scripts/check_research_workflow_primitives.sh
bash scripts/check_context_search_evaluations.sh
```

## 2. 检索与评测层

目标：让 RAG 检索不是一次性 Demo，而是可评测、可回放、可归因。

核心能力：

- lexical retrieval
- embedding retrieval
- hybrid retrieval
- query rewrite / multi-query variants
- parent-child retrieval
- rerank
- evidence compression
- GraphRAG-lite context expansion
- miss taxonomy

parent-child retrieval 的讲法：

```text
child chunk 负责召回，因为小粒度更容易匹配具体问题；parent chunk / parent section 负责上下文补全，因为科研回答需要完整方法和实验背景。
```

评测闭环要求：

- 固定评测数据集。
- 固定运行命令。
- 输出 Hit@8、MRR、miss cases、failure taxonomy。
- 失败样例可以转成 replay cases。
- 论文数量和指标数值只在评测报告生成后写入简历。

统一评测入口：

```bash
python3 scripts/run_retrieval_eval.py --profile realistic
```

该命令会串联 realistic retrieval eval、failure replay export 和 miss taxonomy，并输出面向简历填写的 `resume_summary` 字段。补论文后，优先使用这一条命令生成可复现指标。

底层相关入口：

```bash
bash scripts/check_context_search_evaluations.sh
python3 scripts/build_geoloc_realistic_eval.py
python3 scripts/check_geoloc_realistic_eval.py
python3 scripts/analyze_geoloc_retrieval_misses.py
python3 scripts/run_local_pipeline_profile.py --profile rag_miss_analysis
```

后续补论文后的指标填写规则：

```text
论文数量 = 评测 manifest 中覆盖的 paper_count
问题数量 = realistic/hard question 文件中的 question_count
Hit@8 = quality report 中 primary_hit_at_8 或约定主指标
MRR = quality report 中 primary_mrr
失败类别 = miss analysis 中的 taxonomy categories
```

## 3. 工作流编排层

目标：把“论文到方案”的长流程变成可持久化、可恢复、可定位失败的 workflow。

核心对象：

- `Job`
- `WorkflowStageRun`
- `WorkflowArtifact`

闭环要求：

- 论文解析、paper card、gap mining、idea generation、quality artifacts、Markdown dossier 等阶段应有 stage record。
- 每个 stage 记录状态、输入、输出、错误、配置 hash、代码 commit。
- 可复用已有阶段产物，避免失败后只能整条重跑。
- job artifact 能还原 workflow 输出。

可讲重点：

```text
我把科研流程拆成有状态 stage，每个 stage 都有输入输出和失败信息；这让长任务可以定位问题、复用产物和后续回放。
```

验证入口：

```bash
bash scripts/check_workflow_job_controls.sh
bash scripts/check_research_workflow_primitives.sh
```

## 4. 运行可观测层

目标：让 Agent 的每次工具调用、失败和 replay 都能被看见。

核心对象：

- `AgentRun`
- `ToolCallRecord`
- `ReplayCase`

当前可讲能力：

- Advisor chat 会创建 agent run。
- 工具调用会记录到 `ToolCallRecord`。
- 工具失败会保存错误和延迟。
- 部分失败场景会自动生成 replay case。
- replay 脚本可以本地执行，不依赖真实 provider。
- `/research/agent/metrics` 可以导出 observability metrics。

最少覆盖的 replay 类型：

- 检索未命中回放
- 工具调用失败回放
- 引用审查回放

适合展示的指标：

- `tool_success_rate`
- `replay_pass_rate`
- `average_run_latency_ms`
- `run_status_counts`
- `tool_status_counts`
- `replay_case_type_counts`
- `recent_failures`

验证入口：

```bash
bash scripts/check_agent_replay.sh
bash scripts/check_workflow_job_controls.sh
```

## 5. 产物溯源层

目标：一个 Proposal、Review、Decision Memo 或实验结论，能追溯到来源论文、证据、阶段、配置和代码版本。

核心能力：

- artifact hash
- config hash
- code commit
- workflow stage link
- entity-scoped artifact lineage API

闭环要求：

一个科研产物至少应能追到：

- `paper_id`
- `evidence_id` 或相关 evidence ledger
- `workflow_stage_id`
- `artifact_type`
- `artifact_hash`
- `config_hash`
- `code_commit`
- `created_at`

可讲重点：

```text
科研 Agent 产物不是只保存最终文本，而是保存产物、配置和代码版本的 lineage，方便解释这个 Proposal 为什么被生成、来自哪些证据、用的是哪次运行配置。
```

验证入口：

```bash
python3 scripts/run_local_pipeline_profile.py --profile workflow_lineage_smoke
bash scripts/check_workflow_job_controls.sh
```

## 6. 质量门控层

目标：系统不能在证据不足时直接生成过度 claim，尤其不能自动宣称 SOTA。

核心对象和能力：

- evidence ledger
- assumption audit
- benchmark evidence readiness
- SOTA review package
- external-search evidence package
- manual SOTA signoff
- idea quality gate

闭环要求：

- 证据不足时给出 blocker。
- 引用缺失时标记 needs review。
- benchmark evidence 不充分时阻止 ready-for-claim。
- SOTA claim 需要人工确认。
- gate 输出应能说明：为什么 blocked，下一步补什么证据。

可讲重点：

```text
系统不是直接让模型宣称创新点，而是通过 evidence ledger、assumption audit、benchmark readiness 和人工 SOTA signoff 限制过度 claim。
```

验证入口：

```bash
bash scripts/check_context_search_evaluations.sh
bash scripts/check_research_proposal_contracts.sh
```

## 与简历三条 bullet 的对应关系

### 科研工作流架构设计

支撑层：

- 文档与证据层
- 工作流编排层
- 产物溯源层

可以讲：

```text
围绕 Paper、Evidence、WorkflowStage、WorkflowArtifact 建模，将论文解析、证据组织、gap mining、idea generation、proposal、experiment plan 等环节持久化，支持状态记录、失败定位、产物复用和后续回放。
```

### 证据检索评测闭环

支撑层：

- 检索与评测层
- 运行可观测层

可以讲：

```text
设计关键词/向量混合检索、查询改写、重排序和父子分块层级检索；构建可回放评测集，输出 Hit@8、MRR、miss cases 和失败归因，用于反向优化检索策略。
```

注意：论文数量和指标值等补充论文后再填。

### 产物回放与质量门控

支撑层：

- 运行可观测层
- 产物溯源层
- 质量门控层

可以讲：

```text
通过 AgentRun、ToolCallRecord、ReplayCase 记录工具调用、检索上下文、失败类型和中间产物；结合 Artifact Lineage、引用审查、证据台账、假设审查和 SOTA 人工确认降低过度 claim 风险。
```

## 不应再发散的方向

当前阶段不优先做：

- 多用户 SaaS
- OAuth / SSO
- 支付系统
- 大规模分布式队列
- 默认 Milvus / Qdrant
- 完整 GraphRAG 框架替换
- 复杂 UI 重做
- 开放式 autonomous agent loop

这些不是不能做，而是不服务于当前简历闭环。

## 后续补论文后的评测流程

用户补充论文后，按下面顺序更新评测数字：

1. ingest 新论文。
2. 扩充 realistic / hard query-evidence 标注。
3. 构建 replay cases。
4. 跑 retrieval eval。
5. 跑 miss taxonomy。
6. 更新报告。
7. 只把报告中可复现的数字写入简历。

统一命令：

```bash
python3 scripts/run_retrieval_eval.py --profile realistic \
  --write-json outputs/retrieval-evals/realistic_summary.json \
  --write-markdown outputs/retrieval-evals/realistic_summary.md
```

推荐保留的最终指标：

- paper count
- hard question count
- primary Hit@8
- primary MRR
- replay pass rate
- miss case count
- failure taxonomy category count
- tool call success rate
- average / p95 latency
- workflow completion rate

其中简历最适合展示：

```text
Hit@8 / MRR + Replay Pass Rate + Tool Call Success Rate + Failure Taxonomy
```

原因是这组指标能同时说明 RAG 质量、Agent 工程可靠性和问题定位能力。

## 最终闭环判断

项目闭环不是“功能越多越好”，而是能回答清楚四个问题：

1. 输入论文后，系统如何把论文转成可检索证据？
2. 检索结果为什么可信，失败后怎么复现？
3. 生成的 Proposal / Review / Decision Memo 能追溯到哪些证据和配置？
4. 证据不足或 SOTA claim 风险过高时，系统如何阻止过度结论？

只要代码、测试、报告和 Demo 都能回答这四个问题，这个项目就可以作为简历中的本地科研 Agent 工程项目闭环展示。
