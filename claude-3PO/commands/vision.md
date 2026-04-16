---
name: vision
description: Phase 1 — Ask 10 discovery questions and write product-vision.md
argument-hint: <project-description>
model: sonnet
---

**Phase 1: Vision**

Ask the user 10 discovery questions using `AskUserQuestion`, then write `projects/docs/product-vision.md`.

## Questions

Ask these questions **one at a time** via `AskUserQuestion`:

1. What is the name of your project and who is building it?
2. Who are your target users and what problem do they face today?
3. What has changed recently that makes now the right time to solve this problem?
4. In one paragraph, what does your product do and how does it work at a high level?
5. What are your top 3 value propositions and the user benefit of each?
6. Who are your main competitors or alternatives, and what is your advantage over them?
7. What features are in your MVP and what is explicitly excluded?
8. What is your revenue model and what key metrics will you track?
9. Who is on your team and what is your current runway or budget?
10. What does success look like at MVP launch, 6 months, and 12 months?

## Instructions

1. Ask all 10 questions sequentially using `AskUserQuestion`
2. After collecting all answers, read the product vision template at `${CLAUDE_PLUGIN_ROOT}/skills/visionize/templates/product-vision.md`
3. Populate the template with the user's answers
4. Write the completed document to `projects/docs/product-vision.md`

## Completion

Phase completes when `projects/docs/product-vision.md` is written.
