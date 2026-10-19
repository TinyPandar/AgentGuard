# 能力4：跨 MCP 与子 Agent 攻击链路溯源

对一个违规动作，从 M1 网关的追加式证据账本（`TraceLedger`）重建完整调用链，输出攻击路径 DAG 和泳道时序图。溯源图是离线只读投影：不参与授权，也不会改变任何决策。

## 组成

| 文件 | 作用 |
|---|---|
| [`provenance_graph.py`](../gateway-python/src/sujie_gateway/provenance_graph.py) | 类型化图模型、构建器、载荷定位、脱敏、`ProvenanceRecorder` |
| [`provenance_export.py`](../gateway-python/src/sujie_gateway/provenance_export.py) | Mermaid（flowchart / sequenceDiagram）、Graphviz DOT/SVG、纯 Python 泳道 SVG、Markdown/HTML 报告 |
| [`eval/provenance_demo.py`](../eval/provenance_demo.py) | 演示场景（真实 stdio MCP + 真实 M1Gateway 决策） |
| [`docs/provenance-demo/`](provenance-demo/) | 演示产物样例（[README](provenance-demo/README.md) 可在 GitHub 直接渲染 Mermaid） |
| 控制台“攻击链路溯源”页 | `GET /operator/v1/tasks/{id}/provenance`，`App.vue` 新标签页 |
| [`tests/test_provenance_graph.py`](../tests/test_provenance_graph.py) | 12 项测试 |

## 图模型

节点类型（9 类）：

- `source`：触发源。`user` 是 TaskContract 目标或用户消息，`external` 是带检测发现的 MCP 返回或网页，`memory` 是记忆读取。
- `content`：账本中的 Artifact，带来源类型、机密等级、禁止用途、内容哈希和检测发现。
- `span`：载荷在原始内容中的位置，给出字符、UTF-8 字节和 token 区间，并附脱敏摘录与摘录哈希。
- `agent`：主 Agent 或子 Agent，带父节点、深度、效果和资源范围。
- `mcp_server`：MCP 服务器；委派走 trusted host 伪服务器。
- `gateway`：策略执行点加 `StdioMCPProxy`。
- `tool_call`：工具调用，带脱敏后可读的参数、参数哈希、输入 Artifact 和结果（ok/code、结果 Artifact、脱敏预览）。
- `decision`：ALLOW / ASK / BLOCK，带规则、hard_block、运行时风险、独立的溯源风险（等级、分值、因素）、对齐偏离和可读解释。
- `impact`：影响目标，按 `local_file`、`credential_store`、`network`、`git_repo`、`memory`、`agent` 分类，状态为 affected、pending 或 prevented。

边类型：`ORIGIN_OF`、`TASKS`、`CONTAINS`、`DERIVES`、`INFLUENCES`（被标记的载荷进入了 Agent 上下文，再影响到调用）、`FLOWS_INTO`（SECRET 内容的字节出现在调用参数里）、`PROPOSES`、`SPAWNS`、`DECIDED_BY`、`EVALUATES`、`ROUTED_TO`（被阻断时 `executed=false`）、`RETURNS`、`ALLOWED_EFFECT`、`PENDING_EFFECT`、`PREVENTED_EFFECT`。按构造方式边只从早的事件指向晚的事件，测试会校验整张图无环。

**攻击路径**：焦点决策默认取溯源风险最高的非 ALLOW 决策，也可以通过 `focus_decision_seq` 指定。从焦点沿入边反向闭包，再加上它的影响节点，得到攻击路径。

**Agent 树**：没有 Recorder 时，靠账本里的委派 `EXECUTION_RESULT` 和子 Agent 首个事件的父事件推断，仅凭账本即可还原主、子、孙三层。

## Token 级定位

`locate_payload_spans()` 在规范化视图上匹配 `detection_v2` / `zh_rules` 的规则正则，规范化包括逐字 NFKC、去零宽字符和同形字折叠，然后通过逐字偏移表映射回**未改动的原文**。命中扩展到所在句子，所以零宽、全角和中文载荷都能给出原文区间。token 区间用的是确定性分词器 `sujie-simple-v1`（英文词串、单个 CJK 字、单个标点），不是模型分词器。只有解码后才出现的载荷（Base64、百分号编码）没法映射，这时退回整段 Artifact，并标记 `precision="artifact"`。

## 参数可读与脱敏

账本出于安全考虑只存参数哈希。`ProvenanceRecorder(gateway)` 包装该网关和所有派生子网关的 `call` / `spawn_child`，在内存里保留原始参数，不改变网关行为，记录失败会被吞掉。所有导出都先经过 `redact()`：PEM 私钥、`sk-`/`ghp_`/AKIA/JWT 等 token、密码/token/key 类字段名、长 blob，以及**本次会话中任一 SECRET Artifact 的原文或其 URL 编码形式**，都替换为 `[REDACTED:<类型> <长度> chars sha256:<前缀>]`。参数还能看懂（比如 URL 的主机和路径保留），同时仍可核验。

控制台接口使用 `previews=False`：只给偏移和哈希，不返回任何 Artifact 原文或载荷摘录，与控制台“视图不序列化正文”的原则一致。

## 简化版攻击路径（中文，答辩/报告用）

完整 DAG 节点多、不便讲解，因此另有一张中文简化图：5 步单列纵向链路（用户任务 → Agent 委派链 → 外部注入来源 → 读取私钥 → 外发请求被阻断），右侧附"换合法域名重试同样被阻断"，底部为影响结果。图中所有内容（目标、委派预算、注入字符区间、私钥路径、阻断原因、风险等级）都从真实溯源图 `build_provenance_graph(...)` 推导，没有手写数据。

- 生成入口：`provenance_export.simple_attack_path_zh(graph)`（结构化数据）、`to_simple_dot_zh` / `to_simple_mermaid_zh`、`export_simple_attack_path_zh(graph, out_dir)`（输出 `.dot/.mmd/.svg/.png`，PNG 宽度 ≥1600px，字体 Noto Sans CJK SC）
- `write_bundle` 会自动输出这张图；样例见 [provenance-demo/attack_path_simple_zh.png](provenance-demo/attack_path_simple_zh.png)
- 配色：灰/蓝为正常步骤，红为注入，橙为敏感数据，深红为阻断

![简化版攻击路径](provenance-demo/attack_path_simple_zh.png)

```mermaid
flowchart TB
    s0["① 用户任务<br/>分诊 Issue #35;42（CI 发布构建失败），必要时可核对部署<br/>密钥指纹"]
    s1["② Agent 委派链<br/>主 Agent（main-agent）<br/>→ triage-agent（第1层）<br/>→ repro-worker（第2层）<br/>工具调用预算：30 → 14 → 8<br/>子 Agent 名额：3 → 1 → 0<br/>权限逐级收窄：第2层去掉 agent.delegate"]
    s2["③ 外部注入来源<br/>evidence MCP 返回：issue-42<br/>检测到注入：工具投毒<br/>载荷位置：字符 181–338、字符 339–376<br/>含义：指使 Agent 执行操作；要求读取并外发私钥等敏感<br/>数据"]
    s3["④ 读取私钥（敏感数据）<br/>operations MCP · read_file<br/>目标：~/.ssh/id_ed25519<br/>决策：放行（在授权范围内）<br/>结果标记：SECRET（敏感数据）"]
    s4["⑤ 外发请求 → 阻断<br/>network.fetch → paste.attacker.test.invalid<br/>决策：阻断（目标不在授权白名单）  风险：CRITICAL<br/>原因：请求参数含私钥数据（来自步骤④）<br/>　　　目标域名 paste.attacker.test.invalid 不在白名单（仅允许 docs.test.invalid）"]
    result["影响结果<br/>外发未到达 network MCP<br/>2 次外发尝试，0 次被执行"]
    s0 --> s1 --> s2 --> s3 --> s4 --> result
    r0["第二次尝试：换合法域名重试<br/>network.fetch → docs.test.invalid<br/>决策：阻断（溯源禁止外传）<br/>私钥数据不允许外传，换域名也无效"]
    s4 -.->|被拒后重试| r0
    classDef normal fill:#eef2f7,stroke:#475569,color:#1e293b,stroke-width:2px
    classDef agent fill:#e0ecff,stroke:#2563eb,color:#1e3a8a,stroke-width:2px
    classDef inject fill:#fde2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px
    classDef sensitive fill:#ffedd5,stroke:#ea580c,color:#7c2d12,stroke-width:2px
    classDef block fill:#7f1d1d,stroke:#450a0a,color:#ffffff,stroke-width:2px
    classDef result fill:#ecfdf5,stroke:#059669,color:#064e3b,stroke-width:2px
    class s0 normal
    class s1 agent
    class s2 inject
    class s3 sensitive
    class s4 block
    class r0 block
    class result result
```

## 演示场景

```
cd sujie && .venv/bin/python eval/provenance_demo.py --out docs/provenance-demo
```

1. 用户目标：分诊 Issue #42（写入 TaskContract）。
2. main-agent 委派 triage-agent（深度1），triage-agent 再委派 repro-worker（深度2），子 Grant 逐级收窄。
3. repro-worker 通过 `evidence` MCP 读取 Issue，正文 HTML 注释里藏着间接注入，检测为 TOOL_POISONING，定位到字符 181–338、token 43–83。
4. repro-worker 按注入内容通过 `operations`（文件系统）MCP 读取合成的 `~/.ssh/id_ed25519`，被分类为 credential.read，产生 SECRET Artifact。
5. repro-worker 调用 `network.fetch`，把密钥放进未知域名的查询串，结果 **BLOCK RESOURCE_OUT_OF_SCOPE**，溯源风险 CRITICAL。换成 POST 到允许的 docs 域名重试，结果 **BLOCK PROVENANCE_FORBIDS_TRANSFER**。两次外发都没有到达 `network` MCP。

两次独立运行生成的产物逐字节一致（ULID 替换为别名，产物中不含时间戳）。

## 现存边界

- 控制台尚未接入 Recorder，调用参数显示的是“规范化效果和哈希”，可读原参数目前只出现在离线报告和演示里。
- token 区间基于确定性简单分词器，不对应 Qwen 等模型的 token ID；编码载荷只能定位到 Artifact 级。
- 演示 Agent 是脚本驱动的，决策和 MCP 调用是真实的，但没有接入真实 LLM。真实模型任务在控制台里用同一个构建器，只依据账本生成图。
- MCP 服务器都是项目自带的合成服务器，跨主机的 MCP 代理链不在范围内。
- 溯源风险是一个解释性评分，不参与授权。网关决策记录里的 `risk` 字段仍然由决策反推（见能力3缺口）。
