# 参与开发

感谢参与溯界。当前协作主线位于 `sujie/`，根目录的 `agentguard/` 是历史 v0.1 原型，除非 Issue 明确要求，否则不要在旧版上增加比赛功能。

## 开始之前

1. 阅读 `competition/docs/SUJIE_FINAL_DESIGN.md`，确认需求属于哪个里程碑。
2. 从 Issue 领取一个边界清晰的任务，写明测试 ID、输入、预期决策和真实副作用 Oracle。
3. 从 `main` 创建短分支：`feat/<topic>`、`fix/<topic>`、`test/<topic>` 或 `docs/<topic>`。
4. 不提交真实凭据、真实业务数据、模型缓存、离线 wheel、镜像 tar 或个人环境文件。

## 本地验证

项目要求 Python 3.12：

```powershell
cd sujie
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe dev.py check
.\.venv\Scripts\python.exe dev.py demo
```

Linux/macOS 使用 `.venv/bin/python`。修改 Compose 或隔离边界时，还需在 Linux + Docker 环境运行：

```bash
cd sujie
docker compose -f deploy/m1.compose.yaml config --quiet
sh deploy/run_m1_container_test.sh
```

## Pull Request 要求

- PR 只解决一个主题，并关联 Issue。
- 说明修改的信任边界、失败模式和未覆盖项。
- 新依赖必须记录用途、固定版本、许可证、替代方案以及是否进入安全热路径。
- 新安全能力必须包含正常对照、攻击用例和可观测的副作用 Oracle，不能只断言模型文本输出。
- 修改 Schema、DSL 或授权逻辑时必须补充拒绝路径测试。
- 不得用 Mock、确定性模型或自动化测试数量冒充真实 LLM 指标。

## 指标口径

提交评测结果时至少给出：配置名称、模型与版本、数据集版本、样本分母、随机参数、失败/超时处理、Execution ASR、敏感数据泄露率、正常任务成功率与 P95 延迟。结果文件应可由脚本重新生成，不手工改数字。

## 需要先讨论的变化

以下变化先开 Design Issue 或 ADR，再写代码：

- 改变 `LLM Decision != Authorization` 主原则；
- 新增或扩大可信计算基；
- 允许 Agent 直接获得工具凭据、文件系统或网络权限；
- 修改 `TaskContract`、`TaskGrant`、`ProvenanceEnvelope` 或决策优先级；
- 引入新的模型服务、数据库、中间件或外部网络依赖。
