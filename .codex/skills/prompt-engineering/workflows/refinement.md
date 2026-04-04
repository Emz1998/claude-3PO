# Prompt Refinement Workflow

Use this workflow when improving an existing prompt.

## Phase 1: Prompt Analysis

1. Read the best practices reference: `../references/prompting-best-practices.md`
2. Review the existing prompt and identify:
   - Current structure and organization
   - Task type and target model
   - Reported issues or undesired behaviors
   - Missing elements based on best practices

## Phase 2: Issue Diagnosis

1. Check for common anti-patterns:
   - Vague or implicit instructions
   - Excessive negative framing (more "don't do X" and less of "do Y")
   - Missing context or motivation
   - Conflicting or ambiguous directions
   - Over-explaining things Claude already knows
   - Using "think" when extended thinking is disabled
   - Unintentional triggers for undesired behaviors
2. Identify gaps against best practices:
   - Missing state management for long-horizon tasks
   - No parallel execution guidance for tool-heavy workflows
   - Lack of verification steps for research tasks
   - Missing aesthetic guidelines for frontend work
   - Not providing explicit guidance formatting preferences
3. Note model-specific considerations:
   - Opus 4.5: May need over-engineering prevention, responds to normal language (not aggressive "MUST" phrasing)
   - Sonnet 4.5: Balance verbosity and tool usage patterns
   - Haiku 4.5: May need more explicit guidance

## Phase 3: Refinement Application

1. Apply targeted fixes:
   - Balance negative instructions with positive instructions
   - Add context explaining WHY behaviors matter
   - Make implicit expectations explicit
   - Structure with XML tags in **moderation** for clarity
   - Remove conflicting or redundant guidance
2. Enhance based on task type:
   - Add missing patterns from Key Patterns section in SKILL.md
   - Include appropriate controls (verbosity, tool usage, formatting)
3. Validate refined prompt:
   - Clear and unambiguous
   - Consistent terminology
   - No contradictions
   - Appropriate for target model

## Acceptance Criteria

- Original issues or undesired behaviors are addressed
- Anti-patterns identified and corrected
- Negative framing is balanced with positive instructions
- Missing best practices elements added
- Prompt maintains original intent while improving effectiveness
- Changes are targeted and minimal (avoid unnecessary rewrites)
