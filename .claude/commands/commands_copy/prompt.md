---
name: prompt
description: Prompt Checker and Refiner
argument-hint: <prompt>
---

**Goal**: Check and refine the prompt based on the prompting best practices.

## Context

- Prompt: $ARGUMENTS

## Instructions

- Read the best practices documentation in @.claude/resources/prompting-best-practices.md
- Read the @.claude/resources/prompt-templates.md and choose the best templates according to the user prompt
- Analyze the prompt and check if it meets the prompting best practices.
- If the prompt does not meet the best practices, refine the prompt accordingly based on the best practices.
- Return the refined prompt as an output without adding any other context.

## Rules

- **Important**: Only include the refined prompt in the output. Do not include any other context even introductions or conclusions.
- Respond fast. Avoid any exploration of the codebase or research.
