# Roadmap for v0.1.0

**Task ID Convention:** Sequential numbering (T001, T002, T003...)

**Notation Guide:**

- [P] for Parallel Tasks - task has NO dependencies on other tasks in same milestone
- [SA] for Subagent Tasks - isolated tasks that can be delegated to subagents without context
- Tasks without [P] have dependencies on previous tasks
- MS-[NNN]: Milestone Number (e.g. MS-001)
- T[NNN]: Task Number (e.g. T001)
- SC-[NNN]: Success Criteria at milestone level - measurable outcomes that define milestone success
- **DoD:** Definition of Done at task level - specific conditions that must be met for a task to be considered complete
- **Phase Structure:** 16 sequential phases (Phase 1-16). Phases 4-9 contain parallel milestones that can run simultaneously.

## Phase 1: Foundation - Environment Setup

**CRITICAL: This phase establishes the development environment. Subsequent phases depend on successful completion.**

### **MS-001:** Environment Setup (Week 1)

**Goal:** Next.js 15 + React 19 development environment fully configured with TypeScript strict mode, testing infrastructure, and PWA support

**Success Criteria:**

- SC-001: `npm run dev` and `npm run build` execute with zero errors
- SC-002: TypeScript strict mode compilation passes with zero warnings
- SC-003: Vitest and Playwright test runners execute successfully
- SC-004: PWA installs on desktop and launches in standalone mode
- SC-005: All environment variables load correctly from `.env.local`

**Tasks:**

- [x] T001 [P]: Initialize Next.js 15.1 project with App Router, React 19.1, and TypeScript 5.9
  - **DoD:** Project scaffolded, `npm run dev` starts without errors, `tsconfig.json` has strict mode enabled
- [ ] T002 [P]: Configure Tailwind CSS 4.1 with Shadcn UI theme tokens (see UX Section 2)
  - **DoD:** Tailwind config includes all theme tokens from UX Section 2, a test component renders with theme styles
- [ ] T003 [P]: Set up ESLint, Prettier, and TypeScript strict mode configuration
  - **DoD:** `npm run lint` passes, Prettier formats on save, strict mode flags caught in CI
- [ ] T004: Install core dependencies (Zod, Zustand, Immer, next-pwa)
  - **DoD:** All packages in `package.json`, import statements resolve without errors
- [ ] T005: Install dev dependencies (Vitest 3.2.4, Playwright 1.55.0, React Testing Library, MSW)
  - **DoD:** All dev packages in `package.json`, no version conflicts
- [ ] T006: Configure Vitest for unit testing with React support
  - **DoD:** `npx vitest run` executes a sample test, React component rendering works in tests
- [ ] T007: Configure Playwright for E2E testing (Chrome, Firefox, WebKit)
  - **DoD:** `npx playwright test` runs a sample test across all 3 browsers
- [ ] T008: Set up environment variables structure (.env.local, .env.example) per Tech Specs Section 12
  - **DoD:** `.env.example` lists all required vars with placeholder values, `.env.local` gitignored
- [ ] T009: Configure next-pwa 5.6.0 with service worker and manifest.json (FR-035, FR-036, FR-037)
  - **DoD:** Service worker registers in browser, manifest.json loads with correct app name and icons
- [ ] T010: Create project folder structure per Tech Specs Section 11
  - **DoD:** All directories from Tech Specs Section 11 exist, barrel `index.ts` files in place
- [ ] T010A [P]: Configure global React error boundary component for unhandled errors
  - **DoD:** Error boundary catches thrown errors, renders fallback UI, logs error details
- [ ] T010B [P]: Set up structured logging with log levels (debug, info, warn, error)
  - **DoD:** Logger utility exports `debug`, `info`, `warn`, `error` functions, respects log level config

**Acceptance Criteria:**

- [ ] `npm run dev` starts development server without errors
- [ ] `npm run build` completes successfully
- [ ] TypeScript compilation passes with strict mode
- [ ] PWA manifest loads correctly with app icons
- [ ] Service worker registers in browser
- [ ] Vitest runs with `npm test`

**Verification:**

- Run `npm run build && npm run start` and verify production build works
- Install PWA on desktop and verify it launches standalone
- Run `npx vitest run` to verify test infrastructure

## Phase 2: Foundation - Core Type Definitions

### **MS-002:** Core Type Definitions & Zod Schemas (Week 1)

**Goal:** Define TypeScript interfaces and Zod validation schemas as single source of truth for all data models

**Success Criteria:**

- SC-006: `npx tsc --noEmit` returns zero errors across all type files
- SC-007: All Zod schemas validate sample data correctly and reject invalid data
- SC-008: API types inferred from Zod schemas with no manual duplication
- SC-009: All types accessible via single barrel import from `src/types/index.ts`

**Tasks:**

- [ ] T011 [P] [SA]: Define UserProfile type with tier, usage, settings, and Stripe fields (Tech Specs Section 3)
  - **DoD:** Interface exported, includes all fields from Tech Specs Section 3, compiles without errors
- [ ] T012 [P] [SA]: Define Note type with content (JSONContent), category, metadata, syncStatus
  - **DoD:** Interface exported, `JSONContent` typed correctly, all metadata fields present
- [ ] T013 [P] [SA]: Define Snapshot type for sync conflict recovery
  - **DoD:** Interface exported, includes `snapshotType`, `noteId`, `content`, `createdAt`
- [ ] T014 [P] [SA]: Define category enum: pharmacology, med-surg, pediatrics, ob, mental-health, clinical-rotation, other
  - **DoD:** Enum/union type exported, all 7 categories present, used by Note type
- [ ] T015: Create Zod schemas for Note validation (noteSchema, noteContentSchema) with runtime validation
  - **DoD:** Schemas validate valid notes, reject invalid ones, inferred types match Note interface
- [ ] T016: Create Zod schemas for User validation (userSchema, userPreferencesSchema)
  - **DoD:** Schemas validate valid users, reject invalid fields, inferred types match UserProfile
- [ ] T017: Define API request/response types with Zod schemas (autocompleteRequestSchema, autocompleteResponseSchema)
  - **DoD:** Request/response schemas defined, types inferred via `z.infer<>`
- [ ] T018 [SA]: Define AI types (AutocompleteRequest, AutocompleteResponse, suggestion source)
  - **DoD:** Interfaces exported, `source` field typed as `"ai" | "dictionary"`
- [ ] T019 [SA]: Define Stripe types (checkout session, webhook events, subscription status)
  - **DoD:** Interfaces cover checkout, webhook payload, and subscription lifecycle states
- [ ] T020 [SA]: Create shared utility types (Result<T,E>, AsyncState<T>, APIResponse<T>)
  - **DoD:** Generic types exported, used in at least one API type definition
- [ ] T021 [SA]: Define error types (AppError, ValidationError, NetworkError, SyncError)
  - **DoD:** Error classes/types exported, each includes `code`, `message`, and optional `cause`
- [ ] T022: Create type-safe API client interface with inferred types from Zod schemas
  - **DoD:** API client interface uses Zod-inferred types for all request/response pairs
- [ ] T023: Create barrel exports in src/types/index.ts
  - **DoD:** All types importable from `src/types`, no circular dependencies

**Acceptance Criteria:**

- [ ] All core types defined with proper TypeScript interfaces
- [ ] Zod schemas implemented for all critical data structures
- [ ] API types inferred from Zod schemas (no duplication)
- [ ] Type exports organized in barrel files
- [ ] No TypeScript compilation errors

**Verification:**

- Run `npx tsc --noEmit` and confirm zero errors
- Verify all types are exported from src/types/index.ts
- Test Zod schema validation with sample data

## Phase 3: Foundation - Mock Infrastructure

### **MS-003:** Mock Infrastructure & API Layer (Week 1)

**Goal:** Create comprehensive mock system for all APIs with realistic delays, error states, and edge cases

**Success Criteria:**

- SC-010: MSW intercepts 100% of API calls during development with no unhandled requests
- SC-011: All mock responses pass Zod schema validation
- SC-012: Error states triggerable programmatically for all endpoints
- SC-013: Feature flag toggle switches mock/real APIs without code changes

**Tasks:**

- [ ] T024 [P]: Set up MSW (Mock Service Worker) for API mocking in browser and tests
  - **DoD:** MSW starts in browser dev mode, intercepts at least one test endpoint
- [ ] T025 [P]: Create mock data generators using Zod schemas (faker integration)
  - **DoD:** Generators produce valid data that passes Zod validation for all schemas
- [ ] T026 [P]: Create mock user data with different tiers (free, pro) and quota states
  - **DoD:** At least 2 mock users (free + pro) with different quota levels
- [ ] T027 [P]: Create mock notes collection (10-20 notes across all categories)
  - **DoD:** 10-20 notes generated, covering all 7 categories, valid against noteSchema
- [ ] T028: Create mock AI autocomplete handler with realistic 150-200ms delays
  - **DoD:** Handler returns suggestions after 150-200ms delay, response matches autocompleteResponseSchema
- [ ] T029: Create mock dictionary fallback with 5,000+ nursing terms sample
  - **DoD:** Dictionary JSON file loaded, prefix search returns results for common nursing terms
- [ ] T030: Create mock Stripe checkout/webhook handlers
  - **DoD:** Checkout handler returns session URL, webhook handler processes all 4 event types
- [ ] T031: Create mock auth handlers (login, signup, logout, password reset)
  - **DoD:** All 4 auth flows return appropriate responses, invalid credentials return errors
- [ ] T032: Implement error simulation (network errors, quota exceeded, validation failures)
  - **DoD:** Each error type triggerable via query param or header, returns correct HTTP status
- [ ] T033: Create feature flag system for toggling mock vs real APIs
  - **DoD:** Flags stored in env vars, toggle works at runtime without restart
- [ ] T034: Create mock sync status simulation (online, offline, syncing, conflict)
  - **DoD:** All 4 sync states simulatable, state transitions emit events
- [ ] T035: Document mock API contracts in src/mocks/README.md
  - **DoD:** README lists all endpoints, request/response shapes, and error simulation instructions
- [ ] T035A [P]: Create migration versioning strategy for PostgreSQL schema changes
  - **DoD:** Migration naming convention documented, initial migration file created

**Acceptance Criteria:**

- [ ] MSW intercepts all API calls in development mode
- [ ] Mock responses match Zod schema definitions exactly
- [ ] Error states can be triggered programmatically
- [ ] Feature flags toggle between mock and real APIs
- [ ] Realistic delays simulate production latency

**Verification:**

- Start dev server and verify network tab shows mocked responses
- Trigger error states and verify UI handles them correctly
- Toggle feature flags and verify API switching works

## Phase 4: Core UI with Mocked Backends (Parallel)

All three milestones below can run in parallel after Phase 3 completion (MS-004, MS-005, MS-006):

### **MS-004:** Authentication UI (Week 1-2)

**Goal:** Complete authentication flow with form validation, error handling, and session management (all using mocks)

**Success Criteria:**

- SC-014: All auth flows (signup, login, reset) complete end-to-end with mock backend
- SC-015: Form validation rejects all invalid inputs with user-visible error messages
- SC-016: Protected routes redirect to login within 100ms for unauthenticated users
- SC-017: Session persists across page refreshes using Zustand + mock storage

**Tasks:**

- [ ] T036 [P]: Build Login page UI with form validation (8+ chars, 1 upper, 1 lower, 1 number, 1 special)
  - **DoD:** Login form renders, validates all password rules, displays inline error messages
- [ ] T037 [P]: Build Sign Up page UI with password requirements checklist (UX Section 4.1)
  - **DoD:** Signup form renders with live password checklist, all rules visually indicated
- [ ] T038 [P]: Build Password Reset page and email flow UI
  - **DoD:** Reset form accepts email, shows confirmation message, handles invalid email
- [ ] T039: Create useAuth hook with mock authentication state
  - **DoD:** Hook returns `user`, `isLoading`, `login`, `signup`, `logout`, `resetPassword`
- [ ] T040: Create auth middleware for protected routes (middleware.ts) using mock session
  - **DoD:** Unauthenticated requests to protected routes redirect to `/login`
- [ ] T041: Implement session state management with Zustand
  - **DoD:** Auth state persists in Zustand store, accessible across components
- [ ] T042: Add session expiry handling UI (prompt re-authentication, preserve local data)
  - **DoD:** Expired session shows re-auth modal, local data preserved after re-login
- [ ] T043: Create AuthProvider context with mock user data
  - **DoD:** Provider wraps app, children access user via context, mock data loads on mount
- [ ] T044: Add loading states and error handling for all auth flows
  - **DoD:** Spinner shows during API calls, error messages display on failure
- [ ] T045: Write unit tests for auth forms and validation
  - **DoD:** Tests cover valid/invalid inputs for all 3 forms, all tests pass

**Acceptance Criteria:**

- [ ] User can sign up with mock email/password meeting requirements (FR-022)
- [ ] User can log in and maintain mock session across browser sessions (FR-023)
- [ ] User can reset password via mock email flow (FR-024)
- [ ] Protected routes redirect unauthenticated users to login
- [ ] All form validations work with proper error messages

**Verification:**

- Test signup flow with valid/invalid inputs
- Test login with mock credentials
- Verify protected route redirection
- Test password reset flow

### **MS-005:** Tiptap Editor Integration (Week 2)

**Goal:** Rich text editor with auto-save, formatting toolbar, and distraction-free UI (local storage only)

**Success Criteria:**

- SC-018: Editor loads without SSR errors on first render
- SC-019: All 5 formatting options (bold, italic, heading, list, link) apply and persist
- SC-020: Editor handles 50,000 characters without visible lag or dropped keystrokes
- SC-021: All toolbar status indicators (save, sync, quota) update correctly with mock data

**Tasks:**

- [ ] T046: Install Tiptap 3.4 dependencies (@tiptap/react, @tiptap/starter-kit, extensions)
  - **DoD:** All Tiptap packages in `package.json`, imports resolve without errors
- [ ] T047: Create base TiptapEditor component with dynamic import (SSR disabled)
  - **DoD:** Editor renders client-side only, no SSR hydration errors in console
- [ ] T048: Implement editor placeholder: "Start typing your notes... Type / for commands"
  - **DoD:** Placeholder visible when editor empty, disappears on first keystroke
- [ ] T049: Build editor toolbar with formatting buttons (Bold, Italic, Heading, List, Link) per UX Section 4.4
  - **DoD:** All 5 buttons render, toggle active state, apply formatting to selected text
- [ ] T050: Create inline title editing in toolbar
  - **DoD:** Title field editable in toolbar, changes reflect in note metadata
- [ ] T051: Implement category dropdown in toolbar (7 predefined categories)
  - **DoD:** Dropdown lists all 7 categories, selection updates note category
- [ ] T052: Add AI quota badge component showing remaining requests or "Dictionary" mode (mock data)
  - **DoD:** Badge shows remaining count or "Dictionary" label, updates from mock state
- [ ] T053: Add sync status indicator (Synced/Offline/Syncing...) with color states (mock states)
  - **DoD:** Indicator shows correct label and color for all 3 states
- [ ] T054: Add save status indicator ("Saved just now" -> "Saved 1m ago" -> "Saved 5m ago")
  - **DoD:** Timestamp updates at correct intervals, resets on new save
- [ ] T055: Implement editor max-width 900px centered layout with responsive padding
  - **DoD:** Editor centered at 900px max, padding adjusts at mobile breakpoint
- [ ] T056: Create EditorSkeleton loading component for dynamic import
  - **DoD:** Skeleton displays during editor load, matches editor layout dimensions
- [ ] T057: Write unit tests for editor toolbar and status indicators
  - **DoD:** Tests cover all toolbar buttons and all status indicator states, all pass
- [ ] T057A [P]: Implement XSS sanitization layer for Tiptap content using DOMPurify
  - **DoD:** DOMPurify sanitizes HTML on paste and load, script tags stripped
- [ ] T057B [P]: Handle large paste operations (>10KB) with progress indicator
  - **DoD:** Paste >10KB shows progress bar, editor remains responsive during processing

**Acceptance Criteria:**

- [ ] Editor loads without SSR errors
- [ ] All formatting options work (bold, italic, headings, lists, links)
- [ ] Toolbar displays all status indicators correctly
- [ ] Editor handles up to 50,000 characters without performance degradation (NFR)

**Verification:**

- Paste 50,000 character document and verify no lag
- Test all formatting options and verify they apply correctly
- Verify toolbar is responsive on mobile (overflow menu)

### **MS-006:** Note CRUD UI (Week 2)

**Goal:** Complete note library with create, read, update, delete functionality (mock data)

**Success Criteria:**

- SC-022: All CRUD operations (create, read, update, delete) work end-to-end with mock data
- SC-023: Note library renders 20+ notes without layout issues
- SC-024: Empty state displays correctly when no notes exist
- SC-025: Context menu actions (rename, duplicate, export, delete) all functional

**Tasks:**

- [ ] T088: Create Notes Library page layout with header, filter bar, note cards
  - **DoD:** Page renders with header, filter bar, and note card grid from mock data
- [ ] T089: Build NoteCard component with title, preview, category badge, date, sync status
  - **DoD:** Card displays all 5 data points, truncates preview at 2 lines
- [ ] T090: Implement "New Note" button opening blank editor (FR-006)
  - **DoD:** Button click navigates to editor with empty content, cursor focused
- [ ] T091: Implement note list with grid/list view toggle (FR-007)
  - **DoD:** Toggle switches between grid and list layouts, preference persists
- [ ] T092: Implement click-to-open note in editor (FR-008)
  - **DoD:** Clicking note card opens editor with note content loaded
- [ ] T093: Add inline note title renaming (FR-010)
  - **DoD:** Double-click title enters edit mode, Enter saves, Escape cancels
- [ ] T094: Implement note duplication (FR-011)
  - **DoD:** Duplicate creates new note with "[Title] (Copy)" name, same content
- [ ] T095: Add context menu (right-click/long-press) with Rename, Duplicate, Export, Delete
  - **DoD:** Context menu appears on right-click/long-press with all 4 options
- [ ] T096: Implement soft delete (isDeleted flag, deletedAt timestamp) (FR-009)
  - **DoD:** Delete sets `isDeleted: true` and `deletedAt`, note hidden from library
- [ ] T097 [SA]: Create empty state with illustration and "Create Note" CTA (UX Section 4.3)
  - **DoD:** Empty state renders when no notes, CTA button creates new note
- [ ] T098: Write unit tests for note card and library components
  - **DoD:** Tests cover card rendering, CRUD actions, and empty state, all pass
- [ ] T098A [P]: Add analytics tracking for slash command usage (measure PRD Goal #3)
  - **DoD:** Analytics events fire on slash command use, event includes command type

**Acceptance Criteria:**

- [ ] User can create new notes with cursor ready for input (FR-006)
- [ ] User can view notes in library with previews (FR-007)
- [ ] User can edit existing notes by clicking them (FR-008)
- [ ] User can rename, duplicate, and delete notes
- [ ] Empty state displays when no notes exist

**Verification:**

- Create 10 notes with different categories
- Rename a note and verify title updates in library
- Delete a note and verify it disappears from main library

## Phase 5: Editor Extensions (Parallel)

All three milestones below can run in parallel after MS-005 (Tiptap Editor) completion (MS-007, MS-008, MS-009):

### **MS-007:** Auto-Save & Local Storage (Week 2)

**Goal:** Implement 30-second auto-save to localStorage/IndexedDB with visual feedback (mock sync layer)

**Success Criteria:**

- SC-026: Notes persist across browser close/reopen without data loss
- SC-027: Save operations complete within 500ms measured via Performance API
- SC-028: Save indicator transitions through all states (idle, saving, saved) correctly
- SC-029: Version number increments on each save and is queryable

**Tasks:**

- [ ] T058: Create local storage abstraction layer (PowerSync SQLite interface)
  - **DoD:** Abstraction exposes `get`, `set`, `delete`, `list` methods, backed by localStorage/IndexedDB
- [ ] T059: Implement note CRUD operations on local storage
  - **DoD:** Create, read, update, delete operations work through abstraction layer
- [ ] T060: Create useAutoSave hook with 30-second debounced save
  - **DoD:** Hook triggers save 30s after last edit, cancels pending save on new edit
- [ ] T061: Implement save indicator state machine (idle -> saving -> saved)
  - **DoD:** State transitions correctly, "saved" state shows timestamp
- [ ] T062: Create useLocalNotes hook for CRUD operations
  - **DoD:** Hook returns `notes`, `createNote`, `updateNote`, `deleteNote` with loading states
- [ ] T063: Implement note version tracking (version number increments on each save)
  - **DoD:** Version field increments on save, queryable via hook
- [ ] T064: Add error handling for failed local saves with retry
  - **DoD:** Failed saves retry up to 3 times, error surfaced to UI after exhaustion
- [ ] T065: Create mock sync queue that simulates PowerSync behavior
  - **DoD:** Queue accepts operations, simulates sync delay, reports sync status
- [ ] T066: Write unit tests for auto-save and local storage hooks
  - **DoD:** Tests cover save timing, retry logic, version increment, all pass

**Acceptance Criteria:**

- [ ] Notes auto-save every 30 seconds without blocking editor (FR-016)
- [ ] Save indicator shows "Saved" with timestamp after successful save
- [ ] Local saves complete within 500ms (NFR)
- [ ] App preserves changes if closed without manual save

**Verification:**

- Edit note, wait 30 seconds, close browser, reopen and verify changes preserved
- Time save operation and confirm <500ms
- Test save while "offline" (must complete within 500ms locally)

### **MS-008:** Slash Command System (Week 2)

**Goal:** Implement /template and /formula slash commands with floating menu

**Success Criteria:**

- SC-030: "/" keystroke opens command menu within 100ms
- SC-031: All 5 templates and 6 formulas insert correctly with proper structure
- SC-032: Keyboard navigation (arrows, Enter, Escape) works without mouse
- SC-033: Mobile bottom sheet renders at full width with 52px touch targets

**Tasks:**

- [ ] T067: Create Tiptap slash command extension with "/" trigger
  - **DoD:** Typing "/" in editor triggers extension, fires menu open event
- [ ] T068: Build SlashCommandMenu floating component (320px width, 400px max-height)
  - **DoD:** Menu positions below cursor, respects width/height constraints, scrollable
- [ ] T069: Implement menu keyboard navigation (arrow keys, Enter, Escape)
  - **DoD:** Arrow keys move selection, Enter inserts, Escape closes menu
- [ ] T070 [SA]: Create template content definitions (Care Plan, Medication Card, SOAP Note, Head-to-Toe, Pathophysiology)
  - **DoD:** All 5 templates defined as structured content with labeled fields
- [ ] T071 [SA]: Create formula content definitions with normal ranges (MAP, BMI, IV Drip, Dosage, GCS, Fluid Deficit)
  - **DoD:** All 6 formulas defined with formula text and normal range values
- [ ] T072: Implement template insertion with cursor positioning in first field
  - **DoD:** Template inserts into editor, cursor placed in first editable field
- [ ] T073: Implement formula insertion with formatted structure
  - **DoD:** Formula inserts with label, formula, and normal range formatted correctly
- [ ] T074: Add search/filter as user types after "/"
  - **DoD:** Menu filters options as user types, shows "No results" when nothing matches
- [ ] T075: Style menu items per UX Section 4.5 (44px height, hover states)
  - **DoD:** Items are 44px height, show hover/active states per UX spec
- [ ] T076: Add mobile adaptation (full-width bottom sheet, 52px touch targets)
  - **DoD:** On mobile viewport, menu renders as bottom sheet with 52px item height
- [ ] T077: Write unit tests for slash command parsing and insertion
  - **DoD:** Tests cover trigger detection, filtering, insertion, and keyboard nav, all pass

**Acceptance Criteria:**

- [ ] Typing "/" opens command menu (FR-003)
- [ ] /template offers 5 template options (FR-004)
- [ ] /formula offers 6 formula options with normal ranges (FR-005)
- [ ] Selected template inserts with cursor in first field
- [ ] Menu closes on Escape or clicking outside

**Verification:**

- Type "/template" and verify all 5 options appear
- Insert Care Plan and verify cursor is in Nursing Diagnosis section
- Insert MAP formula and verify normal range "70-100 mmHg" is included

### **MS-009:** AI Autocomplete UI (Week 2)

**Goal:** Implement autocomplete UI with mock AI responses and dictionary fallback

**Success Criteria:**

- SC-034: Suggestions appear within 200ms of last keystroke with mock backend
- SC-035: Dictionary fallback activates seamlessly when mock API simulates offline/quota exceeded
- SC-036: Source badge correctly distinguishes "AI" vs "Dictionary" suggestions
- SC-037: Quota badge decrements after each mock AI request

**Tasks:**

- [ ] T078: Create AutocompletePopup component (300px width, 5 suggestions max)
  - **DoD:** Popup renders at cursor position, shows up to 5 suggestions, scrollable if needed
- [ ] T079: Create useAutocomplete hook with mock AI/dictionary source detection
  - **DoD:** Hook returns `suggestions`, `source`, `isLoading`, switches source based on mock state
- [ ] T080: Load sample nursing dictionary (500 terms for development)
  - **DoD:** Dictionary JSON loaded into memory, searchable via prefix match
- [ ] T081: Implement dictionary prefix matching for offline/over-quota fallback
  - **DoD:** Prefix search returns sorted matches within 50ms for 500 terms
- [ ] T082: Add suggestion source badges ("AI" blue / "Dictionary" gray)
  - **DoD:** Badge renders with correct color and label based on suggestion source
- [ ] T083: Implement Tab/Enter to accept suggestion
  - **DoD:** Tab or Enter inserts selected suggestion into editor, popup closes
- [ ] T084: Add debouncing (150ms) for autocomplete requests
  - **DoD:** Requests fire only after 150ms of no typing, verified via test
- [ ] T085: Handle mock API timeout with dictionary fallback
  - **DoD:** Timeout >500ms triggers dictionary fallback, no UI error shown
- [ ] T086: Create quota tracking UI with mock data
  - **DoD:** Quota badge shows remaining count, updates on each mock AI request
- [ ] T087: Write unit tests for autocomplete hook and popup
  - **DoD:** Tests cover AI mode, dictionary mode, debounce, and fallback, all pass

**Acceptance Criteria:**

- [ ] Mock AI suggestions appear within 200ms of typing (FR-001)
- [ ] Dictionary fallback works when simulating offline (FR-002)
- [ ] Dictionary fallback works when simulating quota exceeded (FR-002)
- [ ] Quota badge updates after each mock AI request (FR-027)

**Verification:**

- Type "met" and verify mock suggestions appear
- Simulate quota exceeded and verify seamless switch to dictionary mode
- Simulate offline and verify dictionary autocomplete still works

## Phase 6: Note Organization & Management (Parallel)

All two milestones below can run in parallel after MS-006 T088-T091 completion:

### **MS-010:** Note Organization UI (Week 2-3)

**Goal:** Implement category filtering, search, and sorting with mock data

**Success Criteria:**

- SC-038: Category filter isolates notes to selected category with zero false positives
- SC-039: Search returns results within 300ms for 1,000 mock notes
- SC-040: Sort order updates immediately on option change
- SC-041: Filter/sort preferences survive browser restart

**Tasks:**

- [ ] T099: Implement category filter dropdown/chips (7 categories) (FR-012)
  - **DoD:** Filter UI shows all 7 categories, selecting one filters note list
- [ ] T100: Implement sort options (date created, last modified, alphabetical) (FR-013)
  - **DoD:** All 3 sort modes work correctly, active sort visually indicated
- [ ] T101: Create useNoteSearch hook with real-time search on title and content (FR-014)
  - **DoD:** Hook returns filtered notes matching query, searches both title and content
- [ ] T102: Build search input with debounced query (300ms)
  - **DoD:** Input fires search after 300ms pause, shows clear button when populated
- [ ] T103: Add "No results" empty state for search (UX Section 10)
  - **DoD:** Empty state renders with message when search returns zero results
- [ ] T104: Add "No notes in [category]" empty state for category filter
  - **DoD:** Empty state renders with category name when filter returns zero results
- [ ] T105: Persist filter/sort preferences in localStorage
  - **DoD:** Preferences load from localStorage on mount, save on change
- [ ] T106: Write unit tests for search and filter logic
  - **DoD:** Tests cover filtering, sorting, search, and persistence, all pass

**Acceptance Criteria:**

- [ ] Category filter shows only notes in selected category
- [ ] Search returns results within 300ms for up to 1,000 notes (NFR)
- [ ] Sort options work correctly for all three modes
- [ ] Preferences persist across sessions

**Verification:**

- Create notes in multiple categories, filter by each
- Search for partial term in note content, verify results appear
- Time search with 100 mock notes, confirm <300ms

### **MS-011:** Trash System UI (Week 3)

**Goal:** Implement trash folder with 30-day recovery and permanent deletion UI

**Success Criteria:**

- SC-042: Deleted notes appear in trash within 1 second of deletion
- SC-043: Restored notes return to library with all content and metadata intact
- SC-044: Permanent delete removes note from all storage with no recovery possible
- SC-045: "Empty Trash" bulk deletes all trash items with single confirmation

**Tasks:**

- [ ] T107: Create Trash page with header showing 30-day warning (UX Section 4.7)
  - **DoD:** Page renders with header, 30-day warning banner, and trash note list
- [ ] T108: Build TrashNoteCard with "Deleted X days ago" label
  - **DoD:** Card shows note info plus relative deletion timestamp
- [ ] T109: Implement "Restore" action to un-delete note (FR-015)
  - **DoD:** Restore clears `isDeleted` flag, note reappears in library
- [ ] T110: Implement "Delete Forever" action with confirmation dialog
  - **DoD:** Confirmation dialog appears, confirm permanently removes note
- [ ] T111: Add "Empty Trash" button with bulk permanent delete (FR-015)
  - **DoD:** Button shows count, confirmation dialog, all trash items deleted on confirm
- [ ] T112 [SA]: Create trash empty state with empty bin illustration
  - **DoD:** Empty state renders with illustration when trash is empty
- [ ] T113: Update notes library to exclude deleted notes from view
  - **DoD:** Library query filters out `isDeleted: true` notes
- [ ] T114: Write unit tests for trash operations
  - **DoD:** Tests cover delete, restore, permanent delete, and empty trash, all pass

**Acceptance Criteria:**

- [ ] Deleted notes appear in trash folder
- [ ] User can restore notes within 30 days (FR-009)
- [ ] User can permanently delete from trash (FR-015)
- [ ] Restored notes appear back in main library

**Verification:**

- Delete a note, navigate to trash, verify it appears
- Restore a note, verify it returns to library with content intact
- Permanently delete a note, verify it no longer exists

## Phase 7: Settings, Onboarding & Export (Parallel)

Three milestones run after Phase 4 completion. _Note: MS-013 (Onboarding) requires MS-008 (Slash Commands) for interactive demo:_

### **MS-012:** Settings & Subscription UI (Week 3)

**Goal:** Complete settings page with mock subscription and tier management

**Success Criteria:**

- SC-046: All 4 settings sections (Account, Subscription, Preferences, Data) render correctly
- SC-047: Theme toggle applies changes across all pages within 100ms
- SC-048: Quota bar accurately reflects mock usage data
- SC-049: Upgrade modal displays feature comparison with correct tier details

**Tasks:**

- [ ] T115: Create Settings page layout with sidebar navigation (desktop) and tabs (mobile)
  - **DoD:** Layout renders sidebar on desktop, tabs on mobile, all sections navigable
- [ ] T116: Build Account section (email, display name, change password link)
  - **DoD:** Section displays user info from mock data, change password link navigates
- [ ] T117: Build Subscription section (tier badge, quota bar, upgrade/manage buttons) with mock data
  - **DoD:** Tier badge shows current tier, quota bar fills proportionally, buttons render
- [ ] T118: Build Preferences section (theme toggle: Light/Dark/System, auto-save toggle)
  - **DoD:** Theme toggle has 3 options, auto-save toggle functional
- [ ] T119: Build Data section (export all, delete account with confirmation)
  - **DoD:** Export button triggers download, delete shows confirmation dialog
- [ ] T120: Implement theme switching with system preference detection
  - **DoD:** Theme applies immediately, "System" option follows OS preference
- [ ] T121: Persist theme preference to localStorage
  - **DoD:** Theme preference loads on app start, survives browser restart
- [ ] T122: Build Upgrade Modal component with feature comparison table (UX Section 4.9)
  - **DoD:** Modal shows Free vs Pro comparison, CTA button present
- [ ] T123: Mock Stripe checkout flow (redirect simulation)
  - **DoD:** Upgrade button simulates redirect, returns with mock Pro tier
- [ ] T124: Write unit tests for settings components
  - **DoD:** Tests cover all 4 sections and theme switching, all pass

**Acceptance Criteria:**

- [ ] All settings sections display correctly
- [ ] Theme changes apply immediately across app
- [ ] Quota usage bar shows mock data accurately
- [ ] Upgrade modal displays correctly

**Verification:**

- Toggle theme and verify all pages update
- Check quota bar reflects mock usage
- Test upgrade modal display

### **MS-013:** Onboarding Flow UI (Week 3)

**Goal:** Implement 2-screen onboarding introducing AI autocomplete and slash commands

**Success Criteria:**

- SC-050: Onboarding triggers on first login and never reappears after completion
- SC-051: Interactive demo successfully detects /template insertion
- SC-052: Slash command hints display until user reaches 5 uses
- SC-053: Keyboard cheatsheet accessible via "?" key from any page

**Tasks:**

- [ ] T125: Create onboarding route (/onboarding)
  - **DoD:** Route renders, redirects authenticated non-onboarded users to it
- [ ] T126: Build Screen 1: Welcome with feature cards (AI Autocomplete, Slash Commands) (UX Section 4.2)
  - **DoD:** Screen shows 2 feature cards with icons and descriptions, "Next" button
- [ ] T127: Build Screen 2: Interactive demo with mini-editor for /template
  - **DoD:** Mini-editor renders, detects "/" input, shows slash command menu
- [ ] T128: Implement demo celebration animation on successful template insertion
  - **DoD:** Animation plays after user inserts a template, "Start creating" button enables
- [ ] T129: Track onboarding completion in localStorage (mock user document)
  - **DoD:** Completion flag set in localStorage, onboarding skipped on subsequent visits
- [ ] T130: Add in-editor tooltip showing "/" trigger until user uses 5+ times
  - **DoD:** Tooltip appears near editor, tracks usage count, hides after 5 uses
- [ ] T131: Implement keyboard shortcut cheatsheet (accessible via "?" key)
  - **DoD:** "?" key opens modal listing all shortcuts, Escape closes it
- [ ] T132: Create persistent UI hint near editor for available commands
  - **DoD:** Hint renders below editor, lists key commands, dismissible
- [ ] T133: Write unit tests for onboarding flow
  - **DoD:** Tests cover both screens, completion tracking, and hint logic, all pass

**Acceptance Criteria:**

- [ ] New users see onboarding after signup (User Story 1)
- [ ] Interactive demo lets user try /template before proceeding
- [ ] Onboarding only shows once per user
- [ ] Slash command hints persist until adoption threshold reached

**Verification:**

- Create new account, verify onboarding appears
- Complete demo interaction, verify "Start creating" button enables
- Log in again, verify onboarding does not reappear

### **MS-014:** Export Functionality (Week 3)

**Goal:** Implement note export to Markdown, Plain Text, and bulk ZIP

**Success Criteria:**

- SC-054: Exported Markdown opens correctly in external Markdown editors
- SC-055: Plain text export preserves content structure without markup
- SC-056: Bulk ZIP organizes notes into category-named folders
- SC-057: Export handles notes with special characters and unicode correctly

**Tasks:**

- [ ] T134 [SA]: Implement Tiptap content to Markdown converter
  - **DoD:** Converter handles headings, bold, italic, lists, links, outputs valid Markdown
- [ ] T135 [SA]: Implement Tiptap content to Plain Text converter
  - **DoD:** Converter strips all formatting, preserves text content and line breaks
- [ ] T136: Add export menu options (Markdown, Plain Text) in note context menu (FR-033)
  - **DoD:** Context menu shows both export options, each triggers correct converter
- [ ] T137: Create download trigger for single note export
  - **DoD:** Browser download initiates with correct filename (`[title].md` or `[title].txt`)
- [ ] T138: Implement bulk export to ZIP with notes organized by category (FR-034)
  - **DoD:** ZIP file contains category folders, each with exported notes
- [ ] T139: Add "Export all notes" button in Settings (UX Section 4.8)
  - **DoD:** Button in Data section triggers bulk ZIP export
- [ ] T140: Write unit tests for export converters
  - **DoD:** Tests cover all formatting types, edge cases, and ZIP structure, all pass

**Acceptance Criteria:**

- [ ] User can export individual notes to .md and .txt (FR-033)
- [ ] User can bulk export all notes as ZIP (FR-034)
- [ ] Exported Markdown preserves formatting
- [ ] ZIP organized by category folders

**Verification:**

- Export note with headings, lists, bold text to Markdown
- Open in Markdown editor and verify formatting preserved
- Bulk export 5 notes in different categories, verify ZIP structure

## Phase 8: Responsive Design & Accessibility (Parallel)

All two milestones below can run in parallel after Phase 7 completion:

### **MS-015:** Responsive Design & Dark Mode (Week 3)

**Goal:** Ensure responsive design across all breakpoints and complete dark mode support

**Success Criteria:**

- SC-058: All pages functional at 320px, 640px, 1024px, and 2560px widths
- SC-059: Dark mode applies to 100% of components with no unstyled elements
- SC-060: All touch targets measure 44x44px minimum on mobile viewports
- SC-061: Animations respect `prefers-reduced-motion` system setting

**Tasks:**

- [ ] T141 [P]: Implement responsive breakpoints (Mobile <640px, Tablet 640-1023px, Desktop 1024px+)
  - **DoD:** Breakpoints defined in Tailwind config, at least one component adapts per breakpoint
- [ ] T142 [P] [SA]: Implement dark mode color palette (UX Section 2)
  - **DoD:** All color tokens have dark mode variants, toggle switches palette globally
- [ ] T143: Adapt navbar for mobile (hamburger menu, condensed logo)
  - **DoD:** Navbar collapses to hamburger on mobile, menu opens/closes correctly
- [ ] T144: Adapt editor toolbar for mobile (formatting in overflow menu)
  - **DoD:** Toolbar shows primary actions, overflow menu contains secondary actions
- [ ] T145: Adapt notes library for mobile (search expands on tap, filters in bottom sheet)
  - **DoD:** Search icon expands to full-width input, filters open in bottom sheet
- [ ] T146: Adapt slash command menu for mobile (full-width bottom sheet, 52px items)
  - **DoD:** Menu renders as bottom sheet on mobile, items are 52px height
- [ ] T147: Adapt settings for mobile (tab navigation instead of sidebar)
  - **DoD:** Settings uses horizontal tabs on mobile instead of sidebar
- [ ] T148: Test and fix all pages at 320px, 640px, 1024px, 2560px widths
  - **DoD:** No layout overflow, truncation, or broken alignment at any breakpoint
- [ ] T149: Implement prefers-reduced-motion support (UX Section 9)
  - **DoD:** All animations disabled when `prefers-reduced-motion: reduce` is set
- [ ] T150: Write visual regression tests for responsive layouts
  - **DoD:** Playwright screenshots captured at all 4 breakpoints, baseline established

**Acceptance Criteria:**

- [ ] App usable on screens from 320px to 2560px (NFR)
- [ ] Dark mode complete with all components styled
- [ ] Mobile touch targets minimum 44x44px
- [ ] Reduced motion respected when enabled

**Verification:**

- Test on iPhone SE (320px) and 4K monitor (2560px)
- Toggle dark mode and verify all components styled correctly
- Enable reduced motion in OS, verify animations disabled

### **MS-016:** Accessibility (Week 3)

**Goal:** Achieve WCAG AA compliance with keyboard navigation and screen reader support

**Success Criteria:**

- SC-062: Full app navigable using keyboard only without mouse
- SC-063: VoiceOver and NVDA announce all content and state changes correctly
- SC-064: All text meets 4.5:1 contrast ratio measured via automated tool
- SC-065: Lighthouse accessibility audit scores 90+

**Tasks:**

- [ ] T151 [P]: Add ARIA labels to all interactive elements
  - **DoD:** Every button, link, input, and toggle has descriptive `aria-label` or `aria-labelledby`
- [ ] T152 [P]: Implement logical tab order across all pages
  - **DoD:** Tab key moves focus in visual reading order, no focus traps
- [ ] T153: Add visible focus indicators to all focusable elements
  - **DoD:** Focus ring visible on keyboard navigation, meets 3:1 contrast
- [ ] T154: Ensure 4.5:1 minimum contrast ratio for all text
  - **DoD:** All text/background combinations verified via contrast checker tool
- [ ] T155: Add screen reader announcements for status changes (aria-live)
  - **DoD:** Save status, sync status, and error messages announced via `aria-live`
- [ ] T156: Make slash command menu accessible (ARIA announcements, keyboard nav)
  - **DoD:** Menu announces open/close, selected item, and insertion via `aria-live`
- [ ] T157: Test with VoiceOver (macOS/iOS) and NVDA (Windows)
  - **DoD:** Complete user flow tested, all content announced, no silent interactions
- [ ] T158: Add alt text to all images and icons
  - **DoD:** All `<img>` tags have `alt` text, decorative icons have `aria-hidden="true"`
- [ ] T159: Test at 200% browser zoom and fix any layout issues
  - **DoD:** No content clipped, overlapped, or inaccessible at 200% zoom
- [ ] T160: Run Lighthouse accessibility audit
  - **DoD:** Lighthouse accessibility score 90+ on all pages

**Acceptance Criteria:**

- [ ] All interactive elements keyboard accessible
- [ ] Screen readers announce all content correctly
- [ ] Contrast ratios meet WCAG AA (4.5:1)
- [ ] 200% zoom works without layout breaking (NFR)

**Verification:**

- Navigate entire app using only keyboard
- Complete user flow with VoiceOver enabled
- Run Lighthouse accessibility audit (target 90+)

## Phase 9: Backend Integration with Feature Flags (Parallel)

Both milestones below can run in parallel after Phase 8 completion:

### **MS-017:** Supabase Setup (Week 3)

**Goal:** Configure Supabase project with Auth, PostgreSQL, and Row Level Security

**Success Criteria:**

- SC-066: All 3 tables (users, notes, snapshots) created with correct column types
- SC-067: RLS policies block cross-user data access in direct SQL queries
- SC-068: Feature flag toggles mock/real auth without code deployment
- SC-069: Database indexes cover all query patterns from Tech Specs Section 3

**Tasks:**

- [ ] T161 [P]: Create Supabase project and configure environment variables
  - **DoD:** Project created, env vars set in `.env.local`, Supabase dashboard accessible
- [ ] T162: Configure Supabase Client SDK (client-side initialization)
  - **DoD:** Client SDK initializes, `supabase.auth.getSession()` returns without error
- [ ] T163: Configure Supabase Admin SDK (server-side for API routes)
  - **DoD:** Admin SDK initializes in API route, can query tables with service role
- [ ] T164: Create PostgreSQL tables (users, notes, snapshots) per Tech Specs Section 3
  - **DoD:** All 3 tables created with columns matching Tech Specs, migrations versioned
- [ ] T165: Implement Row Level Security policies per Tech Specs Section 4
  - **DoD:** RLS enabled on all tables, policies restrict access to `auth.uid()` owner
- [ ] T166: Create database indexes for performance
  - **DoD:** Indexes on `userId`, `category`, `updatedAt`, `isDeleted` columns
- [ ] T167: Test RLS policies prevent cross-user data access
  - **DoD:** Test confirms user A cannot read/write user B's data via direct query
- [ ] T168: Create feature flag to toggle mock vs real Supabase auth
  - **DoD:** Flag in env vars, app switches auth provider based on flag value

**Acceptance Criteria:**

- [ ] Supabase project fully configured
- [ ] All tables created with proper schemas
- [ ] RLS policies enforce user isolation
- [ ] Feature flag switches between mock and real auth

**Verification:**

- Attempt to access another user's data via direct query (should fail)
- Toggle feature flag and verify auth switching works

## Phase 10: Production Auth Implementation

### **MS-018:** Real Authentication Integration (Week 3)

**Goal:** Replace mock auth with real Supabase Auth

**Success Criteria:**

- SC-070: Real signup creates records in both Supabase Auth and `users` table
- SC-071: Session persists across browser refresh and tab duplication
- SC-072: Password reset email delivered via Supabase within 30 seconds
- SC-073: Protected routes enforce real session with no bypass possible

**Tasks:**

- [ ] T169: Implement real Supabase signup with email/password
  - **DoD:** Signup creates auth user and `users` table record, returns session
- [ ] T170: Implement real Supabase login with session management
  - **DoD:** Login returns session, session accessible via `getSession()` after refresh
- [ ] T171: Implement real password reset email flow
  - **DoD:** Reset email sends, link opens reset form, new password saves
- [ ] T172: Create POST /api/auth/initialize endpoint for user document creation
  - **DoD:** Endpoint creates `users` table record from auth user, idempotent on retry
- [ ] T173: Implement session management with secure cookies (24-hour expiry)
  - **DoD:** Session stored in httpOnly cookie, expires after 24 hours
- [ ] T174: Update auth middleware to use real Supabase session
  - **DoD:** Middleware validates real session, redirects on invalid/expired
- [ ] T175: Update AuthProvider to use real Supabase client
  - **DoD:** Provider uses real client, `useAuth` hook returns real user data
- [ ] T176: Add session expiry handling (prompt re-authentication, preserve local data)
  - **DoD:** Expired session shows re-auth prompt, local edits preserved after re-login
- [ ] T177: Write integration tests for auth flows
  - **DoD:** Tests cover signup, login, logout, reset, and session expiry, all pass
- [ ] T177A [P]: Handle concurrent session detection (new device login invalidates old sessions)
  - **DoD:** Login on device B invalidates device A session, device A prompted to re-auth

**Acceptance Criteria:**

- [ ] Real signup creates user in Supabase Auth and users table
- [ ] Real login creates session that persists across browser refresh
- [ ] Password reset sends real email via Supabase
- [ ] Protected routes work with real session

**Verification:**

- Create real test account, log in, refresh browser, verify session persists
- Test password reset flow with real email
- Verify session expiry prompts re-authentication

## Phase 11: Offline-First Data Layer

### **MS-019:** PowerSync Offline Sync (Week 3-4)

**Goal:** Implement PowerSync for offline-first sync between SQLite and Supabase

**Success Criteria:**

- SC-074: Local writes complete within 100ms regardless of network state
- SC-075: Sync to Supabase completes within 5 seconds (P95) after connectivity restored
- SC-076: All editor features work identically in offline mode
- SC-077: Sync status indicator matches actual PowerSync state in real time

**Tasks:**

- [ ] T178: Install and configure PowerSync (@powersync/web)
  - **DoD:** PowerSync SDK initialized, connects to PowerSync service, no console errors
- [ ] T179: Create PowerSync schema matching PostgreSQL tables
  - **DoD:** Schema defines all columns matching Supabase tables, compiles without error
- [ ] T180: Configure PowerSync bucket definitions for user data isolation
  - **DoD:** Buckets scoped to user ID, only user's data syncs to device
- [ ] T181: Replace local storage layer with PowerSync SQLite
  - **DoD:** All CRUD operations use PowerSync SQLite, localStorage layer removed
- [ ] T182: Implement useOnlineStatus hook to detect connectivity changes
  - **DoD:** Hook returns `isOnline` boolean, updates on network change events
- [ ] T183: Create sync status indicator connected to PowerSync state
  - **DoD:** Indicator shows real sync state (synced, syncing, offline, error)
- [ ] T184: Implement auto-sync when network restored
  - **DoD:** Queued changes sync automatically within 5 seconds of reconnection
- [ ] T185: Create feature flag to toggle mock vs real sync
  - **DoD:** Flag switches between mock sync queue and real PowerSync
- [ ] T186: Write integration tests for offline/online sync scenarios
  - **DoD:** Tests cover offline edit, reconnect sync, and data verification, all pass
- [ ] T186A [P]: Handle partial sync failures with retry queue and user notification
  - **DoD:** Failed items retry with backoff, user notified after 3 failures

**Acceptance Criteria:**

- [ ] Notes save to local SQLite instantly
- [ ] Notes sync to Supabase within 5 seconds of connectivity restoration (P95)
- [ ] Offline editing works with all features (FR-018)
- [ ] Sync status indicator reflects real state

**Verification:**

- Edit note offline, restore network, verify sync completes
- Check Supabase database for synced notes

## Phase 12: Data Synchronization Strategy

### **MS-020:** Sync Conflict Resolution (Week 4)

**Goal:** Implement last-write-wins conflict resolution with version history

**Success Criteria:**

- SC-078: Conflicts detected and resolved automatically with no user intervention required
- SC-079: Overwritten versions preserved as snapshots with `snapshotType: "sync_conflict"`
- SC-080: Toast notification displays within 1 second of conflict resolution
- SC-081: Sync reliability exceeds 99% measured across 100+ sync operations

**Tasks:**

- [ ] T187: Implement conflict detection (compare version and updatedAt)
  - **DoD:** Detection identifies conflicting versions by comparing `version` and `updatedAt`
- [ ] T188: Implement last-write-wins algorithm per Tech Specs Section 7
  - **DoD:** Algorithm selects most recent `updatedAt`, applies winning version
- [ ] T189: Create Snapshot when conflict detected (snapshotType: "sync_conflict")
  - **DoD:** Losing version saved to `snapshots` table with correct `snapshotType`
- [ ] T190: Display toast notification on conflict resolution ("Version from [device] kept")
  - **DoD:** Toast shows device info and resolution result, auto-dismisses after 5 seconds
- [ ] T191: Implement exponential backoff retry (5s, 15s, 30s, 60s, 120s) for failed syncs
  - **DoD:** Retry follows exact backoff schedule, stops after 5 attempts with notification
- [ ] T192: Update sync status indicator based on conflict state
  - **DoD:** Indicator shows "Resolving conflict..." during resolution, returns to "Synced"
- [ ] T193: Write integration tests for conflict scenarios
  - **DoD:** Tests simulate concurrent edits, verify resolution and snapshot creation, all pass

**Acceptance Criteria:**

- [ ] Conflicts resolved with last-write-wins algorithm (FR-019)
- [ ] Overwritten versions preserved as snapshots (FR-020)
- [ ] Toast notification shows conflict resolution result
- [ ] 99%+ sync reliability (NFR)
- [ ] Exponential backoff retry completes within 5 minutes or fails with user notification

**Verification:**

- Edit same note on two devices offline, bring online, verify conflict resolution
- Check snapshots table for conflict record

### **MS-021:** Real AI Integration (Week 4)

**Goal:** Replace mock AI with real OpenAI GPT-4.1 nano autocomplete

**Success Criteria:**

- SC-082: Real AI suggestions return within 200ms (P95) measured from last keystroke
- SC-083: Dictionary fallback activates within 100ms when API fails or quota exceeded
- SC-084: Quota decrements accurately in database after each AI request
- SC-085: Throttling enforces max 1 request per 3 seconds per user

**Tasks:**

- [ ] T194: Create POST /api/ai/autocomplete endpoint with token validation
  - **DoD:** Endpoint validates auth token, rejects unauthenticated requests with 401
- [ ] T195: Implement OpenAI GPT-4.1 nano integration with <200ms target
  - **DoD:** OpenAI SDK configured, responses return within 200ms P95 in testing
- [ ] T196: Add request throttling (max 1 request per 3 seconds per user)
  - **DoD:** Requests within 3-second window return 429, throttle tracked per user ID
- [ ] T197: Implement quota tracking in Supabase users table
  - **DoD:** `aiRequestsUsed` field increments on each request, resets monthly
- [ ] T198: Create GET /api/users/quota endpoint for quota checking
  - **DoD:** Endpoint returns `{ used, limit, remaining }`, authenticated only
- [ ] T199: Load full 5,000+ nursing dictionary (nursing-terms.json) into memory
  - **DoD:** Dictionary loaded at startup, prefix search returns results for all terms
- [ ] T200: Implement dictionary prefix matching for production fallback
  - **DoD:** Prefix match returns sorted results within 50ms for 5,000+ terms
- [ ] T201: Update useAutocomplete hook to use real API with feature flag
  - **DoD:** Hook calls real API when flag enabled, falls back to dictionary on failure
- [ ] T202: Handle API timeout (>500ms) with dictionary fallback
  - **DoD:** Timeout triggers dictionary fallback, no error shown to user
- [ ] T203: Write integration tests for AI autocomplete
  - **DoD:** Tests cover real API, throttling, quota, and fallback, all pass

**Acceptance Criteria:**

- [ ] Real AI suggestions appear within 200ms (P95) measured from last keystroke (FR-001)
- [ ] Dictionary fallback works offline (FR-002)
- [ ] Dictionary fallback works when quota exceeded (FR-002)
- [ ] Quota updates in database after each AI request (FR-027)
- [ ] Request throttling enforced (1 per 3 seconds)

**Verification:**

- Type "met" with real API and verify suggestions appear
- Exceed quota and verify seamless switch to dictionary mode
- Time AI response and confirm <200ms typical latency

## Phase 13: Payment & Subscription System

### **MS-022:** Stripe Integration (Week 4)

**Goal:** Implement Pro tier subscription with Stripe checkout, webhooks, and customer portal

**Success Criteria:**

- SC-086: Free tier enforces 100 AI requests/month limit with clear upgrade prompt
- SC-087: Stripe checkout flow completes end-to-end with test card
- SC-088: All 4 webhook events update user tier correctly in Supabase
- SC-089: Customer portal allows plan management without leaving the app flow

**Tasks:**

- [ ] T204: Create Stripe account and configure products (Pro Monthly $8.99, Pro Annual $79)
  - **DoD:** Products created in Stripe dashboard, price IDs stored in env vars
- [ ] T205: Create POST /api/stripe/checkout endpoint for checkout session
  - **DoD:** Endpoint creates Stripe session, returns checkout URL, includes user metadata
- [ ] T206: Create POST /api/stripe/webhook endpoint with signature validation
  - **DoD:** Endpoint validates Stripe signature, rejects invalid webhooks with 400
- [ ] T207: Handle checkout.session.completed webhook (update tier to Pro)
  - **DoD:** Handler updates `tier` to "pro" in `users` table, sets `stripeCustomerId`
- [ ] T208: Handle customer.subscription.updated webhook (plan changes)
  - **DoD:** Handler updates subscription details (plan, period) in `users` table
- [ ] T209: Handle customer.subscription.deleted webhook (downgrade to Free)
  - **DoD:** Handler sets `tier` to "free", clears subscription fields
- [ ] T210: Handle invoice.payment_failed webhook (payment failure handling)
  - **DoD:** Handler flags account, user sees payment failure notification on next login
- [ ] T211: Create POST /api/stripe/portal endpoint for customer portal session
  - **DoD:** Endpoint returns portal URL, user can manage subscription
- [ ] T212: Update Settings subscription section with real Stripe data
  - **DoD:** Settings shows real tier, quota, and subscription details from Stripe
- [ ] T213: Implement tier enforcement in AI autocomplete endpoint
  - **DoD:** Free users blocked at 100 requests/month, Pro users unlimited
- [ ] T214: Create feature flag to toggle mock vs real Stripe
  - **DoD:** Flag switches between mock and real Stripe endpoints
- [ ] T215: Write integration tests for Stripe webhooks
  - **DoD:** Tests cover all 4 webhook events with mock Stripe payloads, all pass

**Acceptance Criteria:**

- [ ] Free users limited to 100 AI requests/month (FR-027)
- [ ] Pro users have unlimited AI requests (FR-028)
- [ ] User can upgrade via real Stripe checkout (FR-030)
- [ ] User can manage subscription via customer portal (FR-031)
- [ ] Subscription status displays correctly from Stripe

**Verification:**

- Test Stripe checkout flow with test card
- Verify webhook updates user tier in Supabase
- Confirm AI quota enforced correctly for free tier

## Phase 14: Critical Path Test Coverage

### **MS-023:** Testing Suite (Week 4)

**Goal:** Comprehensive test coverage for critical paths

**Success Criteria:**

- SC-090: All unit tests pass with zero failures
- SC-091: All E2E tests pass on Chromium, Firefox, and WebKit
- SC-092: CI pipeline runs tests on every PR with pass/fail status reported
- SC-093: Critical user paths (auth, notes, editor, sync, payment) have test coverage

**Tasks:**

- [ ] T216: Write unit tests for slash command parser and template insertion
  - **DoD:** Tests cover parsing, menu display, insertion, and edge cases, all pass
- [ ] T217: Write unit tests for autocomplete hook (AI and dictionary modes)
  - **DoD:** Tests cover both modes, debounce, fallback, and quota tracking, all pass
- [ ] T218: Write unit tests for sync queue and conflict resolution logic
  - **DoD:** Tests cover queue operations, conflict detection, and resolution, all pass
- [ ] T219 [SA]: Write unit tests for Zod validation schemas
  - **DoD:** Tests cover valid data, invalid data, edge cases for all schemas, all pass
- [ ] T220: Write E2E test: signup -> onboarding -> create note -> save flow
  - **DoD:** Test completes full flow from signup to saved note, passes on 3 browsers
- [ ] T221: Write E2E test: offline editing -> reconnect -> sync verification
  - **DoD:** Test simulates offline, edits, reconnects, verifies sync, passes on 3 browsers
- [ ] T222: Write E2E test: slash command insertion (/template, /formula)
  - **DoD:** Test inserts template and formula, verifies content, passes on 3 browsers
- [ ] T223: Write E2E test: AI autocomplete flow and quota enforcement
  - **DoD:** Test triggers autocomplete, verifies suggestions, tests quota, passes on 3 browsers
- [ ] T224: Write E2E test: Stripe checkout and subscription upgrade
  - **DoD:** Test completes mock checkout, verifies tier change, passes on 3 browsers
- [ ] T225: Set up GitHub Actions CI for test runs on PR
  - **DoD:** Workflow runs unit + E2E tests on PR, reports status check
- [ ] T226: Ensure mocks remain available for test environment
  - **DoD:** MSW handlers load in test env, all tests use mocks consistently

**Acceptance Criteria:**

- [ ] All unit tests pass
- [ ] All E2E tests pass on Chromium, Firefox, WebKit
- [ ] CI runs tests on every PR
- [ ] Mocks work correctly in test environment
- [ ] Critical paths have test coverage

**Verification:**

- Run `npm run test` and confirm all pass
- Run `npm run test:e2e` on all browsers
- Create PR and verify CI runs

## Phase 15: Performance & Web Vitals

### **MS-024:** Performance Optimization (Week 4)

**Goal:** Meet all Core Web Vitals and performance targets

**Success Criteria:**

- SC-094: Lighthouse Performance score 90+ on production build
- SC-095: FCP <1.5s, LCP <2.5s, TTI <3.5s, CLS <0.1 measured via Lighthouse
- SC-096: 50,000 character document editable without perceptible lag
- SC-097: Client memory stays under 150MB with 20 notes loaded in Chrome DevTools

**Tasks:**

- [ ] T227: Implement code splitting with dynamic imports for heavy components
  - **DoD:** Editor, slash menu, and settings lazy-loaded, bundle analyzer confirms split
- [ ] T228: Add lazy loading for notes library (virtual scrolling if >100 notes)
  - **DoD:** Virtual scrolling activates at 100+ notes, renders only visible items
- [ ] T229: Optimize images with Next.js Image component
  - **DoD:** All images use `next/image`, served in WebP with responsive sizes
- [ ] T230: Configure service worker caching strategies (NetworkFirst for API, CacheFirst for assets)
  - **DoD:** Service worker caches assets on install, APIs fetched network-first
- [ ] T231: Run Lighthouse audit and address any issues
  - **DoD:** All Lighthouse categories 90+, any flagged issues resolved
- [ ] T232: Verify FCP <1.5s, LCP <2.5s, TTI <3.5s, CLS <0.1 (Tech Specs Section 10)
  - **DoD:** All 4 metrics within target on production build measured via Lighthouse
- [ ] T233: Profile and optimize Tiptap editor for 50,000 character documents
  - **DoD:** 50K chars editable with <16ms frame times during typing
- [ ] T234: Verify client-side memory stays under 150MB with 20 notes loaded
  - **DoD:** Chrome DevTools memory snapshot shows <150MB heap with 20 notes

**Acceptance Criteria:**

- [ ] Lighthouse Performance score 90+
- [ ] Core Web Vitals all in green
- [ ] AI autocomplete <200ms typical
- [ ] Search <300ms for 1,000 notes

**Verification:**

- Run Lighthouse on production build
- Test with 50,000 character note, no lag
- Profile memory usage in Chrome DevTools

## Phase 16: Production Release

### **MS-025:** Deployment & Monitoring (Week 4)

**Goal:** Deploy to Vercel with monitoring, error tracking, and cost alerts

**Success Criteria:**

- SC-098: Production app loads at custom domain with valid SSL
- SC-099: Sentry captures all unhandled exceptions with user context
- SC-100: Cost alerts fire at $50, $75, and $100 thresholds
- SC-101: All mock feature flags disabled in production environment

**Tasks:**

- [ ] T235: Configure Vercel project with environment variables
  - **DoD:** All env vars set in Vercel dashboard, build succeeds with production config
- [ ] T236: Set up custom domain and SSL certificate
  - **DoD:** Domain resolves to Vercel, HTTPS enforced, certificate valid
- [ ] T237: Deploy production build to Vercel
  - **DoD:** Production deployment live, app loads without errors at custom domain
- [ ] T238: Configure Sentry error tracking
  - **DoD:** Sentry SDK initialized, test error captured with user ID and stack trace
- [ ] T239: Configure Vercel Analytics for user behavior
  - **DoD:** Analytics script loaded, page views tracked in Vercel dashboard
- [ ] T240: Set up monitoring alerts for error rates >5%
  - **DoD:** Alert rule configured in Sentry, triggers on >5% error rate
- [ ] T241: Set up cost alerts at $50, $75, $100 thresholds
  - **DoD:** Alerts configured in Vercel/Stripe/OpenAI dashboards at all 3 thresholds
- [ ] T242: Create monitoring dashboard for AI API costs per tier
  - **DoD:** Dashboard shows daily AI cost breakdown by tier, accessible to team
- [ ] T243: Configure Supabase automatic backup
  - **DoD:** Daily backups enabled in Supabase, retention policy set
- [ ] T244: Document rollback procedure
  - **DoD:** Rollback steps documented, Vercel deployment revert tested
- [ ] T245: Remove or disable mock feature flags for production
  - **DoD:** All mock flags set to `false` or removed in production env
- [ ] T245A [P]: Implement PWA update notification with prompt to refresh when new version available
  - **DoD:** Service worker detects new version, user sees "Update available" prompt
- [ ] T245B [P]: Configure analytics dashboard for tracking AI acceptance rate (PRD Goal #6)
  - **DoD:** Dashboard tracks accepted vs dismissed suggestions, filterable by tier

**Acceptance Criteria:**

- [ ] Production app accessible at custom domain
- [ ] All unhandled exceptions, API errors (4xx/5xx), and sync failures reported to Sentry with user ID, session ID, and stack trace
- [ ] Analytics tracking user sessions
- [ ] Cost alerts configured
- [ ] Mocks disabled in production

**Verification:**

- Access production URL, verify app loads
- Trigger intentional error, verify Sentry captures
- Check Vercel Analytics dashboard
