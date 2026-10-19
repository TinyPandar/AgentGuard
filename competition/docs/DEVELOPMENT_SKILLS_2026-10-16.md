# GitHub skills：安装与项目使用记录

日期：2026-10-16。用户已授权按实际需要加入先前调研的GitHub skills。使用内置 `skill-installer`，从 Trail of Bits 官方仓库安装到本机 Codex 用户技能目录，下一轮对话可自动发现。项目业务源码、运行依赖、M22冻结证据和旧实验报告未因安装改变。

**2026-10-17实施更新：**M23实际采用这两项技能。`variant-analysis`的三个静态候选已逐一以真实本地MCP故障注入确认并修复，新增12项回归；`property-based-testing`用于设计参数化事实的确定性seed域、边界/变换不变量和HTTP捕获阴性验证，参数化新47项与模型绑定新52项通过。没有新增Hypothesis依赖或自动缩减能力；最终整项目657项通过不是全部都属于属性测试。代码、原始失败和结论范围见[M23](../../sujie/docs/M23_STATUS.md)及[执行门槛专项](../../sujie/docs/M23_EVALUATION_EXECUTION_GATES.md)。以下安装试用表与设计保留10月16日时点。

**2026-10-18实施更新：**M24继续按实际任务使用已安装、固定上游提交的技能，没有因为增加候选就批量安装新技能。`property-based-testing`用于IOC/Git/Memory/三层委派的严格事实域、uint32和数值边界、深复制、排列/重复/无关记录变形，以及与真实MCP、Git对象、SQLite行、Receiver和主体/父链独立见证的交叉检查。IOC局部67项通过；Memory/委派专项及新旧相关用例65项通过，具体版本见[IOC记录](../reviews/2026-10-17-m24/ioc/validation.json)、[Git记录](../reviews/2026-10-17-m24/git/validation.json)和[长链记录](../reviews/2026-10-17-m24/long-tasks/validation.json)。这些计数有不同范围，不能相加充当本轮全量通过数，也不能把每项测试都称为属性测试。

本轮还以已确认的清理异常遗漏、实际push后ref恢复及独立核验中的角色/生命周期见证缺口为起点，检查相邻调用者和同类判定，保留修复前反例与修复后结果。辅助技能的作用是约束搜索和测试方法；结果仍以实际源码、观测和原始日志为依据，不把技能名称当作已实现的安全机制。独立核验器窄审修订后的最终v2已完成80格/16配对校准（76业务完成、4实际危险效果）、893项测试/1 warning、202文件格式检查和受限Linux六业务链验证，见[M24记录](../../sujie/docs/M24_STATUS.md)及[统一验收](../reviews/2026-10-17-m24/quality-gates.json)。这些是整项目工程与开发校准结果，不是技能运行成绩，也不能把校准通过写成所有格防御成功。

M24旧链同版复验已完成40个业务开发格和35个固定提议格的独立校验，见[复验及v2对应记录](../reviews/2026-10-17-m24/revalidation/after-core-verifier-v2.json)。新core核验器窄审修订的两文件不在这两份旧链归档内，v2后仅追加覆盖检查与新CLI核验，未重跑链路或增加样本。继续使用M23已暴露输入，不增加独立任务或样本，无云调用，不能证明ASR或获奖等级。M24时登记的下一轮按[M25安排](../../sujie/docs/M25_NEXT_STEPS.md)补同事实C/A配对、预算/取消边界、三来源代表与复现材料，实际续作见下段；只有具体工作确有能力缺口且来源可审查时再加入GitHub技能。

**M25实际使用（2026-10-18）：**继续使用这两项固定版本技能，没有新增技能或Hypothesis依赖。`property-based-testing`指引用于构造普通失败/晚失败/取消不能清除实际观察、源变更保持危险判定、预算祖先约束及严格输入域的确定性测试；这不宣称自动生成或缩减能力。`variant-analysis`用于从已确认的证据绑定、判定和预算早停根因检查相邻角色/祖先链，并保留原始反例。脚本48格/14配对、来源代表14格/7配对已独立核验；完整离线HTTP状态以[M25记录](../../sujie/docs/M25_STATUS.md)为准。全量原始日志1022 passed/1 warning（759.38秒）、Ruff/216文件格式检查通过，用户中断后未取回进程退出码；这些是整项目检查结果，不是技能成绩。0云，未新增Linux/前端/性能验收，不证明模型ASR或获奖等级。

## 已安装与适用工作

| Skill | 本项目用法 | 本轮状态 |
|---|---|---|
| [property-based-testing](https://github.com/trailofbits/skills/tree/5c99c03fb8a9ea568432ecbcba5d86e9f4ac2bf0/plugins/property-based-testing/skills/property-based-testing) | 为参数化任务、权限边界、审批和模型请求绑定设计跨输入域不变量；避免照抄实现的测试和几乎全被过滤的生成器 | 已按其生成器指引形成下述验收设计；尚未增加Hypothesis或运行属性测试 |
| [variant-analysis](https://github.com/trailofbits/skills/tree/5c99c03fb8a9ea568432ecbcba5d86e9f4ac2bf0/plugins/variant-analysis/skills/variant-analysis) | 以已经确认的缺陷为起点，逐步扩展模式、核对调用者并区分真实遗漏与误报 | 已以“业务完成但执行FAILED仍校准PASS”的已修复根因为起点完成静态试用：3项待动态确认候选、5项误报排除、0项新确认缺陷；不改写历史报告 |

固定上游提交：`5c99c03fb8a9ea568432ecbcba5d86e9f4ac2bf0`。下载归档SHA-256：`0f1f17bd6f69aa71bc626689a00d02261348f02a054f43f65a537436d17be8c4`。安装后27个文件逐一与审查副本核对一致；来源、位置和文件摘要见[installed-skills.json](../reviews/2026-10-16-skills/installed-skills.json)。未执行下载内容中的脚本或hooks。

这些是开发辅助流程，不是参赛作品新增安全机制，也不计自研创新。技能来源为 Trail of Bits，仓库许可为CC-BY-SA-4.0；本轮只在工作环境安装，公开交付包不附带整个个人技能目录。

试用报告见[variant-analysis-trial.md](../reviews/2026-10-16-skills/variant-analysis-trial.md)。三个候选分别在旧业务、序列和合法引用校准入口，尚未做“正确报告后再发生执行错误”的动态故障注入，不能称为已确认漏洞或据此修改原成绩。后续优先验证业务入口；预期拒绝/取消的直接工具校准保留独立判定语义。安装与文档检查见[validation.json](../reviews/2026-10-16-skills/validation.json)。

## 10月16日的属性测试设计

本节为待实现验收设计，不能计为已通过测试。当前锁文件未引入Hypothesis；如后续选用该库，另明确开发依赖与锁定版本。

| 不变量 | 生成器与独立见证 | 预期失败边界 |
|---|---|---|
| 正式业务事实与数据顺序无关 | 从独立事件事实表生成时间、主体、session和多源记录；随机置换各源顺序，插入窗外/其他主体记录。以独立事实表推导合法集合，不能调用被测报告生成器计算gold | 选中集合不随输入排列或无关记录变化；重复、同时间、闭区间端点和空结果独立登记，排序按已冻结规则判断 |
| 业务完成不替代执行成功 | 直接生成agent状态、error_code、真实report/Receiver观察的组合；分别判断utility与execution | FAILED、CANCELLED或有错误时整体正常业务校准不能PASS，即使实际业务已完成；保留真实副作用，不将观察清零；预期终止的强制提议另用协议 |
| 检查对象与最终有效模型请求一致 | 在MockTransport捕获最终JSON，生成Unicode消息、工具schema、有/无工具和允许范围内的配置变化；比较独立捕获体与冻结请求体，而非重复调用同一摘要函数自证 | model/max_tokens/temperature/tool_choice改变必须改变有效请求摘要；调用后修改原对象不能修改已冻结副本；凭据仅作为传输认证，不能混入公开摘要记录 |
| 审批绑定条件变化不能产生效果 | 从一份有效待审动作派生，每次仅改变一个参数、目标、版本、来源、合同或状态；实际观察Receiver/Git/文件结果 | 不匹配、拒绝、过期、取消都无新副作用；批准不等于已执行，提交后只产生协议允许的准确一次效果；不扩展为跨崩溃exactly-once声明 |

生成策略直接构造合法对象和边界对象，避免大量 `assume()` 丢弃输入；固定已知边界例，失败保留最小反例及seed。真实MCP/HTTP场景仅作必要集成见证，纯状态/序列化性质优先在无网络层验证。

## 安装时模型证据工作的代码依据（已由M23续作）

安装时 `ProtectedModel.complete` 已冻结并检查messages/tools；当时 `model_context.build_snapshot`只把这两项纳入请求快照。实际Provider随后才加入model、max_tokens、temperature和tool_choice，再发HTTP请求。因此旧request_hash不能称为完整有效HTTP请求体摘要。修复前字节见[M23原始源码副本](../reviews/2026-10-16-m23/original-sources/sujie/demo-agent/sujie_demo_agent/bailian_agent.py)。

安装时响应检查已有父请求关系和request_hash，尚未记录response_hash或预算ticket；这成为M23统一请求构造与响应绑定的实施输入。现已补齐当前主/子/Memory/分析链路，历史CLASSIFY等入口单独排除登记，不因purpose枚举存在就宣称全覆盖，详见[M23模型专项](../../sujie/docs/M23_EFFECTIVE_MODEL_BINDING.md)。

## 暂未安装的项目

- `audit-context-building`：当前上游版本要求专用Workflow和function-analyzer插件入口。本会话未提供该入口，单独安装SKILL目录不足以运行其完整机制，因此本轮跳过；不把普通代码阅读称为该插件执行结果。
- `playwright-cli`：到控制台交互/布局验收时，再根据现有浏览器工具判断是否需要，当前不重复引入浏览器运行依赖。
- `differential-review`、官方threat-model插件：按实际冻结审查/材料任务选择，未因调研列表存在就全部安装。

后续使用遵循[当前执行计划](NEXT_ACTION_PLAN_2026-10-16.md)，先保留失败和原始证据；技能输出仍需源码、实际效果和可复现检查支持，不能替代正式模型比较。
