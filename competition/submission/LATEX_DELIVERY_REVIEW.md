# LaTeX 交付修订与待验收项

日期：2026-10-18。代码基线：`99cba60`。本轮为作品报告与交付资料整理，不改动安全运行时、不启动云实验。

## 已完成

1. 新建可编辑的 LaTeX 工程：五章、摘要、11条文献、两张TikZ矢量图、两条机制公式、自动目录/引用/页码。
2. 按官方模板补回“填写说明”页，删掉原报告中的图示占位；保留匿名封面和空作者元数据。
3. 以M25和集成版本更新结果表，分别说明1025项集成本地回归、原M25的1022项日志、48+48+14离线单元和M24六链。旧M21结果不再充当当前报告主结果。
4. 将签名策略分发、任意Shell沙箱、跨角色OS隔离、通用恢复与产品化目标，与已有实现和有限验收区分；去掉无充分来源的行业规模、CVE举例和全面优于传统产品的断言。
5. 减少反复免责、口号和否定式自我定位；把条件放入威胁模型和实验方法，用具体对象与观察表达贡献。
6. 拉取最新主线和PR #14：后者本地审阅分支为 `review/pr-14-deepseek`，快照 `f3b3133`；GitHub当时显示存在合并冲突，本轮未合并。

## 尚待验收

| 项目 | 当前状态 | 完成条件 |
| --- | --- | --- |
| LaTeX编译与版式 | 内置编译未返回诊断 | 成功编译后逐页复核，图表/目录/引用/页码正确 |
| 正式宋体 | Mac只有Songti SC草稿替代 | 合法SimSun环境严格编译并核查嵌入字体 |
| 当前PDF/Release | 旧Release为M21草稿 | 新PDF完成验收后另发版本，不覆盖旧证据身份 |
| 原创性声明 | 已有文本和空白签名件 | 队员签名并按平台槽位处理 |
| 证据包 | 旧包为M21的16业务校准 | 单独移交M25原始观察与核验，再制作有版本索引的脱敏派生包 |
| 可运行程序 | 当前源码已更新到M25 | 当前包在新环境安装、启动、执行和核验通过 |
| 录屏/交互 | 有三段演示骨架，PR14为新界面 | 按最终代码排练、录屏、核验；脚本与真实模型标明 |
| 命名与匿名 | 报告正文无身份/个人路径 | 定稿PDF、截图、录屏、元数据和文件名共同检查 |
| 正式提交 | 尚无平台提交回执 | 按平台要求上传并保存回执 |

## 文献复核记录

2026-10-18再次读取原始论文/出版方与官方规范页面，保留原稿文献条目的题名、作者和标识；Task Shield从预印本更新为ACL 2025正式出版，页码29680–29697，DOI `10.18653/v1/2025.acl-long.1435`。未将其他论文的实验分数搬作本作品成绩。

- CaMeL：https://arxiv.org/abs/2503.18813
- Task Shield：https://aclanthology.org/2025.acl-long.1435/
- AgentSpec：https://conf.researchr.org/details/icse-2026/icse-2026-research-track/29/AgentSpec-Customizable-Runtime-Enforcement-for-Safe-and-Reliable-LLM-Agents
- AuthGraph：https://arxiv.org/abs/2605.26497
- AgentVisor：https://arxiv.org/abs/2604.24118
- ContainmentBench：https://arxiv.org/abs/2607.23999
- AID-Guard：https://arxiv.org/abs/2608.21159
- MCP-SafetyBench：https://arxiv.org/abs/2512.15163
- MCPTox：DOI `10.1609/aaai.v40i42.40895`。DOI页面直连未成功，改从出版方检索到其引用导出记录，核对正式题名不含“Attack”、卷期40(42)、页码35811–35819，并据此更新。出版方入口：https://ojs.aaai.org/index.php/AAAI/article/view/40895 。
- OWASP：https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- MCP：https://modelcontextprotocol.io/specification/2025-06-18

文献核对辅助使用 `citation-management`（Scientific Agent Skills），写作结构使用 `systems-paper-writing`，中文编辑使用 `humanizer-zh`。工具出处单独记录，不计作作品自研机制或实验结果：KASSIS T, AGARWAL V, HE Y, et al. Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents[EB/OL]. 2026. https://doi.org/10.48550/arXiv.2609.00065 （本轮核验最新为2026-09-02的v2，引用使用不带版本的持久链接）。
