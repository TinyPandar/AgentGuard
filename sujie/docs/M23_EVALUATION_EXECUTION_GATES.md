# M23：正常业务校准的执行门槛

开始日期：2026-10-16；续作日期：2026-10-17。范围为 M22 已知错误的三个静态候选的动态验证与最小修复，不是全面安全审计，也不是对历史实验得分的追溯改写。

## 结论与修复

三个候选均在纯脚本故障注入、实际本地 MCP 执行中构造出误 PASS 见证。报告已经正确落盘后，下一次 `complete()` 抛出 `ModelProtocolError`，运行时保留 `task_completed=True` 并正确置 `status=FAILED`；旧调用方仍可能将实际业务事实提升为正常校准 PASS。

以下三个入口现在同时要求 `agent.status == "FINISHED"` 和显式 `error_code is None`，再检查原有业务、安全、轨迹条件；缺失 `error_code` 不予通过。实际业务完成、Receiver、安全观察和原始错误均保留。没有把已经发生的业务副作用改成未完成。

| 入口 | 改动 | 等级 / 置信度 |
|---|---|---|
| [run_business_validation.py](../eval/run_business_validation.py) | 行 PASS 增加正常执行门槛；原有云模式失败 break、未执行格和整批汇总保持 | Medium / High；已修复 |
| [evidence_quote_calibration.py](../eval/evidence_quote_calibration.py) | 行 PASS 增加主任务正常执行门槛；调用者继续转发为批 PASS | Low / High；已修复，见证依赖主脚本故障注入 |
| [run_sequence_calibration.py](../eval/run_sequence_calibration.py) | 增加正常执行门槛；summary 新增原始 agent，原有工具序列条件保持 | Low / High；已修复，见证依赖模型计划拆分故障注入 |

没有新增生产模型工厂接口，没有引入依赖，没有修改共同运行器 v1/v2、预期拒绝校准、既有协议或历史报告。

## 从静态候选到动态见证

使用 [Trail of Bits variant-analysis](https://github.com/trailofbits/skills/tree/main/plugins/variant-analysis)；已阅读安装版本的 SKILL.md、四篇 references 和报告模板。原始根因、逐级检索、8 处结构命中与 5 处误报排除见[前轮窄范围试用报告](../../competition/reviews/2026-10-16-skills/variant-analysis-trial.md)。本轮没有扩大检索范围，也没有把广义结构匹配直接当作 CI 阻断规则。

真实本地 MCP 反例摘要如下。所有行均实际完成报告写入，`status=FAILED`、`error_code=MODEL_PROTOCOL_ERROR`、`task_completed=True`、Receiver 请求数 0、honeytoken 泄露 False，云请求数 0。

| 注入位置 | 旧行 PASS | 旧批 PASS | 说明 |
|---|---:|---:|---|
| 业务四格首格 | True | False | 批次保留 INCOMPLETE，后 3 格未执行；break 保护了批次完整性，但未纠正行结果 |
| 业务四格末格 | True | True | 已跑满 4 格，旧聚合条件将失败末格一并计为成功 |
| 引用报告写入后 | True | True | 业务事实、危险命令逐字引用和原文不变均成立，主执行却已失败 |
| 序列：原分组提议后 | False | False | **阴性反例保留**：只有 2 个可见计划，附带的 3 计划条件挡住了误判 |
| 序列：同提议拆成 3 个计划后 | True | True | 仅将原第 2 轮的 3 个提议拆成 2 轮；仍是 4 提议、阻断 [2,3]、确认执行 [1,4]，下一次完成请求失败 |

业务见证为避免云费用，在测试中将凭据加载替换为合成对象、云后端构造替换为脚本模型，实际走云模式的首格失败 break 和末格汇总分支。没有打开真实或合成 CSV 文件，没有创建真实云 HTTP 客户端。该分支的报告 kind 仍沿用原 runner 的 model-validation 字段，不能据此称为真实云实验。

引用校准的云分析阶段发生在报告写入之前；本轮没有声称“云分析在报告完成后自然报错”。反例仅向主脚本的下一次完成请求注入错误。序列的原固定脚本正常返回同样不会自行生成拆分模型；记录其适用条件，避免把故障注入可达性说成已观察到的生产事故。

完整修复前源码归档、导出、摘要、报告正文、预算账本和复现脚本保留在[反例证据目录](../../competition/reviews/2026-10-16-m23/evaluation-execution-gates/)。[counterexample-index.json](../../competition/reviews/2026-10-16-m23/evaluation-execution-gates/counterexample-index.json) 记录每个文件哈希和五组观察。原前轮的三个 Pending 仅由本轮新证据升级，原报告本身保持不变。

## 回归与边界

新增 [test_evaluation_execution_gates.py](../tests/test_evaluation_execution_gates.py) 共 12 项回归，直接断言行 PASS 和批 PASS，保留真实 MCP 副作用及错误状态，不只测试重新抄写的布尔表达式：

- 业务：首格失败、末格失败、四格全正常；检查未执行格、批状态及已写报告的业务 Oracle。
- 序列：原分组晚失败、三计划晚失败、正常完成；检查原始导出、4 提议、可见计划数、阻断与确认执行序号。
- 合法引用：晚失败、实际 CancelledError 取消和正常完成；检查原文不变、业务事实和命令原文保全，以及行/批判定。
- 状态契约：在实际引用报告写完后，测试专用 Host 子类分别注入 FINISHED 携带错误码、FINISHED 缺少错误码两种状态；行/批均不得 PASS。这是合成状态故障验证，不声称当前运行时能自然产生这两种状态。
- 阴性对照：直接工具 `secret-provider-floor` 保持模型 NOT_STARTED、预期 provider 拒绝、实际 provider 尝试为 0，utility 仍为 True。此类有意验证拒绝的校准不适用正常主任务执行门槛。

前两轮均为 8 passed / 1 failed；仅新增阴性对照的测试夹具不正确：首轮使用了非 ULID scope，被原有输入校验在执行前拒绝；第二轮把未启动状态误写为 IDLE，实际枚举是 NOT_STARTED。已改用 `new_id()` 和实际状态枚举，两轮失败日志均保留，未作为产品缺陷。随后原 9 项通过（24.28 秒），补充的取消/状态契约 3 项通过（5.49 秒）；最终 **12 passed，1 个既有 Starlette/AnyIO 弃用警告，29.61 秒**。四个源码文件的 Ruff 和格式检查均通过。

最终回归日志、前两轮失败日志及修复后逐组摘要保留在[同一证据目录](../../competition/reviews/2026-10-16-m23/evaluation-execution-gates/)，[after-validation.json](../../competition/reviews/2026-10-16-m23/evaluation-execution-gates/after-validation.json) 记录测试源码哈希与输出索引。随后整项目最终同版657项通过，见[M23总验收](M23_STATUS.md)；其中已包含本专项12项，不能重复累加。

可从 `sujie/` 运行：

```sh
PYTHONPYCACHEPREFIX=/private/tmp/sujie-m23-20261016/pycache \
  ../.venv/bin/python -m pytest tests/test_evaluation_execution_gates.py -q
```

本机实际 MCP 启动需要允许本地回环端口；完全受限的沙箱运行结果不能作为产品失败判定。测试不使用真实模型、不测攻击成功率，也没有验证全部模型/隔离故障种类。CI 回归入口是上述行为测试；5/8 噪音率的旧 AST 搜索模式仍不适合作为自动阻断规则。
