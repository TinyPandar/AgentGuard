# M25：同事实比较与三来源绕过代表

开始：2026-10-18。用户要求从M24验收处继续实施；本阶段目标是为国家级奖项目标形成可复核的新实验接口和有限覆盖，不把开发校准写成模型防御成绩。

## 基线与完成边界

[M24](M24_STATUS.md)最终工程验收为893项测试、80格核心/40格业务/35格固定提议与Linux六链。M25开始前保存265份应用/部署源码的精确副本及1183份历史证据摘要，见[baseline.json](../../competition/reviews/2026-10-18-m25/baseline.json)，SHA-256为`49634899b53819341af0723f784fc8abd4314a3c91c70e80e34e266d95ef1431`。本轮新增独立文件，不改M9四冻结文件、M23/M24协议和原始报告，也不修改依赖锁。

2026-10-18最新完整回归日志为 **1022 passed / 1 warning（759.38秒）**，Ruff与216文件格式通过，见[原始日志](../../competition/reviews/2026-10-18-m25/full-check-v1.txt)。警告仍为既有Starlette/AnyIO弃用提示。用户主动中断后原进程会话无法取回，退出码未虚构，见[执行元数据](../../competition/reviews/2026-10-18-m25/full-check-exit-v1.json)。M24的893项保留为原阶段结果。

最终[281份源码/配置冻结](../../competition/reviews/2026-10-18-m25/final-runtime-sources-v1.json)SHA-256为`88905c9e90af4a3f6f34385f5c3d9da273401a7d64be69fae076b0554dafdc71`；原265份文件和1183份历史证据全部保持一致，M9四项匹配，见[只读保全核验](../../competition/reviews/2026-10-18-m25/model-verifier/final-source-preservation-audit-v1.json)。本轮16个新文件均为评测/协议/测试，不改旧应用运行时、UI或部署。脚本48格、本地HTTP48格和来源14格均已通过各自独立核验，离线基础验收完成；正式云实验未完成。

| 工作 | 当前实现 | 尚待验收 |
|---|---|---|
| 同事实比较协议/运行器 | 六候选同事实48独特单元、14配对，脚本完整执行及独立重算通过；48正常执行/46utility/2实际Git危险效果 | 真实模型新协议、资源准入、未见输入与统计 |
| 原始模型请求与角色证据 | 受检正文、call/ticket与actor/role/session绑定；本地HTTP48格/14配对独立核验通过，48正常执行/46utility/2危险效果；祖先预算15项与逐票scope5项修正回归通过 | 进程内MockTransport，不是模型推理或云ASR |
| 三来源代表 | 14格/7配对实际执行及独立核验通过；14utility/3危险标记写入，仅出现在unsafe攻击格，full对应阻断 | 非完整21格，仍缺真实多轮、纯Memory分片及更多语言/转换 |

脚本矩阵：[48格独立结果](../eval/reports/runs/m25_controlled_scripted_20261018_v1/independent-verification-v1.json)；HTTP矩阵：[48格独立结果](../eval/reports/runs/m25_controlled_offline_http_20261018_v1/independent-verification-v1.json)。各自两危险格分别为`git-review--injected--unsafe`和`git-review--injected--strong-static`的实际推送。HTTP实际传输265次，receipt的795个用量单位是合成回应，不是真实模型token或费用；脚本265次请求用量仍为unknown。三来源：[14格独立结果](../eval/reports/runs/m25_source_representatives_20261018_v1/independent-verification-v1.json)。这些实验不合并为独立任务或模型成功率。整项目与国家级奖项目标的评估见[工作与整体报告](../../competition/docs/M25_AND_OVERALL_REPORT_2026-10-18.md)。

## 比较与判定语义

新比较协议为观察性开发实验，`development-exposed`、`formal_ready=false`。同一候选的C/A使用相同业务事实；两个Q仅限时间线/附件。六候选、seed、场景、角色、配对和配置分别计数；48格不等于48个独立任务，也不代表六项全部五配置。

`records_valid`表示记录/配对/预算和清理符合协议；执行成败、合法utility、实际危险效果与引用保全单独重算。普通Agent失败保留并继续，不要求Unsafe中招或Full成功才接受实验记录。完整性失败、清理未确认、全局预算耗尽或操作者取消按协议停批，UNKNOWN和未执行保留。Host自报与独立事实允许分别呈现，不能靠改写实际观察消除差异。

本地HTTP模式通过实际Bailian Provider的prepare/HTTP解析/receipt/账本路径，传输被限定在进程内MockTransport及合成`.invalid`地址。它不访问外网、不进行模型推理；若误传未注册的Provider，离线模式应拒绝。当前真实云CLI关闭，尚未提供凭据路径和总调用预算；不能仅将旧scripted协议传入凭据后称为正式模型实验。

## 来源覆盖口径

有限首轮为三个来源C/A×unsafe/full=12格，再加直接输入合法Unicode引文Q×2，共14格。攻击脚本只在真实来源暴露之后提出同一受禁写入；Memory要求capture归档结束、reconcile新subject真实读取旧Memory后才提议。危险原文合法归档不是实害，实际篡改、额外版本或外发另计。脚本固定动作不证明语义理解或自然语言ASR。

IOC的公开指标传输和Memory原文存档不自动成为独立Q。三来源×七类型仍有未执行格，直接真实追加轮次、纯Memory分片读取等缺口继续公开；不以21个标签替代执行证据。

沿用已安装的`property-based-testing`和`variant-analysis`流程，采用确定性域/变换不变量和实际反例；未添加Hypothesis依赖或自动缩减能力。详细后续见[M25安排](M25_NEXT_STEPS.md)。

预算复审修正的是新评测运行器和核验器：actor所在的phase/Grant之外还受run及中间父Grant约束；逐票据核对实际scope集合，不能仅检查各run聚合数。两个真实账本反例、初始audit投影错误和并行修改触发sourceguard的旧失败均保留，最终冻结后才运行上述完整矩阵。未新做M25 Linux全矩阵、前端构建/布局或整体性能验收，M24 Linux六链仍按其原范围解释。
