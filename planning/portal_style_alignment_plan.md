# Portal Style Alignment Plan

## Goal
Align the data portal (this repo) with the overarching ukbol.org website style, without breaking any portal functionality.

---

## Key Differences (Current Portal vs ukbol.org)

| Element | Portal (current) | ukbol.org | Impact |
|---------|-----------------|-----------|--------|
| **Primary colour** | `#1a365d` (navy) | `#1a4d5a` (deep teal) | All headers, footers, cards |
| **Accent colour** | `#2d5a87` (steel blue) | `#2b7a8c` (medium teal) | Gradients, links, buttons |
| **CSS variables** | Traffic-light only (`--ukbol-green/amber/red/blue/black`) | Full palette (`--ukbol-primary`, `--ukbol-primary-mid`, `--ukbol-accent-light`, `--ukbol-gold`, etc.) | Foundation for theming |
| **Page background** | `linear-gradient(#f5f7fa, #e4e8ec)` | Flat `#f5f7fa` | Subtle change |
| **Link colour** | Browser defaults / Bootstrap blue | `#2b7a8c`, hover `#1a4d5a` | All anchor tags |
| **Heading colours** | Inherited / default | h1/h2: `#1a4d5a`, h3: `#2b7a8c` | Section headings |
| **Navbar** | Dark gradient nav (navy→steel blue) | White bg, bottom border `#e8f4f8`, shadow | Major visual change |
| **Logo in navbar** | None | `ukbol-text-logo-clear.png`, 45px height | Adds branding |
| **Logo in footer** | None | Logo 60px with white filter | Adds branding |
| **Footer bg** | `#1a365d` (navy) | `#1a4d5a` (deep teal) | Colour shift |
| **Card hover shadow** | `rgba(0,0,0,.12)` | `rgba(26,77,90,.15)` | Teal-tinted shadow |
| **Body text colour** | Browser default | `#343a40` | Explicit dark gray |

---

## Proposed Actions

### 1. Update CSS custom properties (low risk)
Add the ukbol.org palette variables alongside the existing traffic-light status colours (which must stay as-is for data visualization):
```css
:root {
  /* ukbol.org brand palette */
  --ukbol-primary:     #1a4d5a;
  --ukbol-primary-mid: #2b7a8c;
  --ukbol-accent-light:#6ab8c8;
  --ukbol-gold:        #d4a017;
  --ukbol-text:        #343a40;
  --ukbol-bg:          #f5f7fa;
  /* existing status colours stay unchanged */
  --ukbol-green:#198754; --ukbol-amber:#ffc107; ...
}
```

### 2. Swap primary/accent colours in gradients and backgrounds (medium risk)
Replace all occurrences of:
- `#1a365d` → `#1a4d5a` (primary navy → deep teal)
- `#2d5a87` → `#2b7a8c` (accent steel → medium teal)

Affects: hero gradient, card headers, navbar, footer, stat-number colour.

### 3. Update page background (low risk)
Change `background: linear-gradient(135deg,#f5f7fa 0%,#e4e8ec 100%)` to flat `background: #f5f7fa` on both index and report pages.

### 4. Set body text colour explicitly (low risk)
Add `color: #343a40` to the body rule.

### 5. Style headings to match ukbol.org (low risk)
Add heading colour rules so section headings (h3 "Gene Datasets", h4 "How to Use", h5 filter labels, etc.) pick up the teal tones:
- h1, h2: `color: #1a4d5a`
- h3: `color: #2b7a8c`

### 6. Style links to match ukbol.org (low risk)
Add `a { color: #2b7a8c; } a:hover { color: #1a4d5a; }` — avoids touching Bootstrap utility classes that handle buttons/badges.

### 7. Restyle the index page hero/navbar (medium risk)
Change the hero section from dark teal gradient with white text to match the ukbol.org pattern:
- Add a **white navbar** above the hero with the UKBOL text logo on the left and a "Back to UKBOL" link on the right
- Keep the hero gradient but use the new teal colours: `linear-gradient(135deg, #1a4d5a 0%, #2b7a8c 100%)`

### 8. Restyle the report page navbar (medium risk)
The report pages currently have a dark gradient navbar. Change to:
- **White background** navbar with bottom border (`2px solid #e8f4f8`) and subtle shadow
- UKBOL text logo on the left (linked to index)
- "Back to Portal" link + dataset name on the right
- Text colours switched to `#1a4d5a` to remain readable on white

### 9. Update card hover shadows (low risk)
Change card hover shadow from `rgba(0,0,0,.12)` to `rgba(26,77,90,.15)` — teal-tinted, matching ukbol.org.

### 10. Add logo to footer (low risk)
Add the UKBOL text logo (60px, white-filtered via `filter: brightness(0) invert(1)`) above the footer text, matching the ukbol.org footer layout.

### 11. Update footer colour (low risk)
Change footer background from `#1a365d` to `#1a4d5a`.

### 12. Copy logo assets to docs/ (required for deployment)
The logos in `assets/images/` need to be available in `docs/` (or a relative path from docs/) since the built site is served from `/docs`. Either:
- Copy them into `docs/assets/images/` during build, or
- Reference them via relative path `../assets/images/` (may not work on GitHub Pages)

Best approach: add a step in `build.py` to copy logo assets into `docs/`.

---

## What NOT to Change
- **Status badge colours** (`--ukbol-green`, `--ukbol-amber`, `--ukbol-red`, `--ukbol-blue`, `--ukbol-black`) — these are data-encoding colours for gap analysis categories and must remain as-is
- **Chart colours** (Plotly pie/bar charts use the same status palette) — no change
- **DataTables styling** — functional, no visual alignment needed
- **Bootstrap version** — already matching at 5.3.3
- **Font stack** — already matching (`system-ui, -apple-system, sans-serif`)
- **Filter panel / interactive components** — functional layout, no design equivalent on ukbol.org
- **JavaScript / data loading** — purely functional, no changes

---

## Risk Assessment
- **Low risk items (1, 3, 4, 5, 6, 9, 10, 11):** Pure colour/text changes, no layout shifts
- **Medium risk items (2, 7, 8):** Layout changes to nav/hero — could affect readability or spacing; will need visual review
- **Item 12:** Build process change — straightforward but needs testing

All changes are confined to `scripts/build.py` (the HTML/CSS templates) plus a minor asset-copy addition. No JavaScript logic changes needed.
