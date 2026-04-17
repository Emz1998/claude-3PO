# Backlog

**Project:** TestProject
**Last Updated:** 2026-04-16
**Goal:** Ship the MVP

## Priority Legend

- P0 — must-have
- P1 — should-have
- P2 — nice-to-have

## ID Conventions

- US — User Story
- TS — Technical Story
- BG — Bug
- SK — Spike

## Stories

### US-001: Login flow

> **As a** user, **I want** to log in **so that** I can access my account

**Description:** Enable users to authenticate via email and password.
**Priority:** P0
**Milestone:** MVP
**Is Blocking:** None
**Blocked By:** None

- [ ] User can register with email + password
- [ ] User can log in with existing credentials
- [ ] User sees an error on invalid credentials

### BG-001: Logout crash

> **What's broken:** App crashes on logout
> **Expected:** Clean session teardown
> **Actual:** Unhandled exception in auth middleware

**Description:** Crash on logout leaves the session inconsistent.
**Priority:** P1
**Milestone:** MVP
**Is Blocking:** None
**Blocked By:** US-001

- [ ] No crash on logout
- [ ] Session is cleared server-side
