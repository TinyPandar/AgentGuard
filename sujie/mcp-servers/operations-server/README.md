# mcp-servers/operations-server

M1 真实 stdio MCP Server，提供受根目录约束的 `read_file`、`write_file` 和仅指向
执行器内部固定 Receiver 的 `send_data`。Agent 只传目的地标签，不能提供任意 URL。

它只用于合成测试目录，不是操作宿主真实文件或公网的生产执行器。
