---
name: strategy
description: Phase 2 — Launch 3 parallel Research agents to investigate tech stack, architecture, and security/DevOps
argument-hint: <research-focus>
model: sonnet
---

**Phase 2: Strategy Research**

Launch 3 `Research` agents **in parallel** (single message, 3 Agent tool calls). Each agent reads `projects/docs/product-vision.md` first.

## Agent Focus Areas

1. **Agent 1 — Tech stack & infrastructure**: Research best-fit languages, frameworks, databases, and hosting for the product's requirements. Evaluate trade-offs (cost, scalability, team expertise).

2. **Agent 2 — Architecture patterns & integrations**: Research architecture styles (monolith vs microservices, event-driven, serverless), API design patterns, and third-party integrations needed.

3. **Agent 3 — Security, compliance & DevOps**: Research authentication strategies, data privacy requirements, CI/CD pipeline options, and deployment strategies for the target platform.

## Instructions

1. Each agent's prompt should start with: "Read `projects/docs/product-vision.md` first, then..."
2. Launch all 3 agents in a **single message**
3. Agents run in foreground — wait for all to complete
4. Allowed: Read, Glob, Grep, WebFetch, WebSearch

## Completion

Once all 3 Research agents complete, synthesize findings and advance to `/decision`.
