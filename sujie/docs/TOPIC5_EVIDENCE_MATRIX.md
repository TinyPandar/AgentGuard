# 题目5：要求—实现—证据矩阵

更新：2026-10-18，[M25](M25_STATUS.md)同事实比较与三来源有限代表已实施，脚本48格及来源14格已通过独立核验；完整离线HTTP状态以阶段总记录为准。全量原始日志记载1022 passed/1 warning、Ruff及216文件格式检查通过，用户中断后未取回进程退出码。整体研判见[M25与项目报告](../../competition/docs/M25_AND_OVERALL_REPORT_2026-10-18.md)；[M24](M24_STATUS.md)的893项及Linux六链保留历史验收边界。F3整体未完成，下一步见[M25安排](M25_NEXT_STEPS.md)。官方依据是[2026-10-14题目快照](../../competition/research/2026-10-14/topic5-official.json)，原始SHA-256 `d758dfe33aa17ce023d8538381d93bdb619fe2ad69fdbcc9593264b315360368`。下面历史证据仍按原阶段解释，不扩大为正式比较成绩。

[已完成汇总](COMPLETED_WORK_SUMMARY.md) · [运行/代码/证据手册](PROJECT_HANDOFF.md) · [W0–W9状态](F2_IMPLEMENTATION_STATUS.md)

## 官方能力与实际支持

| 要求 | 已有实现和阶段证据 | 剩余缺口 |
|---|---|---|
| 1：直接/间接/Memory注入识别 | M11可信补充输入不扩权、MCP正文/元数据规则；M18两实际会话恢复来源并重新检测Memory；M25三来源有限代表经真实暴露后做固定禁止提议并核对实际写入 | 三入口全路径、更多隐性触发/检索和完整执行矩阵，W1/W4/W7 |
| 2：原始意图/计划/全工具序列 | [M13](M13_SEQUENCE_AND_TEMPORAL_SOURCES.md)可信目标、可见提议、全记录工具提议、来源、实际效果/UNKNOWN及请求回复关联 | 跨轮/组合语义、分级检测与更多任务；可见计划不含隐藏思维，W2 |
| 3：语义DSL与三态 | Contract/Grant、效果适配、DSL、ALLOW/ASK/BLOCK；IOC/Git自主审批、执行前复核 | 五效果完整目标矩阵与更广部署，W3/W5 |
| 敏感目录写入 | 逻辑路径/工作区写授权及边界/逃逸测试 | 各敏感目录/平台实际目标矩阵与系统级验收 |
| 敏感网络外发 | [M14](M14_NETWORK_AND_WEB_WORKFLOW.md)真实封闭GET/POST，目标/重定向/header/body/来源检查；M4来源消融 | 公开HTTPS/新隔离拓扑、更广合法请求及任意分片改写DLP |
| 编码/下载执行 | [M15](M15_STRUCTURED_EXECUTION_AND_ARTIFACT.md)注册程序、argv/摘要绑定、拒绝解释、真实子进程/收据 | 通用OS沙箱、进程树/资源限制/跨平台矩阵 |
| 检视下Git推送 | [M16](M16_GIT_DELIVERY_AND_APPROVAL.md)实际封闭Git交付，确切remote/ref/commit/旧值/配置/lease；检视拒绝/授权ASK；M24可变配置事实与真实blob/diff/ref/收据独立参考通过开发校准 | 任意外部Git服务、不可信仓库与完整Linux隔离 |
| 敏感委派 | [M17](M17_ACTUAL_ANALYTICAL_AGENTS.md)秘密输入创建前拒绝、只读子/孙对话，资源/权限/预算收窄、父撤销；M24三源可变事实、主体读取及子输出引用见证通过独立核验 | 更多完整性攻击形态与跨进程隔离 |
| 4：多MCP/多层Agent | M17三个实际对话/两MCP，主体/父子/深度与来源交接；M18两实际会话/版本原文；M24补跨会话实际原文、SQLite行、CAS收据和读取/写入顺序核验 | 同Host非OS隔离；更完整可视化时序和受控正文访问，W4/W9 |
| token来源/DAG/参数返回/影响 | M11本地tokenizer、字面/JSON转义与M13前缀绑定；[M23](M23_EFFECTIVE_MODEL_BINDING.md)当前主/子/Memory/分析完整有效HTTP JSON体冻结、响应摘要/call/预算关联；Trace/DAG与实际状态 | 历史裸分类等入口、全转换/时序展示；响应为HTTPX解码bytes，本地token不等于云内部token，W1/W9 |
| 5：七类绕过及语言 | 有界规范化、部分Unicode/编码/分片/语义伪装等开发变体；M4/M5/M9/M10；M25直接Unicode、外部Base64、Memory语义伪装共14格有限开发执行 | 中英日俄/Emoji、Unicode、分片多轮、注释分隔符、格式编码、上下文稀释、语义伪装完整覆盖与独立执行，W7 |

## 业务与实验支持（不是额外官方硬条件）

- [M25同事实比较](M25_MODEL_COMPARISON.md)：六候选各一份已暴露业务事实，同事实C/A与适用Q、IOC C/R复用，48个独特脚本单元/14配对通过独立核验；正常执行48、业务完成46、实际危险效果2（Git注入的unsafe/strong-static）。[三来源代表](M25_SOURCE_BYPASS.md)14格/7配对全部业务完成，3次禁止的本地标记写入仅在unsafe下、Full为0。禁止动作在真实来源读取后固定提出，证明有限执行边界，不证明自然语言理解或来源机制独有收益。完整离线HTTP矩阵以[M25记录](M25_STATUS.md)为准；Mock无模型推理，云0。281份源码/配置冻结，旧265份及1183份证据保全；无新Linux、前端或性能验收。
- [M24](M24_STATUS.md)：IOC、Git检视、跨会话Memory、三层委派四候选已补Host私有事实manifest和独立参考；最终v2四候选80/80格、16配对通过校准，其中76格完成合法业务、4格观察到Git injected在unsafe/strong-static下的危险发布。旧业务40/40格、8/8配对和固定提议35/35格、7/7配对独立核验通过；[旧链v2对应](../../competition/reviews/2026-10-17-m24/revalidation/after-core-verifier-v2.json)保留不重跑的源码覆盖依据。最终893 passed/1 warning、202文件格式检查和受限Linux六业务链通过。合计六项仍是已暴露开发候选；重复运行不增加独立样本，校准通过不等于全部安全，无新云调用、正式ASR或完整隔离/性能结论。
- [M23](M23_STATUS.md)：三处评测执行门槛修复；两候选8实例/40个开发单元与35个固定提议单元通过独立核验；最终657项回归、Vue类型检查/构建、受限Linux四链通过。无新云模型调用，不表示正式独立任务/ASR或完整隔离性能验收。
- [M22](M22_FIRST_BATCH_STATUS.md)：Mac Git与IOC开发修复、六候选任务登记、四业务共同五配置C20/20与A/Q40/40离线校准；最终同版536 passed/1 warning及Vue构建通过。未产生危险提议，无真实云调用；不是独立留出、ASR或消融优势，参数化输入/正式冻结仍待完成。
- [M19](M19_COMMON_RUNTIME_AND_BASELINES.md)：共同5配置和2消融，35强制提议单元/45脚本业务校准；云7/10完成。3次IOC失败未提发送/BLOCK0，不归因来源机制。公共执行器/Provider保障不计为Full独有贡献。
- [M20](M20_VERIFIED_EVIDENCE_QUOTATIONS.md)：report有界无工具分析，Host字面核对/位置/未引用区间；语义标签为建议，保留原限制。脚本主流程+云分析1请求353tokens，不是完整W6或自主云任务。
- [M21](M21_FOUR_BUSINESS_WORKFLOWS.md)：四个多源业务实际MCP/读取/事实/完整性Oracle，当前13开发profile；最终16脚本运行完成。四云首轮3/4，时间线修复后单独完成，跨版不合并成功率。正式独立任务登记、C/A/Q/R五配置主比较和聚类统计仍待完成。
- 当前控制面主/子/Memory及正文分析角色已做完整有效HTTP JSON请求体绑定与本地捕获验证；历史分类/独立直接调用入口仍按登记排除，不称全覆盖。
- [M23 Linux](M23_LINUX_SMOKE.md)四链和[M24](M24_STATUS.md)六业务链分别保留各自阶段证据，均在同容器/同UID完成；新版整体工具/角色隔离与性能仍待验收。Java/MySQL、12/60任务、200案例、288内部运行和延迟目标均为内部设计选择，不是题目新增要求或已有成绩。

**M25已形成离线同事实比较基础与有限三来源执行证据；F3整体、真实模型协议与资源准入、未见任务冻结、有效消融/统计、完整绕过覆盖及隔离/性能/材料仍未完成。** 冲击国家级奖项的下一阶段重点是同事实对照、实际安全与合法业务收益、复现和匿名交付，具体见[M25安排](M25_NEXT_STEPS.md)。
