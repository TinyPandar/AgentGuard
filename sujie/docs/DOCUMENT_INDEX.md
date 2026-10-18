# 全部文档索引与交接范围

更新：2026-10-18。主线为 `sujie/`，最新进展是M25同事实比较与三来源有限代表；脚本与来源矩阵已独立核验，完整离线HTTP及工程检查边界见[M25记录](M25_STATUS.md)。M24最终v2及以前验收保留原阶段，M21四业务后停止属于历史状态。

## 推荐阅读

[M25与项目总体报告](../../competition/docs/M25_AND_OVERALL_REPORT_2026-10-18.md) → [M25进展](M25_STATUS.md) → [同事实比较](M25_MODEL_COMPARISON.md) / [三来源代表](M25_SOURCE_BYPASS.md) → [M25下一步](M25_NEXT_STEPS.md) → [材料证据骨架](../../competition/docs/COMPETITION_EVIDENCE_OUTLINE_2026-10-18.md) → [已完成工作简明汇总](COMPLETED_WORK_SUMMARY.md) → [项目交接手册](PROJECT_HANDOFF.md) → [当前工作包状态](F2_IMPLEMENTATION_STATUS.md) → [官方证据矩阵](TOPIC5_EVIDENCE_MATRIX.md)。历史F3仍为剩余范围和设计依据。

## 维护口径

- 当前指南直接更新实际入口与现状；历史设计/计划/阶段验收增加各自的后续说明，保留原始数字、失败和版本。历史正文“当前/尚未/下一步”只指原阶段。
- 10月15日交接时曾更新原67份自有Markdown，加入汇总、手册与索引后共70份；该数字是历史整理范围。下表补入本轮审查、执行计划和M22专项，不将历史数量当作当前文件总数。
- 官方调研快照、冻结协议、实验报告、`runtime-sources`中的历史副本文档、外部依赖/许可资产、缓存和构建产物不作为现行编辑对象。原始证据保持不变，不批量改标题/哈希/结果。
- `requirements*.txt`、锁文件、CI/工具配置属于代码/环境事实，不因“更新文档”重新生成；假值`.env.example`不是当前云配置。源码API CSV、操作者token与私人环境不纳入公开文档。
- M22按新指令实施本地修复、任务登记、共同运行器及离线回归；真实模型复测仍须确认本机凭据与预算。没有因修改文档重启未知用户服务；结果按M21/M22版本分开。

## 完整清单

路径相对仓库根目录；“阶段记录”不是当前总验收。复制项目时还应移交手册列出的忽略证据/资产，凭据另行私密移交。

10月15日历史核对结果（本地观察，非签名验收）：当时70份自有文档的332个本地链接目标存在，563份固定证据文件保持摘要，M21脚本v3的84份运行源码当时与实现一致。M22实施后部分源码已变化，不能继续把M21归档称为与当前源码全匹配；新结果及源码对应见M22。历史文件及冻结实现保持原样，不扩展旧验收范围。

| 文档 | 用途 | 适用范围 |
|---|---|---|
| [competition/docs/M25_AND_OVERALL_REPORT_2026-10-18.md](../../competition/docs/M25_AND_OVERALL_REPORT_2026-10-18.md) | 当前总体报告 | M25实际进展、整体能力、国家级奖项目标差距和下一步 |
| [sujie/docs/M25_STATUS.md](M25_STATUS.md) | 当前实施与证据边界 | 1022项全量原始日志及退出码边界、281份冻结；48格脚本、14格来源代表及HTTP状态分别记录 |
| [sujie/docs/M25_MODEL_COMPARISON.md](M25_MODEL_COMPARISON.md) | 同事实观察性比较 | 六候选48格/14配对、C/A同事实、适用Q及IOC C/R去重；脚本/Mock与真实模型分开 |
| [sujie/docs/M25_SOURCE_BYPASS.md](M25_SOURCE_BYPASS.md) | 三来源有限代表 | 直接Unicode/外部Base64/Memory语义伪装14格/7配对；固定本地禁止写入，非完整21格或ASR |
| [sujie/docs/M24_STATUS.md](M24_STATUS.md) | M24阶段验收 | 893项最终回归、四候选80格与生命周期核验修复、40/35复验和Linux六链；v1/v2分开 |
| [sujie/docs/M24_IOC_INSTANCES.md](M24_IOC_INSTANCES.md) | IOC事实域与实际发送核验 | 有界公开地址、数量/重复/噪声、Receiver准确一次；不支持域明确登记 |
| [sujie/docs/M24_GIT_INSTANCES.md](M24_GIT_INSTANCES.md) | Git真实对象与ref核验 | 两版配置blob/diff、固定权限、实际push收据及ref恢复反例 |
| [sujie/docs/M24_LONG_TASK_ADMISSION.md](M24_LONG_TASK_ADMISSION.md) | 三层委派与双新会话Memory | 可变事实、源读取/角色链、实际SQLite历史和CAS |
| [sujie/docs/M24_LINUX_SMOKE.md](M24_LINUX_SMOKE.md) | 六候选Linux有限运行性 | 参数化六链、v2应用/部署分别冻结、容器和主机独立重算；非完整隔离或性能 |
| [sujie/docs/M25_NEXT_STEPS.md](M25_NEXT_STEPS.md) | 下一阶段执行安排 | 离线证据收口、真实模型协议与资源、未见输入/有效消融/统计、隔离性能、演示与匿名包 |
| [competition/docs/COMPETITION_EVIDENCE_OUTLINE_2026-10-18.md](../../competition/docs/COMPETITION_EVIDENCE_OUTLINE_2026-10-18.md) | 参赛材料与演示骨架 | 三项可检验贡献、强基线、失败边界与实际证据出口 |
| [sujie/docs/M23_STATUS.md](M23_STATUS.md) | M23阶段验收 | 657项同版回归、40参数化开发单元、35固定提议、Linux四链与结论边界 |
| [sujie/docs/M23_EVALUATION_EXECUTION_GATES.md](M23_EVALUATION_EXECUTION_GATES.md) | 评测执行门槛 | 三候选动态确认与修复、12项回归；不改旧报告 |
| [sujie/docs/M23_EFFECTIVE_MODEL_BINDING.md](M23_EFFECTIVE_MODEL_BINDING.md) | Provider有效请求/响应关联 | 主/子/Memory/分析本地HTTP捕获与52项新测试；历史入口排除登记 |
| [sujie/docs/M23_PARAMETERIZED_TASKS.md](M23_PARAMETERIZED_TASKS.md) | 两候选参数化/独立SQL复算 | 已暴露开发输入、47项新测试；LF/字节完整性和取消边界 |
| [sujie/docs/M23_DIRECT_EFFECT_CALIBRATION.md](M23_DIRECT_EFFECT_CALIBRATION.md) | 固定提议实际影响核验 | 35单元/7配对，10项新测试；公共底线、实际效果与模型ASR分开 |
| [sujie/docs/M23_LINUX_SMOKE.md](M23_LINUX_SMOKE.md) | 当前有限Linux运行性 | arm64受限单容器四链；非完整工具/角色隔离或性能验收 |
| [sujie/docs/M24_NEXT_STEPS.md](M24_NEXT_STEPS.md) | M23之后具体工作 | 其余四候选准入→覆盖/演示→正式冻结，计划不是已完成结果 |
| [competition/docs/MENTOR_REVIEW_AND_NEXT_PLAN_2026-10-16.md](../../competition/docs/MENTOR_REVIEW_AND_NEXT_PLAN_2026-10-16.md) | M21接手审查 | 默认Mac回归471通过/11失败及原始证据核验；不是修复后成绩 |
| [competition/docs/NEXT_ACTION_PLAN_2026-10-16.md](../../competition/docs/NEXT_ACTION_PLAN_2026-10-16.md) | 当前执行顺序 | 第一批修复/登记→关键能力→冻结比较→交付；计划数字不是成绩 |
| [competition/docs/DEVELOPMENT_SKILLS_2026-10-16.md](../../competition/docs/DEVELOPMENT_SKILLS_2026-10-16.md) | GitHub skills安装与用法 | 固定版本的属性测试/同类缺陷检索；来源摘要、应用边界和待实现测试设计 |
| [sujie/docs/M22_FIRST_BATCH_STATUS.md](M22_FIRST_BATCH_STATUS.md) | 当前第一批实施总览 | Mac环境/Git、IOC、注册表、共同运行器与本轮回归证据 |
| [sujie/docs/M22_IOC_DEVELOPMENT_REPAIR.md](M22_IOC_DEVELOPMENT_REPAIR.md) | IOC开发修复 | 原失败重算、提示修复和离线HTTP控制流；非新云模型成绩 |
| [sujie/docs/M22_TASK_REGISTRATION.md](M22_TASK_REGISTRATION.md) | 任务候选登记 | 六项已暴露开发候选、C/A/Q/R与双Oracle；非正式冻结 |
| [sujie/docs/M22_COMMON_RUNTIME_DEVELOPMENT_V2.md](M22_COMMON_RUNTIME_DEVELOPMENT_V2.md) | 共同运行器开发校准 | 四新业务五配置确定性校准、源码归档与离线重算；云0 |
| [.github/pull_request_template.md](../../.github/pull_request_template.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [AgentGuard v0.1 开发设计文档.md](../../AgentGuard%20v0.1%20%E5%BC%80%E5%8F%91%E8%AE%BE%E8%AE%A1%E6%96%87%E6%A1%A3.md) | 历史设计/计划 | 保留旧方案，不能作为自动执行指令或当前完成清单 |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | 当前入口/状态 | 截至M21；实现、证据与待办按本轮交接解释 |
| [README.md](../../README.md) | 当前入口/状态 | 截至M25；实际结果与边界以M25总记录为准，旧阶段结果保留 |
| [SECURITY.md](../../SECURITY.md) | 当前入口/状态 | 截至M21；实现、证据与待办按本轮交接解释 |
| [competition/docs/CODEX_IMPLEMENTATION_INSTRUCTIONS.md](../../competition/docs/CODEX_IMPLEMENTATION_INSTRUCTIONS.md) | 历史设计/计划 | 保留旧方案，不能作为自动执行指令或当前完成清单 |
| [competition/docs/SUJIE_FINAL_DESIGN.md](../../competition/docs/SUJIE_FINAL_DESIGN.md) | 历史设计/计划 | 保留旧方案，不能作为自动执行指令或当前完成清单 |
| [competition/docs/SUJIE_REVIEW_AND_PLAN_F2.md](../../competition/docs/SUJIE_REVIEW_AND_PLAN_F2.md) | 历史设计/计划 | 保留旧方案，不能作为自动执行指令或当前完成清单 |
| [competition/docs/SUJIE_REVIEW_AND_PLAN_F3.md](../../competition/docs/SUJIE_REVIEW_AND_PLAN_F3.md) | 当前规划 | 目标/排期非成绩；现状看状态表，四业务后已停止 |
| [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [docs/ROADMAP.md](../../docs/ROADMAP.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [docs/SECURITY_MODEL.md](../../docs/SECURITY_MODEL.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [docs/TEAM_COLLABORATION.md](../../docs/TEAM_COLLABORATION.md) | 历史设计/计划 | 保留旧方案，不能作为自动执行指令或当前完成清单 |
| [docs/THREAT_MODEL.md](../../docs/THREAT_MODEL.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/README.md](../README.md) | 当前入口/状态 | 截至M25；本机启动、模块与当前证据边界 |
| [sujie/console-vue/README.md](../console-vue/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/contracts/README.md](../contracts/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/control-plane-java/README.md](../control-plane-java/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/control-plane-python/README.md](../control-plane-python/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/demo-agent/README.md](../demo-agent/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/deploy/README.md](../deploy/README.md) | 历史M1复现 | 只验旧拓扑，新版整体隔离/可移植交付未验收 |
| [sujie/deploy/wheelhouse/README.md](../deploy/wheelhouse/README.md) | 历史M1复现 | 只验旧拓扑，新版整体隔离/可移植交付未验收 |
| [sujie/docs/COMPLETED_WORK_SUMMARY.md](COMPLETED_WORK_SUMMARY.md) | 当前入口/状态 | 截至M21；实现、证据与待办按本轮交接解释 |
| [sujie/docs/DEPENDENCIES.md](DEPENDENCIES.md) | 依赖说明 | 锁文件为准，环境/许可证/审计观察按原阶段解释 |
| [sujie/docs/DOCUMENT_INDEX.md](DOCUMENT_INDEX.md) | 当前入口/状态 | 截至M21；实现、证据与待办按本轮交接解释 |
| [sujie/docs/F2_IMPLEMENTATION_STATUS.md](F2_IMPLEMENTATION_STATUS.md) | 当前入口/状态 | 截至M21；实现、证据与待办按本轮交接解释 |
| [sujie/docs/M0_ACCEPTANCE.md](M0_ACCEPTANCE.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M0_FILE_MANIFEST.md](M0_FILE_MANIFEST.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M0_SECURITY.md](M0_SECURITY.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M10_TASK_DRIFT_DEVELOPMENT.md](M10_TASK_DRIFT_DEVELOPMENT.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M11_CONTEXT_EGRESS.md](M11_CONTEXT_EGRESS.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M12_AUTONOMOUS_APPROVAL_AND_BUDGET.md](M12_AUTONOMOUS_APPROVAL_AND_BUDGET.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M13_SEQUENCE_AND_TEMPORAL_SOURCES.md](M13_SEQUENCE_AND_TEMPORAL_SOURCES.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M14_NETWORK_AND_WEB_WORKFLOW.md](M14_NETWORK_AND_WEB_WORKFLOW.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M15_STRUCTURED_EXECUTION_AND_ARTIFACT.md](M15_STRUCTURED_EXECUTION_AND_ARTIFACT.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M16_GIT_DELIVERY_AND_APPROVAL.md](M16_GIT_DELIVERY_AND_APPROVAL.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M17_ACTUAL_ANALYTICAL_AGENTS.md](M17_ACTUAL_ANALYTICAL_AGENTS.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M18_CROSS_SESSION_MEMORY.md](M18_CROSS_SESSION_MEMORY.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M19_COMMON_RUNTIME_AND_BASELINES.md](M19_COMMON_RUNTIME_AND_BASELINES.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M1_1_SECURITY_HARDENING.md](M1_1_SECURITY_HARDENING.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M1_2_PURPOSE_PROVENANCE.md](M1_2_PURPOSE_PROVENANCE.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M1_ACCEPTANCE.md](M1_ACCEPTANCE.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M1_PROGRESS.md](M1_PROGRESS.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M20_VERIFIED_EVIDENCE_QUOTATIONS.md](M20_VERIFIED_EVIDENCE_QUOTATIONS.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M21_FOUR_BUSINESS_WORKFLOWS.md](M21_FOUR_BUSINESS_WORKFLOWS.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M2_PROGRESS.md](M2_PROGRESS.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M4_PROVENANCE_ABLATION.md](M4_PROVENANCE_ABLATION.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M4_REAL_MODEL.md](M4_REAL_MODEL.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M5_EXTERNAL_BENCHMARK.md](M5_EXTERNAL_BENCHMARK.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M5_INJECAGENT.md](M5_INJECAGENT.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M5_INJECAGENT_LOCAL.md](M5_INJECAGENT_LOCAL.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M6_OPERATOR_CONSOLE.md](M6_OPERATOR_CONSOLE.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M7_GATEWAY_PERFORMANCE.md](M7_GATEWAY_PERFORMANCE.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M8_AUTONOMOUS_CONSOLE.md](M8_AUTONOMOUS_CONSOLE.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/M9_FROZEN_CLASSIFICATION.md](M9_FROZEN_CLASSIFICATION.md) | 阶段记录 | 原阶段版本；顶部交接说明列明后续补齐与仍存边界 |
| [sujie/docs/PLAN_STATUS.md](PLAN_STATUS.md) | 历史设计/计划 | 保留旧方案，不能作为自动执行指令或当前完成清单 |
| [sujie/docs/PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) | 当前入口/状态 | 截至M25；实现、证据与待办按当前交接解释，历史结果分版本 |
| [sujie/docs/TOPIC5_EVIDENCE_MATRIX.md](TOPIC5_EVIDENCE_MATRIX.md) | 当前入口/状态 | 截至M25；官方能力与仍存缺口分项列出 |
| [sujie/docs/adr/ADR-001-dsl-lt.md](adr/ADR-001-dsl-lt.md) | 已接受决策 | 维持in操作符与契约包0.2/载荷1.0的决定 |
| [sujie/docs/adr/ADR-002-context-audit.md](adr/ADR-002-context-audit.md) | 已接受决策 | 维持in操作符与契约包0.2/载荷1.0的决定 |
| [sujie/eval/attacks/README.md](../eval/attacks/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/eval/baselines/README.md](../eval/baselines/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/eval/cases/README.md](../eval/cases/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/eval/oracles/README.md](../eval/oracles/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/mcp-servers/evidence-server/README.md](../mcp-servers/evidence-server/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/mcp-servers/git-server/README.md](../mcp-servers/git-server/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/mcp-servers/malicious-variants/README.md](../mcp-servers/malicious-variants/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/mcp-servers/memory-server/README.md](../mcp-servers/memory-server/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/mcp-servers/operations-server/README.md](../mcp-servers/operations-server/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
| [sujie/sandbox/README.md](../sandbox/README.md) | 当前模块/协作说明 | 含接口职责、兼容旧路径与当前限制；详见交接手册 |
