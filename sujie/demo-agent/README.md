# demo-agent

M1 LangGraph 受控 Agent。`sujie_demo_agent/graph.py` 提供可替换决策模型接口、
明确标注为非 LLM 的确定性攻击测试模型，以及未配置 Provider 的 LangChain 适配器。

从 `sujie/` 运行 `.\.venv\Scripts\python.exe dev.py demo`，可执行正常、间接注入和
ASK 审批单次提交三条真实 stdio MCP 演示。输出不是大模型评测成绩。
