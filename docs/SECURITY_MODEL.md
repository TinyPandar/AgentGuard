# Security model

Authorization is evaluated in this order:

1. the tool must be registered and its arguments must match the schema;
2. the task grant must be valid and within its call budget;
3. the tool and required permission must be in the task grant;
4. the resource must match a task-scoped resource pattern;
5. the side effect must not be explicitly denied;
6. sensitive Artifact flows must be allowed for the destination zone;
7. high detector risk may tighten the result but never grant authority;
8. high-risk tools require an argument-bound backend approval.

External content always has `DATA_ONLY` authority. Trust, sensitivity, risk and
authority are separate dimensions.

Approval tokens bind the trace, subject, tool, canonical argument digest,
resource and input Artifact identifiers. They expire and are consumed once.
