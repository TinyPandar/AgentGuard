# 检测器版本与选择

| 模块 | 版本 | 用途 |
|---|---|---|
| `gateway-python/src/sujie_gateway/detection.py` | `rules-v0.3`（冻结） | 被 `eval/task_aware_protocol.py` 按字节哈希固定（task-aware held-out 协议）。**不得修改**；与 upstream/main 逐字节一致。 |
| `gateway-python/src/sujie_gateway/detection_v2.py` | `rules-v0.4+`（扩展） | 七类绕过、公开数据集规则、结构化中文规则（`zh_rules.py`）等后续检测器工作。 |

- 选择器：`sujie_gateway/detector.py` 的 `get_detector()`；环境变量 `SUJIE_DETECTOR=frozen|extended`。
- **运行时默认 `extended`**：`m1_runtime` 在导入时绑定所选检测器（所有冻结协议测试在该默认下通过，因为协议只固定源文件哈希，不要求运行时使用冻结检测器）。
- 复现冻结检测器行为：启动前设置 `SUJIE_DETECTOR=frozen`。
- 历史评测脚本（InjecAgent、MCP-SafetyBench、task-aware、`run_detection.py` 等）继续直接导入冻结的 `detection`；
  七类绕过矩阵与公开数据集评测（`run_bypass_matrix.py`、`run_public_injection.py`）显式导入 `detection_v2`。
