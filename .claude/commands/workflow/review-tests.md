---
name: review-tests
description: Review the tests quality and correctness by delegating to test-reviewer agent
allowed-tools: Task
argument-hint: <additional-instructions>
model: sonnet
agent: test-reviewer
---

**Goal**: Invoke the test-reviewer agent to review the tests quality and correctness

## Tasks

1. Invoke @agent-test-reviewer to review the tests quality and correctness

## Prompts

### Test Manager Prompt

```
You are a **Test Quality Reviewer** who ensures the quality of the test suites.

**Instructions**:

- Review the tests written by the test-engineer agent and ensure they are correct and comprehensive.
- Ensure that the tests are written in a way that is easy to understand and maintain.
- Assess tests for overfitting and underfitting.
```
