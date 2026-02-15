# UKBOL Website Migration: Implementation Plan

## Overview

Migrate the informational content from the current Drupal-based `ukbol.org` website to a Jekyll-powered static site hosted on GitHub Pages at `ukbol.github.io`. The existing gap analysis data portal (standalone HTML/JS pages under `/species/`) will be preserved as-is and integrated into the new site navigation.

---

## Architecture

**Approach:** Hybrid Jekyll + standalone HTML portal

- **Jekyll** handles the informational wrapper site: homepage, about, related projects, publications, shared navigation, footer, and consistent branding.
- **Existing HTML portal pages** (gap analysis data tables) remain as standalone HTML/JS files — Jekyll passes through any `.html` files that don't have front matter, so these work untouched.
- GitHub Pages builds Jekyll natively — no CI/CD pipeline needed.

---

## Current Repo Structure (before migration)

```
species/
├── docs/                    # GitHub Pages source (currently serving from /docs)
│   ├── index.html           # Gap analysis portal landing page
│   ├── bold_coi.html        # Gene region pages (standalone HTML/JS)
│   ├── midori_12s.html
│   ├── midori_16s.html
│   ├── ncbi_rbcl.html
│   ├── unite_its.html
│   ├── dtol_genome.html
│   └── data/                # Compressed JSON data files
├── data/                    # Raw TSV gap analysis data
├── metadata/
├── scripts/                 # Python build scripts
├── planning/
└── README.md
```

---

## Target Repo Structure (after migration)

```
species/
├── docs/                         # GitHub Pages root (Jekyll source)
│   ├── _config.yml               # Jekyll configuration
│   ├── _layouts/
│   │   ├── default.html          # Base layout (nav, footer, head)
│   │   └── page.html             # Standard content page layout
│   ├── _includes/
│   │   ├── nav.html              # Shared navigation bar
│   │   └── footer.html           # Shared footer
│   ├── _sass/
│   │   └── ukbol.scss            # Custom UKBOL styles (optional, can use inline)
│   ├── assets/
│   │   ├── css/
│   │   │   └── style.scss        # Main stylesheet entry point
│   │   └── images/
│   │       ├── ukbol-logo.png    # UKBOL logo (dragonfly + DNA helix)
│   │       └── ukbol-logo-white.png  # White variant for dark nav
│   │
│   ├── index.md                  # NEW: Main homepage (Jekyll, Markdown)
│   ├── about.md                  # NEW: About UKBOL page
│   ├── projects.md               # NEW: Related projects page
│   ├── publications.md           # NEW: Publications page
│   │
│   ├── species/                  # MOVED: Portal pages go into subdirectory
│   │   ├── index.html            # Gap analysis portal landing (existing, unchanged)
│   │   ├── bold_coi.html         # Existing gene pages (unchanged)
│   │   ├── midori_12s.html
│   │   ├── midori_16s.html
│   │   ├── ncbi_rbcl.html
│   │   ├── unite_its.html
│   │   ├── dtol_genome.html
│   │   └── data/                 # Existing compressed data files
│   │
│   ├── .nojekyll-exclude         # NOT needed — see note below
│   └── 404.md                    # Custom 404 page (optional)
│
├── data/                         # Raw TSV data (unchanged)
├── metadata/
├── scripts/                      # Python build scripts (unchanged)
├── planning/
└── README.md
```

### Key structural decisions

1. **Portal pages move to `docs/species/`** so the root `docs/` can serve Jekyll content pages. The portal will be accessible at `ukbol.github.io/species/` (same URL as now if the repo is configured with a custom domain, or adjust links accordingly).

2. **Portal HTML files must NOT have Jekyll front matter** (the `---` YAML block at the top). Jekyll will copy them through as-is since they lack front matter. This means the existing portal pages require zero modifications.

3. **Alternatively**, if moving files into a subdirectory is undesirable, you can keep the portal pages at root level inside `docs/` alongside the Jekyll `.md` files. Jekyll will only process files with front matter. The trade-off is a slightly messier directory, but it works fine.

---

## Design Specification

### Colour Palette (extracted from logo and existing portal)

| Role | Colour | Hex | Usage |
|------|--------|-----|-------|
| Primary dark | Dark teal/navy | `#1a365d` | Navbar background, hero sections, headings |
| Primary mid | Teal blue | `#2d5a87` | Gradient endpoint, hover states |
| Accent teal | Light teal (from DNA helix in logo) | `#5ba4c9` | Links, accent highlights |
| Text dark | Near-black | `#343a40` | Body text |
| Text muted | Grey | `#6c757d` | Secondary text, captions |
| Background | Off-white | `#f5f7fa` | Page background |
| Background alt | Light grey | `#e4e8ec` | Gradient endpoint, card backgrounds |
| Card white | White | `#ffffff` | Content cards |
| Status green | Green | `#198754` | Status badges (carried from portal) |
| Status amber | Amber | `#ffc107` | Status badges |
| Status red | Red | `#dc3545` | Status badges |
| Status blue | Blue | `#0d6efd` | Status badges |

### Typography

- **Font stack:** `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` (matches existing portal)
- **Headings:** Font-weight 600-700, colour `#1a365d`
- **Body text:** 16px base, 1.6 line height, colour `#343a40`

### Framework

- **Bootstrap 5.3.3** via CDN (same version as portal) — for grid, utility classes, and responsive behaviour
- No additional CSS frameworks — keep it lightweight and academic

### Design Principles

- Clean, professional academic aesthetic — similar to NHM, DEFRA, or Natural England publications
- No hero images or fancy animations — content-first
- Generous white space, readable line lengths (max ~750px for prose)
- Consistent navigation across Jekyll pages AND portal pages (see nav component below)

---

## Component Specifications

### 1. Navigation Bar (`_includes/nav.html`)

```html
<nav class="navbar navbar-expand-lg navbar-dark" style="background:linear-gradient(135deg,#1a365d 0%,#2d5a87 100%);">
  <div class="container">
    <a class="navbar-brand d-flex align-items-center" href="{{ site.baseurl }}/">
      <img src="{{ site.baseurl }}/assets/images/ukbol-logo-white.png" alt="UKBOL" height="40" class="me-2">
      <span>UK Barcode of Life</span>
    </a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navContent">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navContent">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item"><a class="nav-link" href="{{ site.baseurl }}/">Home</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ site.baseurl }}/about">About</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ site.baseurl }}/projects">Projects</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ site.baseurl }}/publications">Publications</a></li>
        <li class="nav-item"><a class="nav-link fw-bold" href="{{ site.baseurl }}/species/">Data Portal</a></li>
      </ul>
    </div>
  </div>
</nav>
```

**Note on portal integration:** The existing portal HTML pages do NOT use Jekyll layouts. To add the shared nav to those pages, you have two options:
- **Option A (recommended):** Add the same nav HTML manually to each portal page (6 files, one-time edit). This keeps them fully standalone.
- **Option B:** Convert portal pages to use Jekyll layout by adding front matter. This is riskier as it may interfere with the complex inline JS.

### 2. Footer (`_includes/footer.html`)

```html
<footer style="background:#1a365d;color:rgba(255,255,255,.8);padding:2rem 0;margin-top:3rem;">
  <div class="container text-center">
    <img src="{{ site.baseurl }}/assets/images/ukbol-logo-white.png" alt="UKBOL" height="50" class="mb-3">
    <p class="mb-1">UK Barcode of Life (UKBOL)</p>
    <p class="small mb-2">
      Coordinated by the <a href="https://www.nhm.ac.uk" style="color:rgba(255,255,255,.9);">Natural History Museum, London</a>
      | Part of <a href="https://ibol.org/" style="color:rgba(255,255,255,.9);">International Barcode of Life</a>
    </p>
    <p class="small mb-0" style="color:rgba(255,255,255,.5);">
      Funded by <a href="https://www.gov.uk/government/organisations/department-for-environment-food-rural-affairs" style="color:rgba(255,255,255,.6);">DEFRA</a>
      via the <a href="https://www.gov.uk/government/organisations/natural-england" style="color:rgba(255,255,255,.6);">Natural England</a> Centre of Excellence for DNA Methods
    </p>
  </div>
</footer>
```

### 3. Default Layout (`_layouts/default.html`)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ page.title }} | UK Barcode of Life</title>
  <meta name="description" content="{{ page.description | default: site.description }}">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    :root {
      --ukbol-primary: #1a365d;
      --ukbol-primary-mid: #2d5a87;
      --ukbol-accent: #5ba4c9;
      --ukbol-text: #343a40;
      --ukbol-bg: #f5f7fa;
    }
    body {
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: var(--ukbol-bg);
      color: var(--ukbol-text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    main { flex: 1; }
    .content-wrapper {
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem 1rem;
    }
    .content-wrapper h1 { color: var(--ukbol-primary); font-weight: 700; margin-bottom: 1.5rem; }
    .content-wrapper h2 { color: var(--ukbol-primary); font-weight: 600; margin-top: 2rem; margin-bottom: 1rem; }
    .content-wrapper h3 { color: var(--ukbol-primary-mid); font-weight: 600; margin-top: 1.5rem; }
    .content-wrapper p { line-height: 1.7; margin-bottom: 1rem; }
    .content-wrapper a { color: var(--ukbol-accent); }
    .content-wrapper a:hover { color: var(--ukbol-primary); }
    .content-wrapper table { width: 100%; margin: 1.5rem 0; }
    .content-wrapper table th { background: var(--ukbol-primary); color: #fff; padding: .5rem .75rem; font-weight: 600; font-size: .9rem; }
    .content-wrapper table td { padding: .5rem .75rem; border-bottom: 1px solid #e9ecef; font-size: .9rem; }
    .content-wrapper table tr:hover { background: #f8f9fa; }
    /* Hero for homepage only */
    .page-hero {
      background: linear-gradient(135deg, #1a365d 0%, #2d5a87 100%);
      color: #fff;
      padding: 3rem 0;
    }
    .page-hero h1 { color: #fff; }
  </style>
</head>
<body>
  {% include nav.html %}
  <main>
    {{ content }}
  </main>
  {% include footer.html %}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

### 4. Page Layout (`_layouts/page.html`)

```html
---
layout: default
---
<div class="container">
  <div class="content-wrapper">
    <h1>{{ page.title }}</h1>
    {{ content }}
  </div>
</div>
```

---

## Jekyll Configuration (`_config.yml`)

```yaml
title: UK Barcode of Life
description: >-
  UK Barcode of Life (UKBOL) — the UK national node of the International
  Barcode of Life initiative. Building comprehensive DNA barcode reference
  libraries for UK biodiversity.
baseurl: ""             # Empty — using custom domain ukbol.org
url: "https://ukbol.org"

# Build settings
markdown: kramdown
kramdown:
  input: GFM

# Exclude from build
exclude:
  - README.md
  - LICENSE
  - scripts/
  - data/
  - metadata/
  - planning/
  - update.bat
  - "*.tsv"

# Permalink structure
permalink: /:title/

# Default front matter
defaults:
  - scope:
      path: ""
      type: "pages"
    values:
      layout: "page"
```

**Important baseurl note:** With the custom domain `ukbol.org`, `baseurl` is set to `""` (empty string). All `{{ site.baseurl }}` references in templates will resolve cleanly. The site will serve from the root of the domain.

---

## Page Content Templates

### Homepage (`index.md`)

```markdown
---
layout: default
title: UK Barcode of Life
---

<div class="page-hero">
  <div class="container">
    <div class="row align-items-center">
      <div class="col-lg-8">
        <h1>UK Barcode of Life</h1>
        <p class="lead">Building comprehensive DNA barcode reference libraries for UK biodiversity</p>
      </div>
      <div class="col-lg-4 text-lg-end">
        <img src="{{ site.baseurl }}/assets/images/ukbol-logo-white.png" alt="UKBOL" height="80">
      </div>
    </div>
  </div>
</div>

<div class="container">
  <div class="content-wrapper">

<!-- ADD YOUR HOMEPAGE TEXT BELOW THIS LINE -->



<!-- END HOMEPAGE TEXT -->

## Explore the Data

Visit the [Gap Analysis Data Portal]({{ site.baseurl }}/species/) to explore DNA barcode coverage across **79,027 UK species** and **6 gene regions**.

  </div>
</div>
```

### About Page (`about.md`)

```markdown
---
layout: page
title: About UKBOL
---

<!-- ADD YOUR ABOUT PAGE TEXT BELOW THIS LINE -->



<!-- END ABOUT TEXT -->
```

### Related Projects Page (`projects.md`)

```markdown
---
layout: page
title: Related Projects
---

<!-- ADD YOUR RELATED PROJECTS TEXT BELOW THIS LINE -->



<!-- END RELATED PROJECTS TEXT -->
```

### Publications Page (`publications.md`)

```markdown
---
layout: page
title: Publications
---

<!-- ADD YOUR PUBLICATIONS TEXT BELOW THIS LINE -->



<!-- END PUBLICATIONS TEXT -->
```

---

## Implementation Steps

### Phase 1: Prepare the repo structure

1. Inside `docs/`, create a new subdirectory `species/`.
2. Move ALL existing portal files into `docs/species/`:
   - `index.html` → `docs/species/index.html`
   - `bold_coi.html` → `docs/species/bold_coi.html`
   - `midori_12s.html` → `docs/species/midori_12s.html`
   - `midori_16s.html` → `docs/species/midori_16s.html`
   - `ncbi_rbcl.html` → `docs/species/ncbi_rbcl.html`
   - `unite_its.html` → `docs/species/unite_its.html`
   - `dtol_genome.html` → `docs/species/dtol_genome.html`
   - `data/` → `docs/species/data/`
3. Verify NONE of the moved HTML files have `---` front matter at the top (they don't currently — confirmed).

### Phase 2: Create Jekyll structure

4. Create `docs/_config.yml` with the configuration above.
5. Create `docs/_layouts/default.html` with the layout above.
6. Create `docs/_layouts/page.html` with the page layout above.
7. Create `docs/_includes/nav.html` with the navigation component.
8. Create `docs/_includes/footer.html` with the footer component.
9. Create `docs/assets/images/` and add the UKBOL logo files:
   - `ukbol-logo.png` (the colour version provided)
   - `ukbol-logo-white.png` (white version for navbar — create or source this)

### Phase 3: Create content pages

10. Create `docs/index.md` (homepage) using the template above. Add homepage text.
11. Create `docs/about.md` using the template above. Add about text from your text file.
12. Create `docs/projects.md` using the template above. Add related projects text.
13. Create `docs/publications.md` using the template above. Add publications text.

### Phase 4: Update portal pages for consistent navigation (Optional but recommended)

14. In each of the 6 portal HTML files inside `docs/species/`, add the shared navigation bar HTML at the top of `<body>`. This is a manual copy-paste of the nav HTML (without Liquid template tags — use hardcoded relative paths instead).
15. Update the "Back to Portal" link in gene page navbars to also include a "Back to UKBOL" link.
16. Update the portal `index.html` footer to link back to the main site.

### Phase 5: Update the build script

17. Update `scripts/build.py` so that its output paths target `docs/species/` instead of `docs/` for the generated portal HTML and data files.
18. Update `update.bat` if it references old paths.

### Phase 6: Update internal links in portal pages

19. In the portal's `docs/species/index.html`, verify that gene page links are relative (e.g., `bold_coi.html` not `/species/bold_coi.html`) — they currently use relative links so this should work without changes.
20. In each gene page, verify the "Back to Portal" link points to `index.html` (relative) — currently correct.

### Phase 7: Test locally

21. Install Jekyll locally: `gem install bundler jekyll`
22. From `docs/`, run: `bundle init && bundle add jekyll && bundle exec jekyll serve`
23. Verify:
    - Homepage renders at `localhost:4000/`
    - About, Projects, Publications pages load correctly
    - Navigation links work across all pages
    - Portal at `localhost:4000/species/` loads correctly
    - Gene region pages load and display data correctly
    - Mobile responsive layout works

### Phase 8: Deploy

24. Create `docs/CNAME` containing a single line: `ukbol.org`
25. Commit and push to GitHub.
26. In GitHub repo Settings → Pages, ensure source is set to "Deploy from a branch" → `main` branch → `/docs` folder. Set custom domain to `ukbol.org` and enable HTTPS.
27. Configure DNS at your domain registrar: add an A record pointing to GitHub Pages IPs (or a CNAME to `ukbol.github.io`).
28. Verify the live site at `https://ukbol.org/`.

---

## URL Structure (after migration, with custom domain ukbol.org)

| Page | URL |
|------|-----|
| Homepage | `ukbol.org/` |
| About | `ukbol.org/about/` |
| Related Projects | `ukbol.org/projects/` |
| Publications | `ukbol.org/publications/` |
| Data Portal | `ukbol.org/species/` |
| COI gap analysis | `ukbol.org/species/bold_coi.html` |
| 12S gap analysis | `ukbol.org/species/midori_12s.html` |
| (etc.) | |

---

## Future Considerations

- **Custom domain:** Add a `CNAME` file to `docs/` containing `ukbol.org`. Configure DNS for `ukbol.org` to point to GitHub Pages (either an A record to GitHub's IPs or a CNAME to `ukbol.github.io`). Enable HTTPS in repo Settings → Pages.
- **DNS redirect:** Ensure `www.ukbol.org` redirects to `ukbol.org` (or vice versa) via DNS provider settings.
- **Jekyll theme:** The implementation above uses a fully custom layout. If you later want a more polished base, consider `just-the-docs` or `minimal-mistakes` Jekyll themes — but the custom approach gives you complete control and matches the portal aesthetic.
- **Automated portal rebuild:** Your existing `scripts/build.py` can be wrapped in a GitHub Action to auto-update portal data on a schedule.

---

## Dependencies

- **Jekyll** (GitHub Pages built-in, no installation needed for deployment)
- **Bootstrap 5.3.3** via CDN (already used by portal)
- **Logo files** (colour and white versions)
- **Page content** in text files (to be pasted into Markdown templates)

---

## Review: Critical Analysis

_Review conducted 2026-02-15 against the current codebase._

### Assessment Summary

The plan is well-structured and covers the core architecture correctly. The hybrid Jekyll + standalone HTML approach is sound — portal HTML files without front matter will pass through the Jekyll build untouched, preserving all interactive functionality. The design specification, component templates, and Jekyll configuration are all production-ready.

However, there are several issues ranging from critical (will break things) to moderate (should be addressed) that need resolution before implementation begins.

---

### CRITICAL Issues

#### 1. Old URL breakage — no redirect strategy

**Problem:** The portal currently serves at `ukbol.github.io/species/` (where `/species/` is the repo name path). When the custom domain `ukbol.org` is configured, GitHub Pages redirects `ukbol.github.io/species/*` to `ukbol.org/*` — stripping the repo name prefix. But after migration, portal pages live at `ukbol.org/species/` (a real subdirectory). This means:

- Old link: `ukbol.github.io/species/bold_coi.html` → redirects to → `ukbol.org/bold_coi.html` → **404**
- Correct new link: `ukbol.org/species/bold_coi.html`

Any bookmarks, shared URLs (including filter-state URLs like `?kingdom=Animalia&status=GREEN`), or external links to the portal will break.

**Fix:** Add a new Phase between Phases 3 and 4:

- Create redirect HTML files at the root of `docs/` for each portal page. These catch traffic that lands at `ukbol.org/bold_coi.html` and redirect to `ukbol.org/species/bold_coi.html`. Use the `jekyll-redirect-from` plugin (supported by GitHub Pages) or simple static HTML redirects:
  ```
  docs/bold_coi.html      → meta refresh redirect to /species/bold_coi.html
  docs/midori_12s.html    → meta refresh redirect to /species/midori_12s.html
  docs/midori_16s.html    → meta refresh redirect to /species/midori_16s.html
  docs/ncbi_rbcl.html     → meta refresh redirect to /species/ncbi_rbcl.html
  docs/unite_its.html     → meta refresh redirect to /species/unite_its.html
  docs/dtol_genome.html   → meta refresh redirect to /species/dtol_genome.html
  ```
- These files MUST NOT have Jekyll front matter (to avoid layout wrapping). Example content:
  ```html
  <!DOCTYPE html>
  <html><head>
  <meta http-equiv="refresh" content="0;url=/species/bold_coi.html">
  <link rel="canonical" href="https://ukbol.org/species/bold_coi.html">
  </head><body>
  <p>Moved to <a href="/species/bold_coi.html">/species/bold_coi.html</a></p>
  </body></html>
  ```
- These redirect files must preserve query string parameters so shared filter URLs continue to work. A small JavaScript snippet may be needed since meta refresh does not forward query strings:
  ```html
  <script>
  window.location.replace('/species/bold_coi.html' + window.location.search + window.location.hash);
  </script>
  ```

#### 2. Phase 4 must not be optional — portal navigation is essential

**Problem:** Phase 4 is marked "Optional but recommended". Without it, users who land on the portal (which is likely the majority of traffic) have no way to navigate to the new website pages. The portal pages currently have no link to a parent site at all.

**Fix:** Remove "(Optional but recommended)" from Phase 4. Make it a required phase. At minimum, the portal `index.html` needs a site-wide navbar and footer. The gene pages should at least get a "UKBOL Home" link added to their existing navbar.

#### 3. `_config.yml` exclude list references non-existent paths

**Problem:** The `exclude` list contains `scripts/`, `data/`, `metadata/`, `planning/`, `update.bat`, and `"*.tsv"`. Since GitHub Pages is configured to build from the `/docs` folder, Jekyll's source directory is `/docs`. None of these directories exist inside `/docs` — they're at the repo root. The exclude directives do nothing and are misleading.

**Fix:** Remove the incorrect entries. The only entries that matter are files actually inside `docs/`:
```yaml
exclude:
  - README.md
  - CNAME
  - Gemfile
  - Gemfile.lock
```
Note: `README.md` should only be excluded if there's one inside `docs/`. If not, remove it too.

#### 4. Build script update needs more specificity

**Problem:** Step 17 says "Update `scripts/build.py` so that its output paths target `docs/species/`". This is vague. The build script uses `--output` with a default of `docs` (line 910 of `build.py`). Simply changing this default would work, but the plan should be explicit about what changes.

**Fix:** Replace step 17 with:
- In `scripts/build.py`, change the `--output` default on line 910 from `'docs'` to `'docs/species'`:
  ```python
  parser.add_argument('--output', default='docs/species', help='Output directory')
  ```
- This single change ensures all generated files (HTML pages, `data/*.json.gz`, `data/*.tsv`) go to `docs/species/` on the next build.
- Update the build script's navbar HTML template (line 439) to add a "UKBOL Home" link alongside the "Back to Portal" link.
- Update the build script's index page generation (`generate_index_html`) to include a link back to the main website in the footer/header.

#### 5. `update.bat` path for build script invocation

**Problem:** Step 18 says "Update `update.bat` if it references old paths". The current `update.bat` calls `python scripts\build.py` with no `--output` argument, relying on the default. If the default changes per issue #4 above, `update.bat` will work correctly without changes. However, `update.bat` also does `git add .` which would stage all files including new Jekyll files — this is fine but worth noting.

**Fix:** Confirm explicitly in the plan that `update.bat` requires no changes if the `build.py` default is updated. Consider adding a note that `git add .` in `update.bat` will also stage any Jekyll infrastructure files if they've been modified.

---

### MODERATE Issues

#### 6. Missing `docs/CNAME` in Phase 2 — duplicated in Phase 8 and Future Considerations

**Problem:** The CNAME file appears in three places: the target repo structure (not listed), Phase 8 step 24, and the "Future Considerations" section. The "Future Considerations" section implies it's optional/future when it's actually a required deployment step.

**Fix:**
- Keep the CNAME creation in Phase 8 (step 24) where it currently is — that's the correct place.
- Remove the "Custom domain" bullet from "Future Considerations" since it's already covered in Phase 8.
- Add `CNAME` to the target repo structure diagram.

#### 7. Missing `www.ukbol.org` DNS setup in deployment steps

**Problem:** The `www` subdomain setup is listed under "Future Considerations" but should be part of the DNS configuration in Phase 8. Users will try `www.ukbol.org` and get an error if this isn't set up.

**Fix:** Move the `www.ukbol.org` redirect instruction into Phase 8, step 27. Add: "Also configure a CNAME record for `www.ukbol.org` pointing to `ukbol.github.io`, or set up a redirect from `www.ukbol.org` to `ukbol.org` via your DNS provider."

#### 8. Missing 404 page implementation

**Problem:** `404.md` is listed in the target structure as "(optional)" but given the URL restructuring (and the redirect issue in #1), a custom 404 page becomes important. Users hitting broken links need guidance.

**Fix:** Make `404.md` a required file. Create it in Phase 3 with content that links to both the homepage and the data portal:
```markdown
---
layout: default
title: Page Not Found
permalink: /404.html
---
<div class="container">
  <div class="content-wrapper text-center">
    <h1>Page Not Found</h1>
    <p>The page you're looking for may have moved.</p>
    <p><a href="/">Return to Homepage</a> | <a href="/species/">Go to Data Portal</a></p>
  </div>
</div>
```

#### 9. Testing checklist is incomplete

**Problem:** Phase 7 (step 23) lists basic checks but omits portal-specific functionality that could break.

**Fix:** Add these verification items to step 23:
- Data loads correctly on gene pages (check browser console for fetch errors on `data/*.json.gz`)
- Filter state URL sharing works (apply filters, copy URL, open in new tab — filters should restore)
- CSV export and TSV download both work
- Plotly charts render (pie chart and bar chart)
- DataTables pagination, search, and sorting work
- Taxonomy cascading dropdowns work (select Kingdom → Phylum options update)
- "Back to Portal" links on gene pages work
- New website nav links from portal pages work (if Phase 4 implemented)

#### 10. Portal nav integration (Phase 4) needs build script alignment

**Problem:** Phase 4 step 14 says to manually add nav HTML to portal pages. But the portal pages are regenerated by `build.py` on every data update. Any manual edits will be overwritten on the next build.

**Fix:** The nav/footer additions for portal pages must be made in `build.py`, not manually in the HTML files. Specifically:
- Update the `generate_report_html` function to include the site-wide nav bar above the existing portal navbar.
- Update the `generate_index_html` function to include the site-wide nav bar and footer.
- Use hardcoded absolute paths (`/`, `/about/`, `/species/`) rather than Liquid template tags since these are standalone HTML files.

Rewrite Phase 4 steps 14-16 to reference build script changes rather than manual edits.

#### 11. Homepage species count will become stale

**Problem:** The homepage template (`index.md`) hardcodes "79,027 UK species" and "6 gene regions". These numbers change when data is updated, but the Markdown file won't be regenerated by the build script.

**Fix:** Either:
- Accept that this number is manually maintained (low maintenance given infrequent changes), or
- Have `build.py` generate a Jekyll data file (e.g., `docs/_data/stats.yml`) with current statistics, then reference it in `index.md` as `{{ site.data.stats.total_species }}`. This keeps the count automatically in sync.

---

### MINOR Issues

#### 12. `_sass/` and `assets/css/style.scss` listed but unused

**Problem:** The target structure includes `_sass/ukbol.scss` and `assets/css/style.scss` but all styles are defined inline in `_layouts/default.html`. These files are never referenced in the implementation steps.

**Fix:** Remove `_sass/` and `assets/css/style.scss` from the target repo structure, or add an implementation step to extract the inline styles into these files. The inline approach is simpler and works fine.

#### 13. Permalink structure may conflict with portal pages

**Problem:** The `_config.yml` sets `permalink: /:title/` which adds trailing slashes. This is fine for Jekyll-processed pages (`about/`, `projects/`). However, confirm that this permalink setting does NOT affect the standalone HTML portal pages (it shouldn't, since they lack front matter — but worth verifying during testing).

**Fix:** Add a note to Phase 7 testing: "Verify that the `permalink` setting does not affect portal HTML files (they should be served at their literal file paths, e.g., `/species/bold_coi.html`)."

#### 14. No mention of `Gemfile` for local development

**Problem:** Step 22 suggests `bundle init && bundle add jekyll` but doesn't mention committing a `Gemfile` or `Gemfile.lock`. GitHub Pages uses its own gem versions, so these files aren't strictly needed for deployment. But for local development consistency, they're useful.

**Fix:** Add a note: "Optionally commit `Gemfile` and `Gemfile.lock` for reproducible local development. Add them to `.gitignore` if you prefer not to track them." Also add `Gemfile` and `Gemfile.lock` to the `_config.yml` exclude list to prevent Jekyll from copying them to the built site.

#### 15. No `robots.txt` or sitemap

**Problem:** No mention of SEO basics. If the old `ukbol.org` Drupal site is currently indexed by search engines, the migration will affect search rankings.

**Fix:** Add `jekyll-sitemap` to the `_config.yml` plugins list (it's supported by GitHub Pages and generates `/sitemap.xml` automatically). Consider adding a `robots.txt` to `docs/`:
```
User-agent: *
Allow: /
Sitemap: https://ukbol.org/sitemap.xml
```

---

### Items the Plan Handles Correctly

For completeness, these aspects are well-covered:

- **Relative links within portal** — All portal internal links (`bold_coi.html`, `data/bold_coi.json.gz`, `index.html`) are relative. They will continue to work after the move to `docs/species/` without modification. Verified in both the HTML output and `build.py` source.
- **Jekyll passthrough for HTML without front matter** — Correctly identified that portal HTML files lack `---` front matter and will be copied through by Jekyll untouched.
- **Bootstrap version consistency** — Both Jekyll pages and portal use Bootstrap 5.3.3 via CDN.
- **Design/branding coherence** — Colour palette, typography, and gradient styles are extracted from the existing portal and applied consistently.
- **baseurl configuration** — Correctly set to `""` for custom domain use.
- **URL structure** — The target URL table is correct and clean.
