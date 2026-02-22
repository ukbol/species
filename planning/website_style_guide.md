UKBOL Website — Style Reference
Framework
Bootstrap 5.3.3 via CDN (no SCSS, no custom build)
All custom CSS is embedded inline in _layouts/default.html — no separate CSS files
CSS Custom Properties
:root {
  --ukbol-primary:     #1a4d5a;  /* deep teal — headings, footer bg */
  --ukbol-primary-mid: #2b7a8c;  /* medium teal — accents, buttons, h3 */
  --ukbol-accent:      #2b7a8c;  /* same as primary-mid */
  --ukbol-accent-light:#6ab8c8;  /* light teal — hover highlights */
  --ukbol-gold:        #d4a017;  /* gold — defined, not widely used yet */
  --ukbol-text:        #343a40;  /* dark gray — body text */
  --ukbol-bg:          #f5f7fa;  /* very light blue-gray — page background */
}

Typography
Font stack: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif
Body: color #343a40, background #f5f7fa
h1: color #1a4d5a, weight 700, margin-bottom: 1.5rem
h2: color #1a4d5a, weight 600, margin-top: 2rem; margin-bottom: 1rem
h3: color #2b7a8c, weight 600, margin-top: 1.5rem
Paragraphs: line-height: 1.7; margin-bottom: 1rem
Links: color #2b7a8c, hover to #1a4d5a
Navbar
Background: white (bg-white)
Bottom border: 2px solid #e8f4f8
Box shadow: 0 1px 4px rgba(0,0,0,.07)
Logo: ukbol-text-logo-clear.png, height 45px, left side (.navbar-brand)
Links: right-aligned (ms-auto), color #1a4d5a
Data Portal link: fw-bold, color #2b7a8c (distinguished from others)
Pages: Home, About, Projects, Publications, Data Portal

Hero Section (.page-hero)
.page-hero {
  background: linear-gradient(135deg, #1a4d5a 0%, #2b7a8c 100%);
  color: #fff;
  padding: 3rem 0;
}
.page-hero h1 { color: #fff; }

Just heading + .lead paragraph text (no logo in the hero)

Cards (.nav-card)
.nav-card { transition: transform .15s, box-shadow .15s; }
.nav-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(26,77,90,.15) !important;
}

Bootstrap classes: border-0 shadow-sm h-100
Card footer: bg-transparent border-0 pb-3
Data Portal card gets: border-top: 3px solid #2b7a8c !important
Grid: col-md-6 col-lg-3 with g-4 gap
Buttons
Outline (standard): btn btn-sm btn-outline-secondary, inline border-color:#2b7a8c; color:#2b7a8c
Solid (Data Portal): btn btn-sm, inline background:#2b7a8c; color:#fff; border-color:#2b7a8c
Arrow icon: → unicode, stretched-link to fill card
Footer
<footer style="background:#1a4d5a; color:rgba(255,255,255,.8); padding:2rem 0; margin-top:3rem;">

Center-aligned text
Logo: height 60px, filter: brightness(0) invert(1) (renders white)
Org name: normal weight, mb-1
Secondary line: .small, links at rgba(255,255,255,.9)
Funding line: .small, color rgba(255,255,255,.5), links at rgba(255,255,255,.6)

Content Pages (.content-wrapper)
.content-wrapper {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

Layout
Sticky footer via flexbox: body { display:flex; flex-direction:column; min-height:100vh; } + main { flex:1; }
That covers everything. The other session just needs to replicate the <style> block, the nav/footer HTML structure, and pull Bootstrap 5.3.3 from the same CDN.