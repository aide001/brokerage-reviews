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
import re
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "content", "posts")
HEADLINES = os.path.join(ROOT, "content", "headlines.json")
OUT = os.path.join(ROOT, "blog")
SITE = "Brokerage Reviews"

e = html.escape


def load_posts():
    posts = [json.load(open(p, encoding="utf-8")) for p in glob.glob(os.path.join(POSTS, "*.json"))]
    return sorted(posts, key=lambda p: p["date"], reverse=True)


def nice_date(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return "%d %s %d" % (d.day, d.strftime("%B"), d.year)


def page(title, description, body, current="news"):
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
        <a href="index.html"{news_current}>Market News</a>
        <a href="headlines.html"{headlines_current}>Headlines</a>
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
""".format(title=e(title), description=e(description), body=body,
           news_current=' aria-current="page"' if current == "news" else "",
           headlines_current=' aria-current="page"' if current == "headlines" else "")


# Small line icons for release cards that have no chart image.
TOPIC_ICONS = {
    "Interest rates": '<path d="M5 19L19 5M7 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm10 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/>',
    "Jobs": '<path d="M4 20v-1a5 5 0 0 1 5-5h6a5 5 0 0 1 5 5v1M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"/>',
    "Inflation": '<path d="M3 17l6-6 4 4 8-8M15 7h6v6"/>',
    "Growth": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "Trade": '<path d="M4 8h14l-4-4M20 16H6l4 4"/>',
}


def kind(p):
    return "official" if p.get("official") else "analysis"


def thumb(p, from_root=False):
    """Card image: the post's first chart, or a topic panel for data releases.
    Image paths are stored relative to blog/; from_root adjusts them for the homepage."""
    if p.get("image"):
        src = re.sub(r"^\.\./", "", p["image"]) if from_root else p["image"]
        return '<img class="post-card-img" src="%s" alt="" loading="lazy" />' % e(src)
    topic = p.get("topic") or p["type"]
    icon = TOPIC_ICONS.get(topic, TOPIC_ICONS["Growth"])
    return ('<div class="post-card-img post-card-panel topic-%s" aria-hidden="true">'
            '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round">%s</svg>'
            '<strong>%s</strong><span>%s</span></div>') % (
        e(re.sub(r"[^a-z]+", "-", topic.lower())), icon, e(topic), e(p["provider"]))


def byline(p):
    return e(p["provider"]) if p.get("official") else "%s · %s" % (e(p["author"]), e(p["provider"]))


def post_card(p):
    return """      <article class="post-card" data-kind="{kind}">
        <a class="post-card-link" href="{slug}.html">
          {thumb}
          <div class="post-card-body">
            <p class="post-meta"><span class="chip">{type}</span> <time datetime="{date}">{nice}</time></p>
            <h2>{title}</h2>
            <p class="post-excerpt">{summary}</p>
            <p class="post-byline">{byline}</p>
          </div>
        </a>
      </article>""".format(slug=e(p["slug"]), thumb=thumb(p), type=e(p["type"]), date=e(p["date"]),
                          nice=nice_date(p["date"]), title=e(p["title"]), summary=e(p["summary"]),
                          byline=byline(p), kind=kind(p))


def related_card(p, prefix=""):
    """Compact card; prefix is the path from the page to blog/ ("" on post pages)."""
    return """          <article class="post-card related-card">
            <a class="post-card-link" href="{prefix}{slug}.html">
              {thumb}
              <div class="post-card-body">
                <p class="post-meta"><span class="chip">{type}</span> <time datetime="{date}">{nice}</time></p>
                <h3>{title}</h3>
              </div>
            </a>
          </article>""".format(slug=e(p["slug"]), thumb=thumb(p, from_root=bool(prefix)), type=e(p["type"]),
                               date=e(p["date"]), nice=nice_date(p["date"]), title=e(p["title"]), prefix=prefix)


def load_headlines():
    return json.load(open(HEADLINES, encoding="utf-8")) if os.path.exists(HEADLINES) else []


def headline_time(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return "%d %s, %s UTC" % (d.day, d.strftime("%b"), d.strftime("%H:%M"))


def headline_item(h):
    # Links open the publisher's own page in a new tab (never framed).
    return """          <li class="headline">
            <a href="{url}" target="_blank" rel="noopener nofollow">{title}</a>
            <span class="headline-meta">{source} · <time datetime="{date}">{when}</time></span>
          </li>""".format(url=e(h["url"]), title=e(h["title"]), source=e(h["source"]),
                          date=e(h["date"]), when=headline_time(h["date"]))


HEADLINE_CREDITS = ("Finance headlines and links from BBC News, the European Central Bank, the Federal Reserve, "
                    "the Bank of Canada and the Reserve Bank of Australia (CC BY 4.0). Articles open on the "
                    "publisher's website; we don't copy their content.")


def headlines_panel(headlines, href="headlines.html", count=6):
    if not headlines:
        return ""
    return """        <section class="headlines-panel" aria-labelledby="headlines-title">
          <div class="headlines-panel-head">
            <h2 id="headlines-title">Latest headlines</h2>
            <a href="{href}">More headlines</a>
          </div>
          <ul class="headline-list">
{items}
          </ul>
        </section>
""".format(href=href, items="\n".join(headline_item(h) for h in headlines[:count]))


def build_headlines(headlines):
    days, groups = [], {}
    for h in headlines:
        day = nice_date(h["date"])
        if day not in groups:
            days.append(day)
            groups[day] = []
        groups[day].append(h)
    if headlines:
        listing = "\n".join("""        <h2 class="headline-day">{day}</h2>
        <ul class="headline-list">
{items}
        </ul>""".format(day=day, items="\n".join(headline_item(h) for h in groups[day])) for day in days)
    else:
        listing = '        <p class="empty">No headlines yet. Check back soon.</p>'
    body = """    <section class="section blog-hero">
      <div class="container narrow">
        <div class="section-head">
          <p class="eyebrow">Market News</p>
          <h1>Latest headlines</h1>
          <p>Finance and central bank headlines from around the web, updated through the day. Each link opens the full story on the publisher's site.</p>
        </div>
{listing}
        <p class="headline-credits">{credits}</p>
        <p class="related-all"><a class="btn btn-ghost" href="index.html">Back to market news</a></p>
      </div>
    </section>""".format(listing=listing, credits=e(HEADLINE_CREDITS))
    return page("Latest headlines — " + SITE, "Finance and central bank headlines from BBC News, the ECB, the Federal Reserve, the Bank of Canada and the RBA.",
                body, current="headlines")


def build_index(posts, headlines=()):
    if posts:
        items = "\n".join(post_card(p) for p in posts)
        filters = """        <div class="news-filters" role="group" aria-label="Show">
          <button type="button" class="filter-btn" data-filter="all" aria-pressed="true">All</button>
          <button type="button" class="filter-btn" data-filter="analysis" aria-pressed="false">Analysis</button>
          <button type="button" class="filter-btn" data-filter="official" aria-pressed="false">Official data</button>
        </div>
"""
        listing = filters + '    <div class="post-grid" id="post-grid">\n%s\n    </div>' % items
    else:
        listing = '    <p class="empty">No commentary has been published yet. Check back soon.</p>'
    body = """    <section class="section blog-hero">
      <div class="container">
        <div class="section-head">
          <p class="eyebrow">Market News</p>
          <h1>Market news and analysis</h1>
          <p>Commentary on currencies, commodities and crypto from professional market analysts, plus the latest official US economic data, published as it arrives.</p>
        </div>
{panel}{listing}
      </div>
    </section>""".format(listing=listing, panel=headlines_panel(list(headlines)))
    return page("Market News — " + SITE, "Forex, commodities and crypto market commentary and official US economic data.", body)


def post_byline(p):
    if p.get("official"):
        return "Official release · %s" % e(p["provider"])
    return "%s, %s, %s" % (e(p["author"]), e(p["authorRole"]), e(p["provider"]))


def source_note(p):
    if p.get("official"):
        url = (p.get("source") or {}).get("url") or ""
        host = re.sub(r"^www\.", "", url.split("/")[2]) if url.count("/") >= 2 else ""
        link = ' <a href="%s" rel="noopener">Read the full release on %s</a>.' % (e(url), e(host)) if url else ""
        return ("<strong>Source:</strong> Official release from the %s, a US government agency, republished "
                "from its public website.%s It is for information only and is not investment advice.") % (e(p["provider"]), link)
    return ("<strong>Source:</strong> This commentary was written by %s, %s at %s, and is republished with "
            "permission. It is for information only and is not investment advice.") % (
        e(p["author"]), e(p["authorRole"]), e(p["provider"]))


HOME = os.path.join(ROOT, "index.html")
HOME_START, HOME_END = "<!-- latest-news:start -->", "<!-- latest-news:end -->"


def update_home(posts, headlines=()):
    """Refresh the "Latest market news" strip between the markers in index.html."""
    if not os.path.exists(HOME):
        return
    page_html = open(HOME, encoding="utf-8").read()
    if HOME_START not in page_html or HOME_END not in page_html:
        return
    cards = "\n".join(related_card(p, prefix="blog/") for p in posts[:4])
    section = """{start}
    <section id="latest-news" class="section section-alt latest-news">
      <div class="container">
        <div class="section-head section-head-row">
          <div>
            <h2>Latest market news</h2>
            <p>Analyst commentary and official economic data, updated through the day.</p>
          </div>
          <a class="btn btn-ghost" href="blog/index.html">All market news</a>
        </div>
        <div class="related-grid latest-grid">
{cards}
        </div>
{headlines}      </div>
    </section>
    {end}""".format(start=HOME_START, end=HOME_END, cards=cards,
                    headlines=headlines_panel(list(headlines), href="blog/headlines.html", count=5))
    before, rest = page_html.split(HOME_START, 1)
    after = rest.split(HOME_END, 1)[1]
    new = before + section + after
    if new != page_html:
        with open(HOME, "w", encoding="utf-8") as fh:
            fh.write(new)


def build_post(p, related):
    more = ""
    if related:
        more = """
        <section class="related" aria-labelledby="related-title">
          <h2 id="related-title">More market news</h2>
          <div class="related-grid">
%s
          </div>
        </section>""" % "\n".join(related_card(r) for r in related)
    body = """    <article class="section post">
      <div class="container narrow">
        <p class="breadcrumb"><a href="index.html">Market News</a> / {type}</p>
        <h1 class="post-title">{title}</h1>
        <p class="post-meta"><time datetime="{date}">{nice}</time> <span class="post-meta-by">{byline}</span></p>
        <div class="post-body">
{content}
        </div>
        <aside class="post-source">
          {source}
        </aside>
{more}
        <p class="related-all"><a class="btn btn-ghost" href="index.html">See all market news</a></p>
      </div>
    </article>""".format(type=e(p["type"]), title=e(p["title"]), date=e(p["date"]), nice=nice_date(p["date"]),
                         byline=post_byline(p), source=source_note(p), content=p["bodyHtml"], more=more)
    return page(p["title"] + " — " + SITE, p["summary"] or p["title"], body)


def main():
    posts = load_posts()
    headlines = load_headlines()
    os.makedirs(OUT, exist_ok=True)
    # Remove pages for posts that no longer exist.
    keep = {p["slug"] + ".html" for p in posts} | {"index.html", "headlines.html"}
    for f in os.listdir(OUT):
        if f.endswith(".html") and f not in keep:
            os.remove(os.path.join(OUT, f))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(build_index(posts, headlines))
    with open(os.path.join(OUT, "headlines.html"), "w", encoding="utf-8") as fh:
        fh.write(build_headlines(headlines))
    for p in posts:
        # The three most recent other posts, newest first.
        related = [r for r in posts if r["slug"] != p["slug"]][:3]
        with open(os.path.join(OUT, p["slug"] + ".html"), "w", encoding="utf-8") as fh:
            fh.write(build_post(p, related))
    update_home(posts, headlines)
    print("Built blog: %d post(s)." % len(posts))


if __name__ == "__main__":
    main()
