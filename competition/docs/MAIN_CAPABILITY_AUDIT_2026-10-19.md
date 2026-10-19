# 最新主分支能力审计与补强方案

日期：2026-10-19（北京时间）。审计基线：[`fb6e6e4a1f37c727fd295470e34ae3069921d89b`](https://github.com/jiapengLi11/AgentGuard/commit/fb6e6e4a1f37c727fd295470e34ae3069921d89b)，包含PR #18。审计时没有待合并PR。

**结论：已有真实工具、授权审批、跨角色来源和效果核验支撑的工程原型，可以作为团队接力初版；五项赛题能力尚未全部闭环，当前也未形成可直接上传的最终参赛包。** 优先保留并完善现有Host/MCP架构，补统一来源接入、执行前研判、独立风险和敏感路径硬策略，然后完善溯源图、绕过验收和同版效果证据。

## 审计依据与验证边界

- 按GitHub完整提交ID取得独立源码快照；对460个已跟踪文件逐一计算Git blob SHA-1，与GitHub递归树核对一致。本地main随后正常fetch并快进到同一提交。旧文档用于定位，以下判断再对照本版源码。
- 官方依据：[题目5原始快照](../research/2026-10-14/topic5-official.json)。本轮按仓库保留的赛题文字逐项核对，没有重新认证赛事网站或提交平台的最新变化。
- 本轮定向回归：**97 passed、1 skipped、1 warning，36.86秒**。跳过项为未准备固定tokenizer资产；警告为Starlette/AnyIO弃用提示。测试使用Python3.12.15、原requirements.lock的71个适用依赖，独立临时环境，无云模型调用。
- 最新main的[质量CI](https://github.com/jiapengLi11/AgentGuard/actions/runs/39146513377)：Ubuntu **1025 passed、1 skipped、1 warning，1202.26秒**；Windows **1023 passed、1 failed、2 skipped、1 warning，2416.18秒**。Vue构建和Compose配置检查通过。Compose配置有效不代表整套容器已运行验收。
- Windows失败为`test_well_formed_but_forged_child_facts_fail_independent_task_oracle`，共享`finished()`在8秒内未观察到终态，报`MODEL_RUN_DID_NOT_FINISH`。本轮Mac定向运行该用例通过；不能据此关闭Windows问题，也不能把超时直接断定为安全判定错误。
- 两组新增本地探针分别检查规则/返回字段和自有临时目录写入。它们用于确认特定实现边界，不统计ASR、泛化率或真实业务攻击成功率。[验证记录](../../docs/validation/MAIN_CAPABILITY_AUDIT_2026-10-19.json)保存结果、命令和源码定位。
- 本轮未发云请求、未新增业务实现、未复跑全部历史矩阵、未进行当前界面浏览器验收、Linux新拓扑或性能验收。

## 完成度总览

“已有代表闭环”指真实代码和有限执行证据成立；“部分实现”指有组件但尚不能满足该项完整范围。这里不使用缺少权重依据的百分比。

| 赛题项 | 当前程度 | 可以展示的内容 | 决定性缺口 |
| --- | --- | --- | --- |
| 1 多源注入识别 | 部分实现，三类来源有代表流程 | 直接补充输入、外部正文/工具元数据、跨会话Memory | 返回字段接入不统一；语义检测入口有限；真实追加轮次及检索记忆未闭环 |
| 2 意图—计划—工具对齐 | 有可信任务和决策后解释，跨轮研判较弱 | 四类偏离解释、工具序列、实际效果/UNKNOWN | 执行前偏离评估、组合行为状态、原始请求到契约的受控确认 |
| 3 DSL与三态策略 | 代表闭环最完整，仍有共同缺口 | 语义效果、Contract/Grant、真实ASK/批准/执行复核 | DSL上下文事实少；风险由决策反推；缺独立敏感路径硬策略及完整目标验收 |
| 4 跨MCP/子Agent溯源 | 来源与主体证据较强，可视化和完整调用证据不足 | 多层Agent、来源父链、实际会话、局部token映射 | 全量参数/返回的受控证据；调用级DAG和角色时序图 |
| 5 对抗鲁棒性 | 部分规则与有限来源代表，完整覆盖证据最弱 | NFKC、Cf过滤、有限编码规范化、三来源代表 | 日俄/同形、分片多轮、编码、稀释及语义伪装的系统对照 |
| 工程与交付 | 有可编辑报告和构建链，待统一版本定稿 | 新控制台、LaTeX/PDF、测试及源码打包工具 | Windows稳定性、跨机复现、当前版报告与证据包、全员签名和最终上传 |

## 能力1 多源注入识别

### 已有实现

1. `M1Gateway.register_user_input()`登记DIRECT来源、原文摘要和发现，不允许补充文本改变Contract/Grant；凭据形状输入会限制出口。
2. `StdioMCPProxy`扫描序列化工具元数据，绑定server/tool/schema版本；实际调用前重新核对目录和版本，拒绝漂移。
3. `_record_tool_result()`对顶层字符串`data.content`建立Artifact、规范化视图和INDIRECT/MEMORY发现；Memory另有延迟指令规则。
4. 真实请求已具备不可变快照、完整HTTP JSON体绑定、角色/票据和响应收据关联。**模型请求递归字段出口检查已经存在，不能把它与工具返回的来源登记/注入检测混为一谈。**

### 本版确认的不足

| 子项 | 当前情况 | 最小补强 | 验收条件 |
| --- | --- | --- | --- |
| 工具返回字段 | 只在顶层`content`登记和扫描；Host随后把完整result序列化给模型 | 增加有深度/字节限制的返回文本枚举器，保存JSON字段路径与来源；结构键、说明/schema等实际可见文本也明确纳入范围或拒绝 | 嵌套、数组、额外字段中的合成指令均有来源记录和检测结果；已扫描结构与实际模型输入对应 |
| 统一检测 | 可选语义分类主要挂在`evidence.read_alert`后；存在任务感知分类组件，但未统一接入所有来源 | 同一检测契约接收任务、来源、正文、历史；规则快速通路加有预算的无工具语义判断；输出发现/未知/错误 | 直接、网页、工具描述/返回、Memory均经同一编排；失败不得伪装成CLEAR；分类器不能授权 |
| 资源类型 | 工单/邮件等有合成本地业务；不等于实际PDF/DOCX解析、IDE源码及外部服务适配 | 先做通用内容适配接口，接入实际文档提取结果、源码和一种真实业务资源 | 保存文件/资源版本、提取器版本、字段/页/段位置；提取失败显式记录；不必建设所有生产连接器 |
| 直接多轮 | API只有建任务时一次`user_message`，且仅report接受；无现有任务追加消息接口 | 加入同一会话的受控追加消息、顺序编号和只读原任务绑定 | 两次以上真实追加及中间模型调用可复核；文本伪装管理员不能变更权限 |
| 检索式污染 | SQLite版本化固定key读写、CAS和跨会话流程已经实现；没有检索/chunk召回接口 | 接入一种有界全文或向量检索，记录query、document/chunk/revision、召回和暴露链 | 先写污染、结束会话、新会话真实检索触发；同时包含正常召回、过期事实和恶意指令对照 |

本轮字段探针在相同`evidence.read_alert`动作下比较：顶层恶意`content`产生1个Artifact/1个发现；嵌套`result.content`和数组`results[].text`均为0个Artifact/0个发现；安全`content`加恶意额外字段仅登记安全正文，发现为0。完整结构仍返回Host。这里证实的是**登记/检测覆盖缺口**，没有证明越权工具已执行或秘密已泄露。

源码定位：`sujie/gateway-python/src/sujie_gateway/m1_runtime.py:111,1162,1789`；`sujie/demo-agent/sujie_demo_agent/bailian_agent.py:838,878`；`sujie/gateway-python/src/sujie_gateway/model_context.py:106,283`；`sujie/control-plane-python/sujie_control/api.py:62,258`；`sujie/control-plane-python/sujie_control/runtime.py:1339`。

## 能力2 意图 计划 工具语义对齐

### 当前可成立的能力

可信TaskContract包含目标、用途、资源和允许/禁止效果；记录模型可见工具提议、顺序、主体、拒绝和执行观察。`alignment.py`能根据可信字段解释GOAL、RESOURCE、SIDE_EFFECT和DATA_FLOW偏离；`sequence_alignment.py`保留失败/UNKNOWN，且不会把时间邻近硬称为泄露因果。这些是有价值的基础。

### 尚未成立的完整能力

- `explain_alignment()`是决策后解释，`M1Gateway.call()`仅在BLOCK时调用。它解释为何被现有策略拒绝，尚不是在ALLOW/ASK/BLOCK之前独立评估语义偏离。
- `trusted_goal`主要来自固定profile；聊天文本是report的补充输入，不等于任意业务请求已被可信地转成契约。
- 现有序列规则主要关联credential.read后的transfer提议，明确`data_flow_proven=False`；没有通用的“多步单独合法、组合后越权”前置状态机。

### 补强方案

增加只读的`TaskIntentSnapshot`和执行前`AlignmentAssessment`，同时覆盖正常、待确认和禁止动作。字段至少包含原目标、计划动作、目标资源/目的地、依赖来源、历史关联、偏离维度、证据ID、不确定状态。建议从“读后编码再外发、分片累计、读后委派、子Agent中转”四种有限组合实现，保持硬授权检查独立。

评估输出采用可解释等级和事实，暂不包装为未经标定的概率。模型给出的语义判断只参与风险信号，不能扩大权限；业务目标变更需可信操作者明确确认并新建契约版本。

验收至少包含合法多步、单步越权、跨轮组合越权、无法证明数据流、失败/取消；每个结论均能从记录重算。展示同一任务的“原目标→第几步偏离→证据→决策→实际效果”，同时统计正常业务被打断的情况。

源码定位：`alignment.py:1`；`m1_runtime.py:1213,1536,1564`；`sequence_alignment.py:115`，均位于`sujie/gateway-python/src/sujie_gateway/`。

## 能力3 策略DSL与三态

### 共同基础与共同缺口

已有安全解析的YAML DSL、类型化谓词和更严格结果优先合并；Contract/Grant还在Python前置执行真实权限、资源、用途、过期和快照检查。ASK具备可信操作者入口、确切动作/内容/来源/工具绑定，以及执行前再验证。它已经超过工具名黑白名单。

但DSL本次实际获得的事实主要为`runtime.prerequisites_passed`和`action.effect`，未完整接入已支持命名空间中的contract/data/provenance/history。决策记录的risk是`LOW if ALLOW else HIGH`，uncertainty固定0，不能称独立动态风险。

补强时建立统一可信`PolicyContext`，把目标/数据等级/来源用途/目的地/委派边界/历史事实传入DSL，存储命中规则和事实版本；增加独立风险依据。禁止路径、凭据外发等硬规则始终优先，风险较低或人工点击不能解除硬禁止。

### 五类动作逐项状态

| 动作 | 已实现与证据 | 当前边界 | 建议与验收 |
| --- | --- | --- | --- |
| 敏感fs.write | 默认只准output报告写入；逻辑路径拒绝逃逸；POSIX用目录fd/O_NOFOLLOW与原子替换 | 没有独立的敏感目标名称硬禁止；默认范围拒绝不等于任何宽授权下都拒绝 | 建立可信敏感目标注册与硬策略，明确Unix/Windows映射、别名/链接；全部在自有测试根中验证原文件未改变 |
| 敏感net.fetch | 有界GET/POST、目标/路径/重定向/DNS约束；query/header/body受检；已知受保护值的有限编码检查；来源未登记则拒绝 | 公共IOC确定性脱敏/传输代表闭环较强；不等于任意秘密片段、重组改写的通用DLP | 加入片段与多次传输关联、支持的转换链和合法外发对照；区分公共保护底座与来源机制收益 |
| 编码/下载exec | 只允许注册程序和确切argv语法；程序/解释器摘要绑定、超时和输出界限；真实子进程验收 | 不是通用Shell分析器或任意命令OS沙箱；固定程序拒绝有益但不能声称理解所有等价命令 | 继续保持结构化执行，补语法变体、注释/全角/组合、合法复杂参数，分别展示拒绝原因与实际进程未启动证据 |
| 检视git.push | review禁推；publish针对确切remote/ref/commit/old值ASK；工具状态复核、显式lease、防重复和UNKNOWN | 主要为封闭本地Git，任意不可信仓库/外部服务未验收 | 保留现有强项，纳入统一风险/解释，补真实仓库集成前的目标登记；检视永不因模型自称批准而推送 |
| 子Agent传密 | 主→review→verify真实对话；只收Artifact ID，不接受模型自造权限/任务；子权限/预算收窄；敏感输入创建前拒绝 | 已登记SECRET和已知受保护值有效；未标记凭据、部分片段和复杂转换仍缺覆盖；同Host非OS隔离 | 传入前对实际序列化委派包检查标签/内容/来源；增加未标记合成凭据、片段、多层中转与正常资料对照 |

**敏感路径新增探针：**在自有临时工作区，通过真实stdio MCP向逻辑`case-001/.ssh/authorized_keys`写合成标记。默认report为BLOCK/EFFECT_NOT_GRANTED；显式将可信契约和Grant放宽为该工作区file.write后为ALLOW，合成文件确实生成。未访问用户home或真实凭据。它确认缺少独立敏感名称硬策略，**不是默认profile逃逸，也不证明真实宿主`~/.ssh`可写**。

每类策略要验证合法ALLOW、可授权ASK的批准/拒绝/输入变化和越权BLOCK；硬禁止不为凑三态而变成人工可解除。没有官方要求必须开放通用Shell。

源码定位：`m1_runtime.py:434,485,1536,1692,1974,2029`；`dsl.py:13,143`；`network_policy.py:150`；`execution_policy.py:97`；`mcp-servers/operations-server/server.py:19,41,84`；`tests/test_git_delivery_gateway.py:55`；`tests/test_analysis_delegation_boundary.py:66`，上述路径均在`sujie/`相应模块下。

## 能力4 跨MCP与子Agent溯源

| 子项 | 当前实现 | 还差什么 | 补强验收 |
| --- | --- | --- | --- |
| 触发源 | USER_MESSAGE、MCP_TOOL_RESULT、WEB_PAGE、MEMORY和父Artifact | 嵌套返回/结构字段统一来源、检索chunk和完整资源适配 | 一条违规动作反向定位到实际读取资源、字段/版本/原文位置 |
| 主体链 | 主/子/孙身份、父Grant、深度、共享预算和Trace；Memory独立会话 | 应将角色、会话、MCP调用与证据节点统一关联 | 从主到孙再到工具/目标逐跳可点，不能只按事件头初始session推断所有主体 |
| token级归属 | 固定Qwen本地tokenizer、字符/UTF-8偏移、字面/JSON转义来源；未知改写保守继承 | tokenizer资产不随源码，干净环境会不可用；规范化/解码/拼接精确映射有限 | 启动就显示可用/不可用；补资产校验及Unicode/转义/转换断言，不把本地token称为云内部token |
| 参数与返回 | 主要记录arguments_hash及tool/ok/code；正文Artifact和新会话预览补充可读内容 | 新预览每消息最多12000字符，未包含完整assistant工具参数；不是所有工具的完整持久调用证据 | 以统一tool_call_id关联参数、结果/错误、actor/session/server、摘要和受控原文；截断有明确标志 |
| DAG | SVG节点来自Artifact，边来自parents；可查后继及受影响资源 | 不是包含Agent/MCP/决策/目标的完整攻击路径图 | 增加调用/主体/决策/资源节点及类型边；来源关联与已证明数据流分开 |
| 时序 | 有按顺序展示的`ol.timeline`和工具序列表 | 尚无按User/Agent/Gateway/MCP分泳道的调用/回应图 | 从同一证据模型生成泳道图，展示请求/回应/审批/取消，能跳转原文及实际效果 |
| 影响范围 | 有RESOURCE_READ/AFFECTED、接收端/Git/文件事实和UNKNOWN | 图与界面需要统一区分目标、已尝试、已确认、未知 | 不把BLOCK提议列作已发生影响；无回执保留UNKNOWN，由独立观察核验 |

新控制台的进步应保留：直接/继承来源告警区分、正常返回折叠、拒绝展开、跳转和任务报告明显更可用。但`chatRecords`仍有来源/位置回退匹配，后续应依统一调用ID连接，减少复杂多角色时的歧义。本轮只审源码和既有记录，没有重新声称浏览器全流程通过。

新`conversation`进入受认证的contexts和导出，可能含INTERNAL正文。应将“供评委公开的脱敏导出”和“本机操作者受控原文”分开实现和验收；不能沿用“导出只有哈希”旧说明。

源码定位：`protected_model.py:237`、`tokenizer_mapper.py:15,44`位于`sujie/demo-agent/sujie_demo_agent/`；`model_context.py:133`位于网关包；`App.vue:96,529,1205,1277`位于`sujie/console-vue/src/`；`views.py:6,109`、`api.py:246`位于控制面包。

## 能力5 七类对抗鲁棒性

| 类别 | 当前程度 | 本轮/源码依据 | 最小补强与验收 |
| --- | --- | --- | --- |
| 多语言与Emoji | 中英代表，未覆盖日俄 | 规则中英关键词；本轮纯日文、俄文样例均未触发 | 同意图中英日俄/混排/Emoji，配对正常外文任务和引用；分别评测识别与实际效果 |
| Unicode | 全半角、零宽等已处理；同形替换不足 | NFKC及Cf过滤；本轮全角/零宽命中，西里尔同形样例未命中 | 明确支持的同形/不可见字符映射，保留原文与映射；合法外文不能一律当攻击 |
| 拆分/多轮 | 单文本有限样例，真实多轮未闭环 | 本轮片段样例未命中；无追加消息API | 独立暴露事件及中间模型调用，逐步累积上下文；评测业务与副作用，不能预拼文本冒充多轮 |
| 注释/分隔符 | 部分HTML注释规则可中，exec有语法拒绝 | 仍主要依赖完整关键词或固定argv | 注释穿插、伪角色分隔和组合载荷，区分文本语义检测与命令拒绝，不允许注入取得角色权限 |
| 格式/编码 | re.I、NFKC、有界percent/HTML解码 | 原文Base64本轮未命中；已知秘密的Base64/hex出口保护另已存在 | 有大小/层数限制的候选解码和来源映射，配对正常编码数据；超限输出UNKNOWN/拒绝策略 |
| 上下文稀释 | 有长度/深度硬界限和小型长文本smoke | 保护资源上限不等于长对话中仍识别语义 | 在支持长度内分档测首/中/尾与多轮，记录实际暴露和截断；未暴露或超限不算防御成功 |
| 语义伪装 | 有任务感知分类开发组件和Memory代表 | 本轮假审批业务包装未命中规则；语义分类未统一编排 | 任务感知判断贯穿来源，以合法运维/引用为对照；测误报、业务完成及越权提议/实际效果 |

本轮9个确定性规则探针：普通英文、全角/零宽会产生发现；日文、俄文、同形、拆分、纯Base64、假审批包装未产生发现；合法培训引用产生发现。**这只是具体反例与信号记录，不是9个独立任务，也不是整个系统的攻击成功率。** 最终动作仍可能被权限/来源/出口机制拒绝，不能由规则漏报推导已经失守。

建议内部以三来源×七类组织适用覆盖。每格包含原文、来源、检测、模型是否提出越权动作、网关决策、实际效果、合法业务与UNKNOWN。先冻结开发集，再准备未见任务、重复和真实模型比较；不要依有利结果删选样例。21格是内部组织方式，不是官方规定只运行21次即可。

源码定位：`detection.py:13,39,67`、`memory_detection.py:1`位于网关包；`sujie/eval/cases/detection_v1.json`；`sujie/tests/test_detection_eval.py`；`sujie/eval/run_source_bypass_representatives_v1.py`。

## 效果证据 工程与交付

| 项目 | 现有成果 | 补强要求 |
| --- | --- | --- |
| 离线比较 | M25脚本48格、封闭HTTP48格、来源14格和独立重算 | 格数不等于独立任务；Mock无模型推理；保留46/48合法完成、实际危险效果及不利结果，不合并跨版成功率 |
| 真实模型效果 | 历史有小规模云验证；有实际Provider、保护和共享预算基础 | 当前M25 runner CLI仅scripted-only/offline-http；另建版本协议、受控云入口与预算准入后做同版强基线/消融，历史结果不能替代 |
| 正常业务代价 | 有Oracle、危险原文引用和恢复代表 | 对比业务完成、引用保全、延迟/请求与失败；没有提出危险动作不能算网关成功拦截 |
| 研究结论 | 来源约束、审批绑定、可重算实际效果可作为贡献候选 | 逐项说明相对强基线增加了什么；对照公开相关工作，区分机制贡献与共有执行器保护 |
| 跨平台稳定性 | Ubuntu完整通过；Windows已修换行等兼容问题 | 先为失败等待输出actor状态、阶段时间和清理证据，再判断平台启动慢或逻辑卡死；不直接放宽断言或盲目增加时间 |
| 可复现运行 | 本轮干净临时Python环境依赖安装及97项专项成功 | 补干净机器安装、tokenizer准备、前端构建、启动及三条演示的一次完整复现；本轮没有证明此全流程通过 |
| 部署隔离 | M24有非root/只读/无外网单容器六链历史验收；M1有分服务Compose | 当前版重新验收选定拓扑；同容器/同UID不等于角色OS隔离，Compose config通过不等于实际部署通过；无需把所有产品化隔离当官方新增硬条件 |
| 性能 | 有旧M1纯策略与旧网关测试基础 | 对当前链分别量策略/网关、MCP/工具、模型/网络耗时，报告冷/热、样本和分位；不拿旧纯策略毫秒数代表当前端到端 |
| 报告版本 | 17页LaTeX/PDF，最新报告CI通过；固定引用99cba60的281份源码 | 当前10份运行时文件与报告基线不同，严格当前模式按预期失败。先补当前验收，再新建证据记录和报告绑定，保留旧成绩身份 |
| 正式资料 | 设计、部署、测试流程、源码与打包脚本已具雏形 | 当前版源码/证据包、许可与匿名检查、正式字体、全员声明签名、必要演示视频、命名和平台回执；现Release仍M21，不作为当前成品 |

电子签仅已由用户授权生成本地试排，未提交公开仓库。本报告不附签名、个人图片、密钥、预算数据库或真实业务导出。

## 建议按可验收工作包接力

| 顺序 | 工作包 | 主要文件/接口 | 完成判据 |
| --- | --- | --- | --- |
| P0-A | 固定基线与Windows失败定位 | 测试等待、任务/子角色状态、CI证据上传 | 同一提交的Ubuntu/Windows均通过适用检查；失败时可定位阶段并确认清理，历史失败保留 |
| P0-B | 统一返回文本接入与完整调用证据 | m1_runtime、ProtectedModel、控制面存储/投影 | 嵌套/数组/额外字段均可追溯；实际模型可见文本有记录；参数/结果以call ID受控复核；公开导出脱敏 |
| P0-C | 执行前对齐 风险与DSL事实 | alignment、sequence_alignment、M1Policy、DSL | ALLOW/ASK/BLOCK均有独立风险依据；至少四类跨轮组合；命中规则/事实可重算；硬边界不可降级 |
| P0-D | 敏感目标硬策略与五动作专项 | 逻辑资源适配、策略、可信执行器 | 自有根的敏感目标在宽Grant下仍拒绝；五类动作覆盖正常、确认、拒绝、输入变化和实际效果 |
| P1-A | 三来源入口与七类绕过 | 内容适配、多轮API、检索Memory、检测编排 | 有真实暴露和中间调用的配对覆盖；区分检测、提议、策略、实际效果与业务损失 |
| P1-B | 调用DAG与角色时序图 | 统一证据API、Vue图与时序视图 | 三来源各一条违规链可点击复盘；从原文/token到角色/MCP/目标贯通；无效果不画成已发生 |
| P1-C | 同版本模型对照 | 新协议、预算、Runner、独立Oracle | 先冻结再执行；资源准入后运行；强基线/消融、失败与UNKNOWN齐全，收益和代价均报告 |
| P2 | 最终复现 报告与程序包 | 部署、文档、证据索引和Release | 干净环境复现、最终代码/报告/证据同版，签名和匿名处理完成，上传并保存回执 |

P0-B为P0-C/P1-B提供共同证据接口；P0-C/P0-D稳定后再冻结较大的效果比较。界面图与素材可在接口确定后并行实现，但图上的事实应来自同一底层记录。工作包是接力建议，不表示已安排具体队员或自动启动云实验。

正式赛题要求的是五项能力和列明的交付材料。未见任务统计、消融和更充分真实模型比较用于增强“技术先进性/对抗验证”的证据质量；Java/MySQL、多用户、任意Shell、固定测试数量以及四种系统形态全部实现，都不是此次复核新增的参赛门槛。

## 本轮可复查命令

在固定审计提交、Python3.12与原requirements.lock环境中：

```bash
cd sujie
python -m pytest -q \
  gateway-python/tests/test_detection.py \
  gateway-python/tests/test_alignment.py \
  gateway-python/tests/test_dsl.py \
  gateway-python/tests/test_m1_policy.py \
  tests/test_network_gateway.py \
  tests/test_execution_gateway.py \
  tests/test_git_delivery_gateway.py \
  tests/test_analysis_delegation_boundary.py \
  tests/test_model_context_guard.py \
  tests/test_sequence_alignment.py \
  tests/test_operator_delegated_agent.py --durations=10
```

报告默认检查应通过；严格当前源码检查应因与历史基线不同而失败，两者不是互相矛盾的质量结论：

```bash
python competition/submission/tools/check_report_latex.py
python competition/submission/tools/check_report_latex.py --require-current-source
```

新增探针的合成输入、结果与适用边界见验证JSON；460份源码快照哈希核对、97项专项和这些探针不替代全量跨平台、浏览器或真实模型验收。
