"""Shared pieces for the generated pages: site settings, menu and page template.

Every generated page lives one folder below the site root (blog/, brokers/,
best/), so links to shared files are written as "../<path>". The homepage
(index.html) is hand-written; keep its menu in the same order as NAV.
"""
import html
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
e = html.escape


def load_json(*parts):
    return json.load(open(os.path.join(ROOT, *parts), encoding="utf-8"))


SETTINGS = load_json("content", "site.json")
SITE = SETTINGS.get("siteName") or "Brokerage Reviews"
SITE_URL = (SETTINGS.get("siteUrl") or "").rstrip("/")
DATA_VERIFIED = bool(SETTINGS.get("dataVerified"))
FCA_ONLY = bool(SETTINGS.get("guidesFcaOnly"))
CONTACT_EMAIL = (SETTINGS.get("contactEmail") or "").strip()
AUTHOR = SETTINGS.get("author") or {}
YEAR = datetime.now(timezone.utc).year
PARTNER_OPINION = bool(SETTINGS.get("partnerOpinionPosts"))


def is_partner_opinion(post):
    """Partner commentary that gives a view on markets (not official data, not a weekly performance recap)."""
    return not post.get("official") and "weekly" not in post.get("type", "").lower()


def is_published(post):
    return PARTNER_OPINION or not is_partner_opinion(post)

# Site menu, paths from the site root. "key" marks the page shown as current.
NAV = [
    ("best/index.html", "Best Brokers", "best"),
    ("index.html#compare", "Compare", None),
    ("index.html#calculator", "Cost Calculator", None),
    ("index.html#methodology", "How We Rate", None),
    ("blog/index.html", "Market News", "news"),
    ("index.html#faq", "FAQ", None),
]

DISCLAIMER = ("<strong>Disclaimer:</strong> Information on this site, including broker reviews and market "
              "commentary, is for general information only and is not financial, investment or trading advice. "
              "Some links are affiliate links: we may earn a commission if you open an account, at no cost to you, "
              "and this never affects a broker's rating. Broker fees, spreads, leverage and availability vary by "
              "country and change often; always check the broker's own website. Trading forex and CFDs on margin "
              "carries a high level of risk and may not be suitable for all investors.")


# ---------- SEO helpers ----------

TITLE_MAX, DESC_MAX = 60, 158


def seo_title(title):
    """Search engines cut titles at about 60 characters: drop the " — site name" suffix when it doesn't fit."""
    suffix = " — " + SITE
    if len(title) > TITLE_MAX and title.endswith(suffix):
        return title[: -len(suffix)]
    return title


def seo_description(text):
    """Meta descriptions are cut at about 155-160 characters: shorten at a word boundary."""
    text = " ".join(text.split())
    if len(text) <= DESC_MAX:
        return text
    cut = text[: DESC_MAX - 1].rsplit(" ", 1)[0].rstrip(" ,;:.-—")
    return cut + "…"


def image_size(path):
    """(width, height) of a PNG, GIF or JPEG file, or None."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(26)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
            if head[:6] in (b"GIF87a", b"GIF89a"):
                return int.from_bytes(head[6:8], "little"), int.from_bytes(head[8:10], "little")
            if head[:2] == b"\xff\xd8":
                fh.seek(2)
                while True:
                    marker = fh.read(2)
                    if len(marker) < 2 or marker[0] != 0xFF:
                        return None
                    seg_len = int.from_bytes(fh.read(2), "big")
                    if 0xC0 <= marker[1] <= 0xCF and marker[1] not in (0xC4, 0xC8, 0xCC):
                        data = fh.read(5)
                        return int.from_bytes(data[3:5], "big"), int.from_bytes(data[1:3], "big")
                    fh.seek(seg_len - 2, 1)
    except OSError:
        return None
    return None


IMG_TAG = re.compile(r"<img\b(?![^>]*\bwidth=)[^>]*>")


def size_images(markup, page_dir):
    """Add width/height to <img> tags that lack them, so the page doesn't jump as images load.
    page_dir is the page's folder relative to the site root ("" for the homepage)."""
    def fix(m):
        tag = m.group(0)
        src = re.search(r'\bsrc="([^"]+)"', tag)
        if not src or "://" in src.group(1):
            return tag
        size = image_size(os.path.normpath(os.path.join(ROOT, page_dir, src.group(1))))
        if not size:
            return tag
        return tag.replace("<img", '<img width="%d" height="%d"' % size, 1)
    return IMG_TAG.sub(fix, markup)


def abs_url(path):
    """Absolute URL for a root-relative path, or "" until siteUrl is set."""
    return "%s/%s" % (SITE_URL, path) if SITE_URL else ""


def author_person():
    """schema.org Person for the site's reviewer, or None if no author is set."""
    if not AUTHOR.get("name"):
        return None
    person = {"@type": "Person", "name": AUTHOR["name"], "jobTitle": AUTHOR.get("role", "")}
    if SITE_URL:
        person["url"] = abs_url("about/index.html#author")
        if AUTHOR.get("photo"):
            person["image"] = abs_url(AUTHOR["photo"])
    return person


def byline(prefix="../", verb="Reviewed by", date=None):
    """Author line with a small photo, linking to the bio on the About page."""
    if not AUTHOR.get("name"):
        return '<p class="muted small review-updated">Updated %s</p>' % date if date else ""
    photo = ('<img class="byline-photo" src="%s%s" alt="" loading="lazy" />' % (prefix, e(AUTHOR["avatar"]))
             if AUTHOR.get("avatar") else "")
    when = ' <span class="byline-sep">·</span> Updated %s' % date if date else ""
    return ('<p class="byline">%s<span>%s <a href="%sabout/index.html#author">%s</a>%s</span></p>'
            % (photo, verb, prefix, e(AUTHOR["name"]), when))


def organization():
    """schema.org Organization for the site itself (homepage and About page), or None until siteUrl is set."""
    if not SITE_URL:
        return None
    org = {"@context": "https://schema.org", "@type": "Organization", "name": SITE, "url": SITE_URL + "/",
           "logo": abs_url("assets/favicon.svg")}
    if CONTACT_EMAIL:
        org["email"] = CONTACT_EMAIL
        org["contactPoint"] = {"@type": "ContactPoint", "contactType": "customer support", "email": CONTACT_EMAIL}
    return org



def nav_links(current, indent, prefix="../"):
    return "\n".join('%s<a href="%s%s"%s>%s</a>' % (
        indent, prefix, href, ' aria-current="page"' if key and key == current else "", label)
        for href, label, key in NAV)


def page(title, description, body, path, current=None, jsonld=(), noindex=False, og_type="website", image=None):
    """A full HTML page. path is the page's own root-relative path (e.g. "brokers/ig.html")."""
    url = abs_url(path)
    title, description = seo_title(title), seo_description(description)
    body = size_images(body, os.path.dirname(path))
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
           nav=nav_links(current, " " * 8), footer_links=nav_links(None, " " * 8) + '\n        <a href="../about/index.html">About &amp; editorial policy</a>', disclaimer=DISCLAIMER)


def breadcrumbs(items):
    """BreadcrumbList structured data from [(name, root-relative path), ...]."""
    if not SITE_URL:
        return None
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": name, "item": abs_url(path)}
                                for i, (name, path) in enumerate(items)]}
