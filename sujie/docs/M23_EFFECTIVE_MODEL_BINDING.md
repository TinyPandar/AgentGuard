# M23 完整有效模型请求与返回绑定

任务开始于 2026-10-16，2026-10-17 续作。这里记录本地实现与离线 HTTP 捕获结果；没有调用真实云模型。正式任务数据、评分与输入冻结仍由其他登记流程决定，本记录不能代替正式评测准入。

## 本轮补上的缺口

原 `ProtectedModel` 冻结并检查 `messages/tools`，而 `BailianChatModel` 在检查后才组装 `model`、`max_tokens`、`temperature` 和 `tool_choice`。因此原 `request_hash` 不能证明完整 HTTP JSON 正文与已检查内容一致。旧响应事件也没有关联实际返回摘要和预算票据。

现在保留原 `request_hash` 的含义，新增完整正文的 `effective_request_hash`。可信 Provider 先生成不可变的 `PreparedModelRequest`；Host 核验其中 `messages/tools` 与原输入相同，对全部有效字段、嵌套字符串和字典键运行数据策略，再预留预算、记录事件并调用 `complete_prepared`。HTTPX 直接以 `content=frozen_json.encode("utf-8")` 发送原冻结体；发送方法不会重新读取可变的模型名、输出上限、温度、tool choice、凭据、端点或超时配置。

准备接口替换输入或删掉原有工具会以 `MODEL_BINDING_INPUT_CHANGED` 拒绝。新增 Provider 配置字段也要经过大小、结构、敏感值、来源分类和用途检查；不会因为它不在原 `messages/tools` 中而跳过检查。原本无工具时，HTTP 正文不发送 `tools/tool_choice`，旧摘要仍按 `tools=[]` 计算，保持历史含义。

## 摘要与关联字段

| 字段 | 含义与边界 |
| --- | --- |
| `request_hash` | 旧规范化 `messages/tools` JSON 的 SHA-256；含义未改 |
| `effective_request_hash` | 实际冻结并发送的完整 UTF-8 HTTP JSON 正文 SHA-256 |
| `binding_scope` | 真实适配器为 `HTTP_JSON_BODY`；普通脚本模型为 `MESSAGES_TOOLS_ONLY` |
| `call_id` | Host 每次尝试生成的本地调用 ID |
| `budget_ticket` | 同一次调用在 SQLite 预算账本中的 reservation ID |
| `response_hash` | Host 实际返回 message 的规范化 JSON SHA-256；无法规范化时为 null，状态为 `UNAVAILABLE` |
| `provider_receipt.message_hash` | Provider 解析得到的 message 摘要，包括有效但随后被拒绝的 message；范围标作 `CANONICAL_PROVIDER_MESSAGE_JSON` |
| `provider_receipt.raw_response_hash` | HTTPX 暴露的、已经内容解码后的响应正文 bytes SHA-256；范围标作 `HTTPX_DECODED_RESPONSE_BODY_BYTES` |
| `raw_response_status` | 有真实 bytes 才记 `CAPTURED`；缺失响应或旧测试替身无 bytes 时为 `UNAVAILABLE` |

请求与响应事件同时包含旧摘要、有效正文摘要、call ID 和 ticket；响应 receipt 必须与本次请求一致。Provider 的有效 message 摘要、返回 message 和响应 envelope 中的 message 也必须一致，失败会拒绝采用响应。实际返回 message 与整个响应 envelope 都经过敏感值检查；凭据出现在被忽略的字段或字段名中同样不能成为有效输出。

这里的关联是可信本地 Host、HTTP 调用和账本之间的关联。没有声称服务器签名、远端生成证明或 TLS 数据包级取证。有效正文摘要不包含 URL、HTTP headers、Authorization 或其他传输配置；响应 bytes 摘要也不是压缩前网络线上的原始 octets。

## 兼容、凭据与预算

- `fields` 保留原消息和工具字段的来源映射；`effective_fields` 登记完整正文的安全路径、长度、来源跨度与继承关系。配置中出现的来源同样进入返回 lineage。
- 本地 tokenizer 对完整有效正文的字符串字段映射偏移。映射附带范围说明，仍保留 `provider_tokenization=UNKNOWN`；没有证明供应商内部 token 或模板等价。
- 对话前缀校验、已经观察到的 assistant message 来源绑定和后续未知改写的保守继承继续保留。
- 凭据仅在必要的本地传输私有对象和 Authorization 中存在。事件、receipt、控制台和 Recorder 不复制请求正文、响应正文、header 或凭据原值；异常只返回常量代码。
- `MODEL_REQUEST_CHECKED` 表示已检查并获预算准入，不单独证明网络已成功到达供应商。失败、取消和未知用量都保留 reservation；没有可核实用量时不退款。
- 真实 Provider 使用单次响应 receipt 中的用量结算，避免并发时从共享 usage 列表误归属其他调用；历史脚本模型继续使用已有 usage 列表兼容路径。
- `RecordedModel` 透明传递 prepared/send，保留原 recipe、首轮 `content_hash/system_hash/tools_hash` 配对字段，并追加完整正文与 receipt。下一次准备仍检查 recipe drift；准备后的配置变化不能改变本次冻结体。

## 实际入口登记

完整清单见 [effective_model_entrypoints_development_v1.json](../eval/protocols/effective_model_entrypoints_development_v1.json)，新增测试会用 AST 对照 `control-plane-python` 与 `demo-agent` 运行代码中的全部 `ProtectedModel` 构造点，防止当前入口登记漏项；不把 `eval` 内的单项故障注入/出口校准辅助构造点计为正式运行入口。

| 当前入口 | 实际 purpose | 本轮覆盖 |
| --- | --- | --- |
| `TaskSession._run_agent` | MAIN | 普通主智能体及当前 operator/common-runtime 入口 |
| `MemoryWorkflow.run` | MAIN | capture 和后续新记忆会话，共享父预算 |
| `AnalysisDelegation.invoke` | SUBAGENT | review 与嵌套 verify 子智能体 |
| `EvidenceAnalysis.invoke` | ISOLATED_ANALYSIS | 无工具引文分析 |
| `ProtectedModel.for_purpose` | Host 选择的支持 purpose | 五种 purpose 的 HTTP 捕获测试；这是能力证明，不代表所有历史调用点已迁移 |

当前共同运行器的 `RecordedModel(BailianChatModel(...))` 能继续得到 `HTTP_JSON_BODY` 证据。脚本校准后端只得到 `MESSAGES_TOOLS_ONLY`，不会伪称发生 HTTP 绑定。

历史 `NoToolSemanticClassifier`、`TaskAwareSemanticClassifier`、`TaskAwareSemanticClassifierV2` 的 bare Provider 调用，以及 `run_bailian.py`、`injecagent_local.py` 的历史直接调用循环，没有在本轮统一到网关的 role/source/budget 入口。它们保留 Provider 层的凭据检查与冻结发送，但不能引用为已具备上述网关证据。M9 四个冻结源码未修改。

## 验证记录

新增测试在 [test_effective_model_binding.py](../tests/test_effective_model_binding.py)，全部 HTTP 返回由 `httpx.MockTransport` 生成，无真实凭据、云请求或新增依赖。

覆盖五种 purpose、Unicode 和无工具正文，模型/输出上限/温度/tool choice 配置变化，检查后以及 await 期间的配置和输入 mutation，Provider 准备时输入替换，额外配置与字典键敏感值检查，配置来源分类和用途，message/完整响应正文不同摘要范围，ignored envelope 凭据，响应失败/取消/未知预算，receipt 和 envelope 不一致，畸形脚本响应与畸形本地 completion。两项实际 MCP 集成通过主智能体、嵌套子智能体和记忆新会话，另有实际无工具引文分析 HTTP 路径。

中间日志保留于 `/private/tmp/sujie-m23-20261016/`：首轮 `model-binding-first.log` 是 37 通过、1 失败（漏列 `MODEL_OUTPUT_PROTECTED_VALUE` 常量，已修复）；后续 `model-binding-unit.log` 为 38 通过；`model-binding-unit-final.log` 为 43 通过；`model-binding-regression.log` 为 136 通过。`model-binding-regression-final.log` 为 144 项通过（116.48 秒），覆盖已有模型上下文、预算、工具智能体、共同 Recorder、IOC HTTP、引文分析与新绑定测试；该轮运行期间追加了最后的 response-hash 状态与畸形输入阴性用例，所以仍列为中间回归。

最新绑定源码的新增 **52 项全部通过**（7.51 秒，`model-binding-new-final.log`），包含最后的 NaN/无效 UTF-8/非 message 返回和三个畸形 completion 分支。ruff 检查及格式化通过。随后[M23总验收](M23_STATUS.md)的同版657项全部通过，已包含这52项；不能重复累加。

持久化日志、源码摘要及验证索引位于 [model-binding 验证目录](../../competition/reviews/2026-10-16-m23/model-binding/validation.json)。
