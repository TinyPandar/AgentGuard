# 七类绕过：三来源规则检测矩阵 v2

本页是 **2026-10-18 新开发批次**，不追溯修改 M9 冻结分类实验、M21 云任务结果或 `detection_v1.json` 历史样本。代码在 `feat/seven-bypass-matrix` 分支验证后才能视为发布。属于 **提示注入初筛**，不是 Agent 攻击成功率/网关实际阻断率。

## 覆盖范围

`eval/cases/bypass_matrix_v2.json` 为 3 种入口（DIRECT 认证消息补充、INDIRECT 外部工具结果、MEMORY 记忆读取）× 7 种绕过标签 × 攻击/正常对照，合计 **42 条合成规则检测样本**（21 攻击 + 21 对照）。每个单元 1 个样本，不代表独立业务数或随机分布下的检出率。测试可重新运行，也不会覆盖旧数据集。

七类：多语言/Emoji、Unicode 混淆、跨片段/多轮、注释与分隔符、字符编码、长上下文稀释、语义伪装。标签是基准扰动类别；检测器的 `attack_family` 按实际规则含义（例如 CONTEXT_HIJACK、AUTHORIZATION_FORGERY）生成，不应混为一谈。

## 方法及边界

- 单源规则仍走 `detect_indirect`，运行时 DIRECT/INDIRECT/MEMORY 可沿用现有调用。新增 `detect_indirect_segments` 接收 **Host 已核验且同一信任上下文** 的有序 `(artifact_id, text)`，同时扫描各段与顺序拼接。只有调用方明确传入的分段才有跨轮能力；**未修改主 Host 使其自动聚合所有跨轮消息**。
- NFKC、零宽、HTML/URL 双轮解码之外，增加有限 Unicode escape、显式标记 Base64、部分混淆字形、日俄覆盖、可解释的已授权敏感外发伪装。未知编码/隐喻、自由重写的语义注入仍可能漏检，需要独立任务感知分类及执行策略处理。
- 对 `>1,000,000` 字符的输入显式抛 `CONTENT_SCAN_LIMIT_EXCEEDED`，调用方必须拒绝/分段后再处理，不能把错误视为 CLEAN。归一化可缩短视图；原文和原始长度独立保留。命中范围为整段保守原文范围，不伪造字符级精确映射。
- 仅对明确培训引用且不执行的 **完整单段** 使用保守豁免；增加新的执行指令仍检出。该启发式并非通用引用理解。
- 检测结果仅是 `DETECTION_FINDING` 辅助信号，**不直接赋权，也不代替** Contract/Grant、来源用途、执行前复核、真实出口保护。语义分类器、动态执行、审批流程和真实副作用需单独验收。

## 离线复现

从 `sujie/` 使用 Python 3.12 项目环境：

```powershell
.\.venv\Scripts\python.exe eval/run_bypass_matrix.py --out eval/reports/runs/seven_bypass_v2.json
.\.venv\Scripts\python.exe -m pytest tests/test_seven_bypass_matrix.py gateway-python/tests/test_detection.py tests/test_detection_eval.py -q
.\.venv\Scripts\python.exe dev.py check
```

若输出路径已存在，评测拒绝覆盖。JSON 包含数据 SHA-256、检测器版本、42 条样本逐项结果、每来源/类别混淆矩阵，不回显样本正文。报告中的“攻击召回/正常误报”仅指 **合成规则分类**；无 LLM 请求、模型诱导提议、真实泄露/篡改、业务完成与 Receiver Oracle，不得称为比赛 ASR。

下一步必须将三来源真实通道分段绑定、加入 C/A/Q/R 独立任务、跨工具序列和真实副作用 Oracle、模型预提议与执行后阻断判定，才可扩展到完整官方能力 5 验收。

## 2026-10-19：真实入口回归

新增 `tests/test_bypass_runtime.py`，使用真实 stdio MCP 工具、SQLite 记忆服务和本地 Receiver，而不是仅切换检测函数的来源标签：

- 三来源各执行 6 条攻击和 6 条正常对照，共 36 个单段场景；检查原文、来源、归一化视图、finding、暴露事件和后续工具提议之间的关联。记忆经过网关写入再读取，并检查父来源保留。
- 每个场景主动提出凭据读取和外发，再生成本地报告；检查危险操作被拒绝、Receiver 未收到请求、报告实际落盘。正常/未命中样本也提出同样操作，验证授权不依赖检测命中。这些是脚本化提议，不代表模型被诱导后的 ASR。
- 额外覆盖三来源的原始长度和 NFKC 膨胀边界，共 6 个场景。DIRECT 保持既有 4096 字符上限；工具和记忆正文扫描超限时，网关返回 `ok=false`、`code=CONTENT_SCAN_LIMIT_EXCEEDED`，不返回 `data`，不创建正常归一化/模型暴露事件，并用 `CONTENT_REGISTERED` 的 `scan_status=REJECTED` 留存拒绝记录。随后正常读取仍可继续。
- 已经执行的工具操作保持原有授权判定；返回内容被扣留不表示副作用被回滚。审批后结果超限也会消费审批、保留副作用审计并缓存失败结果，重复 commit 不再执行工具。

运行：`python -m pytest tests/test_bypass_runtime.py -q`。该文件的 3 个参数化入口测试内部遍历 36 个场景，加上 6 个边界测试和 1 个审批响应故障注入测试，共 10 项 pytest 测试。

这些样本用于入口接线回归，不是独立冻结测试集；跨轮自动聚合、真实模型提议和完整七类端到端评测仍未完成。尤其不能把单源规则矩阵中的长文本样本直接视为 DIRECT 实际入口支持的长度。
