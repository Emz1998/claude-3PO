---
name: generating-business-plan
description: Generates comprehensive business plans by researching market data, competitors, and industry trends, then filling out a structured template. Use when creating business plans, market analysis, or when user mentions "business plan", "market research", or "competitive analysis".
---

**Goal**: Generate a complete business plan by researching the market and filling out the business plan template

## Context

- **Product/Company name**: $0
- **Instructions**: $1

## Instructions

- If no product/company name is provided, ask the user to provide it
- Use the `research-specialist` agent (via Task tool with `subagent_type: research-specialist`) for all market research, competitor analysis, and industry trend research
- Fill out every section of `business-plan-template.md` with researched, evidence-based content
- If the user does not provide a product/company name, ask before proceeding
- If existing project docs exist (e.g., `project/docs/executive/product-vision.md`, `project/docs/product/product-brief.md`), read them for context before researching

## Workflow

**Phase 1: Gather Context**

- Read user-provided instructions and arguments
- Read `project/docs/executive/product-vision.md` for project vision
- Check for existing project docs in `project/docs/` for context
- Read template from `.claude/skills/business-plan/business-plan-template.md`

**Phase 2: Research**

- Delegate to `research-specialist` agent to research:
  - Market size (TAM/SAM/SOM) for the target industry
  - Direct and indirect competitors
  - Industry trends and market conditions
  - Pricing benchmarks from similar products
  - Go-to-market strategies used by competitors
- Collect and synthesize research findings

**Phase 3: Generate Business Plan**

- Fill out each section of the template using research findings and user context
- Ensure all placeholder fields (`[...]`) are replaced with actual content
- Mark estimates clearly with `(est.)` where data is approximated
- Save completed business plan to `project/docs/executive/business-plan.md`

**Phase 4: Review and Report**

- Verify all template sections are complete
- Report completion with file path and summary of key findings

## Rules

- NEVER fabricate market data without research backing
- ALWAYS mark estimates and assumptions explicitly
- NEVER skip sections; use "N/A - [reason]" if a section is genuinely not applicable
- KEEP financial projections conservative and clearly labeled as estimates
- Follow documentation rules (no emojis, use lists over paragraphs, max 2 header levels)

## Acceptance Criteria

- All template sections filled with researched content
- No remaining placeholder text (`[...]`) in the final output
- Market data sourced through research-specialist agent
- Saved to `project/docs/business/business-plan.md`
- Estimates and assumptions clearly marked
