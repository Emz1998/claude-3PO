---
name: brainstorm
description: Interactive brainstorming session using questions to explore and refine project ideas
allowed-tools: AskUserQuestion, Write
argument-hint: <topic or idea to brainstorm>
model: sonnet
---

**Goal**: Facilitate an interactive brainstorming session using only `AskUserQuestion` tool to explore, refine, and document ideas collaboratively with the user

## Context

- Topic to brainstorm: $ARGUMENTS

## Workflow

### Phase 1: Idea Exploration

- Use `AskUserQuestion` to understand the core topic/problem
- Ask clarifying questions about scope, constraints, and goals
- Explore different angles and perspectives through questions
- Gather initial ideas from the user

### Phase 2: Idea Refinement

- Use `AskUserQuestion` to dive deeper into promising ideas
- Ask about feasibility, resources, and potential challenges
- Help prioritize and compare different approaches
- Refine ideas based on user feedback

### Phase 3: Session Wrap-Up

- Use `AskUserQuestion` to ask if the user wants to continue brainstorming
- If done, ask if user wants to create a `brainstorm-summary.md` file
- If yes, create the summary file with all session details using `Write` tool
- Save the summary file to the `project/brainstorm-summary.md` file

## Rules

- **NEVER** output text directly - all communication MUST use `AskUserQuestion` tool
- **NEVER** use any tools other than `AskUserQuestion` and `Write` (for final summary only)
- **DO NOT** assume the session is complete - always ask if user wants to continue
- **DO NOT** create summary file without explicit user confirmation
- **ALWAYS** provide multiple choice options to guide the brainstorming flow

## Acceptance Criteria

- All interaction uses `AskUserQuestion` tool exclusively
- Session continues until user explicitly confirms completion
- User is asked about creating summary file before writing it
- Summary file (if created) captures all key ideas and decisions from the session
