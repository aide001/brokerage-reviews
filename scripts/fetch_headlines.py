#!/usr/bin/env python3
"""Collect the latest headlines from other sites for the Market News pages.

Only the headline, the link and the publisher's name are kept; articles stay
on the publisher's site. Each source below was checked for permission to
display its headlines on a commercial website:

  BBC News             BBC encourages use of its feeds on websites, credited
                       "BBC News", without BBC logos.
  European Central Bank  Free use if reproduced accurately and the ECB is
                       cited; links must open the full page (not in a frame).
  Reserve Bank of Australia  Creative Commons Attribution 4.0, credited.
  Federal Reserve      US government work, public domain.
  Bank of Canada       Free use with attribution, not implying endorsement.

Sources that only allow personal or non-commercial use (e.g. the Guardian,
the Bank of England, investingLive) are deliberately left out. Check a new
source's terms before adding it here.

Writes content/headlines.json (newest first), then rebuilds the blog.

    python3 scripts/fetch_headlines.py [--days 30] [--max 40]
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
OUT = os.path.join(ROOT, "content", "headlines.json")
USER_AGENT = "Mozilla/5.0 (compatible; BrokerageReviewsBot/1.0)"

SOURCES = [
    # BBC Business mixes market news with consumer and lifestyle stories, so its
    # headlines must match a finance term ("only") and not read as personal-finance
    # or human-interest pieces ("skip"). "limit" keeps it from crowding out the rest.
    {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "limit": 10,
     "only": r"\b(markets?|shares|stocks?|FTSE|Dow Jones|Nasdaq|S&P 500|investors?|interest rates?|inflation"
             r"|Bank of England|Federal Reserve|Fed|ECB|central banks?|pound|sterling|dollar|euro|yen|yuan"
             r"|currenc(y|ies)|oil prices?|crude|diesel|petrol|fuel prices|gas prices|energy prices|gold|silver|copper"
             r"|commodit(y|ies)|bitcoin|crypto\w*|bonds?|gilts?|yields?|borrowing costs|debt|tariffs?"
             r"|trade (war|deal|deficit|talks)|export ban|GDP|economy|economic|recession|unemployment"
             r"|wage growth|earnings|profits?|IPO|takeover|merger|banks?|banking|lenders?|mortgage rates"
             r"|Treasury|IMF|OPEC)\b",
     "skip": r"^(I|My|We|We're|Would|Should|How much|What's the smallest|Could an?)\b|\byou\b|\byour\b"
             r"|here's (why|how)|Business Daily|bank of mum and dad|leave people|what can we do|charity|^Is it time to|premium bonds|says charity|must keep going|West Bank|thieves|robbery|murder|attack(ed)? man"},
    {"name": "European Central Bank", "url": "https://www.ecb.europa.eu/rss/press.html"},
    {"name": "Reserve Bank of Australia", "url": "https://www.rba.gov.au/rss/rss-cb-media-releases.xml"},
    {"name": "Federal Reserve", "url": "https://www.federalreserve.gov/feeds/press_all.xml",
     # Routine bank-supervision notices aren't market news.
     "skip": r"approval of application|enforcement action|termination of enforcement|applications? (for|by)"},
    {"name": "Federal Reserve", "url": "https://www.federalreserve.gov/feeds/speeches.xml",
     # Titles read "Cook, An Update on ..."; shown as "Fed's Cook: An Update on ...".
     "retitle": (r"^([A-Z][\w'-]+), (.+)$", r"Fed's \1: \2")},
    {"name": "Bank of Canada", "url": "https://www.bankofcanada.ca/content_type/press-releases/feed/"},
]


def wanted(source, title):
    if source.get("only") and not re.search(source["only"], title, re.I):
        return False
    return not (source.get("skip") and re.search(source["skip"], title, re.I))

NS = {
    "rss1": "http://purl.org/rss/1.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "atom": "http://www.w3.org/2005/Atom",
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_date(s):
    s = (s or "").strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d.astimezone(timezone.utc)


def clean_url(url):
    url = (url or "").strip()
    url = re.sub(r"(?<!:)//+", "/", url)  # ECB links contain a doubled slash
    url = re.sub(r"[?&]at_(medium|campaign)=[^&]*", "", url).rstrip("?&")  # BBC tracking tags
    return url if re.match(r"^https://", url) else None


def entries(source):
    root = ET.fromstring(get(source["url"]))
    for it in list(root.iter("item")) + list(root.iter("{%s}item" % NS["rss1"])):
        find = lambda tag: (it.findtext(tag) or it.findtext("rss1:" + tag, namespaces=NS) or "")
        yield find("title"), find("link"), find("pubDate") or it.findtext("dc:date", namespaces=NS)
    for it in root.iter("{%s}entry" % NS["atom"]):
        link = it.find("atom:link", NS)
        yield (it.findtext("atom:title", namespaces=NS), link.get("href") if link is not None else "",
               it.findtext("atom:published", namespaces=NS) or it.findtext("atom:updated", namespaces=NS))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=30, help="drop headlines older than this (default 30)")
    parser.add_argument("--max", type=int, default=40, help="keep at most this many (default 40)")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []
    by_url = {h["url"]: h for h in old}
    failed = 0
    for source in SOURCES:
        try:
            found = list(entries(source))
        except Exception as exc:  # keep the other sources going
            print("error  %s: %s" % (source["name"], exc))
            failed += 1
            continue
        added = 0
        for title, link, date in found:
            title, url = clean(title), clean_url(link)
            if not title or not url or not date:
                continue
            if source.get("retitle"):
                title = re.sub(source["retitle"][0], source["retitle"][1], title)
            if not wanted(source, title):
                continue
            when = parse_date(date)
            if url not in by_url:
                added += 1
            by_url[url] = {"title": title, "url": url, "source": source["name"],
                           "date": when.strftime("%Y-%m-%dT%H:%M:%SZ")}
        print("ok     %s: %d item(s), %d new" % (source["name"], len(found), added))

    # Re-check saved headlines too, so tightened rules also clear older entries.
    rules = {}
    for src in SOURCES:
        rules.setdefault(src["name"], []).append(src)
    by_url = {u: h for u, h in by_url.items()
              if any(wanted(src, h["title"]) for src in rules.get(h["source"], []))}
    limits = {src["name"]: src.get("limit") for src in SOURCES}
    counts, headlines = {}, []
    for h in sorted(by_url.values(), key=lambda h: h["date"], reverse=True):
        if parse_date(h["date"]) < cutoff:
            continue
        counts[h["source"]] = counts.get(h["source"], 0) + 1
        if limits.get(h["source"]) and counts[h["source"]] > limits[h["source"]]:
            continue
        headlines.append(h)
    headlines = headlines[:args.max]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(headlines, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("\n%d headline(s) saved%s." % (len(headlines), "" if not failed else ", %d source(s) failed" % failed))

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_blog
    build_blog.main()
    return 1 if failed == len(SOURCES) else 0


if __name__ == "__main__":
    sys.exit(main())
