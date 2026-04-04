# Prompt Creation Workflow

Use this workflow when creating a new prompt from scratch.

## Phase 1: Requirements Analysis

1. Read the best practices reference: `../references/prompting-best-practices.md`
2. Identify the task type:
   - Agentic coding workflows
   - Research and information gathering
   - Document creation and frontend design
   - Multi-context window tasks
   - Tool orchestration and parallel execution
3. Determine target model (Sonnet 4.5, Haiku 4.5, or Opus 4.5)
4. Identify key requirements and desired behaviors

## Phase 2: Prompt Creation

1. Apply core principles:
   - Be explicit with instructions
   - Add context and motivation behind requirements
   - Tell Claude what to do instead of what not to do
   - Use XML tags for structured sections
2. Structure the prompt based on task type:
   - Long-horizon tasks: Add state management and progress tracking guidance
   - Tool-heavy workflows: Include parallel execution instructions
   - Research tasks: Add verification and hypothesis tracking
   - Frontend work: Include aesthetic and design guidelines
3. Add appropriate controls:
   - Verbosity level (concise vs detailed updates)
   - Tool usage patterns (proactive vs conservative)
   - Output formatting requirements
   - Quality and completeness expectations

## Phase 3: Optimization and Validation

1. Review for Claude 4.x specific patterns:
   - Avoid "think" terminology when extended thinking is disabled
   - Use modifiers to encourage quality output
   - Frame instructions positively
   - Include reasoning and reflection guidance where appropriate
2. Validate prompt structure:
   - Clear, explicit instructions
   - Appropriate context and motivation
   - Examples align with desired behavior
   - No conflicting or ambiguous directions
3. Test considerations documented for target model(s)

## Acceptance Criteria

- Prompt is clear, explicit, and free of ambiguity
- Instructions include context and motivation where helpful
- Task-specific patterns from best practices are incorporated
- Prompt structure uses XML tags for organization
- No conflicting or contradictory guidance
- Output format requirements are specified positively
- Model-specific considerations are addressed
