# 溯界比赛实现

> 2026-10-19实施：[结构化返回来源首批](docs/M26_RESULT_SOURCE_STATUS.md)，补全受支持JSON文本字段和字段名的来源/规则覆盖。21项新专项及本地全量1046项通过、1项跳过，跨平台Python CI待确认；不代表统一语义研判已完成。

> 2026-10-19：新增基于 `fb6e6e4` 的[主线五能力审计与补强方案](../competition/docs/MAIN_CAPABILITY_AUDIT_2026-10-19.md)，含97项专项、返回字段/敏感逻辑路径探针和最新跨平台CI边界；后续接力优先看该记录，旧阶段成绩保留原版。

> 2026-10-18 后续进度：[聊天控制台](docs/CONSOLE_CHAT_CHECKPOINT.md)。历史实验成绩不变。

> **2026-10-18 main 同步说明：**本目录整合本地 M22—M25 工作，并保留远端独立修复；旧阶段结果仍按原源码与证据版本解释。本次合并版本的检查状态见 [main 同步记录](../docs/GITHUB_MAIN_SYNC_2026-10-18.md)，不能用历史测试数字替代本次验收。[旧提交材料和 Release](../competition/submission/README.md)尚未更新为 M25 成果。

更新：2026-10-18，M25同事实比较与三来源有限代表已实施；当前结果和未完成项见阶段记录。当前运行/评测主线是本目录。

## 交接入口

- [M25与项目总体报告](../competition/docs/M25_AND_OVERALL_REPORT_2026-10-18.md) / [M25阶段记录](docs/M25_STATUS.md)
- [同事实比较](docs/M25_MODEL_COMPARISON.md) / [三来源代表](docs/M25_SOURCE_BYPASS.md)
- [M24实施与验收](docs/M24_STATUS.md) / [下一阶段安排](docs/M25_NEXT_STEPS.md)
- [M23阶段验收](docs/M23_STATUS.md) / [原M24计划](docs/M24_NEXT_STEPS.md)
- [M22第一批实施记录](docs/M22_FIRST_BATCH_STATUS.md)
- [当前执行计划](../competition/docs/NEXT_ACTION_PLAN_2026-10-16.md)
- [已完成工作简明汇总](docs/COMPLETED_WORK_SUMMARY.md)
- [项目交接手册](docs/PROJECT_HANDOFF.md)：安装、启动、预算、代码定位、证据和剩余工作
- [文档索引](docs/DOCUMENT_INDEX.md)：当前指南与历史记录
- [当前工作包](docs/F2_IMPLEMENTATION_STATUS.md) / [赛题证据矩阵](docs/TOPIC5_EVIDENCE_MATRIX.md)

已完成契约/三态网关、真实MCP、来源传播、模型输入/出口保护、共享预算、IOC/Git自主审批、网络/进程/Git效果、多层Agent、两个Memory会话、字面引用核验及四类新业务，共13个开发profile。Python控制面与Vue已实现，Java/MySQL未实现。

**四类业务在M21完成后曾停止；用户已于10/16要求按新计划恢复开发，随后完成M22–M24本地工程与开发校准，并继续实施M25离线比较基础。F3整体及正式模型主比较仍未完成。**

## 安装与本机启动

在本目录，Python3.12、Node20.19+或22.12+，Git业务另需Git：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe dev.py prepare-tokenizer
Push-Location console-vue
npm ci
npm run build
Pop-Location
.\.venv\Scripts\python.exe dev.py demo
.\.venv\Scripts\python.exe dev.py console
```

Linux/macOS用 `.venv/bin/python`。默认地址 `http://127.0.0.1:8765`，凭据为本机 `.control-runtime/operator-token.txt`。无云凭据时使用固定动作/确定性演示；安装及首次固定分词器准备需要网络或核验离线资源，分词器不含模型权重。

原本地M22—M25的Mac接手环境使用仓库根目录`.venv/`，从本目录执行`../.venv/bin/python dev.py check`；原Windows环境与依赖备份保留在本地，不随Git上传。新机器按上文创建自己的环境，历史环境记录不代表克隆后已有依赖。

云模型/端口/预算参数用 `control-plane-python/run_console.py`，见[手册](docs/PROJECT_HANDOFF.md)。`dev.py console`不透传参数，`.env.example`不是实际Provider配置。旧8765进程未随代码自动更新，勿清理用户任务；先导出再协调重启或使用新端口。

## 模块

| 目录 | 职责 |
|---|---|
| `contracts/` | 九类Schema、包0.2/载荷1.0、fixtures与不变量 |
| `gateway-python/` | MCP代理、合同/Grant、DSL、三态/审批、来源/Trace与序列 |
| `demo-agent/` | 旧LangGraph演示、有界百炼Host、子角色、正文分析、模型保护与预算 |
| `control-plane-python/` | 独立认证服务、13profile、临时环境及事实/读取/效果Oracle |
| `console-vue/` | 同源操作者页面；前端不是授权来源 |
| `mcp-servers/`、`sandbox/` | 文件、网络、执行、Git交付、版本Memory及旧测试服务/实际封闭副作用 |
| `eval/` | 冻结协议、开发数据、五配置、校准、云实验和离线重算 |
| `deploy/` | 历史M1/M23部署保留；M24六候选参数化Linux有限smoke通过，整体工具/角色隔离未验收 |
| `control-plane-java/` | 未实现占位，不是启动依赖 |

## 验证与边界

`python dev.py check`执行ruff/格式检查和pytest；`demo`为非LLM确定性真实MCP演示。`schema / unit / test / lint / format`为开发入口，`format`会修改代码。评测/性能脚本会写输出，复现时选择新目录，不覆盖旧成绩。

M25全量原始日志记载 **1022 passed / 1 warning（759.38秒）**，Ruff及216文件格式检查通过；用户中断后未取回进程退出码，详见[M25记录](docs/M25_STATUS.md)。48格/14配对脚本比较的正常执行48、业务完成46、实际危险效果2；14格/7配对来源代表的业务完成14、unsafe下3次本地禁止写入、Full下0次，均已独立核验。完整离线HTTP矩阵状态以M25总记录为准；封闭Mock传输不做模型推理，云调用0，不作ASR。

M24历史最终v2 **893 passed / 1 warning**，202文件格式通过；80格核心候选、40格业务复验、35固定提议和Linux六链通过独立核验。Memory生命周期核验缺口已修复，原v1与反例保留，云调用0，见[M24记录](docs/M24_STATUS.md)。前端7份源码未改，保留M23构建证据；M22的536项及M21脚本/云首轮失败和修复单例保留原版，跨版本不合并成功率。这些开发校准均不代表正式ASR或排名。

Host与执行器可信；子/孙对话同Host；任务/审批临时，预算账本持久不等于任务恢复；审批单次提交不等于跨崩溃exactly-once。本地token不是云内部token，来源Hash不是事实证明，字面引用核验不是语义核实。

真实模型新协议与资源准入、未见输入/统计、有效消融、历史裸分类入口统一、完整覆盖矩阵、信息保全/恢复比较、新版整体Linux隔离性能和材料仍待完成。M25脚本同事实比较与有限来源代表已执行；这些开发记录不构成正式模型效果。M25未新增Linux、前端或性能验收。当前主/子/Memory/引用分析的有效HTTP JSON请求体与响应摘要绑定已验收，不能扩展为历史入口全覆盖。旧原型不参加主评测，历史M1容器/性能/分类/云报告按各自版本解释。接手需另存忽略的证据、源码归档及固定资源；凭据私下交接。
