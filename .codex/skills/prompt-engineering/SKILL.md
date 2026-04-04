---
name: prompt-engineering
description: Crafts, refines, and optimizes prompts for Claude 4.x models using best practices for instruction clarity, tool usage, and long-horizon reasoning. Use when creating user/system prompts, refining existing prompts, optimizing model interactions, or when user mentions prompt engineering, prompt optimization, prompt refinement, or Claude 4.x prompting.
---

**Goal**: Create and refine effective, well-structured prompts for Claude 4.x models that maximize instruction following, tool usage, and task completion quality.

**IMPORTANT**: Read `references/prompting-best-practices.md` at the start of any prompt engineering task to understand Claude 4.x specific patterns and capabilities.

## Workflow

Determine which workflow to follow:

- **Creation**: User needs a new prompt from scratch → See [workflows/creation.md](workflows/creation.md)
- **Refinement**: User has an existing prompt that needs improvement → See [workflows/refinement.md](workflows/refinement.md)

## Rules

- Check which Claude Model you are.
- Always read `references/prompting-best-practices.md` before starting prompt work
- Be explicit and specific rather than vague or general
- Provide context explaining WHY behaviors are important
- Use XML tags to structure prompt sections clearly
- Prefer telling Claude what TO do rather than what NOT to do
- Match prompt style to model (Opus 4.5 needs less hand-holding than Haiku 4.5)
- For long-horizon tasks, include state management and progress tracking
- For tool-heavy workflows, explicitly encourage parallel execution
- Avoid time-sensitive information in prompts
- Use consistent terminology throughout

## Key Patterns for Common Use Cases

**Agentic Coding**:

- Encourage code exploration before proposing solutions
- Add file cleanup instructions if minimizing temporary files
- Include over-engineering prevention for Opus 4.5
- Request parallel file reads for efficiency

**Research Tasks**:

- Define clear success criteria
- Encourage hypothesis tracking and verification
- Request structured approach with confidence levels
- Enable self-critique and iteration

**Long-Horizon Work**:

- Enable context awareness behavior
- Request structured state files (JSON) + progress notes (text)
- Encourage git usage for state tracking
- Emphasize incremental progress over completeness

**Frontend Design**:

- Include typography, color, motion, and background guidelines
- Discourage generic "AI slop" aesthetics
- Request distinctive, context-appropriate design choices
- Encourage creative interpretation

**Tool Orchestration**:

- Add parallel execution instructions for independent operations
- Balance proactive vs conservative tool usage based on needs
- Use fully qualified MCP tool names (ServerName:tool_name)

## Acceptance Criteria

- Prompt follows documentation rules (concise, high-level, no overexplaining)
- Best practices reference was consulted before work began
- Workflow-specific criteria met (see workflow files for details)
