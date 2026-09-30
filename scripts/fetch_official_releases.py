#!/usr/bin/env python3
"""Publish US government economic releases to the Market News blog.

Reads the public RSS feeds of the Federal Reserve Board, the Bureau of Labor
Statistics and the Bureau of Economic Analysis, and saves each new release
as content/posts/<slug>.json, then rebuilds the blog. Works of the US
government are in the public domain; every post names its source agency
and links to the original release.

Releases older than --days (default 45) are ignored, and releases already
saved are skipped, so it is safe to run on a schedule. Standard library only.

    python3 scripts/fetch_official_releases.py [--days 45] [--dry-run]
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "content", "posts")
USER_AGENT = "Mozilla/5.0 (compatible; BrokerageReviewsBot/1.0)"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

FED = "Federal Reserve"
BLS = "US Bureau of Labor Statistics"
BEA = "US Bureau of Economic Analysis"

# Each feed: agency, URL, and which items to keep with the topic they get.
FEEDS = [
    {"agency": FED, "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
     # Projections and minutes pages only link to PDFs/other pages, so only
     # policy statements (whose text is on the release page) are published.
     "rules": [(r"FOMC statement", "Interest rates")]},
    {"agency": BLS, "url": "https://www.bls.gov/feed/empsit.rss",
     "rules": [(r"", "Jobs")], "title": "US jobs report: {month}"},
    {"agency": BLS, "url": "https://www.bls.gov/feed/cpi.rss",
     "rules": [(r"", "Inflation")], "title": "US consumer prices (CPI): {month}"},
    {"agency": BEA, "url": "https://apps.bea.gov/rss/rss.xml",
     "rules": [(r"^GDP", "Growth"),
               (r"^Personal Income and Outlays", "Inflation"),
               (r"^U\.S\. International Trade in Goods and Services", "Trade")]},
]

# Paragraphs from release pages that are contact details, not content.
BOILERPLATE = re.compile(r"media inquiries|email protected|^For release at|^Share$|^Implementation Note"
                         r"|^(January|February|March|April|May|June|July|August|September|October|November"
                         r"|December) \d{1,2}, \d{4}$", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", errors="replace")


def text(s):
    """Plain text from an HTML fragment, whitespace collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def paragraphs(fragment):
    parts = re.findall(r"<p[^>]*>(.*?)</p>", fragment or "", re.S | re.I) or [fragment or ""]
    return [t for t in (text(p) for p in parts) if t and not BOILERPLATE.search(t)]


def parse_date(s):
    s = (s or "").strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        d = datetime.fromisoformat(s)
    return d.astimezone(timezone.utc)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:70].rstrip("-")


def reference_month(summary, published):
    """'August 2026' for a release published in September that covers August."""
    m = re.search(r"\b(" + "|".join(MONTHS) + r")\b", summary)
    if not m:
        return published.strftime("%B %Y")
    month = MONTHS.index(m.group(1)) + 1
    year = published.year - 1 if month > published.month else published.year
    return "%s %d" % (m.group(1), year)


def fed_release_body(url):
    """The paragraphs of a Federal Reserve press release page."""
    page = get(url)
    start = page.find('id="article"')
    if start < 0:
        return []
    article = page[start:]
    end = article.find('id="lastUpdate"')
    return paragraphs(article[:end if end > 0 else None])


ATOM = "{http://www.w3.org/2005/Atom}"


def items(feed):
    """Entries of an RSS 2.0 or Atom feed."""
    root = ET.fromstring(get(feed["url"]))
    for it in root.iter("item"):
        yield {
            "title": text(it.findtext("title")),
            "link": (it.findtext("link") or "").strip(),
            "date": parse_date(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")),
            "summary": it.findtext("description") or "",
        }
    for it in root.iter(ATOM + "entry"):
        link = it.find(ATOM + "link")
        yield {
            "title": text(it.findtext(ATOM + "title")),
            "link": (link.get("href") if link is not None else "").strip(),
            "date": parse_date(it.findtext(ATOM + "published") or it.findtext(ATOM + "updated")),
            "summary": it.findtext(ATOM + "content") or it.findtext(ATOM + "summary") or "",
        }


def topic_for(feed, title):
    for pattern, topic in feed["rules"]:
        if re.search(pattern, title, re.I):
            return topic
    return None


def build_post(feed, item, topic):
    summary_paras = paragraphs(item["summary"])
    summary = " ".join(summary_paras)
    title = item["title"]
    if not title and feed.get("title"):
        title = feed["title"].format(month=reference_month(summary, item["date"]))
    body = summary_paras
    if feed["agency"] == FED:
        # Fed feed items carry only a title; the release text is on the page.
        body = fed_release_body(item["link"])[:10]
        summary = body[0] if body else title
        if re.fullmatch(r"Federal Reserve issues FOMC statement", title, re.I):
            title = "Fed policy statement: %d %s" % (item["date"].day, item["date"].strftime("%B %Y"))
    m = re.match(r"^GDP,? \(?(Advance|Second|Third) Estimate\)?.*?\b([1-4])(?:st|nd|rd|th) Quarter (\d{4})", title, re.I)
    if m:
        # BEA's GDP titles list every table in the release; keep the headline.
        title = "US GDP (%s estimate): Q%s %s" % (m.group(1).lower(), m.group(2), m.group(3))
    if not body:
        body = [summary or title]
    if len(summary) > 220:
        summary = summary[:217].rsplit(" ", 1)[0] + "…"
    slug = "%s-%s" % (item["date"].strftime("%Y-%m-%d"), slugify(title))
    return {
        "slug": slug,
        "title": title,
        "date": item["date"].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "Official Release",
        "topic": topic,
        "author": feed["agency"],
        "authorRole": "",
        "provider": feed["agency"],
        "official": True,
        "summary": summary,
        "image": None,
        "bodyHtml": "\n".join("<p>%s</p>" % html.escape(p, quote=False) for p in body),
        "source": {"agency": feed["agency"], "url": item["link"], "feed": feed["url"]},
    }


def known_urls():
    urls = set()
    for name in os.listdir(POSTS) if os.path.isdir(POSTS) else []:
        if name.endswith(".json"):
            post = json.load(open(os.path.join(POSTS, name), encoding="utf-8"))
            urls.add((post.get("source") or {}).get("url"))
    return urls


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=45, help="ignore releases older than this (default 45)")
    parser.add_argument("--dry-run", action="store_true", help="list what would be saved without saving")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    known = known_urls()
    saved, failed = 0, 0
    for feed in FEEDS:
        try:
            feed_items = list(items(feed))
        except Exception as exc:  # one feed being down shouldn't stop the others
            print("error  %s: %s" % (feed["url"], exc))
            failed += 1
            continue
        for item in feed_items:
            topic = topic_for(feed, item["title"])
            if not topic or item["date"] < cutoff or item["link"] in known:
                continue
            post = build_post(feed, item, topic)
            print("%s %s (%s)" % ("would " if args.dry_run else "saved ", post["slug"], feed["agency"]))
            if not args.dry_run:
                os.makedirs(POSTS, exist_ok=True)
                with open(os.path.join(POSTS, post["slug"] + ".json"), "w", encoding="utf-8") as fh:
                    json.dump(post, fh, indent=2, ensure_ascii=False)
                    fh.write("\n")
                known.add(item["link"])
            saved += 1

    print("\n%d new release(s)%s." % (saved, "" if not failed else ", %d feed(s) failed" % failed))
    if saved and not args.dry_run:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import build_blog
        build_blog.main()
    return 1 if failed == len(FEEDS) else 0


if __name__ == "__main__":
    sys.exit(main())
