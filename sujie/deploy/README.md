# M1 Docker 验证

拓扑使用两个 Docker internal 网络：Agent 只连接 `agent-net`，Receiver 只连接
`tool-net`，Gateway 连接二者。Agent 镜像不包含 Gateway/MCP 源码，不挂载测试工作区，
也没有审批 API。

联网环境直接运行：

```sh
sh deploy/run_m1_container_test.sh
```

离线环境先导入并标记可信 linux/amd64 Python 基础镜像，将与 requirements.lock 对应的
CPython 3.12 Linux wheels 放入 `deploy/wheelhouse/`，然后运行：

```sh
export SUJIE_PYTHON_BASE=sujie/python-base:3.12.13
export SUJIE_OFFLINE_BUILD=1
sh deploy/run_m1_container_test.sh
```

离线模式强制 `pip --no-index`；缺 wheel 会直接构建失败。脚本使用普通
`docker compose down --remove-orphans` 清理本项目容器和网络，从不删除 Volume。

成功标准：Agent 输出 `receiver_directly_unreachable=true`、`external_network_unreachable=true`、
`secret_mount_absent=true` 和 `docker_socket_absent=true`；
独立 Oracle 输出 `receiver_requests=0`、`report_written=true` 和
`honeytoken_in_report=false`。该验证使用确定性测试模型，不是 LLM 评测。
