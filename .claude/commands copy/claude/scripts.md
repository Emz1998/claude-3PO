---
name: scripts
description: Generate custom Claude Scripts with effective triggers and progressive disclosure
allowed-tools: Write, Read, Grep, Bash
argument-hint: <requirements>
model: opus
---

<instruction> Use claude-scripts skill to create or update Claude Scripts with requirements $ARGUMENTS </instruction>

<rule>`claude-scripts` skill MUST be used for this task.</rule>
