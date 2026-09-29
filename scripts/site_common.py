"""Shared pieces for the generated pages: site settings, menu and page template.

Every generated page lives one folder below the site root (blog/, brokers/,
best/), so links to shared files are written as "../<path>". The homepage
(index.html) is hand-written; keep its menu in the same order as NAV.
"""
import html
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
e = html.escape


def load_json(*parts):
    return json.load(open(os.path.join(ROOT, *parts), encoding="utf-8"))


SETTINGS = load_json("content", "site.json")
SITE = SETTINGS.get("siteName") or "Brokerage Reviews"
SITE_URL = (SETTINGS.get("siteUrl") or "").rstrip("/")
DATA_VERIFIED = bool(SETTINGS.get("dataVerified"))
YEAR = datetime.now(timezone.utc).year

# Site menu, paths from the site root. "key" marks the page shown as current.
NAV = [
    ("best/index.html", "Best Brokers", "best"),
    ("index.html#compare", "Compare", None),
    ("index.html#calculator", "Cost Calculator", None),
    ("index.html#methodology", "How We Rate", None),
    ("blog/index.html", "Market News", "news"),
    ("blog/headlines.html", "Headlines", "headlines"),
    ("index.html#faq", "FAQ", None),
]

DISCLAIMER = ("<strong>Disclaimer:</strong> Information on this site, including broker reviews and market "
              "commentary, is for general information only and is not financial, investment or trading advice. "
              "Some links are affiliate links: we may earn a commission if you open an account, at no cost to you, "
              "and this never affects a broker's rating. Broker fees, spreads, leverage and availability vary by "
              "country and change often; always check the broker's own website. Trading forex and CFDs on margin "
              "carries a high level of risk and may not be suitable for all investors.")


def abs_url(path):
    """Absolute URL for a root-relative path, or "" until siteUrl is set."""
    return "%s/%s" % (SITE_URL, path) if SITE_URL else ""


def nav_links(current, indent, prefix="../"):
    return "\n".join('%s<a href="%s%s"%s>%s</a>' % (
        indent, prefix, href, ' aria-current="page"' if key and key == current else "", label)
        for href, label, key in NAV)


def page(title, description, body, path, current=None, jsonld=(), noindex=False, og_type="website", image=None):
    """A full HTML page. path is the page's own root-relative path (e.g. "brokers/ig.html")."""
    url = abs_url(path)
    head = []
    if noindex:
        head.append('<meta name="robots" content="noindex, follow" />')
    if url:
        head.append('<link rel="canonical" href="%s" />' % e(url))
        head.append('<meta property="og:url" content="%s" />' % e(url))
    head += ['<meta property="og:site_name" content="%s" />' % e(SITE),
             '<meta property="og:type" content="%s" />' % og_type,
             '<meta property="og:title" content="%s" />' % e(title),
             '<meta property="og:description" content="%s" />' % e(description),
             '<meta name="twitter:card" content="%s" />' % ("summary_large_image" if image else "summary")]
    if image and SITE_URL:
        head.append('<meta property="og:image" content="%s" />' % e(abs_url(image)))
    for data in jsonld:
        # "</" inside JSON would end the script element early.
        head.append('<script type="application/ld+json">%s</script>' % json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>{title}</title>
  <meta name="description" content="{description}" />
  {head}
  <link rel="icon" href="../assets/favicon.svg" type="image/svg+xml" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../css/styles.css" />
  <script>
    try {{
      var t = localStorage.getItem("br-theme");
      if (t) document.documentElement.setAttribute("data-theme", t);
    }} catch (e) {{}}
  </script>
</head>
<body>
  <div class="risk-banner" role="note">
    <strong>Risk warning:</strong> CFDs and leveraged forex are complex instruments and carry a high risk of losing money rapidly. Most retail investor accounts lose money when trading CFDs. Consider whether you can afford to take that risk.
  </div>

  <header class="site-header">
    <div class="container header-inner">
      <a href="../index.html" class="logo" aria-label="{site} home">
        <img src="../assets/favicon.svg" alt="" width="32" height="32" />
        <span>Brokerage<b>Reviews</b></span>
      </a>
      <nav class="main-nav" id="main-nav">
{nav}
      </nav>
      <div class="header-actions">
        <button class="icon-btn" id="theme-toggle" aria-label="Toggle dark mode" title="Toggle dark mode">
          <svg class="icon-sun" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          <svg class="icon-moon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>
        </button>
        <button class="icon-btn menu-btn" id="menu-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="main-nav">
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
      </div>
    </div>
  </header>

  <main>
{body}
  </main>

  <footer class="site-footer">
    <div class="container footer-inner">
      <div>
        <a href="../index.html" class="logo logo-footer">
          <img src="../assets/favicon.svg" alt="" width="28" height="28" />
          <span>Brokerage<b>Reviews</b></span>
        </a>
        <p class="muted">Independent forex broker comparisons and reviews.</p>
      </div>
      <div class="footer-links">
{footer_links}
      </div>
    </div>
    <div class="container disclaimer">
      <p>{disclaimer}</p>
      <p class="muted">&copy; <span id="year"></span> {site}. All rights reserved.</p>
    </div>
  </footer>

  <script src="../js/site.js"></script>
</body>
</html>
""".format(title=e(title), description=e(description), head="\n  ".join(head), body=body, site=e(SITE),
           nav=nav_links(current, " " * 8), footer_links=nav_links(None, " " * 8), disclaimer=DISCLAIMER)


def breadcrumbs(items):
    """BreadcrumbList structured data from [(name, root-relative path), ...]."""
    if not SITE_URL:
        return None
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": name, "item": abs_url(path)}
                                for i, (name, path) in enumerate(items)]}
