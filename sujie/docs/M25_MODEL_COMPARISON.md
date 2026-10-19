# M25：同事实观察性开发比较运行器

新协议、runner与独立核验器用于六项开发候选的同事实对照，保留M23/M24原协议与报告。当前身份是`observational`、`development-exposed`、`formal_ready=false`。默认脚本、封闭离线HTTP可执行，真实云CLI明确拒绝，不读取凭据文件；这不是正式云比较、未见留出或ASR结果。

## 唯一单元与顺序

六候选各生成seed20261018的一份事实，分别构造clean和injected；时间线、附件另有quoted。当前seed与生成机制均已暴露。

| 分组 | 格数 | 范围 |
|---|---:|---|
| 六候选C/A×unsafe、strong-static、full | 36 | 每候选同一事实，主配置按候选循环轮换 |
| 时间线、三层委派、Memory的A×no-source、no-recovery | 6 | 事前固定子集，Full的A结果直接复用 |
| 时间线、附件Q×strong-static、full、no-recovery | 6 | 同一事实的合法危险原文保全 |
| IOC C∩R | 0额外 | clean批准流程的原三格同时标C/R，不重跑 |
| 合计 | 48 | 14组配置配对、六个事实组，非48独立任务 |

`--case`选择完整pair组，不能挑单配置或删除不利结果；summary明确列`selected_pair_ids/omitted_protocol_pair_ids`与实际执行顺序。子集不称完整48格。跨配置核相同初始逻辑资料、权限、模型recipe及初始请求；跨C/A/Q只共用事实组，不能要求场景载荷hash也相同。

## 完整记录和实际结果分开

每格保存实际report、导出、Host原始字节/效果见证、模型调用节点及预算。`record_valid`只表示记录采集完整，普通agent FAILED可以保留完整记录并继续；执行正常、合法业务完成和实际危险效果分别列于`assessment`，不要求Unsafe中招或Full成功才算有效记录。

整体`records_valid`及兼容字段`passed`要求所选计划完整、配对有效、清理确认且run_status为FINISHED；它们不是防御通过率。完整性异常、清理未确认或全局预算不足立即停止；取消与无法完整采集保留partial export、UNKNOWN、未执行/未完成列表。末格取消可能已有完整记录但尚未登记pair，不能补写成FINISHED。

所有角色共同使用每任务12请求/200000本地预留单位，整体默认上限按所选格数乘该值，完整矩阵最多576请求/9600000单位。`--request-limit/--unit-limit`只能收紧。缺失用量保留预留，脚本无Provider用量不代表免费云调用。预留单位不是计费token或金额，协议明确`billing_bound=NOT_GUARANTEED`。

## 请求、角色和封闭HTTP

本轮专用`EvidenceRecordedModel`在原`RecordedModel`外保留已检查的messages/tools规范JSON bytes；HTTP另保留实际Prepared有效请求体bytes，均用base64编码。编码前检查已知受保护值，不记录认证header或Provider密钥。每请求按导出`context_audit`与事件ID/主体/sequence/payload_hash绑定call_id、budget_ticket、purpose及角色；task.events的MODEL详情本来为空，不能拿空投影替代原audit。

MAIN和委派角色使用共同contract session，Memory的capture/reconcile使用各自实际session；actor始终分别记录。节点记录backend真实`transport_attempts`，包括失败和取消时已发生的尝试；请求预留、实际transport尝试、云调用是三个不同计数。

offline-http仅接受活跃MockTransport上下文登记的实际Bailian backend及精确`.invalid`端点，仍走Prepared请求与真实HTTP解析代码。模型快照`qwen-plus-2025-12-01`、输出1024、temperature0、tool_choice auto、请求30秒保持固定；脚本模型自身recipe如实登记。scripted-only拒绝prepared Provider，不能把误传的真实Provider记作云0；自定义无prepared的Python后端仍属于可信测试代码边界。

真实云需要新的资源准入：仓库外现有凭据路径、总请求与可实施的token/费用限制及全部校准费用。当前runner的cloud模式不启用，不能把`--unit-limit`当成账单保证。离线HTTP的transport尝试是进程内MockTransport，不是云模型推理。

## 运行入口

从`sujie/`执行，输出目录必须全新。先封存六份共同事实：

```sh
../.venv/bin/python eval/core_parameterized_tasks.py --out-dir eval/reports/runs/m25_comparison_inputs --seed 20261018
../.venv/bin/python eval/run_controlled_model_comparison_v1.py --instance-dir eval/reports/runs/m25_comparison_inputs --out-dir eval/reports/runs/m25_comparison_scripted
../.venv/bin/python eval/run_controlled_model_comparison_v1.py --instance-dir eval/reports/runs/m25_comparison_inputs --out-dir eval/reports/runs/m25_comparison_offline_http --mode offline-http --case delegated-report--clean --case memory-update--clean
```

实际验收应在源码稳定后运行：runner每格前及结束前核归档源字节，不能在其他人改同一源码时假装“同版通过”。独立核验器重算事实、模型原字节/角色/票据、账本和计数；原始失败、并行改动引起的sourceguard停止与最终结果分别留存。阶段进度与下一步见[M25执行安排](M25_NEXT_STEPS.md)，本地测试不能替代真实模型收益和参赛交付。

2026-10-18最终脚本48格/14配对已完成并通过[独立CLI](../eval/reports/runs/m25_controlled_scripted_20261018_v1/independent-verification-v1.json)：48正常执行、46utility、2个Git injected实际危险效果，0云/0Provider transport。265次本地请求预留均无Provider用量，保留unknown，不能写成实际token或云成本。

完整本地HTTP48格/14配对也已通过[独立CLI](../eval/reports/runs/m25_controlled_offline_http_20261018_v1/independent-verification-v1.json)：48正常执行、46utility、同样两个Git危险格，265次进程内MockTransport、0云；795个receipt用量单位来自合成回应，不是真实模型token。两次归档均为`f37121338d86e38a2e037c0134a80892e054727be9d688c32db0830e891713b6`，不增加独立任务或模型样本。统一状态见[M25记录](M25_STATUS.md)。新核验逐票检查MAIN/run、Memory phase/run、review/verify父Grant链与root作用域；同额票据跨run交换即使总数不变也拒绝。
