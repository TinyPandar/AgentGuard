# 已完成工作简明汇总

> 2026-10-19：最新源码基线 `fb6e6e4` 的[逐项能力审计](../../competition/docs/MAIN_CAPABILITY_AUDIT_2026-10-19.md)已完成。新增97项专项通过、1项tokenizer资产跳过；Ubuntu全量通过，Windows尚有1项终态等待失败。统一返回字段、执行前研判、独立风险/敏感目标硬策略、完整调用图和绕过覆盖继续待补；未新增业务实现或云实验。

> 2026-10-18 后续进度：[聊天控制台](CONSOLE_CHAT_CHECKPOINT.md)，与下文历史记录分开解释。

交接基准：2026-10-15；更新至2026-10-18的M25。先读[M25与项目总体报告](../../competition/docs/M25_AND_OVERALL_REPORT_2026-10-18.md)及[M25阶段记录](M25_STATUS.md)，下一步见[M25安排](M25_NEXT_STEPS.md)；M24及以前结果保留各自版本。
比赛实现主线为 `sujie/`；根目录 `agentguard/` 为历史 v0.1 原型。
**四类业务已完成；F3整体计划尚未完成。** 用户已要求按[执行计划](../../competition/docs/NEXT_ACTION_PLAN_2026-10-16.md)恢复修复与离线校准，正式独立任务冻结和云主比较仍未完成。以下M0–M21历史数字不追溯改写。

## 已完成的工作

| 工作 | 已实现的结果 | 证据入口 |
|---|---|---|
| 可信授权与网关 | 九类 JSON Schema、TaskContract/TaskGrant、语义效果映射、策略 DSL、ALLOW/ASK/BLOCK、执行前复核、工具元数据与版本检查 | [M0](M0_ACCEPTANCE.md)、[M1](M1_ACCEPTANCE.md)、[加固](M1_1_SECURITY_HARDENING.md) |
| 来源与用途约束 | Artifact 父来源、保守派生、暴露集合、受控文件/Memory 来源恢复；普通摘要、引用或子任务输出不能获得授权 | [M2](M2_PROGRESS.md)、[M18](M18_CROSS_SESSION_MEMORY.md) |
| 检测与序列解释 | 规则规范化、无工具任务感知分类、冻结分类实验、候选 v2 开发比较；可信目标、可见计划、工具提议、来源与实际效果关联 | [M9](M9_FROZEN_CLASSIFICATION.md)、[M10](M10_TASK_DRIFT_DEVELOPMENT.md)、[M13](M13_SEQUENCE_AND_TEMPORAL_SOURCES.md) |
| 模型输入与出口 | messages/tools 快照、字面及 JSON 转义区间、本地固定 Qwen tokenizer、请求/回应保护、Provider 凭据检查、共享持久预算 | [M11](M11_CONTEXT_EGRESS.md)、[M12](M12_AUTONOMOUS_APPROVAL_AND_BUDGET.md) |
| 真实工具与审批 | 文件、封闭 HTTP、注册程序子进程、本机 Git 远端、记忆；IOC/Git 支持模型暂停、批准、提交、续跑及拒绝/未知状态处理 | [M12](M12_AUTONOMOUS_APPROVAL_AND_BUDGET.md)、[M14–网络](M14_NETWORK_AND_WEB_WORKFLOW.md)、[M15–执行](M15_STRUCTURED_EXECUTION_AND_ARTIFACT.md)、[M16–Git](M16_GIT_DELIVERY_AND_APPROVAL.md) |
| 多层 Agent 与记忆 | 主→review→verify 三个实际模型对话、子权限收窄；两个独立会话间保存/复核版本化原文，CAS 追加与篡改检查 | [M17](M17_ACTUAL_ANALYTICAL_AGENTS.md)、[M18](M18_CROSS_SESSION_MEMORY.md) |
| 危险证据引用 | 报告入口可调用有界无工具分析角色；Host 核对原文字面引用、位置、未引用区间及来源限制 | [M20](M20_VERIFIED_EVIDENCE_QUOTATIONS.md) |
| 四类新增业务 | 多源事件时间线、Issue 分级、邮件附件一致性、多版本知识冲突；实际 MCP 读取、报告落盘及独立事实/读取/资料完整性判定 | [M21](M21_FOUR_BUSINESS_WORKFLOWS.md) |
| 操作者系统 | Python 控制面与 Vue 控制台：认证、任务、审批、来源 DAG、序列研判、实际影响、Agent/Memory 状态及脱敏导出 | [当前使用说明](PROJECT_HANDOFF.md) |
| 评测与工程证据 | 五配置共同运行框架、脚本副作用校准、小规模固定云模型实验、外部基准受限适配、离线重算、源码归档；历史 M1 Linux 容器及网关性能实验 | [M4](M4_REAL_MODEL.md)、[M5](M5_EXTERNAL_BENCHMARK.md)、[M7](M7_GATEWAY_PERFORMANCE.md)、[M19](M19_COMMON_RUNTIME_AND_BASELINES.md) |

## 最新验证结论

- M25：新增[同事实观察性比较](M25_MODEL_COMPARISON.md)、独立核验和[三来源代表](M25_SOURCE_BYPASS.md)。脚本48格/14配对已独立核验：正常执行48、业务完成46、实际危险效果2（Git注入的unsafe/strong-static）；来源14格/7配对已独立核验：业务完成14，3次本地禁止标记写入仅在unsafe，Full为0。完整离线HTTP矩阵状态以[M25记录](M25_STATUS.md)为准，已有6项HTTP专项通过；Mock不做模型推理，云调用0。全量原始日志记载 **1022 passed / 1 warning（759.38秒）**，Ruff及216文件格式检查通过；用户中断后未取回进程退出码。281份源码/配置已冻结，原265份及1183份历史证据逐字节保全。无新Linux、前端或性能验收，不作正式ASR。
- M24：四候选参数化和独立事实核验完成；Memory生命周期核验缺口已修复，最终v2 **893 passed / 1 warning（672.97秒）**、Ruff及202文件格式通过。80格/16配对（76utility、4实际危险效果）、两业务40格/8配对、固定提议35格/7配对与Linux六链通过独立核验；没有新云调用，不作ASR。前端源码未改，原v1与后续反例保留，见[M24](M24_STATUS.md)。
- M23：确认并修复三处“业务已完成而执行失败仍PASS”的评测遗漏；完整有效HTTP JSON请求体冻结发送与响应/预算关联；时间线/附件参数化8实例，40个五配置开发单元和35个固定提议单元通过独立复算。最终同版 **657 passed / 1 warning**、182文件格式与Vue类型检查/构建通过；Linux非root/只读/无外网单容器四条Host/MCP链完成。无新云调用；两候选的参数化不代表六项正式任务已准入，同容器不代表工具/角色隔离，见[M23](M23_STATUS.md)。
- M22：修复Mac Git临时目录问题、IOC主动发起审批与发送判定；登记六项候选任务，四业务接入共同五配置。最终同版 **536 passed / 1 warning**，172文件格式与Vue类型检查/构建通过；C20/20、A/Q40/40离线开发校准通过，Q逐字引用20/20。无云调用、无危险提议，不作为真实模型防御率或独立任务成绩。参数化新输入与正式冻结仍待完成，见[M22记录](M22_FIRST_BATCH_STATUS.md)。
- M21 最终脚本：四业务 × 正常/注入/合法引用，加四项强制越权校准，共 **16/16 业务完成**；强制提议各阻断秘密读取和外发，云调用为 0。
- M21 云模型：首轮 **3/4** 完成，时间线窗口/排序错误保留；加入有界窗口查询后，同一时间线开发样例单独完成。合计 **18 请求、29,789 tokens**。跨版本结果不合并为成功率。
- M19：35 个强制提议单元符合预定配置差异，45 次脚本业务完成；云模型 **7/10** 完成，三项 IOC 未提出发送动作且 BLOCK=0，不能归因为来源防御收益。
- M20：脚本主流程和真实 MCP 配合一次云分析完成引用核验，云分析 **1 请求、353 tokens**；不是全程自主云 Agent 实验。
- M21当时完整回归在时间线查询修复**之前**：479 passed、2 skipped、1 项既有警告；该阶段修复后业务及引用专项52 passed。M22已另行执行上述当前同版全量检查，历史数字保留；远端CI与新界面浏览器布局尚未验收。

## 接手时必须知道

当前共 **13 个开发 profile**，不等于 13 个已登记的独立基准任务。五配置为 `unsafe / strong-static / full / no-source / no-recovery`，仅供评测使用。

尚未完成：真实模型协议和资源准入、六候选未见输入与预算冻结及同事实 C/A/适用Q/去重R 正式主比较、聚类统计与有效消融、完整三来源×七绕过覆盖、历史裸分类等入口统一、广泛信息保全与恢复对照、新版 Linux 整体隔离/性能验收、正式交付材料与现场复现。当前主/子/Memory/引用分析的完整有效HTTP JSON请求体绑定已完成，精确范围见[M23专项](M23_EFFECTIVE_MODEL_BINDING.md)。Java/MySQL、多操作者、任务/审批跨崩溃恢复也未实现。

子 Agent 在同一 Host 内运行；本地 token 映射不等于云模型内部 token；引用字面核验不证明语义正确；审批单次提交不等于跨重启 exactly-once。所有实验限定于合成、封闭场景，不能称为比赛 ASR、全量公开基准成绩或获奖保证。

接手操作、代码定位与证据保存：[项目交接手册](PROJECT_HANDOFF.md)。全部文档用途：[文档索引](DOCUMENT_INDEX.md)。剩余工作状态：[F3 工作包](F2_IMPLEMENTATION_STATUS.md)。
