# UI/UX Specifications - Avaris NBA Prediction Platform

## 1. Design Principles

**Core Philosophy**

- Data-first design surfaces predictions and performance metrics prominently
- Transparency builds trust through visible track records and verifiable history
- Minimal friction enables quick access to daily picks
- Desktop-first experience with responsive mobile adaptation
- SEO-optimized content structure for discoverability

**Design System Foundation**

- Base unit: 4px spacing grid
- Typography: Inter (primary), JetBrains Mono (data/stats)
- Type scale: 12px to 48px with 1.5 line height
- Border radius: 4px (tight), 8px (medium), 16px (loose)
- Elevation: Subtle shadows for cards and modals

## 2. Color System

### Primary Colors

**Prediction Win - Green**

- Primary: `#22C55E` (HSL: 142 71% 45%)
- Foreground: White
- Use: Winning predictions, positive ROI, success states

**Prediction Loss - Red**

- Primary: `#EF4444` (HSL: 0 84% 60%)
- Foreground: White
- Use: Losing predictions, negative trends, error states

**Brand - Blue**

- Primary: `#3B82F6` (HSL: 217 91% 60%)
- Foreground: White
- Use: Primary actions, links, brand accents

### Semantic Colors

**Light Theme**

- Background: `#FFFFFF`
- Foreground: `#0F172A` (Slate 900)
- Card: `#F8FAFC` (Slate 50)
- Border: `#E2E8F0` (Slate 200)
- Muted: `#64748B` (Slate 500)
- Destructive: `#DC2626`
- Success: `#16A34A`
- Warning: `#F59E0B`

**Dark Theme**

- Background: `#0F172A` (Slate 900)
- Foreground: `#F8FAFC` (Slate 50)
- Card: `#1E293B` (Slate 800)
- Border: `#334155` (Slate 700)
- Muted: `#94A3B8` (Slate 400)
- Destructive: `#F87171`
- Success: `#4ADE80`
- Warning: `#FBBF24`

### Special Color Contexts

**Confidence Indicators**

- High (65%+): Green background, bold styling
- Medium (55-65%): Blue background, standard styling
- Low (<55%): Gray background, muted styling

**Team Colors**

- Home team: Primary brand blue
- Away team: Secondary gray
- Dynamic: Team-specific colors loaded for each matchup

## 3. Core Architecture

### Navigation Header

**Visual Design**

- Height: 64px (desktop), 56px (mobile)
- Position: Fixed top with blur backdrop
- Background: Semi-transparent with backdrop-filter
- Logo: Left-aligned, clickable to homepage
- Navigation: Center-aligned tabs (desktop)
- Actions: Right-aligned (theme toggle, auth buttons)

**Behavior**

- Sticky on scroll with shadow on scroll
- Mobile: Hamburger menu with slide-out drawer
- Current page indicator: Bottom border accent

### Pick Card Component

**Visual Design**

- Container: Full width, 16px padding, 8px border radius
- Layout: Horizontal split (teams | prediction | details)
- Team logos: 48px diameter with lazy loading
- Team names: 18px bold, abbreviation on mobile
- Game time: Muted text, relative or absolute format
- Prediction badge: Pill shape with confidence color
- Win probability: Large percentage, 2 decimal places

**States**

- Default: Standard card styling
- Highlighted: Border accent for featured picks
- Completed (Win): Green left border, checkmark icon
- Completed (Loss): Red left border, X icon
- Pending: No result indicator

## 4. Core Components

### Today's Picks Grid

**Visual Design**

- Container: Max 1200px centered, responsive padding
- Layout: Single column (mobile), grid (tablet+)
- Gap: 16px between cards
- Empty state: Illustration with "No games scheduled" message

**Sorting/Filtering**

- Default sort: Game time ascending
- Confidence filter: All, High only
- Show/hide completed: Toggle button

### Performance Dashboard Widgets

**Win Rate Widget**

- Large percentage display (48px font)
- Ring chart visualization
- Trend arrow (up/down vs previous period)
- Secondary text: "X wins / Y total picks"

**ROI Widget**

- Percentage with +/- prefix
- Color: Green (positive), Red (negative)
- Assumption text: "Flat $100 per pick"

**Streak Indicator**

- Visual streak (W/L icons in sequence)
- Current streak count prominently displayed
- Last 10 results shown

**Recent Results List**

- Scrollable list of last N predictions
- Each row: Date, matchup, pick, outcome
- Tap to expand for full details

### Prediction Article Layout

**Visual Design**

- Max width: 720px centered
- Typography: Prose optimized (18px, 1.75 line height)
- Heading: Team matchup as H1
- Meta: Date, game time, confidence level

**Sections**

- Prediction summary: Hero section with pick and probability
- Key factors: Bulleted insights driving prediction
- Team stats comparison: Side-by-side data table
- Historical matchups: Recent head-to-head results

### Newsletter Signup Form

**Visual Design**

- Inline form: Email input + submit button
- Position: Bottom of homepage, article sidebar
- Input: 320px width, 48px height
- Button: Primary blue, "Subscribe" text

**States**

- Default: Empty input with placeholder
- Loading: Spinner in button, disabled input
- Success: Checkmark, "Subscribed!" message
- Error: Red border, error message below

## 5. Application Screens

### Homepage (Today's Picks)

**Hero Section**

- Headline: "Today's NBA Picks" with date
- Subheadline: Model win rate badge ("57.3% Win Rate")
- Quick stats: Total picks today, high-confidence count

**Picks Grid**

- All games for today sorted by time
- Expandable for quick view of key stats
- Click through to full article

**Performance Teaser**

- Mini dashboard with key metrics
- CTA: "View Full Track Record"

**Newsletter CTA**

- Value proposition: "Daily picks in your inbox"
- Email capture form

### Prediction Article Page

**Header**

- Breadcrumb: Home > Predictions > Date > Matchup
- H1: "Lakers vs Celtics Prediction - Jan 15, 2025"
- Meta bar: Tip-off time, network, arena

**Prediction Hero**

- Large card with predicted winner highlighted
- Win probability percentage
- Confidence badge (High/Medium/Low)

**Analysis Content**

- MDX-rendered prose content
- Data tables with team comparisons
- Key factors list with icons

**Related Picks**

- Other games on same date
- Previous matchups between teams

**SEO Elements**

- Schema.org structured data
- Open Graph meta for social sharing
- Canonical URL

### Performance Dashboard

**Summary Cards Row**

- 4 cards: Win Rate, ROI, Total Picks, Current Streak
- Full width grid, responsive stacking

**Charts Section**

- Win rate over time (line chart)
- Confidence calibration (accuracy by confidence level)
- Home vs Away performance (bar chart)

**Full History Table**

- Filterable by date range
- Sortable columns
- Pagination (25 per page)
- Export to CSV button

### Authentication Pages

**Login Page**

- Container: 400px max width, centered
- Form: Email, password inputs
- Actions: "Sign In" primary, "Forgot password" link
- Social: "Continue with Google" button
- Footer: "Don't have an account? Sign up"

**Signup Page**

- Same layout as login
- Additional: Password confirmation field
- Terms checkbox: "I agree to Terms of Service"

## 6. Responsive Design

### Breakpoints

- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: 1024px+
- Large Desktop: 1280px+

### Responsive Adaptations

**Navigation**

- Desktop: Full horizontal nav with all links visible
- Mobile: Hamburger menu with slide-out drawer

**Pick Cards**

- Desktop: Horizontal layout with all details
- Tablet: Compact horizontal
- Mobile: Stacked vertical layout

**Dashboard Widgets**

- Desktop: 4-column grid
- Tablet: 2-column grid
- Mobile: Single column stack

**Article Layout**

- Desktop: Centered prose with sidebar
- Mobile: Full-width, no sidebar

## 7. Accessibility

### Keyboard Navigation

**Shortcuts**

- `/`: Focus search (future feature)
- `?`: Open keyboard shortcuts help
- Escape: Close modals/dropdowns
- Tab: Navigate interactive elements
- Enter: Activate focused element
- Arrow keys: Navigate pick cards list

**Focus Indicators**

- Visible ring around all interactive elements
- 2px offset blue ring (`#3B82F6`)
- Never remove focus indicators

### ARIA Attributes

**Pick Cards**

- Role: article
- aria-labelledby: Team matchup heading
- aria-describedby: Prediction details

**Dashboard Widgets**

- Role: region
- aria-label: Widget title (e.g., "Win Rate Statistics")

**Navigation**

- Role: navigation
- aria-label: "Main navigation"
- Current page: aria-current="page"

### Screen Reader Support

- All icons have text labels or aria-label
- Team logos have alt text with team name
- Loading states announced with aria-live
- Error messages announced immediately
- Data tables with proper headers and scope

## 8. Animation & Motion

### Transition Timing

- Instant: < 50ms (micro-interactions)
- Quick: 150ms (hover states, button presses)
- Standard: 300ms (page transitions, modals)
- Slow: 500ms (complex state changes)

### Animation Principles

**Page Transitions**

- Fade in content on navigation
- No layout shift during transitions
- Skeleton loading for async data

**Card Interactions**

- Hover: Subtle scale (1.02) and shadow increase
- Click: Brief scale down (0.98)
- Result reveal: Slide in from left with fade

**Modal Animations**

- Backdrop: Fade in 200ms
- Dialog: Scale from 0.95 to 1 with fade
- Exit: Reverse with quicker timing (150ms)
- Easing: ease-out for enter, ease-in for exit

**Micro-interactions**

- Button hover: Background color shift
- Toggle: Smooth slide animation
- Form validation: Shake on error

**Performance Considerations**

- Use CSS transforms over position changes
- Prefer opacity for fades
- Respect `prefers-reduced-motion` setting
- GPU-accelerated animations only

## 9. Dark Mode

### Theme Switching

**Controls**

- Toggle button in header (desktop) or settings
- Icon: Sun (light mode) / Moon (dark mode)
- Smooth 200ms color transition
- Persists choice to localStorage

**System Integration**

- Default: Follow system preference
- Options: Light, Dark, System
- No flash of wrong theme on page load (CSS variables)

**Color Adaptations**

- Charts: Adjust grid and line colors for contrast
- Team logos: Ensure visibility on dark backgrounds
- Shadows: Reduced opacity, softer on dark theme
- Borders: Lighter opacity for subtlety

## 10. Performance Targets

### Critical Metrics

- **Page load**: < 2s on 3G connection
- **First Contentful Paint**: < 1.5s
- **Largest Contentful Paint**: < 2.5s
- **Time to Interactive**: < 3.5s
- **Cumulative Layout Shift**: < 0.1
- **API response display**: < 500ms

### Optimization Strategies

- Static generation for prediction articles (ISR 1-hour revalidation)
- Lazy load team logos and images
- Debounce filter/search inputs (300ms)
- Virtual scrolling for long history tables
- Skeleton loading states for all async content
- Code splitting for dashboard charts

## 11. Design Checklist (MVP)

**Before v0.1.0 Release**

- [ ] Homepage with today's picks grid
- [ ] Individual prediction article pages
- [ ] Pick card component with all states (pending, win, loss)
- [ ] Confidence indicators (High/Medium/Low)
- [ ] Performance dashboard with key metrics
- [ ] Win rate and ROI widgets
- [ ] Recent results list
- [ ] Full pick history table with filters
- [ ] Newsletter signup form
- [ ] Responsive layouts (mobile, tablet, desktop)
- [ ] Dark mode support
- [ ] Keyboard navigation throughout
- [ ] WCAG AA compliant contrast ratios
- [ ] Loading and error states for all components
- [ ] SEO meta tags and structured data
- [ ] Lighthouse SEO score 90+
- [ ] Page load under 2 seconds

---

**Design System**: Built with Tailwind CSS v4, leveraging utility classes for consistent spacing, typography, and responsive design. Component library inspired by Shadcn UI patterns for accessibility compliance.

**Additional Resources**:

- Design tokens: Defined in `tailwind.config.ts`
- Component library: `src/components/ui/`
- Brand guidelines: `project/executive/app-vision.md`
