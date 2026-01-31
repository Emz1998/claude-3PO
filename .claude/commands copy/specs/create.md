---
name: specs
description: Create or update specification documents (prd, tech-specs, or ux-specs)
allowed-tools: Read, Write, Glob, Grep
argument-hint: <specs-type>
model: opus
---

<specs-type> $ARGUMENTS </specs-type>

<dependency-chain>
app-vision.md → prd.json → tech-specs.md → ui-ux.md
</dependency-chain>

<instruction>

- Use `product-management` skill to generate product.json if specs-type is prd
- Use `specs-creator` skill to generate tech-specs.md or ui-ux.md specification document if specs-type is tech-specs or ui-ux
- If <specs-type> is not specified, generate all specification documents (prd, tech-specs, and ux-specs)

</instruction>

<rules> Must use `specs-creator` skill to generate <specs-type> specification document </rules>
