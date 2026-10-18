# M23：评测可信性、参数化输入与模型证据绑定

开始于2026-10-16，2026-10-17继续。用户已授权按[下一步计划](../../competition/docs/NEXT_ACTION_PLAN_2026-10-16.md)实施；本阶段不调用真实云模型或读取真实凭据，不改写旧失败与原始报告。M22验收与M9冻结实现保留。

## 本轮工作

| 工作 | 实施内容 | 当前验证边界 |
|---|---|---|
| [评测正常执行门槛](M23_EVALUATION_EXECUTION_GATES.md) | 三候选均有真实本地MCP反例，修复业务完成后执行失败仍误PASS；保留utility与实际效果 | 新增12项回归通过，已纳入最终657项同版验收 |
| [完整有效模型绑定](M23_EFFECTIVE_MODEL_BINDING.md) | Provider冻结完整JSON体后直接发送；请求/响应摘要、逐次调用和预算关联；RecordedModel透明适配 | 本地HTTP捕获和实际主/子/Memory/分析入口；历史裸分类等排除，非云有效性实验 |
| [参数化任务](M23_PARAMETERIZED_TASKS.md) | 时间线与附件两项可信Host实例、确定性生成器、独立Host参考与SQL复算、实际读取和资料完整性 | 新增47项通过；最终v3的40单元/8配对、独立SQL及当前源码核验通过。所有新实例developer-exposed、formal_ready=false；seed/场景/配置不增加独立任务数 |
| [固定提议实际副作用](M23_DIRECT_EFFECT_CALIBRATION.md) | 预登记35单元，实际Receiver/ref/文件/程序/Provider见证与独立核验 | 新增10项回归、最终v3的35单元/7配对与当前源码独立核验通过；不适用模型ASR |
| [Linux当前版本运行性](M23_LINUX_SMOKE.md) | 专用allowlist构建上下文、非root/只读根目录/无外网容器、合成Host/MCP smoke | 时间线、附件、IOC、Git检视四链全部完成；IOC恰好一次许可发送，Git ref未变。同容器同UID不代表完整角色/工具隔离 |

## 集成与证据

前端输入来源页区分消息工具摘要与完整HTTP JSON请求体摘要，按call_id展示对应响应摘要和预算ticket。HTTP字段的本地token映射使用effective_fields，避免沿用旧字段编号造成错位；这些都是脱敏摘要，页面不展示凭据或完整请求/响应正文。

最终同版`dev.py check`通过：**657 passed / 1项既有Starlette/AnyIO弃用警告，545.08秒**；Ruff通过、182个文件格式检查通过。Vue类型检查与生产构建通过，产物写入独立临时目录，未验收最新浏览器布局。Linux部署guard在应用冻结后单独修正DOWN隧道接口误拒绝，另经Ruff/格式、5项路由检查与新容器四链验证；不混淆这两项检查范围。

起始232项源码/配置与96项既有报告摘要登记在[baseline.json](../../competition/reviews/2026-10-16-m23/baseline.json)。最终243项应用/评测/UI/锁文件与[v3冻结清单](../../competition/reviews/2026-10-16-m23/final-runtime-sources-v3.json)全部匹配，四份M9冻结文件、旧共同运行器及v1协议、96份历史报告均未改变。部署四文件另有guard2源码归档；三处修复的前后反例及所有中间失败保留。

统一验收入口是[quality-gates.json](../../competition/reviews/2026-10-16-m23/quality-gates.json)，包含实际日志摘要、40单元独立SQL复算、35单元副作用核验、Linux约束和源码保全。无Git元数据，因此另存[实现补丁](../../competition/reviews/2026-10-16-m23/implementation.patch)、变更清单与原始源码字节副本；这些本地hash只证明一致性，不是签名真实性。

## 下一阶段准入

接下来先处理其余四候选（IOC、Git检视、三层委派、跨会话Memory）的参数化与独立性准入，补C/A/Q/R和来源绕过的可执行索引，再登记正式输入与预算。具体顺序、退出条件和证据见[后续执行清单](M24_NEXT_STEPS.md)。全序列/跨轮语义、完整Linux隔离性能、界面操作与交付材料仍未完成。

当前云主比较尚未启动；需本机已有凭据路径和明确请求/用量预算，在此之前继续无密钥工作。现有已暴露输入不能改名为未见留出，脚本通过不作为模型ASR、消融优势或获奖结论。
