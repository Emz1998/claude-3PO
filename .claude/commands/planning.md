---
name: plan
description: Collaborative planning session using questions to explore solutions to user's problem/goal
allowed-tools: AskUserQuestion, Write
argument-hint: <problem-description-or-goal>
model: sonnet
---

**Goal**: Facilitate a collaborative planning session using only `AskUserQuestion` tool to explore, refine, and document solutions to user's problem/goal collaboratively with the user

## Context

- Problem/goal to solve: $ARGUMENTS

## Workflow

### Phase 1: Idea Exploration

- Use `AskUserQuestion` to understand the core problem/goal
- Ask clarifying questions about scope, constraints, and goals
- Explore different angles and perspectives through questions
- Gather initial solutions from the user

### Phase 2: Idea Refinement

- Use `AskUserQuestion` to dive deeper into promising solutions
- Ask about feasibility, resources, and potential challenges
- Help prioritize and compare different approaches
- Refine solutions based on user feedback

### Phase 3: Session Wrap-Up

- Use `AskUserQuestion` to ask if the user wants to continue planning
- If done, ask if user wants to create a `plan.md` file
- If yes, create the summary file with all session details using `Write` tool. If No, ask the user what they still need.
- Save the summary file to the `.claude/plans/plan.md` file

## Rules

- **NEVER** output text directly - all communication MUST use `AskUserQuestion` tool
- **NEVER** use any tools other than `AskUserQuestion` and `Write` (for final summary only)
- **DO NOT** assume the session is complete - always ask if user wants to continue
- **DO NOT** create summary file without explicit user confirmation
- **ALWAYS** provide multiple choice options to guide the planning flow
- **DO NOT** overcomplicate/overengineer the plan. Keep it simple and efficient.
- **VERY IMPORTANT**: Include code outputs in the plan.md file for each approach considered.

## Acceptance Criteria

- All interaction uses `AskUserQuestion` tool exclusively
- Session continues until user explicitly confirms completion
- User is asked about creating summary file before writing it
- Summary file (if created) captures all key ideas and decisions from the session

## Plan MD File Requirements

- Must include code snippets with explanations and expected code outputs
- Must include a summary of the plan
- Must include a list of approaches considered
- Must include pros and cons of each approach
- Must include the final approach chosen and why
