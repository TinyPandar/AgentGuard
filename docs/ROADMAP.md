# Roadmap

## v0.1 - authorization MVP

- [x] Unsafe baseline
- [x] rule detector and normalizer
- [x] TaskGrant and deterministic policy
- [x] approval binding
- [x] Artifact-level data-flow control
- [x] audit and three-mode benchmark

## v0.2 - agent and MCP integration

- [ ] expose the mock registry through an MCP proxy
- [ ] integrate one LangGraph demo agent
- [ ] keep raw tool credentials outside the agent process
- [ ] add explicit user approval UI/API
- [ ] add persistent SQLite audit storage

## v0.3 - evaluation depth

- [ ] import BIPIA/InjecAgent-compatible cases
- [ ] add multilingual and encoded attack variants
- [ ] add hard-negative security-analysis prompts
- [ ] measure Execution ASR, leakage rate, normal-task success and P95 latency
- [ ] add UER-BERT and LLM-judge detector ablations
