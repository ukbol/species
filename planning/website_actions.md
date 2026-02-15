# UKBOL Website: Implementation Plan

> **Last updated:** 2026-02-15
> **Status:** Planning complete — ready for Phase 1 implementation

---

## Progress Tracker

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Create website repo and Jekyll infrastructure | `[ ] NOT STARTED` |
| 2 | Create content pages | `[ ] NOT STARTED` |
| 3 | Local testing | `[ ] NOT STARTED` |
| 4 | Deploy to GitHub Pages | `[ ] NOT STARTED` |
| 5 | Custom domain setup (ukbol.org) | `[ ] NOT STARTED` |
| 6 | Portal integration (ukbol/species repo) | `[ ] NOT STARTED` |
| 7 | Final testing | `[ ] NOT STARTED` |

### Session Log

| Date | Session | Work Done |
|------|---------|-----------|
| 2026-02-15 | 1 | Created initial plan; reviewed against codebase; rewrote for two-repo approach |
| | | |

---

## Overview

Build the UKBOL informational website (homepage, about, projects, publications) as a Jekyll static site in a **new, separate repo** (`ukbol/ukbol.github.io`). The existing gap analysis data portal in `ukbol/species` remains untouched during website development. Once the website is functional, the portal is integrated via navigation links and build script updates — no portal files are moved.

### Why a separate repo?

- **Zero risk to the portal** — the `ukbol/species` repo is not modified until Phase 6
- **Independent development** — website can be built, tested, and deployed without affecting portal availability
- **Clean separation** — informational content lives in its own repo; data portal lives in its own repo

---

## Architecture Decision: Repo Naming

### Recommended: `ukbol/ukbol.github.io` (GitHub org-level site)

A repo named `<org>.github.io` is treated as the **organisation-level GitHub Pages site**. This has a critical advantage:

- `ukbol.github.io/` serves from `ukbol/ukbol.github.io`
- `ukbol.github.io/species/` **automatically** serves from `ukbol/species` (project site)
- When custom domain `ukbol.org` is set on the org site:
  - `ukbol.org/` → website (from `ukbol/ukbol.github.io`)
  - `ukbol.org/species/` → portal (from `ukbol/species`) — **automatically, no changes needed**

This means **no portal files need to move**, no redirects are needed, and existing portal URLs at `ukbol.github.io/species/*` seamlessly become `ukbol.org/species/*`.

### Alternative: `ukbol/website`

If you use `ukbol/website` instead:
- It serves at `ukbol.github.io/website/` by default
- With custom domain `ukbol.org`, the website serves at `ukbol.org/`
- **But** the portal in `ukbol/species` stays at `ukbol.github.io/species/` — it does NOT appear under `ukbol.org/species/`
- To serve the portal at `ukbol.org/species/`, you would need to copy portal output files into the website repo

**This plan assumes the recommended approach: `ukbol/ukbol.github.io`.** If you choose `ukbol/website`, an additional step is needed in Phase 6 to copy portal files into the website repo (noted where relevant).

---

## Target Repo Structure (`ukbol/ukbol.github.io`)

```
ukbol.github.io/
├── _config.yml
├── _layouts/
│   ├── default.html           # Base layout (nav, footer, head)
│   └── page.html              # Standard content page layout
├── _includes/
│   ├── nav.html               # Shared navigation bar
│   └── footer.html            # Shared footer
├── assets/
│   └── images/
│       ├── ukbol-logo.png     # UKBOL logo (colour)
│       └── ukbol-logo-white.png   # White variant for dark nav
├── index.md                   # Homepage
├── about.md                   # About UKBOL
├── projects.md                # Related projects
├── publications.md            # Publications
├── 404.md                     # Custom 404 page
├── robots.txt                 # Search engine directives
├── CNAME                      # Custom domain: ukbol.org
├── Gemfile                    # Local dev dependencies
└── README.md
```

**Note:** No portal files live here. The portal continues to be served from `ukbol/species` at `/species/`.

---

## Existing Portal Structure (`ukbol/species` — unchanged until Phase 6)

```
species/
├── docs/                      # GitHub Pages source (serving at /species/)
│   ├── index.html             # Portal landing page (6 gene cards, stats)
│   ├── bold_coi.html          # Gene region pages (standalone HTML/JS)
│   ├── midori_12s.html
│   ├── midori_16s.html
│   ├── ncbi_rbcl.html
│   ├── unite_its.html
│   ├── dtol_genome.html
│   └── data/                  # Compressed JSON + TSV data files
├── data/                      # Raw TSV gap analysis input
├── metadata/
├── scripts/
│   └── build.py               # Generates all portal HTML + data files
├── planning/
│   └── website_actions.md     # This file
└── update.bat                 # Windows: copy data → build → deploy
```

### Portal details relevant to integration

- **All internal links are relative** — gene pages link to `data/bold_coi.json.gz`, `index.html`, etc. These work regardless of what URL prefix the site is served under.
- **Portal pages have NO Jekyll front matter** (`---` block) — they are plain HTML and will pass through any Jekyll build untouched.
- **Portal pages are regenerated by `build.py`** — any manual edits to HTML files are overwritten on the next data update. All persistent changes must go into `build.py`.
- **build.py output default** is `--output docs` (line 910). The data path in generated HTML is `data/<gene>.json.gz` (relative).
- **Navbar in gene pages** has a "Back to Portal" link pointing to `index.html` (relative).
- **Portal index** links to gene pages via relative hrefs: `bold_coi.html`, `midori_12s.html`, etc.

---

## Design Specification

### Colour Palette (from logo and existing portal)

| Role | Hex | Usage |
|------|-----|-------|
| Primary dark | `#1a365d` | Navbar background, hero sections, headings |
| Primary mid | `#2d5a87` | Gradient endpoint, hover states |
| Accent teal | `#5ba4c9` | Links, accent highlights |
| Text dark | `#343a40` | Body text |
| Text muted | `#6c757d` | Secondary text, captions |
| Background | `#f5f7fa` | Page background |
| Card white | `#ffffff` | Content cards |

### Typography

- **Font stack:** `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` (matches portal)
- **Headings:** Weight 600–700, colour `#1a365d`
- **Body text:** 16px base, 1.7 line height, colour `#343a40`

### Framework

- **Bootstrap 5.3.3** via CDN (same version as portal)
- No additional CSS frameworks

### Design Principles

- Clean, professional academic aesthetic — similar to NHM, DEFRA, or Natural England publications
- No hero images or animations — content-first
- Generous white space, readable line lengths (max ~800px for prose)
- Consistent navigation across website pages and portal pages

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
        <li class="nav-item"><a class="nav-link" href="{{ site.baseurl }}/about/">About</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ site.baseurl }}/projects/">Projects</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ site.baseurl }}/publications/">Publications</a></li>
        <li class="nav-item"><a class="nav-link fw-bold" href="{{ site.baseurl }}/species/">Data Portal</a></li>
      </ul>
    </div>
  </div>
</nav>
```

The "Data Portal" link points to `/species/` which resolves to the portal served from `ukbol/species`.

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
baseurl: ""
url: "https://ukbol.org"

markdown: kramdown
kramdown:
  input: GFM

permalink: /:title/

plugins:
  - jekyll-sitemap

exclude:
  - Gemfile
  - Gemfile.lock
  - README.md

defaults:
  - scope:
      path: ""
      type: "pages"
    values:
      layout: "page"
```

**Notes:**
- `baseurl: ""` — correct for a custom domain. All `{{ site.baseurl }}` references resolve cleanly.
- `jekyll-sitemap` — supported by GitHub Pages, auto-generates `/sitemap.xml`.
- `exclude` — only lists files that exist in this repo's root. No need to exclude `scripts/`, `data/`, etc. as those live in the `ukbol/species` repo.
- `permalink: /:title/` — applies only to files with front matter. Will not affect portal HTML files (which have no front matter and live in a different repo anyway).

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

Visit the [Gap Analysis Data Portal]({{ site.baseurl }}/species/) to explore DNA barcode coverage across UK species and multiple gene regions.

  </div>
</div>
```

**Note:** The portal link text avoids hardcoding species/gene counts that go stale. If you want live stats on the homepage, see the `_data/stats.yml` approach in Phase 6.

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

### 404 Page (`404.md`)

```markdown
---
layout: default
title: Page Not Found
permalink: /404.html
---
<div class="container">
  <div class="content-wrapper text-center py-5">
    <h1>Page Not Found</h1>
    <p class="lead">The page you're looking for doesn't exist or may have moved.</p>
    <p>
      <a href="/" class="btn btn-primary me-2">Return to Homepage</a>
      <a href="/species/" class="btn btn-outline-primary">Go to Data Portal</a>
    </p>
  </div>
</div>
```

### robots.txt

```
User-agent: *
Allow: /
Sitemap: https://ukbol.org/sitemap.xml
```

---

## Implementation Steps

### Phase 1: Create website repo and Jekyll infrastructure

**Repo:** `ukbol/ukbol.github.io`
**Prerequisites:** GitHub org admin access to create the repo

- [ ] **1.1** Create repo `ukbol/ukbol.github.io` on GitHub (public, no template, empty — or with a README)
- [ ] **1.2** Clone the repo locally
- [ ] **1.3** Create `_config.yml` with the configuration specified above
- [ ] **1.4** Create `_layouts/default.html` with the default layout
- [ ] **1.5** Create `_layouts/page.html` with the page layout
- [ ] **1.6** Create `_includes/nav.html` with the navigation bar component
- [ ] **1.7** Create `_includes/footer.html` with the footer component
- [ ] **1.8** Create `assets/images/` and add logo files:
  - `ukbol-logo.png` (colour version)
  - `ukbol-logo-white.png` (white version for navbar/footer — create or source this)
- [ ] **1.9** Create `Gemfile` for local development:
  ```ruby
  source "https://rubygems.org"
  gem "github-pages", group: :jekyll_plugins
  ```
- [ ] **1.10** Commit and push: `"Initial Jekyll infrastructure"`

**Completion check:** Repo exists on GitHub with layouts, includes, config, and logo assets.

---

### Phase 2: Create content pages

**Repo:** `ukbol/ukbol.github.io`
**Prerequisites:** Phase 1 complete; page content text available

- [ ] **2.1** Create `index.md` using the homepage template above. Add homepage text.
- [ ] **2.2** Create `about.md` using the about template. Add about text.
- [ ] **2.3** Create `projects.md` using the projects template. Add projects text.
- [ ] **2.4** Create `publications.md` using the publications template. Add publications text.
- [ ] **2.5** Create `404.md` using the 404 template above.
- [ ] **2.6** Create `robots.txt` at the repo root with the content above.
- [ ] **2.7** Create `CNAME` containing a single line: `ukbol.org`
- [ ] **2.8** Commit and push: `"Add content pages, 404, robots.txt, and CNAME"`

**Completion check:** All `.md` pages exist with content. CNAME file present.

---

### Phase 3: Local testing

**Repo:** `ukbol/ukbol.github.io`
**Prerequisites:** Phase 2 complete; Ruby and Bundler installed locally

- [ ] **3.1** Run `bundle install` in the repo root
- [ ] **3.2** Run `bundle exec jekyll serve` to start the local dev server
- [ ] **3.3** Verify the following at `http://localhost:4000/`:

Website checks:
- [ ] Homepage renders with hero section, content, and portal link
- [ ] About page renders at `/about/`
- [ ] Projects page renders at `/projects/`
- [ ] Publications page renders at `/publications/`
- [ ] Navigation bar appears on all pages with correct links
- [ ] Footer appears on all pages
- [ ] Logo images load in navbar and footer
- [ ] "Data Portal" nav link points to `/species/` (will 404 locally — that's expected since the portal lives in a different repo)
- [ ] Mobile responsive layout works (resize browser or use dev tools)
- [ ] 404 page renders at `/404.html` with links to homepage and portal
- [ ] `/sitemap.xml` is generated (from `jekyll-sitemap` plugin)

- [ ] **3.4** Fix any issues found
- [ ] **3.5** Commit and push fixes if any

**Completion check:** All website pages render correctly locally. Navigation works. Mobile layout works.

---

### Phase 4: Deploy to GitHub Pages

**Repo:** `ukbol/ukbol.github.io`
**Prerequisites:** Phase 3 complete

- [ ] **4.1** In GitHub repo Settings → Pages:
  - Source: "Deploy from a branch"
  - Branch: `main` (root `/`)
  - Click Save
- [ ] **4.2** Wait for GitHub Actions build to complete (check the Actions tab)
- [ ] **4.3** Verify the site is live at `https://ukbol.github.io/` (temporary URL before custom domain)
- [ ] **4.4** Verify that the existing portal at `https://ukbol.github.io/species/` still works (it should — different repo, unaffected)

**Completion check:** Website live at `ukbol.github.io`. Portal still functional at `ukbol.github.io/species/`.

---

### Phase 5: Custom domain setup

**Prerequisites:** Phase 4 complete; access to DNS management for `ukbol.org`

- [ ] **5.1** At your DNS registrar, configure the following records for `ukbol.org`:

  **Option A — Apex domain (recommended):**
  ```
  Type   Name   Value
  A      @      185.199.108.153
  A      @      185.199.109.153
  A      @      185.199.110.153
  A      @      185.199.111.153
  ```

  **Plus www redirect:**
  ```
  Type    Name   Value
  CNAME   www    ukbol.github.io
  ```

  **Option B — CNAME only (if your DNS provider supports CNAME flattening):**
  ```
  Type    Name   Value
  CNAME   @      ukbol.github.io
  CNAME   www    ukbol.github.io
  ```

- [ ] **5.2** In GitHub repo Settings → Pages → Custom domain: enter `ukbol.org` and click Save
- [ ] **5.3** Wait for DNS propagation (can take up to 48 hours, usually much faster)
- [ ] **5.4** Once DNS has propagated, tick "Enforce HTTPS" in GitHub Pages settings (GitHub will provision a TLS certificate — this may take a few minutes)
- [ ] **5.5** Verify:
  - `https://ukbol.org/` loads the website homepage
  - `https://ukbol.org/about/` loads the about page
  - `https://ukbol.org/species/` loads the data portal (served from `ukbol/species`)
  - `https://www.ukbol.org/` redirects to `https://ukbol.org/`
  - `https://ukbol.github.io/` redirects to `https://ukbol.org/`
  - `https://ukbol.github.io/species/` redirects to `https://ukbol.org/species/`

**Completion check:** `ukbol.org` serves the website. `ukbol.org/species/` serves the portal. HTTPS enforced. www redirects correctly.

**Important:** If the portal does NOT appear at `ukbol.org/species/`, check that the `ukbol/species` repo's GitHub Pages settings still point to the `main` branch `/docs` folder. The org-level custom domain should automatically apply to project sites.

---

### Phase 6: Portal integration (ukbol/species repo)

**Repo:** `ukbol/species`
**Prerequisites:** Phase 5 complete; website live at `ukbol.org`

This phase adds site-wide navigation to the portal pages so users can navigate between the website and portal. **All changes go into `build.py`** because portal HTML files are regenerated on every data update — manual edits would be overwritten.

- [ ] **6.1** In `scripts/build.py`, update `generate_index_html()` to add a site-wide navbar above the existing hero section. Use hardcoded absolute paths (not Liquid template tags):

  ```html
  <nav class="navbar navbar-expand-lg navbar-dark" style="background:linear-gradient(135deg,#1a365d 0%,#2d5a87 100%);">
    <div class="container">
      <a class="navbar-brand d-flex align-items-center" href="/">
        <span>UK Barcode of Life</span>
      </a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#siteNav">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="siteNav">
        <ul class="navbar-nav ms-auto">
          <li class="nav-item"><a class="nav-link" href="/">Home</a></li>
          <li class="nav-item"><a class="nav-link" href="/about/">About</a></li>
          <li class="nav-item"><a class="nav-link" href="/projects/">Projects</a></li>
          <li class="nav-item"><a class="nav-link" href="/publications/">Publications</a></li>
          <li class="nav-item"><a class="nav-link fw-bold active" href="/species/">Data Portal</a></li>
        </ul>
      </div>
    </div>
  </nav>
  ```

- [ ] **6.2** In `scripts/build.py`, update `generate_report_html()` to add the same site-wide navbar above the existing gene-page navbar (the one with "Back to Portal"). Use a different `id` for the collapse target (`siteNav`) to avoid conflicts with any existing page elements.

- [ ] **6.3** In `scripts/build.py`, update the portal index footer to include links back to the main website (matching the footer style from the website).

- [ ] **6.4** Run the build script to regenerate all portal pages:
  ```bash
  python scripts/build.py
  ```

- [ ] **6.5** Test portal locally — open `docs/index.html` in a browser and verify:
  - Site-wide navbar appears above portal content
  - All nav links use absolute paths (`/`, `/about/`, `/species/`)
  - Gene pages show site-wide navbar above the "Back to Portal" navbar
  - Portal functionality is unaffected (filters, charts, tables, downloads)

- [ ] **6.6** **(Optional)** Have `build.py` generate a `_data/stats.yml` file in the website repo with current statistics (total species, species with data, true gaps, gene count). The website homepage can then reference `{{ site.data.stats.total_species }}` to keep counts in sync. Only pursue this if both repos are checked out locally side by side.

- [ ] **6.7** Commit and push changes to `ukbol/species`:
  ```
  git add scripts/build.py docs/
  git commit -m "Add site-wide navigation to portal pages"
  git push
  ```

- [ ] **6.8** Wait for GitHub Pages to rebuild, then verify at `https://ukbol.org/species/` that the site-wide navbar appears.

**Completion check:** Portal pages show site-wide navigation. Users can navigate from portal to website and back. All portal functionality (filters, charts, downloads, shared URLs) works correctly.

---

### Phase 7: Final testing

**Prerequisites:** Phase 6 complete

- [ ] **7.1** Website page checks at `https://ukbol.org`:
  - Homepage loads with hero, content, and portal link
  - About, Projects, Publications pages load with correct content
  - Nav links work across all pages
  - Footer appears on all pages
  - Mobile layout works

- [ ] **7.2** Portal checks at `https://ukbol.org/species/`:
  - Portal index loads with all 6 gene cards and statistics
  - Site-wide navbar appears and links work
  - Each gene page loads (click into at least COI and one other)

- [ ] **7.3** Portal functionality (test on at least one gene page):
  - Data loads (table populates with rows)
  - Taxonomy cascading dropdowns work (select Kingdom → Phylum options update)
  - Status filter buttons work (click GREEN → table filters)
  - Pie chart and bar chart render and update with filters
  - CSV download button works
  - TSV download button works
  - Shareable URL: apply filters, copy URL from address bar, open in new tab — filters should restore
  - "Back to Portal" link returns to portal index

- [ ] **7.4** Cross-navigation:
  - From website homepage, click "Data Portal" → arrives at portal
  - From portal, click "Home" in site-wide nav → arrives at website homepage
  - From gene page, "Back to Portal" → portal index, then "Home" → website

- [ ] **7.5** Redirect checks:
  - `https://ukbol.github.io/` → redirects to `https://ukbol.org/`
  - `https://ukbol.github.io/species/` → redirects to `https://ukbol.org/species/`
  - `https://www.ukbol.org/` → redirects to `https://ukbol.org/`
  - `https://ukbol.org/nonexistent` → shows custom 404 page

- [ ] **7.6** Fix any issues found, commit, and push to the appropriate repo.

**Completion check:** Full site works end-to-end. Navigation between website and portal is seamless. Portal functionality preserved. Redirects work.

---

## URL Structure (final state)

| Page | URL | Served from |
|------|-----|-------------|
| Homepage | `ukbol.org/` | `ukbol/ukbol.github.io` |
| About | `ukbol.org/about/` | `ukbol/ukbol.github.io` |
| Projects | `ukbol.org/projects/` | `ukbol/ukbol.github.io` |
| Publications | `ukbol.org/publications/` | `ukbol/ukbol.github.io` |
| 404 | `ukbol.org/404.html` | `ukbol/ukbol.github.io` |
| Sitemap | `ukbol.org/sitemap.xml` | `ukbol/ukbol.github.io` |
| Portal index | `ukbol.org/species/` | `ukbol/species` |
| COI gap analysis | `ukbol.org/species/bold_coi.html` | `ukbol/species` |
| 12S gap analysis | `ukbol.org/species/midori_12s.html` | `ukbol/species` |
| 16S gap analysis | `ukbol.org/species/midori_16s.html` | `ukbol/species` |
| RBCL gap analysis | `ukbol.org/species/ncbi_rbcl.html` | `ukbol/species` |
| ITS gap analysis | `ukbol.org/species/unite_its.html` | `ukbol/species` |
| Genome gap analysis | `ukbol.org/species/dtol_genome.html` | `ukbol/species` |

---

## Notes for Future Sessions

### How to resume work

1. Check the **Progress Tracker** table at the top to see which phase is current
2. Check the **Session Log** for what was done previously
3. Read the current phase's steps — unchecked items are remaining work
4. Update the session log and progress tracker as you complete phases

### Key decisions already made

- **Repo name:** `ukbol/ukbol.github.io` (org-level site) — allows portal to automatically serve under the custom domain
- **No portal file moves needed** — portal stays in `ukbol/species`, website in its own repo
- **Portal changes go in `build.py`** — never manually edit the generated HTML files
- **Custom domain:** `ukbol.org` — CNAME file committed to repo, DNS configured at registrar

### What NOT to change in `ukbol/species` until Phase 6

- Do not modify `scripts/build.py`
- Do not move any files in `docs/`
- Do not add Jekyll files (`_config.yml`, `_layouts/`, etc.) to the species repo
- Do not change GitHub Pages settings for the species repo

### Dependencies

- **Jekyll** — built-in to GitHub Pages, no installation needed for deployment
- **Ruby + Bundler** — needed only for local testing (Phase 3)
- **Bootstrap 5.3.3** via CDN
- **Logo files** — colour and white versions (must be sourced or created)
- **Page content** — text for homepage, about, projects, and publications pages
- **DNS access** — for configuring `ukbol.org` to point to GitHub Pages
