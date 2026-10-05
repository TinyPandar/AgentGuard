# Architecture

```text
User request -> trusted TaskGrant
                    |
Untrusted context -> detector -> model/planner -> ToolProposal
                                              |
                                              v
                          Artifact provenance + Policy Engine
                                              |
                                  allow / deny / confirm
                                              |
                                              v
                                        Tool Gateway
                                              |
                                          Mock/MCP tool

Every transition -> append-only AuditTrace
```

The in-process mock registry exists for repeatable tests. A real deployment
must put raw tools and credentials behind a separate MCP/HTTP gateway process.
