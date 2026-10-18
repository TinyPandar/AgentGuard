# M23：固定提议的实际副作用校准

开始日期2026-10-16，续作日期2026-10-17。复用既有共同运行器的直接提议阶段，在新目录验证当前源码；旧M19报告、原协议与共同运行器v1保持原样。本记录不表示模型攻击成功率或正式独立任务评测。

## 范围与判定

预登记矩阵为7条封闭链路×5配置，共35单元：带来源限制的正文外发、检视下Git推送、授权Git推送、业务外文件写入、未注册程序与合法构件核验、网页资料转发、秘密读取与共享Provider出口保护。每组使用相同逻辑初态与提议，在新的合成靶场运行；统一测试主体对所有绑定ASK执行批准和提交。

预期实际影响和业务事实在运行前写入 [effect_calibration_m23_v1.json](../eval/protocols/effect_calibration_m23_v1.json)。这里没有自主Agent启动，状态应为 `NOT_STARTED`；这一限定不适用于要求正常完成的自主业务，后者仍需FINISHED且明确无错误。

新增独立核验器 [verify_effect_calibration_m23.py](../eval/verify_effect_calibration_m23.py)，先核对源码归档、导出和配对，再用Receiver载荷摘要、Git实际ref/推送回执、文件前后摘要、进程启动及实际保存报告重算影响与业务事实，并交叉核对公开Oracle。原运行器保留自己的判定；新增核验器额外要求预登记的utility观察符合预期，不能用ALLOW/BLOCK直接替代实际效果。

exec/web校准新增实际报告原文见证，避免只信任构造报告前的临时变量。进程见证区分日志行数、未注册动作的实际启动数、注册动作启动数和最终总启动数；旧汇总器对带新字段的记录使用实际启动数，对旧归档保留旧解释。

## 独立复审与阴性验证

复审发现并修正了三个交叉观察遗漏：Git见证与公开ref/attempt/confirmed不一致，IOC许可载荷判定与公开两布尔不一致，以及进程见证与总启动数不一致。新增实际MCP后篡改单项观察的阴性测试，矛盾记录必须被拒绝。另避免把STARTED/FINISHED等多行回执重复当多个进程。

旧runner在中断时可能尚未填写reported_tokens。新增核验器先核对可用归档，再明确报 `EFFECT_INCOMPLETE_RUN`，不将其误称为摘要损坏或补成成功；测试保留35个未完成单元及失败位置，原输出不修改。

新增 [test_effect_calibration_m23.py](../tests/test_effect_calibration_m23.py) 最终 **10 passed / 1既有Starlette/AnyIO警告，11.13秒**。包含真实注册进程、HTTP、Git和IOC链路，错误报告、矛盾观察、Provider公共底线、中断保全及独立CLI入口。早期6项、交叉检查后9项及最终10项日志全部保留，整项目验收另记。

## 最终同版运行

最终v3报告位于 `eval/reports/runs/m23_direct_effects_20261017_v3/`：**35/35单元、7组五配置配对全部通过**，实际影响与预登记矩阵相符，独立CLI核验ok、当前源码匹配与M9四冻结检查均通过，云调用0。归档SHA-256：`ff78e9618a424ed043201a9531f3df60e54b64683d848066fda745cc497c8e17`。

前一版 `_v1` 也完成35单元，但其后参数化输入边界和取消记账代码修正；该报告保留，不能算为最终同版额外样本。最终核验器/协议/测试准确源码在v3目录的 `m23-verifier-sources.json`，对应[验证记录](../../competition/reviews/2026-10-16-m23/direct-effects/validation.json)；各轮测试、运行日志及受控中断报告已保留。复现必须选择新目录：

```sh
../.venv/bin/python eval/run_common_runtime_validation.py \
  --stage calibration --out-dir eval/reports/runs/a-new-m23-effect-run
../.venv/bin/python eval/verify_effect_calibration_m23.py \
  eval/reports/runs/a-new-m23-effect-run \
  --out eval/reports/runs/a-new-m23-effect-run/m23-verification.json
```

原runner的runtime-sources归档不自动包含新增核验文件，复现者需同时保留上述补充源码归档和根实现补丁。

## 结论边界

固定提议校准验证门禁与实际效果是否一致。Unsafe仍共享注册执行器、封闭路由、Provider秘密保护等底线，公共底线的拒绝不能归为Full独有收益；本阶段也不检验模型是否服从攻击、恢复提示是否改善模型行为，或人类能否正确审批。Receiver、Git、文件、程序均为本机合成靶场，本地哈希一致性不是外部签名认证。正式新输入、C/A/Q/R云比较、完整Linux拓扑隔离和性能分别验收。
