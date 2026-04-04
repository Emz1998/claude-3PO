# SKILL.md Template

## YAML Frontmatter

```yaml
---
name: [skill-name]
description: [Action verb] [what it does]. Use when [trigger conditions] or when user mentions [keywords].
context: [fork] (optional)
disable-model-invocation: [true|false] (optional)
allowed-tools: [comma-separated list of tools] (optional)
agent: [agent-name] (optional) (must be defined if context is set to fork)
hooks: [comma-separated list of hooks] (optional)
---
```

## Instructions

- [Instruction 1]
- [Instruction 2]
- [Instruction 3]
- ...

## Workflow

### Phase 1: [Phase Name]

- [Task 1]
- [Task 2]
- [Task 3]
- ...

### Phase 2: [Phase Name]

- [Task 1]
- [Task 2]
- [Task 3]
- ...

### Phase 3: [Phase Name]

- [Task 1]
- [Task 2]
- [Task 3]
- ...

## Rules

- [Constraint 1]
- [Constraint 2]
- [Constraint 3]
- ...

## Acceptance Criteria

- [Criterion 1]
- [Criterion 2]
- [Criterion 3]
- ...

```

## Guidelines

### Naming Convention

Use gerund form (verb + -ing):

- `processing-pdfs`
- `analyzing-spreadsheets`
- `managing-databases`
```
