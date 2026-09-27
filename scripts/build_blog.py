#!/usr/bin/env python3
"""Build the static blog pages from content/posts/*.json.

Writes blog/index.html (all posts, newest first) and blog/<slug>.html for
each post. Run by import_commentary.py; run it directly after editing a post.

    python3 scripts/build_blog.py
"""
import glob
import html
import json
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "content", "posts")
OUT = os.path.join(ROOT, "blog")
SITE = "Brokerage Reviews"

e = html.escape


def load_posts():
    posts = [json.load(open(p, encoding="utf-8")) for p in glob.glob(os.path.join(POSTS, "*.json"))]
    return sorted(posts, key=lambda p: p["date"], reverse=True)


def nice_date(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return "%d %s %d" % (d.day, d.strftime("%B"), d.year)


def page(title, description, body):
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>{title}</title>
  <meta name="description" content="{description}" />
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
      <a href="../index.html" class="logo" aria-label="Brokerage Reviews home">
        <img src="../assets/favicon.svg" alt="" width="32" height="32" />
        <span>Brokerage<b>Reviews</b></span>
      </a>
      <nav class="main-nav" id="main-nav">
        <a href="../index.html#top-picks">Top Picks</a>
        <a href="../index.html#compare">Compare</a>
        <a href="../index.html#calculator">Cost Calculator</a>
        <a href="index.html" aria-current="page">Market News</a>
        <a href="../index.html#faq">FAQ</a>
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
    <div class="container disclaimer">
      <p><strong>Disclaimer:</strong> Market commentary is provided by third parties for general information only and is not investment advice or a recommendation to trade. Past performance is not a reliable indicator of future results. Trading forex and CFDs on margin carries a high level of risk and may not be suitable for all investors.</p>
      <p class="muted">&copy; <span id="year"></span> Brokerage Reviews. All rights reserved.</p>
    </div>
  </footer>

  <script src="../js/site.js"></script>
</body>
</html>
""".format(title=e(title), description=e(description), body=body)


def post_card(p):
    thumb = ('<img class="post-card-img" src="%s" alt="" loading="lazy" />' % e(p["image"])) if p.get("image") else ""
    return """      <article class="post-card">
        <a class="post-card-link" href="{slug}.html">
          {thumb}
          <div class="post-card-body">
            <p class="post-meta"><span class="chip">{type}</span> <time datetime="{date}">{nice}</time></p>
            <h2>{title}</h2>
            <p class="post-excerpt">{summary}</p>
            <p class="post-byline">{author} · {provider}</p>
          </div>
        </a>
      </article>""".format(slug=e(p["slug"]), thumb=thumb, type=e(p["type"]), date=e(p["date"]),
                          nice=nice_date(p["date"]), title=e(p["title"]), summary=e(p["summary"]),
                          author=e(p["author"]), provider=e(p["provider"]))


def build_index(posts):
    if posts:
        items = "\n".join(post_card(p) for p in posts)
        listing = '    <div class="post-grid">\n%s\n    </div>' % items
    else:
        listing = '    <p class="empty">No commentary has been published yet. Check back soon.</p>'
    body = """    <section class="section blog-hero">
      <div class="container">
        <div class="section-head">
          <p class="eyebrow">Market News</p>
          <h1>Daily market commentary</h1>
          <p>Analysis of currencies, commodities and crypto from professional market analysts, published as it arrives.</p>
        </div>
{listing}
      </div>
    </section>""".format(listing=listing)
    return page("Market News — " + SITE, "Daily forex, commodities and crypto market commentary.", body)


def build_post(p, newer, older):
    nav = []
    if older:
        nav.append('<a class="post-nav-link" href="%s.html"><small>Older</small>%s</a>' % (e(older["slug"]), e(older["title"])))
    if newer:
        nav.append('<a class="post-nav-link post-nav-next" href="%s.html"><small>Newer</small>%s</a>' % (e(newer["slug"]), e(newer["title"])))
    body = """    <article class="section post">
      <div class="container narrow">
        <p class="breadcrumb"><a href="index.html">Market News</a> / {type}</p>
        <h1 class="post-title">{title}</h1>
        <p class="post-meta"><time datetime="{date}">{nice}</time> · {author}, {role}, {provider}</p>
        <div class="post-body">
{content}
        </div>
        <aside class="post-source">
          <strong>Source:</strong> This commentary was written by {author}, {role} at {provider}, and is republished with permission. It is for information only and is not investment advice.
        </aside>
        <nav class="post-nav" aria-label="More commentary">{nav}</nav>
        <p><a href="index.html">&larr; All market news</a></p>
      </div>
    </article>""".format(type=e(p["type"]), title=e(p["title"]), date=e(p["date"]), nice=nice_date(p["date"]),
                         author=e(p["author"]), role=e(p["authorRole"]), provider=e(p["provider"]),
                         content=p["bodyHtml"], nav="".join(nav))
    return page(p["title"] + " — " + SITE, p["summary"] or p["title"], body)


def main():
    posts = load_posts()
    os.makedirs(OUT, exist_ok=True)
    # Remove pages for posts that no longer exist.
    keep = {p["slug"] + ".html" for p in posts} | {"index.html"}
    for f in os.listdir(OUT):
        if f.endswith(".html") and f not in keep:
            os.remove(os.path.join(OUT, f))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(build_index(posts))
    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        with open(os.path.join(OUT, p["slug"] + ".html"), "w", encoding="utf-8") as fh:
            fh.write(build_post(p, newer, older))
    print("Built blog: %d post(s)." % len(posts))


if __name__ == "__main__":
    main()
