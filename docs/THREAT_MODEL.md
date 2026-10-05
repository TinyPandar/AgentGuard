# Threat model

## Protected assets

- internal and confidential data;
- tool credentials and privileged APIs;
- integrity of external side effects;
- user intent and approval state;
- audit evidence.

## Untrusted inputs

- user-controlled prompts;
- RAG documents, web pages, PDFs and emails;
- tool results and long-term memory content;
- model-generated tool names and arguments.

## In-scope attacks

- direct and indirect prompt injection;
- tool selection and argument manipulation;
- forged user confirmation;
- sensitive-data flow to an external destination;
- unknown tool, permission and resource access.

## Security goal

Detection may miss an injection. A missed detection must not grant a tool,
resource, permission, data flow or approval that is absent from the trusted
task grant.

## Out of scope for v0.1

- model weight and training-data security;
- enterprise IAM and multi-tenancy;
- production scaling and availability;
- complete DLP classification;
- defense against compromise of the gateway host itself.
