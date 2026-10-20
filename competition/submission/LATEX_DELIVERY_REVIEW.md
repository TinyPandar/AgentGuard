# LaTeX 交付修订与待验收项

日期：2026-10-20（第二轮）。报告绑定快照：`1b64b1f`。该快照的运行时源码与持续集成验证过的 `96d591b` 逐字节一致，差异只在文档与验证记录。本轮只改报告与交付资料，不动安全运行时、不启动云实验。

## 一、为什么重绑

上一版报告冻结在 `99cba60`（10-18）。之后的合并带来四项与赛题直接相关的能力：结构化工具返回的逐字段来源登记、检测器 `rules-v0.6`（含冻结/扩展双版本）、敏感写入目标的不可覆盖拒绝、跨 MCP 与跨子 Agent 的溯源图与攻击路径导出。正文没有覆盖这些内容，评审只能靠"报告基线 + 口头增量"补充，这在对齐性上是不利的。

本轮把这些内容并入正文，并把绑定更新到 `1b64b1f`。之所以单独用一个只含验证记录与清单生成器的提交作为绑定对象，是为了让"报告引用的提交"和"CI 验证过的代码"可以分开指定：不必为了写报告而改动运行时，也不必让报告去引用一个尚未验证的新代码状态。

绑定检查由 `tools/check_report_latex.py` 完成，它核对四件事：正文确实引用了被绑定提交、该提交里存在所声明的验证记录、记录哈希一致、清单内 312 份源码的 git blob 哈希一致。当前工作区与报告基线是否相符单独报告，不混入"报告是否可交付"的判定。

## 二、本轮变更

| 变更 | 落点 | 内容 |
| --- | --- | --- |
| 基线重绑 | `latex/runtime-version.json`、第三章 §3.1 | `99cba60` → `1b64b1f`；验证记录 `docs/validation/MAIN_SYNC_VALIDATION_2026-10-20.json`（312 份源码） |
| 赛题列明规则对照表 | 第一章 §1.2（新增表） | 7 条规则逐条给实现对象与证据位置；"运行时风险等级"标为部分完成 |
| 结构化工具返回来源登记 | 第二章 §2.4（新增） | 逐叶子字段登记取值路径、哈希、父来源；未命中模式按未登记处理 |
| 双检测器与协议固定 | 第二章 §2.6（新增） | 冻结 `rules-v0.3` 由源文件哈希固定，扩展 `rules-v0.6` 为运行时默认，`SUJIE_DETECTOR` 切换 |
| 敏感写入不可覆盖 | 第二章 §2.7（新增） | 名单口径、与执行器检查的分工、CVE-2025-53773 向量 |
| 溯源图与攻击路径导出 | 第二章 §2.10（新增）、第四章 | 类型化节点/边、跨 MCP 与跨子 Agent 合并、离线导出 HTML/DOT/Mermaid/SVG |
| 三平台回归表 | 第三章 §3.3 | Ubuntu 1107 / Windows 1106 / macOS 1107，同提交 |
| 规则检测离线评测 | 第三章 §3.4（新增表） | 14 / 42 / 140 条三组结果，附口径限定 |
| 历史阶段标注 | 第三章 §3.5–§3.6 | M25 离线矩阵与 M19–M21 云记录明确标为历史源版本 |
| 创新与总结 | 第四章、第五章 | 补"文本风险与动作授权分离""证据账本→溯源图"两项；结论同步新基线 |
| 参考文献 | `sections/references.tex` | 新增 CVE-2025-53773 与四个公开数据集（11 → 16 条） |
| 原创性声明签署件 | `dist/`、`tools/build_originality_statement.py` | 四份手写电子签合成 PDF/DOCX，日期 2026-10-20；签名素材只按显式路径读入，不进版本库 |

工具侧另修了两处缺陷，均在同一轮完成并有正反例测试：

- `tools/build_report_binding.py`：清单由一条固定规则从 git 对象重算（`sujie/` 下除文档、评测报告、README、点文件与静态资源外的全部文件），拒绝覆盖已有记录。
- `tools/build_evidence_packet.py`：`PATH_RE` 曾把 `\s` 写成字面反斜杠加 s，导致以字母 s 开头的路径被截断；同时修正 Windows 盘符模式误匹配 JSON 转义、以及合成演示路径 `/workspace/case-001/home/.ssh` 被误报为泄漏。
- `tools/build_source_package.py`：凭据扫描把自标注的合成夹具与真实命中分开，未标注的真实命中直接失败退出（已用 `sk-` 令牌与 PEM 体做负例验证）。

## 三、已完成并核验

1. 源码检查：`check_report_latex.py` 返回 `ok`，摘要 421 字（上限 500），16 条文献，312 份源码零偏差，正文无身份信息与个人路径，`instructions.tex` 保留"本页不删除"。
2. 结构检查：五个 `\chapter{`，无未定义 `\ref`，括号与环境配对，`\cite` 键全部存在。
3. 编译：CI 运行 [39427275140](https://github.com/jiapengLi11/AgentGuard/actions/runs/39427275140) 通过；23 页、421,517 字节（上限 10 MB），SHA-256 `1e8509ccac096f445e8e25f8a99ce6383d68f0bcf83c0492a17bd4b146985099`；编译日志 0 处溢出、0 处缺字、0 处未定义引用；A4、字体已嵌入、书签保留。
4. 版式：本轮修掉两处表格溢出——规则检测表把检测器并入数据集列，混淆矩阵列加宽到 0.27；赛题对照表加宽状态列，避免"部分完成"被拆行。抽查第 6、15 页，表 1.1、表 3.1 与 §3.4 正文均在页边距内。
5. 数据核对：正文每个数字都能对回证据文件，对应关系如下。

| 正文数字 | 证据文件 |
| --- | --- |
| Ubuntu 1107 / Windows 1106 / macOS 1107 | `docs/validation/MAIN_SYNC_VALIDATION_2026-10-20.json`、CI 运行记录、`logs/dev-check-macos-96d591b.log` |
| 312 份源码 | 同上（清单由 git blob 哈希重算） |
| 14 条：TP5/FN2/FP1/TN6 | `runs/competition_evidence_20261020/detection_v1.json` |
| 42 条：TP21/FN0/FP0/TN21 | `runs/competition_evidence_20261020/bypass_matrix_v2.json` |
| 140 条：TP45/FN35/FP0/TN60 | `runs/competition_evidence_20261020/public_injection_heldout.json` |
| 分来源召回 85/65/55/20% | 同上 `by_source` 字段 |
| 16 单元、云调用 0 | `runs/competition_repro_20261018/summary.json` |
| 48/14、46 完成、2 危险 | `docs/validation/M25_LOCAL_ACCEPTANCE_2026-10-18.json` |

## 四、尚待验收

| 项目 | 当前状态 | 完成条件 |
| --- | --- | --- |
| LaTeX 编译与版式 | 新基线版本已通过 CI 编译与源码检查；表格溢出已修 | 改稿后重新编译，检查受影响页面 |
| 正式宋体 | CI 使用 Fandol 宋体（Mac 可用 Songti SC 代替） | 在合法 SimSun 环境严格编译并核查字体嵌入 |
| 当前 PDF / Release | `submission-2026-10-20` 里仍是 `99cba60` 版报告 | 新 PDF 验收后替换该资产，不覆盖旧证据身份 |
| 原创性声明 | 文本与官方模板逐字一致；已用四份手写电子签合成签署件（PDF/DOCX，日期 2026-10-20） | 核对签名与队员一一对应；若组委会要求原件，另附扫描件 |
| 证据包 | 已更新到 `96d591b`（53 文件、967 KB、0 路径泄漏） | 在新环境安装、启动、执行并复核 |
| 可运行程序 | 源码包 519 文件 / 2.26 MB，凭据扫描 clean | 在新环境安装、启动、核验 |
| 录屏 | 有 `演示脚本-溯界.md`，无成品视频 | 按最终代码排练、录制、核验 |
| 运行时风险等级 | 正文标为"部分完成" | 若要点为已完成，需独立分级器与校准实验 |
| 命名与匿名 | 正文无身份/个人路径 | 定稿 PDF、截图、录屏、元数据、文件名共同检查 |
| 正式提交 | 尚无平台提交回执 | 按平台要求上传并保存回执 |

## 五、文献复核记录

2026-10-18 读取原始论文/出版方与官方规范页面，保留原稿条目的题名、作者与标识；Task Shield 从预印本更新为 ACL 2025 正式出版，页码 29680–29697，DOI `10.18653/v1/2025.acl-long.1435`。未将其他论文的实验分数搬作本作品成绩。

2026-10-20 新增两类条目：CVE-2025-53773 以 CVE 计划官方记录为出处（GitHub Copilot / Visual Studio 经注入的工作区设置获得代码执行）；四个公开数据集以 Hugging Face 仓库的固定修订号与许可证登记，评测脚本只读取这些修订，不随上游变动。

- CaMeL：https://arxiv.org/abs/2503.18813
- Task Shield：https://aclanthology.org/2025.acl-long.1435/
- AgentSpec：https://conf.researchr.org/details/icse-2026/icse-2026-research-track/29/AgentSpec-Customizable-Runtime-Enforcement-for-Safe-and-Reliable-LLM-Agents
- AuthGraph：https://arxiv.org/abs/2605.26497
- AgentVisor：https://arxiv.org/abs/2604.24118
- ContainmentBench：https://arxiv.org/abs/2607.23999
- AID-Guard：https://arxiv.org/abs/2608.21159
- MCP-SafetyBench：https://arxiv.org/abs/2512.15163
- MCPTox：DOI `10.1609/aaai.v40i42.40895`。DOI 页面直连未成功，改从出版方检索到引用导出记录，核对正式题名不含"Attack"、卷期 40(42)、页码 35811–35819。出版方入口：https://ojs.aaai.org/index.php/AAAI/article/view/40895 。
- CVE-2025-53773：https://www.cve.org/CVERecord?id=CVE-2025-53773
- gandalf_ignore_instructions：`Lakera/gandalf_ignore_instructions`，rev `04737b65`，MIT
- mcp-tool-poisoning：`fevziegeyurtsevenler/mcp-tool-poisoning`，rev `9b7a1088`，Apache-2.0
- agent-safety-bench-zh：`uninhibited-scholar/agent-safety-bench-zh`，rev `4089ae3e`，CC-BY-4.0
- prompt-injections：`deepset/prompt-injections`，rev `4f61ecb0`，Apache-2.0
- OWASP：https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- MCP：https://modelcontextprotocol.io/specification/2025-06-18

文献核对辅助使用 `citation-management`（Scientific Agent Skills），写作结构使用 `systems-paper-writing`，中文编辑使用 `humanizer-zh`。工具出处单独记录，不计作作品自研机制或实验结果：KASSIS T, AGARWAL V, HE Y, et al. Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents[EB/OL]. 2026. https://doi.org/10.48550/arXiv.2609.00065 （核验最新为 2026-09-02 的 v2，引用使用不带版本的持久链接）。
