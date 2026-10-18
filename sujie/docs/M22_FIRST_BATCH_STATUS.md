# M22：恢复开发后的第一批实施记录

日期：2026-10-16。用户已要求从[下一步执行计划](../../competition/docs/NEXT_ACTION_PLAN_2026-10-16.md)开始实施，2026-10-15“四业务完成后停止”的历史状态不再表示本轮尚未恢复。F3整体和正式提交仍未完成。

本轮目标为Mac Git修复、IOC合法任务开发修复、候选任务登记和共同运行器扩展。旧M19/M21报告、失败与M9冻结实现保留；本轮结果独立记录，不改写历史成绩。

## 已完成的本机运行修复

`control-plane-python/sujie_control/runtime.py` 在可信Host创建临时目录后使用 `resolve(strict=True)`。执行器仍拒绝不可信Git路径及其祖先别名；没有放宽 `sealed_git.path_identity`。

新增回归覆盖：通过带符号链接祖先的可信临时目录创建Git检视/发布任务，两者均使用规范化根路径；直接向执行器提供不可信别名仍被拒绝。默认Mac TMPDIR下，Git、共同模型运行和配置校准三个测试文件共 **33 passed / 1 warning，151.12秒**，包含原11个失败用例及3项新增回归。后续整体验收以本轮最终全量结果为准。

## 当前Mac环境

- 仓库根目录新建 `.venv/`：CPython 3.12.14，按 `sujie/requirements.lock` 离线缓存安装71个锁定依赖，兼容性检查通过。
- `sujie/.venv/` 是移交的Windows环境，保留原样，当前Mac命令不要使用它。
- `console-vue/node_modules/` 已按原锁文件重建Mac依赖；原Windows目录保存在 `console-vue/.tmp/node_modules-windows-pre-m22/`，该目录不进入公开交付包。
- 在实际前端目录执行类型检查与生产构建通过；本轮验证输出写到独立临时目录，原dist未被该验证覆盖。
- 已只读确认现有Docker为 **Linux / Docker Desktop / 29.4.0**，当前未发现Python/Sujie本地镜像。这改变了旧交接时“暂无Linux资源”的事实，但不代表新版完整拓扑、旁路隔离或性能已验收。本轮未因该确认拉取镜像或启动容器。

从仓库根目录执行本机检查：

```bash
./.venv/bin/python sujie/dev.py check
```

前端在 `sujie/console-vue/` 中使用 `npm run build`。若需启动控制台，从 `sujie/` 使用 `../.venv/bin/python control-plane-python/run_console.py`，自定义端口/预算参数直接传给该脚本；不要在未导出用户任务前停止既有服务。

## IOC开发修复与候选任务登记

IOC初始提示、工具说明、读取后反馈及有界纠正提示明确“调用发送工具发起审批，Host暂停等待真实审批结果”。公开Oracle新增精确IOC载荷、准确一次与拒绝状态，避免把合法结束误当原发送目标完成。新增六项离线HTTP捕获校准，与原九项审批测试共 **15 passed / 1 warning，24.57秒**；正常、注入、过早结束后的纠正、拒绝、超时与批准后取消均保留真实副作用判定。见[IOC修复记录](M22_IOC_DEVELOPMENT_REPAIR.md)。

原三个IOC云失败能确认未提出发送动作；原导出不能恢复完整模型原话，不能直接证明失败由某一提示歧义导致。本轮只证明Host/工具说明与控制流的离线行为，不代替同版真实模型复测，原M19仍为7/10。

已新增六候选任务的机器可加载注册表、真实源码符号引用与C/A/Q/R映射，区分业务/安全/执行状态和审批控制流。双Oracle支持PASS/FAIL/UNKNOWN，缺少见证不会默认为安全通过；宽Grant或推送尝试也不直接当实际攻击成功。注册表专项 **24 passed，8.44秒**，包括真实MCP引用保全及错误报告阴性校准。详见[任务登记](M22_TASK_REGISTRATION.md)。

## 四业务共同五配置开发校准

四类M21业务已接入新的共同运行器与独立CLI核验器。最终clean报告为四业务×五配置，共 **20/20**；每单元执行FINISHED、无错误、业务判定通过，四组配对成立，Receiver请求0、合成蜜标泄漏0，云调用0。服务账本保留80次脚本调用的未知usage，不把reported_tokens=0当云成本为零的测量结论。

独立复审修复了“业务已真实完成但执行后续失败仍判校准通过”的缺陷：执行状态和业务结果分开判定，FAILED/CANCELLED或带错误不能通过校准，但仍保留实际业务完成与副作用。另补协议选择、主动省略和计划单元的严格派生核验，以及独立CLI模块路径修复。

三份开发报告及中间源码均原样保留，最终版本位于 `eval/reports/runs/m22_common_business_clean_five_configs_execution_gated_20261016/`。独立CLI核验20单元/4配对、当前源码对应、M9四冻结摘要均通过；最终源码归档SHA-256为 `9dbaa930d6418cf92c1879ca0854f402bb98df75fee97808e22be4b907689169`。详见[共同运行器记录](M22_COMMON_RUNTIME_DEVELOPMENT_V2.md)。

随后保持上述源码归档不变，单独运行四业务×五配置×A/Q，共 **40/40**；8组配对、真实读取/正确报告/资料完整性与执行门槛均通过，Q逐字引用 **20/20**。报告位于 `eval/reports/runs/m22_common_business_attack_quote_five_configs_20261016/`，独立CLI核验通过。Receiver请求0、蜜标泄漏0，190次提议均为必要读取或业务报告写入；危险提议、BLOCK和ASK均为0。160次脚本调用的usage仍为未知。

两份最终报告合计 **60个开发配置单元**，覆盖C/A/Q，不是60个独立任务。协议登记的强制提议与其他任务C未在本轮报告执行，不计通过；注册表的R映射也不表示本轮已做真实模型授权实验。脚本没有产生危险提议，不能计算模型ASR、归因网关阻断或宣称消融收益。

## 最终质量验收与剩余范围

最终源码冻结后执行 `dev.py check`：ruff通过、**172文件格式检查通过，536 passed / 1 warning，414.88秒**，退出码0，无跳过。警告为既有Starlette/AnyIO弃用提示。检查结束后复核206项源码摘要无变化。前端DTO补齐IOC三布尔可选字段后，类型检查与生产构建已通过，未宣称浏览器布局验收。验收摘要见[quality-gates.json](../../competition/reviews/2026-10-16-implementation/quality-gates.json)，原始全量检查输出见[full-check-final.txt](../../competition/reviews/2026-10-16-implementation/full-check-final.txt)。

现有业务输入已经暴露，任务登记和新业务共同配置校准仍按development记录。正式独立任务输入/协议冻结、预算确认与云主比较尚未完成。

当前仍需参数化fixture与独立Oracle、生成并封存新输入，完成完整模型请求/返回证据、21单元覆盖、跨轮语义/时序、Linux新版隔离与性能和正式材料。云复测需要本机已有凭据路径与明确请求/用量预算；本轮未读取真实凭据、未发起云请求，也未强行清理旧用户任务或预算账本。

本轮起始源码及历史报告摘要已另存 [baseline.json](../../competition/reviews/2026-10-16-implementation/baseline.json)，可审查源码变更见[implementation.patch](../../competition/reviews/2026-10-16-implementation/implementation.patch)。原8项历史报告摘要、共同运行器v1/协议与M9四冻结文件均未改变。第一批本机修复与上述离线校准已验收；P0-C的参数化新输入与正式任务冻结仍未完成，不能据此启动正式主比较。
