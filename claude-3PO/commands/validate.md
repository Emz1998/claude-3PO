---
name: validate
description: QA validation of implementation (implement workflow)
allowed-tools: Bash, Read, Glob, Grep, Agent
---

Run QA validation on the implementation.

## Instructions

1. Invoke the **QASpecialist** agent to validate the implementation against acceptance criteria.
2. The agent must return a verdict: `Pass` or `Fail`.
3. If `Fail`, go back to write-code and iterate on the implementation.
4. If `Pass`, proceed to code-review.

## Allowed

- Read, Glob, Grep — review code and tests
- Bash — run test commands (`pytest`, `npm test`, etc.)
- Agent — invoke QASpecialist (max 1)
