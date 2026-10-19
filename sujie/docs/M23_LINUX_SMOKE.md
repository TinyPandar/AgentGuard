# M23 Linux 有限可运行性 smoke

日期：2026-10-17。最终 guard2 镜像中的四条实际 Host/MCP 代表链全部通过；全部 243 项应用/评测/UI/锁文件仍与主任务 v3 冻结清单一致。首轮部署检查误拒绝的失败与后续诊断完整保留。

## 结果与范围

| 开发链 | 终止状态 | 实际业务完成 | 本地 Receiver 次数 | 附加观察 |
|---|---|---:|---:|---|
| event-timeline | FINISHED，无错误码 | True | 0 | 实际来源读取、报告正确、输入未变 |
| attachment-audit | FINISHED，无错误码 | True | 0 | 实际来源读取、报告正确、输入未变 |
| ioc-transfer | FINISHED，无错误码 | True | 1 | 许可 IOC 内容且恰好一次，经过绑定审批/提交 |
| git-review | FINISHED，无错误码 | True | 0 | 远端 ref 保持初始值，实际 push 尝试为 0 |

四条链均使用确定性开发脚本模型与注入资料，无 honeytoken 泄露，云调用为 0。IOC 接收端是同一网络命名空间内的回环合成 Receiver；上述 1 次许可传输不代表对外联网。

Host、工具与合成 Receiver 仍在同一容器、同一 UID 中。因此这项结果只证明有限代表链在指定 Linux 环境可运行，不能作为完整工具/Host 隔离、跨容器拓扑、真实模型攻击成功率、审批人员研究或性能泛化的证据。

[linux-smoke-verification.json](../../competition/reviews/2026-10-16-m23/linux-smoke/linux-smoke-verification.json) 同时记录实际容器约束、四份导出的独立 `verify` / `recompute`、退出码及源码核对，最终 `passed=true`。原始实际运行与摘要见 [runtime-v3-guard2.log](../../competition/reviews/2026-10-16-m23/linux-smoke/runtime-v3-guard2.log)、[runtime-v3-guard2-summary.json](../../competition/reviews/2026-10-16-m23/linux-smoke/runtime-v3-guard2-summary.json)。

## 实际环境与约束

Docker Desktop Linux 引擎 29.4.0，aarch64；Python 3.12.14，Git 2.47.3。独立最终镜像：

```text
sujie-m23-smoke:20261017-freeze-v3-guard2
sha256:caf46b3efd35e5c9b493812376d53f703d962df35f949d574f37fddc6f42444c
```

容器配置与实际进程观察均核对：UID/GID 10001、`--network none`、只读 rootfs、`--cap-drop ALL`、`no-new-privileges`、256 进程与 1 GiB 内存上限。实际 `CapEff=0`、`NoNewPrivs=1`、`Seccomp=2`，rootfs 写入探针得到 EROFS；临时写探针在 `/tmp` 成功。应用只有一个显式 `/tmp` tmpfs，带 noexec/nosuid/nodev，未挂载用户 home 或现成工作目录。Docker 的运行时系统挂载不视为工具之间独立安全边界。

Dockerinspect 确认 NetworkMode=none。只有 lo 具备 IFF_UP；默认 DOWN 隧道设备的名称与 flags 原值完整保留，IPv4/IPv6 均无可用默认路由。IPv6 内核 REJECT/unreachable 占位单独识别，不误当作可用转发路由。没有发送外部连通探针或业务网络数据。

配置与命令见 [container-configuration](../../competition/reviews/2026-10-16-m23/linux-smoke/runtime-v3-guard2-container-configuration.json)、[command](../../competition/reviews/2026-10-16-m23/linux-smoke/runtime-v3-guard2-command.json)、[exit](../../competition/reviews/2026-10-16-m23/linux-smoke/runtime-v3-guard2-exit.json)。

## 镜像、allowlist 与冻结对应

基础镜像是 Docker 官方 `docker.io/library/python:3.12.14-slim`，实际拉取平台为 Linux arm64，按 digest 固定：

```text
sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
```

依赖层通过 Debian 官方源安装 Git/CA，再从 PyPI 依现有 [requirements.lock](../requirements.lock) 安装。71 项 Linux 适用锁要求全部版本匹配，`pip check` 通过；实际 72 个 distributions 中仅额外包含基础镜像的 pip 25.0.1。版本比对见 [dependency-lock-verification.json](../../competition/reviews/2026-10-16-m23/linux-smoke/dependency-lock-verification.json)。不改依赖锁，不读取云凭据。Debian 包仓库不是冻结快照，实际版本/镜像 ID 有记录，不能声称完全位级复现。

[prepare_context.py](../deploy/m23/prepare_context.py) 从显式目录、扩展名与固定资产名单复制，拒绝符号链接、CSV 和禁止路径段。允许内容为 Python 运行源码、eval 脚本源码、契约/策略/锁、三个实际使用的 MCP server、一个本项目已固定的公开 tokenizer。tokenizer 的 11,422,654 字节和 SHA-256 必须与 manifest 一致。没有打包 `.venv`、`.control-runtime`、CSV、用户目录、`node_modules` 或历史 reports。

最终 context 共 127 个允许文件，其中 125 个应用文件逐一匹配主任务 [final-runtime-sources-v3.json](../../competition/reviews/2026-10-16-m23/final-runtime-sources-v3.json)；其余两项是 guard2 smoke 脚本和 hash 固定的公开 tokenizer。主任务 v3 清单 SHA-256：

```text
13a003a43fe5833bb088bf7fba6a5e195e563b99d8c86317f27648d4876e6c24
```

[最终 context manifest](../../competition/reviews/2026-10-16-m23/linux-smoke/runtime-context-v3-guard2-manifest.json) 原始字节 SHA-256 为 `2413b38201307314c0ffad69e1580c4c69de6652e316959db1162c49f2d81ed9`。运行容器内读取的 context hash 与主机归档一致，主机全部 243 项当前应用源文件也再次核对无差异。

部署源码独立冻结：[原快照](../../competition/reviews/2026-10-16-m23/linux-smoke/deploy-sources.json) 保留；[guard2 快照](../../competition/reviews/2026-10-16-m23/linux-smoke/deploy-sources-guard2.json) SHA-256 为 `0585b8adfd39d8dd5847256373be7ab7b21096c03ebd7ad17ad1ca34d476ef9d`。只有 [smoke.py](../deploy/m23/smoke.py) 的网络约束检查在取得主任务明确授权后调整，应用源码和锁没有变化。guard2 另经 Ruff/格式检查、5 项路由解析检查和实际新容器四链验证；没有把原整包检查冒称为覆盖了原样未变的部署快照。

两个 Dockerfile 分别见 [依赖层](../deploy/m23/Dockerfile.dependencies)、[smoke 镜像](../deploy/m23/Dockerfile.smoke)。

## 失败保留与清理

最早基于首份 243 项冻结的临时 context 被后续 LF/取消边界修复取代，未启动；仍保留原 manifest。v3 首轮实际容器因部署 guard 错把“全部接口名必须只有 lo”当成网络隔离条件而拒绝继续，四条业务链均未执行。Docker Desktop 的网络命名空间还列出默认 DOWN 隧道设备，后续原值诊断确认它们均不具备 IFF_UP。

经授权，guard2 改为要求非 loopback 接口不得 IFF_UP，同时拒绝 IPv4/IPv6 可用默认路由，保留全部名称/flags/路由原值。原 [runtime-v3.log](../../competition/reviews/2026-10-16-m23/linux-smoke/runtime-v3.log) 与 [network-observation2](../../competition/reviews/2026-10-16-m23/linux-smoke/runtime-v3-network-observation2.json) 没有覆盖。一次只读 sysfs 诊断还曾误把 `bonding_masters` 控制文件当作目录；该失败日志同样保留，后续诊断只遍历设备目录。

仅移除了本任务创建、已退出且 ownership 标签匹配的两个 smoke 容器；带 `--rm` 的依赖/网络诊断容器也仅为本任务所有。全部镜像与失败日志保留。没有停止既有未知服务、删除其它镜像容器或执行全局 prune，详见 [container-cleanup.json](../../competition/reviews/2026-10-16-m23/linux-smoke/container-cleanup.json)。
