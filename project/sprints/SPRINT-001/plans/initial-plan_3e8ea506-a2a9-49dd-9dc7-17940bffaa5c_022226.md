# Initial Implementation Plan - TS-012: Next.js 15 Project Setup

**Task:** TS-012
**Sprint:** SPRINT-001
**Story Points:** 3
**Date:** 2026-02-22
**Status:** Draft - Pending Approval

---

## Objective

Set up a greenfield Next.js 15 project with App Router, TypeScript strict mode, Tailwind CSS v4, ESLint, Prettier, and Vitest. Establish the folder structure defined in `architecture.md`. All acceptance criteria validated by passing `npm run dev`, `npm run build`, `npm run lint`, and `tsc --noEmit`.

## Goals

1. Working Next.js 15 dev server and production build
2. TypeScript strict mode with zero errors
3. ESLint + Prettier enforcing coding standards from `coding-standards.md`
4. Folder structure matching `architecture.md`
5. Vitest installed and wired into `npm run check`
6. `.gitignore` updated for Node.js/Next.js

## Scope

**In Scope**
- Next.js 15 + React 19 + App Router initialization
- TypeScript strict mode configuration
- Tailwind CSS v4 setup (per ADR-006)
- ESLint + Prettier with project-specific rules
- Vitest installation and script wiring
- Folder structure with placeholder/barrel files
- `.gitignore` update for Node.js entries
- `pyproject.toml` update to exclude `src/` from Python package scanning

**Out of Scope**
- Firebase setup (TS-013)
- Python pipeline setup (TS-016)
- Any business logic, components, or pages beyond default placeholders
- CI/CD pipeline configuration
- Playwright or E2E test setup

---

## Subtasks

**Priority order: T-001 -> T-002 -> T-003** *(T-002 and T-003 depend on T-001; T-002 and T-003 are independent of each other)*

## T-001: Initialize Next.js 15 with App Router and TypeScript

**Priority:** 1 - Must complete first
**Estimated effort:** 1 hour

**Steps:**
1. Run `npx create-next-app@latest` with these flags: TypeScript, App Router, Tailwind CSS, `src/` directory, no import alias customization
2. Verify Next.js 15 and React 19 are installed in `package.json`
3. Confirm Tailwind CSS v4 is installed (not v3) - upgrade if `create-next-app` installs v3
4. Enable `strict: true` in `tsconfig.json` (verify all strict sub-flags are on)
5. Set `next.config.ts` (not `.js` or `.mjs`) with minimal config
6. Install Vitest: `npm install -D vitest`
7. Add npm scripts to `package.json`:
   - `"check": "tsc --noEmit && eslint src/ && vitest run"`
   - `"test": "vitest"`
8. Update `.gitignore` with Node.js/Next.js standard entries: `node_modules/`, `.next/`, `out/`, `.env*.local`, `*.tsbuildinfo`, `next-env.d.ts`
9. Update `pyproject.toml` to exclude `src` from setuptools: add `exclude = ["src*"]` under `[tool.setuptools.packages.find]`
10. Run `npm run dev` - verify server starts without errors
11. Run `npm run build` - verify production build succeeds
12. Run `tsc --noEmit` - verify zero type errors

**Files created/modified:**
- `/home/emhar/avaris-ai/package.json` (created)
- `/home/emhar/avaris-ai/tsconfig.json` (created)
- `/home/emhar/avaris-ai/next.config.ts` (created)
- `/home/emhar/avaris-ai/src/app/page.tsx` (created)
- `/home/emhar/avaris-ai/src/app/layout.tsx` (created)
- `/home/emhar/avaris-ai/src/app/globals.css` (created)
- `/home/emhar/avaris-ai/.gitignore` (modified - add Node.js entries)
- `/home/emhar/avaris-ai/pyproject.toml` (modified - exclude src)
- `/home/emhar/avaris-ai/package-lock.json` (created)
- `/home/emhar/avaris-ai/tailwind.config.ts` (created, if generated - may not exist with Tailwind v4)

**Definition of Done:**
- `npm run dev` starts without errors
- `npm run build` succeeds
- `tsc --noEmit` passes with zero errors
- `package.json` contains Next.js 15, React 19, Tailwind v4, Vitest
- `tsconfig.json` has `strict: true`

---

## T-002: Configure ESLint and Prettier with Project Standards

**Priority:** 2 - Depends on T-001
**Estimated effort:** 45 minutes

**Steps:**
1. Install Prettier and ESLint-Prettier integration: `npm install -D prettier eslint-config-prettier eslint-plugin-prettier`
2. Create `.prettierrc` with coding standards settings:
   - `tabWidth: 2`, `printWidth: 100`, `singleQuote: true`, `semi: true`, `trailingComma: "all"`
3. Configure ESLint (flat config `eslint.config.mjs` if Next.js 15 generates it, otherwise `.eslintrc.json`):
   - Extend `next/core-web-vitals`, `next/typescript`
   - Add Prettier plugin to avoid conflicts
   - Add rule: prefer named exports (warn on default exports except in `src/app/`)
4. Run `npm run lint` - fix any warnings until clean
5. Run Prettier across `src/` to format existing files
6. Verify no conflicts between ESLint and Prettier

**Files created/modified:**
- `/home/emhar/avaris-ai/.prettierrc` (created)
- `/home/emhar/avaris-ai/eslint.config.mjs` (modified, or `.eslintrc.json` depending on scaffold output)
- `/home/emhar/avaris-ai/package.json` (modified - new devDependencies)

**Definition of Done:**
- `npm run lint` passes with zero errors and zero warnings
- `.prettierrc` matches coding-standards.md exactly (2 spaces, 100 width, single quotes, semicolons, trailing commas all)
- ESLint and Prettier do not conflict

---

## T-003: Create Project Folder Structure per architecture.md

**Priority:** 3 - Depends on T-001
**Estimated effort:** 30 minutes

**Steps:**
1. Create directories:
   - `src/app/blog/`
   - `src/app/dashboard/`
   - `src/components/blog/`
   - `src/components/dashboard/`
   - `src/components/layout/`
   - `src/lib/`
   - `src/types/`
   - `public/` (likely already exists from scaffold)
2. Create barrel `index.ts` files with empty named exports in:
   - `src/components/blog/index.ts`
   - `src/components/dashboard/index.ts`
   - `src/components/layout/index.ts`
   - `src/lib/index.ts`
   - `src/types/index.ts`
3. Create placeholder route files:
   - `src/app/blog/page.tsx` (minimal placeholder)
   - `src/app/dashboard/page.tsx` (minimal placeholder)
4. Verify `tsc --noEmit` still passes after adding all files
5. Verify `npm run build` still succeeds

**Files created:**
- `/home/emhar/avaris-ai/src/app/blog/page.tsx`
- `/home/emhar/avaris-ai/src/app/dashboard/page.tsx`
- `/home/emhar/avaris-ai/src/components/blog/index.ts`
- `/home/emhar/avaris-ai/src/components/dashboard/index.ts`
- `/home/emhar/avaris-ai/src/components/layout/index.ts`
- `/home/emhar/avaris-ai/src/lib/index.ts`
- `/home/emhar/avaris-ai/src/types/index.ts`

**Definition of Done:**
- All directories from architecture.md exist
- Barrel index.ts files present in component, lib, and types directories
- Placeholder pages render without errors
- `npm run build` still succeeds
- `tsc --noEmit` still passes

---

## Risks and Mitigations

1. **`create-next-app` installs Tailwind v3 instead of v4**
   - *Mitigation:* Check installed version immediately. If v3, uninstall and install `tailwindcss@4` manually. Tailwind v4 uses CSS-based config instead of `tailwind.config.ts`.

2. **ESLint flat config vs legacy config mismatch**
   - *Mitigation:* Next.js 15 may scaffold either format. Work with whatever is generated. Do not force a config format change.

3. **Vitest conflicts with Next.js or React 19**
   - *Mitigation:* Install only `vitest` as dev dependency for now. Full test config (jsdom, React Testing Library) deferred to when actual tests are written.

4. **`pyproject.toml` change breaks existing Python tooling**
   - *Mitigation:* Only add `exclude = ["src*"]` to the existing `[tool.setuptools.packages.find]` section. Test that `pip install -e .` still works if applicable.

---

## Validation Checklist

*All must pass before TS-012 is marked complete:*

- [ ] `npm run dev` starts development server without errors
- [ ] `npm run build` completes with production output
- [ ] `tsc --noEmit` passes with zero errors
- [ ] `npm run lint` passes with zero errors/warnings
- [ ] `npm run check` runs type check, lint, and vitest without failure
- [ ] Folder structure matches architecture.md
- [ ] `.prettierrc` matches coding-standards.md settings
- [ ] TypeScript strict mode confirmed in `tsconfig.json`
- [ ] Tailwind CSS v4 confirmed in `package.json`
- [ ] `.gitignore` includes Node.js/Next.js entries
