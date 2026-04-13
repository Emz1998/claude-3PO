---
session_id: 1a3a57d4-2a2d-4f4f-a543-bf412e0cacee
workflow_type: build
date: 2026-04-12
timestamp: 2026-04-12T01:11:02.955530
---
# Snake and Ladders Game Implementation Plan

## Context

We are building a Snake and Ladders board game as a single self-contained HTML file (`index.html`). This is a standalone mini-project within the `/home/emhar/avaris-ai/` repository, placed under a new `games/snake-ladders/` directory. The game has no relationship to the existing Python ML codebase -- it is a clean-slate browser game with zero external dependencies. Everything (HTML structure, CSS styles, JavaScript logic) lives in one file.

The game supports 2-player local multiplayer with turn-based dice rolling, animated piece movement along a boustrophedon (zigzag) numbered 10x10 board, snake/ladder slide animations, 3D dice rolling animation, and a modern glassmorphism UI with dark mode, responsive design, and keyboard accessibility.

## Dependencies

None. The file is entirely self-contained:
- HTML5 for structure
- CSS3 (Grid, Custom Properties, `backdrop-filter`, 3D transforms, keyframes) for styling and animation
- Vanilla JavaScript (ES6+) for game logic
- No build tools, no package managers, no CDN links

## Contracts

The entire application lives in a single `<script>` block. Below are the key data structures and function signatures that form the internal API contract.

### Constants

```javascript
// Board configuration
const BOARD_SIZE = 10;
const TOTAL_CELLS = 100;

// Snakes: key = head (land here), value = tail (slide to)
const SNAKES = {
  16: 6, 47: 26, 49: 11, 56: 53, 62: 19,
  64: 60, 87: 24, 93: 73, 95: 75, 98: 78
};

// Ladders: key = bottom (land here), value = top (climb to)
const LADDERS = {
  1: 38, 4: 14, 9: 31, 21: 42, 28: 84,
  36: 44, 51: 67, 71: 91, 80: 100
};
```

### Game State Object

```javascript
const gameState = {
  players: [
    { id: 1, name: 'Player 1', position: 0, color: '#ff6b6b' },
    { id: 2, name: 'Player 2', position: 0, color: '#4ecdc4' }
  ],
  currentPlayerIndex: 0,
  diceValue: 1,
  isRolling: false,       // true during dice animation
  isMoving: false,        // true during piece movement animation
  gameOver: false,
  phase: 'idle'           // 'idle' | 'rolling' | 'moving' | 'checking' | 'sliding' | 'won'
};
```

### Core Functions -- Signatures and Responsibilities

**Board Rendering**

```javascript
/**
 * Convert a board position (1-100) to {row, col} grid coordinates.
 * Handles boustrophedon (zigzag) numbering:
 *   Row 0 (bottom) = cells 1-10 left-to-right
 *   Row 1 = cells 11-20 right-to-left
 *   Row 2 = cells 21-30 left-to-right, etc.
 * Returns {row: 0-9, col: 0-9} where row 0 is the BOTTOM of the board.
 */
function positionToCoords(position) -> { row: number, col: number }

/**
 * Build the 10x10 board grid inside #board-container.
 * Creates 100 cell <div> elements with:
 *   - Cell number label
 *   - CSS class for snake-head, snake-tail, ladder-bottom, ladder-top
 *   - data-position attribute
 * Cells are rendered top-to-bottom (row 9 first) to match visual layout.
 */
function renderBoard() -> void

/**
 * Draw SVG overlay lines/curves for snakes and ladders on top of the grid.
 * Snakes: red/orange curved paths with head/tail markers.
 * Ladders: green/blue straight lines with rung markers.
 * Uses an absolutely-positioned <svg> element over the board.
 */
function drawSnakesAndLadders() -> void
```

**Dice System**

```javascript
/**
 * Generate random 1-6, trigger 3D dice spin animation,
 * update gameState.diceValue, then call movePlayer().
 * Sets gameState.phase = 'rolling' during animation.
 * Animation duration: ~800ms.
 */
function rollDice() -> void

/**
 * Update the dice face display to show the given value (1-6).
 * Renders dots in the classic dice-face pattern using CSS grid.
 */
function updateDiceFace(value: number) -> void
```

**Player Movement**

```javascript
/**
 * Animate the current player's piece from current position
 * to (current + diceValue), stepping one cell at a time
 * with ~150ms delay per step.
 * After arriving, calls checkForSnakeOrLadder().
 * Sets gameState.phase = 'moving'.
 */
function movePlayer() -> void

/**
 * Move a player piece DOM element to the visual position of a given cell.
 * Uses CSS transform: translate(x, y) for GPU-accelerated animation.
 */
function animatePieceTo(playerIndex: number, targetPosition: number) -> Promise<void>

/**
 * After landing, check SNAKES and LADDERS maps.
 * If found, animate slide to new position with a distinct
 * sliding animation (phase = 'sliding'), then call nextTurn().
 * If position === 100, call handleWin().
 * Otherwise, call nextTurn().
 */
function checkForSnakeOrLadder() -> void

/**
 * Switch to next player, update UI indicators, set phase = 'idle'.
 * Special rule: if dice === 6, same player rolls again.
 */
function nextTurn() -> void
```

**Win and Reset**

```javascript
/**
 * Set gameState.phase = 'won', show celebration overlay
 * with confetti animation and winner announcement.
 * Disable dice rolling.
 */
function handleWin(playerIndex: number) -> void

/**
 * Reset gameState to initial values, clear board highlights,
 * reset piece positions, hide celebration overlay.
 */
function resetGame() -> void
```

**UI and Accessibility**

```javascript
/**
 * Update the status bar text showing whose turn it is,
 * dice result, and any snake/ladder event messages.
 * Uses ARIA live region for screen reader announcements.
 */
function updateStatus(message: string) -> void

/**
 * Toggle between light and dark mode by switching
 * a data-theme attribute on <html> and updating CSS custom properties.
 */
function toggleDarkMode() -> void

/**
 * Keyboard event handler: Space/Enter to roll dice,
 * 'N' for new game, 'D' for dark mode toggle.
 */
function handleKeyboard(event: KeyboardEvent) -> void

/**
 * Recalculate SVG overlay positions when window resizes.
 * Debounced to avoid excessive redraws.
 */
function handleResize() -> void
```

### CSS Custom Properties Contract

```css
:root {
  --bg-primary: #0f0c29;
  --bg-secondary: #302b63;
  --bg-tertiary: #24243e;
  --text-primary: #ffffff;
  --text-secondary: #b8b8d4;
  --glass-bg: rgba(255, 255, 255, 0.08);
  --glass-border: rgba(255, 255, 255, 0.15);
  --glass-shadow: rgba(0, 0, 0, 0.3);
  --cell-bg: rgba(255, 255, 255, 0.05);
  --cell-border: rgba(255, 255, 255, 0.1);
  --snake-color: #ff6b6b;
  --ladder-color: #51cf66;
  --player1-color: #ff6b6b;
  --player2-color: #4ecdc4;
  --board-size: clamp(280px, 90vmin, 800px);
  --cell-size: calc(var(--board-size) / 10);
  --piece-size: calc(var(--cell-size) * 0.4);
  --animation-speed: 1;  /* multiplier, 0 for reduced-motion */
}

[data-theme="light"] {
  --bg-primary: #667eea;
  --bg-secondary: #764ba2;
  --text-primary: #1a1a2e;
  --text-secondary: #4a4a6a;
  --glass-bg: rgba(255, 255, 255, 0.25);
  --glass-border: rgba(255, 255, 255, 0.4);
  --cell-bg: rgba(255, 255, 255, 0.2);
  --cell-border: rgba(255, 255, 255, 0.3);
}
```

### HTML Structure Contract

```
<html data-theme="dark">
  <head> ... <style> all CSS </style> </head>
  <body>
    <div class="game-container">
      <header class="glass-panel">
        <h1>Snake & Ladders</h1>
        <div class="controls">
          <button id="dark-mode-toggle">
          <button id="new-game-btn">
        </div>
      </header>
      <main class="game-layout">
        <aside class="player-panel glass-panel" id="player1-panel">
          <!-- Player 1 info, avatar, position -->
        </aside>
        <div class="board-wrapper">
          <div id="board-container" class="glass-panel">
            <!-- 100 cell divs rendered by JS -->
            <svg id="snake-ladder-overlay">
              <!-- SVG paths for snakes and ladders -->
            </svg>
            <div id="player-pieces">
              <!-- Player piece elements positioned via transform -->
            </div>
          </div>
        </div>
        <aside class="dice-panel glass-panel">
          <div id="dice" class="dice-3d"> <!-- 3D dice faces --> </div>
          <button id="roll-btn">Roll Dice</button>
          <div id="status" role="status" aria-live="polite"></div>
        </aside>
      </main>
      <div id="celebration-overlay" class="hidden">
        <!-- Win screen with confetti -->
      </div>
    </div>
    <script> all JavaScript </script>
  </body>
</html>
```

## Tasks

The following tasks are ordered for implementation within the single `index.html` file. Each task builds on the previous one. Since everything is in one file, "sections" refers to logical blocks within that file.

### Task 1: File scaffolding and HTML structure
**What**: Create `games/snake-ladders/index.html` with the complete HTML skeleton: `<!DOCTYPE html>`, `<head>` with meta viewport and title, empty `<style>` block, body structure matching the HTML contract above, empty `<script>` block.
**Why**: Establishes the DOM structure that CSS and JS will target.
**Acceptance**: File opens in browser showing the raw HTML elements (unstyled).

### Task 2: CSS custom properties and base styles
**What**: Inside the `<style>` block, implement:
- CSS custom properties for both dark (default) and light themes as specified in the contract
- `@media (prefers-reduced-motion: reduce)` to set `--animation-speed: 0`
- Animated gradient background on `body` using `background-size: 400% 400%` with a slow `@keyframes gradientShift`
- Base reset (`*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }`)
- `.game-container` as a flex column centered layout
- `.glass-panel` utility class: `background: var(--glass-bg)`, `backdrop-filter: blur(12px)`, `border: 1px solid var(--glass-border)`, `border-radius: 16px`, `box-shadow`
**Why**: Establishes the visual foundation and theming system.
**Acceptance**: Page shows gradient background with glass-effect empty panels.

### Task 3: Game layout (responsive)
**What**: CSS for `.game-layout` using CSS Grid with areas: `player-panel | board-wrapper | dice-panel`. Board wrapper centers the board at `var(--board-size)`. Use `@media` queries:
- Desktop (>1024px): 3-column layout, side panels visible
- Tablet (768-1024px): 2-column, dice panel below board
- Mobile (<768px): single column stack
**Why**: Ensures playability across devices.
**Acceptance**: Layout reflows correctly at different viewport sizes.

### Task 4: Board grid rendering (JS + CSS)
**What**: Implement `positionToCoords()` and `renderBoard()` in JavaScript. CSS for `#board-container` as a 10x10 CSS Grid. Each cell gets:
- Position number label (small, top-left corner)
- Alternating background colors (checkerboard pattern using `:nth-child` or computed classes)
- Subtle border and hover effect
- `data-position` attribute for JS targeting
- Special visual indicators (colored dot/icon) for snake heads, snake tails, ladder bottoms, ladder tops

**Boustrophedon logic**: Row index 0 is the bottom visual row. For even row indices (0, 2, 4, 6, 8) cells go left-to-right. For odd row indices (1, 3, 5, 7, 9) cells go right-to-left. The HTML must render from row 9 (top visual) down to row 0 (bottom visual).

**Why**: The board is the core visual element. Getting the zigzag numbering correct is critical.
**Acceptance**: Board displays 1-100 in correct snake-and-ladders order. Cell 1 is bottom-left, cell 100 is top-left (or top-right depending on board size parity -- for a 10x10 board with even row count, cell 100 is in the top-left).

### Task 5: SVG snake and ladder overlays
**What**: Implement `drawSnakesAndLadders()`. Create an `<svg>` element absolutely positioned over the board. For each snake, draw a wavy/curved path (using SVG `<path>` with cubic bezier curves) from head cell center to tail cell center, colored red/orange with a triangular head marker. For each ladder, draw two parallel lines with rungs between them from bottom cell to top cell, colored green/blue.

Calculate pixel positions by getting cell element positions relative to the board container using `getBoundingClientRect()` or computed offsets from `positionToCoords()` and `var(--cell-size)`.

**Why**: Visual indicators make the game intuitive -- players must see where snakes and ladders are.
**Acceptance**: Snakes appear as colored curves, ladders as parallel lines with rungs, correctly connecting their respective cells. Lines redraw on window resize.

### Task 6: Player pieces and positioning
**What**: Create two player piece DOM elements (colored circles with player number or icon) inside `#player-pieces`. Implement `animatePieceTo()` which computes the target cell's pixel center from `positionToCoords()` and `var(--cell-size)`, then sets `transform: translate(Xpx, Ypx)` with CSS `transition: transform 0.15s cubic-bezier(0.25, 0.46, 0.45, 0.94)`. When two players are on the same cell, offset them slightly so both are visible.

**Why**: Players need visual representation on the board.
**Acceptance**: Two colored circles appear at position 0 (off-board or at start area). Calling `animatePieceTo(0, 5)` smoothly moves player 1's piece to cell 5.

### Task 7: Dice system with 3D animation
**What**: Implement the dice as a 3D CSS cube using `transform-style: preserve-3d` and six face `<div>`s positioned with `rotateX/Y` and `translateZ`. Each face shows the correct dot pattern (1-6) using CSS grid for dot placement. `rollDice()` generates a random value, applies a `@keyframes diceRoll` animation (rapid multi-axis rotation for ~800ms), then rotates to the face showing the result. Implement `updateDiceFace()` for the final resting state.

**Why**: The dice is the primary interaction point; 3D animation adds visual delight.
**Acceptance**: Clicking "Roll Dice" triggers a spinning 3D cube that lands on a random face. The numeric result is visually clear.

### Task 8: Turn-based game loop
**What**: Implement the core game loop connecting dice to movement:
1. `rollDice()` sets `phase = 'rolling'`, disables the roll button, runs dice animation
2. After animation, calls `movePlayer()` which sets `phase = 'moving'`
3. `movePlayer()` animates piece step-by-step (position + 1 each step, ~150ms per step)
4. After arriving, calls `checkForSnakeOrLadder()` which sets `phase = 'checking'`
5. If snake/ladder found, sets `phase = 'sliding'`, animates to new position, shows status message
6. Calls `nextTurn()` which sets `phase = 'idle'` and re-enables rolling
7. Special rule: rolling a 6 gives an extra turn (same player)
8. Edge case: if dice roll would take player past 100, the move is skipped (player stays put)

**Why**: This is the game's logic backbone.
**Acceptance**: Two players can alternate turns. Rolling moves the piece visually. Landing on snake/ladder triggers slide. Rolling 6 gives an extra turn. Cannot overshoot 100.

### Task 9: Player panels and status display
**What**: Implement player panel UI showing:
- Player name and color indicator
- Current position number
- Active turn highlight (glowing border or pulsing animation on the current player's panel)
- `updateStatus()` function that writes messages to `#status` div (ARIA live region)
- Turn indicator changes after each turn

**Why**: Players need clear feedback about game state.
**Acceptance**: Active player's panel is visually highlighted. Status messages appear for dice rolls, snake encounters, ladder climbs, and extra turns.

### Task 10: Win detection and celebration
**What**: Implement `handleWin()`:
- Detect when a player lands exactly on cell 100
- Set `phase = 'won'`, disable dice
- Show `#celebration-overlay` with winner announcement
- CSS confetti animation using multiple small colored `<div>`s with random `@keyframes` (fall from top with rotation and horizontal drift)
- "Play Again" button that calls `resetGame()`

Implement `resetGame()`:
- Reset all `gameState` properties to initial values
- Move pieces back to start
- Hide celebration overlay
- Set phase to 'idle'

**Why**: The game needs a clear end state and replay ability.
**Acceptance**: Landing on 100 shows a celebration screen with confetti and winner name. "Play Again" resets everything.

### Task 11: Dark mode toggle
**What**: Implement `toggleDarkMode()` that toggles `data-theme` between "dark" and "light" on the `<html>` element. Add a toggle button in the header (sun/moon icon using unicode or CSS shapes). CSS transitions on custom property changes for smooth theme switching.

**Why**: User preference for light/dark display.
**Acceptance**: Clicking the toggle smoothly transitions all colors between dark and light themes.

### Task 12: Keyboard accessibility and ARIA
**What**: Implement `handleKeyboard()`:
- Space or Enter: roll dice (when phase is 'idle')
- N key: new game
- D key: toggle dark mode
- Add `tabindex`, `role="button"`, `aria-label` to interactive elements
- ARIA live region on `#status` announces game events to screen readers
- Focus management: after rolling, focus returns to roll button

**Why**: Accessibility is a requirement and improves UX for keyboard users.
**Acceptance**: Game is fully playable using only keyboard. Screen reader announces turn changes and events.

### Task 13: Responsive polish and final details
**What**: Final responsive tweaks:
- `clamp()` on font sizes for fluid typography
- Board scales smoothly using `vmin` units
- Touch-friendly button sizes (minimum 44x44px tap targets)
- SVG overlay redraws on resize (debounced `handleResize()`)
- Smooth scrolling to board on mobile after dice roll
- Loading state: board renders on `DOMContentLoaded`
- Add subtle hover effects on cells showing position number
- Add move history log (last 5 moves) in the status panel

**Why**: Polish differentiates a good game from a great one.
**Acceptance**: Game looks and plays well on mobile (375px width), tablet (768px), and desktop (1440px). No layout breaks, no overlapping elements, animations are smooth.

## Files to Modify

Only one file needs to be created:

| Action | Path |
|--------|------|
| Create directory | `/home/emhar/avaris-ai/games/snake-ladders/` |
| Create file | `/home/emhar/avaris-ai/games/snake-ladders/index.html` |

No existing files are modified.

## Verification

Since this is a standalone HTML file with no test framework, verification is manual and visual.

1. **Open in browser**: Open `index.html` directly in a browser (Chrome/Firefox/Safari). The game should render immediately with no console errors.

2. **Board correctness**: Visually confirm cell 1 is bottom-left, cell 10 is bottom-right, cell 11 is directly above cell 10 (right side), cell 20 is above cell 1 (left side). Cell 100 should be top-left.

3. **Snake/ladder placement**: Verify that SVG overlays connect the correct cells by cross-referencing with the SNAKES and LADDERS constants. Hover over cells to confirm position numbers.

4. **Gameplay test**:
   - Roll dice for Player 1, confirm piece moves correct number of squares
   - Confirm Player 2's turn follows
   - Roll a 6, confirm same player gets another turn
   - Land on a snake head, confirm piece slides down with animation
   - Land on a ladder bottom, confirm piece climbs up with animation
   - Reach cell 100, confirm win celebration appears
   - Click "Play Again", confirm full reset

5. **Responsive test**: Use browser DevTools responsive mode to test at 375px, 768px, and 1440px widths. Confirm no overflow, no broken layout, buttons are tappable.

6. **Dark mode test**: Toggle dark mode, confirm all elements switch theme smoothly. Verify the toggle persists visually (button icon changes).

7. **Keyboard test**: Tab to the roll button, press Space to roll. Press N for new game. Press D for dark mode. Confirm all work without mouse.

8. **Accessibility test**: Open browser accessibility inspector (Chrome Lighthouse or axe). Confirm no critical ARIA violations. Confirm status messages are announced.

9. **Performance test**: Open DevTools Performance tab, record a dice roll + piece movement sequence. Confirm animations run at 60fps (no jank). Check that `backdrop-filter` does not cause severe paint issues on mobile.

10. **Console check**: Open DevTools Console. Play a full game. Confirm zero errors or warnings.
