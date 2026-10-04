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

from site_common import SITE, abs_url, breadcrumbs, page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "content", "posts")
OUT = os.path.join(ROOT, "blog")
e = html.escape


def load_posts():
    posts = [json.load(open(p, encoding="utf-8")) for p in glob.glob(os.path.join(POSTS, "*.json"))]
    return sorted(posts, key=lambda p: p["date"], reverse=True)


def nice_date(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return "%d %s %d" % (d.day, d.strftime("%B"), d.year)


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


def build_index(posts):
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
{notice}{listing}
      </div>
    </section>""".format(listing=listing, notice=advice_notice())
    return page("Forex market news and analysis — " + SITE,
                "Forex, commodities and crypto market commentary and official US economic data.",
                body, "blog/index.html", current="news",
                jsonld=[x for x in [breadcrumbs([("Home", ""), ("Market News", "blog/index.html")])] if x])


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


NOT_ADVICE = ("<strong>Not financial advice.</strong> Market news, commentary and data on this site are for general "
              "information only. They are not financial, investment or trading advice, or a recommendation to buy "
              "or sell any instrument. Trading forex and CFDs carries a high risk of losing money; consider "
              "independent advice before making any decision.")


def advice_notice():
    return '        <p class="advice-notice" role="note">%s</p>\n' % NOT_ADVICE


HOME = os.path.join(ROOT, "index.html")
HOME_START, HOME_END = "<!-- latest-news:start -->", "<!-- latest-news:end -->"


def update_home(posts):
    """Refresh the "Market news" strip between the markers in index.html."""
    if not os.path.exists(HOME):
        return
    page_html = open(HOME, encoding="utf-8").read()
    if HOME_START not in page_html or HOME_END not in page_html:
        return
    news = "\n".join('            <li><a href="%s">%s</a><span>%s · %s</span></li>'
                     % (e("blog/%s.html" % p["slug"]), e(p["title"]), e(p["type"]), nice_date(p["date"]))
                     for p in posts[:5])
    section = """{start}
    <section id="latest-news" class="news-compact" aria-labelledby="latest-news-title">
      <div class="container">
        <h2 id="latest-news-title">Market news</h2>
        <div class="news-compact-col">
          <h3>Latest posts <a href="blog/index.html">All</a></h3>
          <ul>
{news}
          </ul>
        </div>
        <p class="news-compact-note">For general information only; not financial, investment or trading advice.</p>
      </div>
    </section>
    {end}""".format(start=HOME_START, end=HOME_END, news=news)
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
{notice}        <div class="post-body">
{content}
        </div>
        <aside class="post-source">
          {source}
        </aside>
{more}
        <p class="related-all"><a class="btn btn-ghost" href="index.html">See all market news</a></p>
      </div>
    </article>""".format(type=e(p["type"]), title=e(p["title"]), date=e(p["date"]), nice=nice_date(p["date"]),
                         byline=post_byline(p), source=source_note(p), content=p["bodyHtml"], more=more,
                         notice=advice_notice())
    path = "blog/%s.html" % p["slug"]
    article = {"@context": "https://schema.org", "@type": "NewsArticle" if p.get("official") else "Article",
               "headline": p["title"][:110], "datePublished": p["date"],
               "author": {"@type": "Organization" if p.get("official") else "Person", "name": p["author"]},
               "publisher": {"@type": "Organization", "name": SITE}}
    if abs_url(path):
        article["mainEntityOfPage"] = abs_url(path)
    if p.get("image") and abs_url(""):
        article["image"] = abs_url(re.sub(r"^\.\./", "", p["image"]))
    crumbs = breadcrumbs([("Home", ""), ("Market News", "blog/index.html"), (p["title"], path)])
    return page(p["title"] + " — " + SITE, p["summary"] or p["title"], body, path, current="news",
                jsonld=[x for x in [article, crumbs] if x], og_type="article",
                image=re.sub(r"^\.\./", "", p["image"]) if p.get("image") else None)


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
    for p in posts:
        # The three most recent other posts, newest first.
        related = [r for r in posts if r["slug"] != p["slug"]][:3]
        with open(os.path.join(OUT, p["slug"] + ".html"), "w", encoding="utf-8") as fh:
            fh.write(build_post(p, related))
    update_home(posts)
    print("Built blog: %d post(s)." % len(posts))
    import build_site  # the sitemap lists news posts too
    build_site.write_sitemap()


if __name__ == "__main__":
    main()
