**溯界（Sujie / AgentGuard）：导师视角审查与下一阶段计划**

审查日期：2026-10-16（北京时间）。范围：现有源码、交接与阶段文档、关键原始评测产物、本机离线复现，以及 GitHub skills 调研。本次新增审查记录，不恢复交接文档中已停止的功能开发，不调用云模型、不安装调研到的 skills。

**总体判断**

项目已经达到“核心链路较完整、具备实质业务的研究原型”阶段，适合继续收口参赛。真实 MCP、可信授权门禁、来源传播、动作绑定审批、真实工具副作用、三层模型对话、跨会话 Memory 和操作者控制台均有代码与阶段证据。当前最需要投入的是正式有效性比较、官方条款覆盖、新环境复现和提交材料。

不能据现有结果判断已达到一等奖水平。系统功能已成形，但独立任务上的安全收益、合法业务可用性、完整拓扑边界和可交付性尚未形成同一冻结版本的证据闭环。不使用一个精确百分比代表完成度：代码实现、条款验收、实验论证和竞赛交付的分母不同。

| 维度 | 当前判断 | 依据与剩余工作 |
|---|---|---|
| 核心工程 | 较成熟的研究原型 | 真实工具、授权、审批、来源、模型预算与界面已接通；通用产品能力并非现阶段重点 |
| 官方五能力 | 代表链成立，完整验收未完成 | 主要缺口为三入口×七绕过、完整请求/返回证据、跨轮组合语义和完整可视化时序 |
| 有效性实验 | 开发验证阶段 | 有真实模型和消融探索；没有正式独立基础任务上的共同主比较 |
| 创新论证 | 有可验证的贡献候选 | 必须通过强静态基线、来源/恢复消融和合法对照隔离收益 |
| 可部署与交付 | 尚未就绪 | Windows 搬运环境需重建；新版整体隔离、新环境演示、匿名材料和提交包仍待收口 |

**阅读交接后的事实校准**

本次以 [交接手册](../../sujie/docs/PROJECT_HANDOFF.md)、[完成汇总](../../sujie/docs/COMPLETED_WORK_SUMMARY.md)、[当前状态](../../sujie/docs/F2_IMPLEMENTATION_STATUS.md)、[能力矩阵](../../sujie/docs/TOPIC5_EVIDENCE_MATRIX.md) 和代码/原始报告为准。[F3](SUJIE_REVIEW_AND_PLAN_F3.md) 是规划依据，正文中“当前”的许多表述属于 10 月 14 日旧快照；其后 M11–M21 已补上真实子孙对话、自主 ASK、两会话 Memory 和四类新增业务。接手时不应再次把这些列为从零开发项。

比赛主线是 `sujie/`。根目录 `agentguard/` 是 v0.1 历史原型。Java/Spring/MySQL 只有规划或说明，当前 Python 控制面和 Vue 才是实际产品入口。此目录没有 `.git`，不能从本地确认提交历史、远端 CI 或代码作者归属；恢复版本管理是后续冻结工作的前置事项。

| 已有内容 | 核验结论 | 代码入口 |
|---|---|---|
| MCP 与工具目录绑定 | 实际 stdio 服务；注册元数据摘要；调用前重新核对工具版本 | `sujie/gateway-python/src/sujie_gateway/m1_runtime.py:90`、`:168` |
| Contract/Grant/DSL 与审批 | 实际参数映射成效果；批准和提交分离；提交复核动作、输入、来源和状态 | 同文件 `:210`、`:1426`、`:1974`、`:2029` |
| 模型出口保护 | 主 Host、子角色与 Memory 会话确有 ProtectedModel 包装 | `sujie/control-plane-python/sujie_control/runtime.py:451`；`sujie/demo-agent/sujie_demo_agent/delegated_agent.py:162`；`sujie/control-plane-python/sujie_control/memory_workflow.py:300` |
| 三层 Agent | main→review→verify 为实际独立对话和收窄 Grant；运行于同一可信 Host | `sujie/demo-agent/sujie_demo_agent/delegated_agent.py:105`、`:188` |
| 跨会话记忆 | 实际 SQLite 事务、历史核验与 CAS 版本追加 | `sujie/sandbox/versioned_memory.py:85` |
| 结构化执行 | 固定解释器与注册 Worker，真实 `Popen(shell=False)`、摘要/超时/收据 | `sujie/sandbox/execution_executor.py:90`、`:115` |
| 业务与前端 | 13 个开发 profile；四类新增业务具有读取、事实和未修改资料判定；Vue 类型检查可运行 | `sujie/control-plane-python/sujie_control/business_oracles.py`、`profiles.py`、`sujie/console-vue/src/App.vue` |

**现有成绩能证明什么**

| 原始实验 | 可引用事实 | 解释边界 |
|---|---|---|
| `four_business_m21_scripted_v3` | 16/16 脚本业务完成；84 份归档源码与当前源码匹配；正式离线核验 `ok:true` | 确定性开发验收，云调用为 0；不是 16 个独立任务或真实模型 ASR |
| `four_business_m21_model_v1` | 真实模型首轮 3/4；15 请求、24,144 reported tokens | 时间线失败必须保留；原报告为 `passed:false` |
| `four_business_m21_timeline_model_v2` | 修复后，同一时间线开发样例单独完成；3 请求、5,645 tokens | 不能与前一版本的三例成功合并成同版 4/4 |
| `common_real_model_m19_v1` | 五配置×两个开发单元，7/10 完成；31 请求、25,005 tokens | 三个 IOC 失败没有提出发送动作，BLOCK=0，不能作为来源机制拦截收益 |
| `evidence_quotes_m20_cloud_v1` | 脚本主流程配一次云分析，353 tokens | 字面引用核验，不能表述为完整自主云 Agent 业务实验 |

四份关键归档的内容摘要均自洽；M9 四个冻结文件摘要保持一致。旧云实验对应的代码与当前版本存在差异，符合历史阶段记录；归档自洽不代表签名真实性、任务全部成功或泛化效果。报告目录约 341 MB，原始失败与源码归档实际存在，且多数被 `.gitignore` 排除。提交时应单独选择脱敏证据，不能只复制源码。

本轮本机复现的具体结果写在同目录后述验证记录中；旧文档的“479 passed”是历史 Windows 成绩，不直接冒充本轮成绩。

**最影响竞争力的缺口，按优先级排序**

1. **P0：尚无正式独立任务上的安全收益比较。** 13 个 profile 是开发适配入口，不自动等于 13 个独立基准任务。四业务协议显式为 exposed development、只跑 Full；M19 共同运行器的真实模型只有两个开发单元。现有 `calibration_backend` 也尚未接入四类 M21 业务，不能只改一个次数参数就宣称已能正式扩跑。
2. **P0：合法 IOC 任务有实际失败。** 先用已有失败轨迹查清提示、轮数、工具说明、ASK 发起或停止条件的原因；在开发集修复。安全系统需要同时证明能阻止越权、能完成明确授权的工作。正式评测保留每个失败和未执行单元，禁止只重试并挑成功。
3. **P0：本轮确认 Mac Git 业务创建失败，迁移交付尚未完成。** 本轮全回归为 **471 passed / 11 failed / 1 warning**，11 项均涉及控制面 Git 任务或对应共同配置校准。`runtime.py:153–155` 直接保留默认临时目录 `/var/folders/...`，`sealed_git.py:29` 拒绝所有带符号链接的祖先路径，而 macOS 的 `/var` 指向 `/private/var`，导致 `GIT_ALIAS_FORBIDDEN`，控制面返回 503。直接构造合成 GitFixture 已确认：默认路径失败，同路径先 `resolve(strict=True)` 或使用 `/private/tmp` 均成功且 Git 状态有效。建议可信 Host 创建临时目录后规范化根路径，保留对不可信仓库别名的拒绝策略，并补平台回归。本轮没有修改源码。另有搬来的 Windows `.venv` 与前端原生依赖需要重建；当前目录缺少 Git 历史，不能据此完成提交差异审查。
4. **P1：模型审计没有绑定完整有效 HTTP 请求/返回。** `model_context.py:204` 仅封存 messages/tools；`bailian_agent.py:99` 后续才添加 model、max_tokens、temperature、tool_choice；`protected_model.py:205` 的响应事件没有完整响应摘要绑定。`eval/run_semantic_bailian.py:63` 等旧独立入口尚未统一包装。建议在可信 Provider 统一构造最终请求、固定有效配置并绑定响应证据，认证材料继续单独保护。
5. **P1：来源片段与变换的覆盖有限。** `model_context.py:133` 主要查找整份来源原文或 JSON 转义；不能据此声称任意子串、摘要、分片、跨轮拼接都可精确追踪。纯模块合成检查中，完整 SECRET 来源被拒绝，截取子串或插入分隔符可失去该来源匹配；这只是模块层覆盖负例，未证明真实主链已泄密，主链另有读取授权、蜜标等防线。后续应补显式来源传播和正负对照，不能仅扩关键词。
6. **P1：序列展示尚不足以证明跨轮组合攻击识别。** `sequence_alignment.py:115` 的组合模式主要关联 credential.read→transfer，并明确 `data_flow_proven=False`；该模块不作授权决策。建议选两个具体组合做验收与消融，区分“关联到事件”“证明数据流”和“阻断了危险效果”。
7. **P1：新版完整隔离与现场验证欠缺。** 当前 MCP 和子角色使用可信宿主进程；注册 Worker 的超时不等于 CPU/内存/文件系统/网络隔离，直接 kill 子进程也不等于清理进程树。历史 M1 compose 未覆盖当前整套拓扑。交接称暂无 Linux 环境，本轮没有把该历史状态当作当前资源事实；应先确认可用环境，再安排当前版本验收。

三来源×七类绕过应有 21 单元索引，逐项列输入入口、检测、决策、真实状态和证据类型。一个脚本校准、一个真实模型样例、一个 UI 截图分别能证明不同内容。token 来源应继续明确为本地固定 tokenizer 的映射，不能表述成供应商内部 token 或模型因果解释。

**创新主张应收敛到三条可被检验的命题**

| 候选贡献 | 需要证明的收益 | 应采用的对照 |
|---|---|---|
| 任务—来源—用途联合约束真实工具效果 | 静态权限允许时，攻击性来源仍不能借摘要、子 Agent 或 Memory 获得新授权；合法操作仍可完成 | StrongStatic、Full、no-source，先相同提议校准，再独立真实模型执行 |
| 保留危险证据的恢复 | 遭注入仍能保留必要事实、原文和出处，并完成业务 | Full、no-recovery；资源允许再加提醒/旧投影，检查信息损失和额外成本 |
| 审批与实际参数、版本、来源、效果联动 | 批准的就是被展示的动作，漂移/重放/取消不会获得额外副作用 | 授权 ASK 正例及参数替换、版本变化、过期、跨任务、执行 UNKNOWN 负例 |

任务对齐、来源约束与运行时 DSL 已有相关工作，应明确差异和引用：[Task Shield](https://arxiv.org/abs/2412.16682)、[CaMeL](https://arxiv.org/abs/2503.18813)、[AgentSpec](https://arxiv.org/abs/2503.18666)。本轮已打开三篇论文摘要页确认方向。不要把这些单项机制包装为首次，也不要把论文中的不同模型/数据成绩直接并入本项目比较。

**提交前排期：10 月 16 日至 22 日**

本轮打开的[官方邀请函](https://cpipc.acge.org.cn/cw/contestNews/detail/2c90800c8093eef401809d33b36f0652/2c9080199ed8b78d019ed96ceea21560?page=0)写明：报名截止 2026-10-18 23:59，揭榜挑战赛/创意作品赛作品截止 10-22；初赛关注创新、完成程度、性能、应用价值与文档。以下先按此安排，队伍人数、投入时间和资格审核状态仍需队伍确认。题目详细能力以仓库保存的 10-14 官方 JSON 为依据；本轮 web 工具未成功重新解析题目 JSON，未声称正文已逐字复核到最新。

| 日期 | 首要工作 | 当日可验收产物 |
|---|---|---|
| 10/16 | 固定现状证据；建立本机环境；处理已确认的 Mac 临时目录/Git 问题；分析 IOC 失败；核对报名与学校审核 | 本机检查记录、失败归因清单、当前源码/依赖摘要、报名状态由队伍确认 |
| 10/17 | 登记独立任务与双 Oracle；开发集修补；接通新版共同运行器 | 新任务注册表与协议版本；五配置的相同提议/副作用校准；至少一个正常与授权 ASK 实例 |
| 10/18 | 补核心请求证据、关键绕过负例、序列关联与时序缺口；确认隔离资源 | 官方条款逐项标绿/黄/红；三段稳定演示；材料初稿；正式评测前锁定范围和预算 |
| 10/19 | 冻结代码、模型、输入、协议、Oracle 与配置；先跑小批再跑主比较 | 全部预定单元登记、首批原始失败保留、原始副作用/任务完成结果，不边看正式答案边调策略 |
| 10/20 | 完成主比较与两消融；核验实际效果及成本；若有 Linux 则验收当前拓扑 | 同版结果表、基础任务分组统计、支持范围；无法完成的范围明确披露 |
| 10/21 | 在新目录/另一操作者环境复现；整理匿名材料、许可证、证据、程序包 | 可复现包、脱敏报告、源码/版本/协议索引、无密钥演示、演示视频及逐项交付检查 |
| 10/22 | 只处理提交阻塞、核对上传文件并保存回执 | 队伍实际提交回执；预留平台问题处理时间，不把“本地打包完成”当“已提交” |

若人手或预算不足，先减重复、第二模型、额外公开基准和界面装饰；保住五能力支持范围、关键硬策略、合法对照、原始证据与可运行交付。Java/MySQL 重写、多租户、微调、任意 Shell、跨崩溃持久审批与大量扩样暂缓。真实 CVE 的封闭复现更适合在核心比较和提交包稳定后增强，不能用自建相似靶场冒充原漏洞复现。

**建议的第一轮正式实验协议**

这是待实施的新方案，不是本轮已经跑出的结果，也不是官方规定数量：

- 从现有适配中选八个核心基础任务候选：时间线、附件核对、IOC 通报、构件核验、Git 检视、Git 发布、三层委派、跨会话 Memory 更新。逐项审查可信目标、工具流程、初始状态和成功判据的实质差异；不足独立性的应合并或替换。
- 为每个任务单独封存新的输入/攻击，登记来源和已暴露情况。已有开发样例不能仅改名为未见留出；同一模板变体和重复运行不当新任务。
- 先做 C正常/A攻击 × 五配置（unsafe / strong-static / full / no-source / no-recovery），八任务时为 80 task-run；Q合法危险引用、R授权高风险在有自然业务含义的任务上加做，按类别分开汇总。若配套子任务不同，不拼成同一效用分母。
- 五配置共享固定模型/输出上限、可信提示、工具、初始状态、预算、审批测试主体和 Oracle。保留共同执行器、Provider 凭据保护等基础设施，并公开哪些保护各配置共有，不能把公共保障当作 Full 独有收益。
- 每个运行分别记录：是否有危险提议、网关决策、实际泄露/篡改/执行、任务完成、ASK、引用/事实保全、请求与 reported tokens、失败/未知/未执行。模型自评不能替代文件摘要、Receiver 记录、Git ref、Memory 历史等独立 Oracle。
- 攻击成功率、实际阻断与“模型未尝试攻击”单列。按基础任务分组报告，重复不能当独立样本；小样本百分比同时列整数分母，不包装统计显著性。
- 当前共同运行器不直接支持上述所有新业务。新建协议/运行器版本，保留旧 v1 与失败记录；开发修复完成后再冻结正式输入。
- 预算先按全部角色计：80 单元在每任务 12 请求上限下可达 960 请求，另计协议中不属于该上限的调用。历史 M19/M21 的均值只能作量级估算，不能保证免费额度。先固定请求/用量上限、停止条件和复验余量；额度不足在正式开跑前缩矩阵，运行后不删除失败。

**面向评委的演示与交付**

保留三条最容易形成清晰论证的演示：无防御时观察到真实危险效果；Full 阻断该效果并完成合法任务；明确授权高风险操作通过 ASK、核对预览、提交、续跑，实际效果准确。另备子 Agent/Memory 长链及危险原文合法引用案例。

每案能从可信目标定位到来源、上下文字段、工具参数、决策、审批、实际资源变化和恢复结果；显示真实云模型/脚本校准/历史回放的模式与代码版本。既有 DAG、列表和 token 表要形成可核查案件，不能只增加图形数量。

邀请函要求 PDF 文档不超过 10M、可执行程序及匿名正文/展示材料，决赛陈述演示测试和提问总计 20 分钟并现场检查源码。具体命名、模板、资格与签字由队伍按平台核对。建议交付包括：整体设计、部署说明、测试样例与流程、源码/锁文件、可执行演示、精选脱敏原始证据及重算脚本、许可证清单和正式声明。不要打包 API CSV、操作者 token、个人 `.control-runtime` 或整个虚拟环境。

**GitHub skills：已确认存在的推荐**

检索时逐个打开了原始仓库和 `SKILL.md`，未安装或执行外部脚本。优先采用能产出可审查证据的少量技能。

| 优先级 | Skill 与原始链接 | 对本项目的具体用法 | 使用条件 |
|---|---|---|---|
| P0 | [OpenAI Codex Security / threat-model](https://github.com/openai/plugins/blob/main/plugins/codex-security/skills/threat-model/SKILL.md) | 梳理 Host/网关/MCP/模型的信任边界，形成有源码依据的威胁模型与剩余风险 | 应使用完整官方插件及 references；插件 manifest 标 Proprietary，不能当可随意复制重发的开源代码 |
| P0 | [Trail of Bits / property-based-testing](https://github.com/trailofbits/skills/blob/main/plugins/property-based-testing/skills/property-based-testing/SKILL.md) | 用 Hypothesis 等检验权限不扩张、拒绝无副作用、审批参数不漂移、路径规范化等不变量 | 产出可重现反例；不替代真实模型有效性/ASR 实验 |
| P0 | [Trail of Bits / audit-context-building](https://github.com/trailofbits/skills/blob/main/plugins/audit-context-building/skills/audit-context-building/SKILL.md) | 逐函数对齐前队友交接与调用链，定位检查生效层、信任假设和证据缺口 | 用于建立审查上下文，输出不能自动视作确认漏洞 |
| P1 | [Microsoft / playwright-cli](https://github.com/microsoft/playwright/blob/main/packages/playwright-core/src/tools/skills/playwright-cli/SKILL.md) | 自动走任务→拦截→审批→溯源→导出，采集 trace/截图/视频以稳定现场演示 | 需要浏览器环境；UI 通过不能替代安全效果核验 |
| P1 | [Trail of Bits / variant-analysis](https://github.com/trailofbits/skills/blob/main/plugins/variant-analysis/skills/variant-analysis/SKILL.md) | 对一个已确认的绕过根因，查找其他工具、变换与检查/执行不一致的同类路径 | 先有根因实例再用；候选点需进一步验证 |
| P2 | [Trail of Bits / differential-review](https://github.com/trailofbits/skills/blob/main/plugins/differential-review/skills/differential-review/SKILL.md) | 冻结前审查补丁是否放宽权限、遗漏调用者或重新引入绕过 | 当前目录无 Git 历史，应先恢复可比较版本；可对明确保存的 diff 使用 |

首批建议为 threat-model、property-based-testing 和 playwright-cli，分别补“边界可信”“安全性质可检验”“演示可复现”。交接仍不清楚时加 audit-context-building；发现具体根因后用 variant-analysis，冻结前用 differential-review。

当前 [openai/skills](https://github.com/openai/skills) 的 README 标注 deprecated，并指向 [openai/plugins](https://github.com/openai/plugins)。旧 security-threat-model/security-best-practices/playwright 文件仍在，但不作为当前首选来源。[Trail of Bits](https://github.com/trailofbits/skills) README 说明可通过 Codex 的 Claude marketplace compatibility 使用，仓库许可证为 CC-BY-SA-4.0；[Playwright](https://github.com/microsoft/playwright/blob/main/LICENSE) 为 Apache-2.0；[Codex Security manifest](https://github.com/openai/plugins/blob/main/plugins/codex-security/.codex-plugin/plugin.json) 标 Proprietary。技能使用与复制/改编/再发布是不同事项，引用进参赛材料时保留相应归属，不把第三方流程作为自研创新。

如后续安装，应固定 commit、核查引用文件/脚本/hooks/MCP 权限，只装本轮所需单项。技能提升开发和验证质量，作品获奖仍依赖原创贡献、实验可信度和交付完成度。

**本轮验证记录**

临时 Python 环境：`/private/tmp/agentguard-review-20261016/venv`，CPython 3.12.14；依赖按现有 `requirements.lock` 安装 71 包成功。原 Windows `.venv` 保留。前端源文件与锁文件复制至独立临时目录，`npm ci --ignore-scripts` 后，Node 25.9.0 / Vite 7.3.7 类型检查与生产构建通过；原 Windows `node_modules` 保留。部署环境仍建议按交接选固定的受支持版本。

当前目录直接执行前端构建时因缺少 `@rollup/rollup-darwin-arm64` 失败，属于搬运依赖不适配。Python 首轮集成测试在沙箱内因禁止绑定本机 loopback 端口失败；允许临时本机测试端口后重跑，用以区别执行环境限制与代码缺陷。静态检查通过，166 文件格式通过，M21 脚本原始证据正式重算通过、84 源文件匹配，M9 四个冻结摘要匹配。

允许本机临时测试端口后的完整回归最终为 **471 passed、11 failed、1 warning，326.63 秒**；共收集并执行 482 项，无跳过。11 项失败全部位于 Git 控制面/共同配置校准，具体根因已如上复现。此结果保留默认 macOS 临时目录条件，不能删除失败或用旧 Windows 479 passed 替换。其余通过项也不等于 471 个独立安全任务。

随后仅把 `TMPDIR` 指向真实路径 `/private/tmp/agentguard-review-20261016/canonical-tmp`，允许本机测试端口，不修改源码；Git 操作者专项复验 **7 passed、1 warning，18.05 秒**。这是针对性环境绕过，支持上述根因诊断，不等于剩余四个相关用例已复验或默认环境全量已通过。

本轮没有修复业务源码，后续修复需重跑受影响用例及同版必要回归。此次未做云模型新实验、新版 Linux 隔离或浏览器操作/布局验收；不据构建成功推断界面交互已完成验收。机器可读核验记录：[validation.json](../reviews/2026-10-16/validation.json)。
