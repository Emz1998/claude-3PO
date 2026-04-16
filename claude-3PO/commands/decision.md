---
name: decision
description: Phase 3 — Ask 10 technical decision questions informed by strategy research, then write decisions.md
argument-hint: <decision-context>
model: sonnet
---

**Phase 3: Technical Decisions**

Ask the user 10 technical decision questions using `AskUserQuestion`, informed by the strategy research. Then write `projects/docs/decisions.md`.

## Questions

Read the decision questions from `${CLAUDE_PLUGIN_ROOT}/commands/decision_questions.md`.

Ask these questions **one at a time** via `AskUserQuestion`. For each question, provide context from the strategy research to help the user decide:

1. Which programming language and framework will you use for the backend?
2. Which frontend framework or platform will you build on?
3. Which database type and specific product will you use?
4. How will you handle authentication and authorization?
5. Will you start with a monolith, microservices, or serverless architecture?
6. Which cloud provider and hosting approach will you use?
7. What is your API strategy — REST, GraphQL, or RPC?
8. How will you handle CI/CD and deployment?
9. What third-party services or APIs will you integrate?
10. What are your non-negotiable technical constraints or requirements?

## Instructions

1. Read `projects/docs/product-vision.md` for product context
2. Summarize key findings from the strategy research agents before each question
3. Ask all 10 questions sequentially using `AskUserQuestion`
4. Write the completed decisions document to `projects/docs/decisions.md`

## Completion

Phase completes when `projects/docs/decisions.md` is written.
