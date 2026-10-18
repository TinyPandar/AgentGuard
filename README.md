# 溯界（Sujie / AgentGuard）

> 2026-10-18：新增[聊天控制台](sujie/docs/CONSOLE_CHAT_CHECKPOINT.md)，含实现、数据处理变化及验证边界；下文旧阶段记录保留。

> **2026-10-18 交付进度：**M22—M25 代码已整合，M25 LaTeX 作品报告已通过 [PR #15](https://github.com/jiapengLi11/AgentGuard/pull/15) 合入 `main`。报告为17页、358882字节，已通过XeLaTeX构建和全页版式审阅；见[交付状态与剩余事项](competition/submission/LATEX_DELIVERY_REVIEW.md)。原 Release 仍为M21快照。各阶段实验保留原版本身份，本次代码整合验证见 [main 同步记录](docs/GITHUB_MAIN_SYNC_2026-10-18.md)。

面向大模型智能体提示注入与工具滥用的运行时安全网关，用于中国研究生网络安全创新大赛题目5。模型提出动作，可信 Host/网关按任务契约、Grant、来源用途和 DSL 实施 **ALLOW / ASK / BLOCK**，记录真实副作用。

更新：2026-10-18，M25已实现同事实观察性比较和三来源有限代表；脚本48格与来源14格通过独立核验，完整离线HTTP状态以阶段总记录为准。**比赛主线为 `sujie/`；根目录 `agentguard/` 是历史v0.1原型。**

## 交接入口

- **作品交付：**[LaTeX工程与编译说明](competition/submission/latex/README.md) / [交付验收清单](competition/submission/LATEX_DELIVERY_REVIEW.md) / [PDF构建产物](https://github.com/jiapengLi11/AgentGuard/actions/runs/39140488105)（登录GitHub后下载 `sujie-m25-latex-review`）。正式宋体、签名、M25原始证据移交、新环境运行和录屏仍待完成。
- [M25与项目总体报告](competition/docs/M25_AND_OVERALL_REPORT_2026-10-18.md) / [M25阶段记录](sujie/docs/M25_STATUS.md)。
- [同事实比较协议与边界](sujie/docs/M25_MODEL_COMPARISON.md) / [三来源代表](sujie/docs/M25_SOURCE_BYPASS.md)。
- [M24实施与验收](sujie/docs/M24_STATUS.md)：四候选参数化、独立核验与生命周期修复；v1结果和最终v2分开记录。
- [下一阶段安排](sujie/docs/M25_NEXT_STEPS.md)：同事实模型比较、来源绕过、演示和匿名交付；[材料证据骨架](competition/docs/COMPETITION_EVIDENCE_OUTLINE_2026-10-18.md)。
- [M23阶段验收](sujie/docs/M23_STATUS.md)：657项回归、40个参数化开发单元、35个固定提议单元与Linux四链历史证据。
- [M22第一批实施记录](sujie/docs/M22_FIRST_BATCH_STATUS.md)：Mac修复、IOC开发修复、任务登记与共同运行器的本轮证据及边界。
- [当前执行计划](competition/docs/NEXT_ACTION_PLAN_2026-10-16.md)：实施顺序、准入条件、正式评测与交付安排。
- [已完成工作简明汇总](sujie/docs/COMPLETED_WORK_SUMMARY.md)：已有成果、最近验证与剩余缺口。
- [项目交接手册](sujie/docs/PROJECT_HANDOFF.md)：安装、启动、预算、代码、证据保存与接手顺序。
- [全部文档索引](sujie/docs/DOCUMENT_INDEX.md)：每份指南/记录的适用阶段。
- [当前状态](sujie/docs/F2_IMPLEMENTATION_STATUS.md) / [官方能力证据矩阵](sujie/docs/TOPIC5_EVIDENCE_MATRIX.md) / [F3计划](competition/docs/SUJIE_REVIEW_AND_PLAN_F3.md)。

四类新增业务在M21验收后曾停止；2026-10-16已按用户要求恢复第一批修复与离线校准。F3整体、正式独立任务冻结与云主比较仍未完成。旧设计的技术栈、数量目标和排期不能视为已交付或官方指定条件。

## 已实现的范围

| 范围 | 当前结果 |
|---|---|
| 授权与执行 | 九类契约、真实stdio MCP、效果映射、DSL、三态、审批绑定、执行前复核与工具版本检查 |
| 来源与模型 | Artifact/DAG、保守传播、输入快照/本地token、请求/回应保护、固定百炼模型及共享预算 |
| 工具与长链 | 封闭文件/HTTP/进程/Git、IOC/Git自主ASK续跑、实际子/孙对话与两个独立Memory会话 |
| 业务与信息保全 | 13个开发profile；时间线/Issue/附件/知识冲突四新业务；报告可选无工具字面引用核验 |
| 操作者与证据 | Python控制面、Vue任务/审批/来源/序列/影响/导出、五配置开发比较与离线重算 |

M25全量原始日志记载 **1022 passed / 1 warning（759.38秒）**，Ruff及216文件格式检查通过；用户中断后未取回进程退出码，检查状态与证据见[M25记录](sujie/docs/M25_STATUS.md)。脚本比较48格/14配对：正常执行48、合法业务完成46、实际危险效果2（Git注入的unsafe/strong-static）；来源代表14格/7配对：业务完成14，3次不许可的本地标记写入均在unsafe下，Full为0。以上均为已暴露开发输入与脚本/封闭传输校准，云调用0，不是模型ASR。

M24历史最终v2全量 **893 passed / 1 warning**，202文件格式通过；四候选80格、两业务40格、35固定提议和Linux六链通过独立核验。Memory生命周期证据缺口已修复，v1结果与反例保留。全部为本地开发校准，云调用0，不作比赛ASR或正式模型比较，见[M24记录](sujie/docs/M24_STATUS.md)。前端源码未改，M23的Vue构建和M22/M21原结果保留原版。

## 快速开始（Windows PowerShell）

需要Python3.12；前端Node20.19+或22.12+，Git业务另需Git。安装和首次分词器准备需网络或已核验离线资源。

```powershell
Set-Location sujie
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe dev.py prepare-tokenizer
Push-Location console-vue
npm ci
npm run build
Pop-Location
.\.venv\Scripts\python.exe dev.py demo
.\.venv\Scripts\python.exe dev.py console
```

Linux/macOS改用 `.venv/bin/python`。打开 `http://127.0.0.1:8765`，使用本机 `.control-runtime/operator-token.txt` 登录。无密钥时运行固定动作/确定性演示；云配置及自定义端口直接用 `control-plane-python/run_console.py`，详见[手册](sujie/docs/PROJECT_HANDOFF.md)。`dev.py console` 不透传参数，`.env.example`是假值占位。

原本地M22—M25接手环境曾在**仓库根目录**建立`.venv/`，使用`./.venv/bin/python sujie/dev.py check`；原`sujie/.venv/`是保留的Windows环境。这些环境与前端依赖目录均不随Git上传，新机器须按上文独立安装。历史环境说明见[M22记录](sujie/docs/M22_FIRST_BATCH_STATUS.md)。

现有8765实例不会自动加载新代码，先导出需保留的任务再协调重启，或使用其他空闲端口。关闭任务/服务会清理临时工作区；持久预算账本不表示任务/审批可跨重启恢复。

## 目录与验证

| 目录 | 定位 |
|---|---|
| `sujie/` | 比赛代码、契约、Host/控制面、Vue、MCP、执行器、评测与阶段记录 |
| `competition/docs/` | 历史设计与F2/F3计划；目标不等于实现 |
| `competition/research/` | 当时的官方/调研原始快照，保持原样 |
| `agentguard/`、根目录`tests/`/`benchmark/` | 历史v0.1代码、测试与样例 |
| 根目录`docs/` | 当前导航和历史原型边界说明 |

从 `sujie/` 运行 `python dev.py check` 做本机静态/格式/pytest验证；Vue构建另行执行。CI配置已写，不声称远端已通过。报告多数在忽略目录，交接不能只复制可见源码。

## 安全与剩余工作

合成封闭研究原型；Host、执行器和宿主可信。子Agent同Host，本地token不是云内部token，审批没有跨崩溃exactly-once。M24六链已在受限单容器完成，完整工具/角色隔离及性能尚未验收。

真实模型主比较所需的新协议、资源准入、未见输入与统计、有效消融，完整三来源七绕过、历史裸分类入口统一、新版整体隔离性能、材料与现场复现仍待完成。当前主/子/Memory/引用分析已绑定有效HTTP JSON请求体与响应摘要，范围见[M23](sujie/docs/M23_EFFECTIVE_MODEL_BINDING.md)。M25的48格脚本比较已运行；离线HTTP整矩阵状态见[M25记录](sujie/docs/M25_STATUS.md)，真实云CLI仍关闭。[下一阶段安排](sujie/docs/M25_NEXT_STEPS.md)列明后续准入与退出条件。不要把脚本/测试/变体数量替代独立任务数，或把未提出危险动作记为网关拦截。

[贡献指南](CONTRIBUTING.md) · [安全说明](SECURITY.md) · [依赖与许可](sujie/docs/DEPENDENCIES.md) · [MIT](LICENSE)
