#!/usr/bin/env python3
"""Build the broker pages that search engines index.

From content/brokers.json, content/affiliate-links.json and content/site.json
this writes:

  js/data.js            the broker data used by the homepage scripts
  brokers/<id>.html     one review page per broker
  best/<slug>.html      "Best ... brokers" guides, each a ranked list
  best/index.html       hub listing every guide and review
  index.html            the homepage's guides hub, static top picks and SEO tags
                        (between <!-- ...:start --> / <!-- ...:end --> markers)
  sitemap.xml           only once siteUrl is set in content/site.json
  robots.txt

Rankings come only from fields every broker has (ratings, costs, platforms,
deposit, regulators), so each guide says exactly how it ranks. While
dataVerified is false in content/site.json the broker pages show a sample-data
notice and carry noindex, so unverified figures are never indexed.

    python3 scripts/build_site.py
"""
import glob
import json
import math
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_common import (DATA_VERIFIED, ROOT, SITE, SITE_URL, YEAR, abs_url, breadcrumbs, e, load_json,  # noqa: E402
                         page)

PIP_VALUE = 10  # USD per pip per standard lot on EUR/USD
MONTH = datetime.now(timezone.utc).strftime("%B %Y")

DATA = load_json("content", "brokers.json")
CATEGORIES = DATA["categories"]
TIER1 = DATA["tier1"]
AFFILIATE = {k: v.strip() for k, v in load_json("content", "affiliate-links.json").items()
             if not k.startswith("_") and isinstance(v, str)}


def round_half_up(x, places):
    f = 10 ** places
    return math.floor(x * f + 0.5) / f


BROKERS = []
for b in DATA["brokers"]:
    b = dict(b)
    b["overall"] = round_half_up(sum(b["ratings"][c["key"]] * c["weight"] for c in CATEGORIES), 1)
    b["cost"] = round_half_up(b["spread"] * PIP_VALUE + b["commission"], 2)
    b["tier1"] = any(r in TIER1 for r in b["regulators"])
    BROKERS.append(b)
BY_ID = {b["id"]: b for b in BROKERS}
BY_RATING = sorted(BROKERS, key=lambda b: (-b["overall"], b["name"]))


# ---------- Formatting ----------

def money(n, digits=0):
    return "$" + ("{:,.%df}" % digits).format(n)


def stars(score):
    return ('<span class="stars" role="img" aria-label="%.1f out of 5"><span class="stars-fill" style="width:%s%%">'
            '</span></span>' % (score, round(score / 5 * 100, 1)))


def logo(b, size="", prefix="../"):
    """Same markup as logo() in js/app.js. Decorative: the name is always shown next to it."""
    cls = "broker-logo" + (" broker-logo-" + size if size else "")
    for ext in ("svg", "png"):
        path = "assets/logos/%s.%s" % (b["id"], ext)
        if os.path.exists(os.path.join(ROOT, path)):
            return '<span class="%s has-img" aria-hidden="true"><img src="%s%s" alt="" loading="lazy" /></span>' % (
                cls, prefix, path)
    letters = "".join(w[0] for w in re.sub(r"[^A-Za-z0-9 ]", " ", b["name"]).split()[:2]).upper() or b["name"][:2]
    hexcol = b["color"].lstrip("#")
    r, g, bl = (int(hexcol[i:i + 2], 16) for i in (0, 2, 4))
    text = "#111" if (r * 299 + g * 587 + bl * 114) / 1000 > 160 else "#fff"
    return '<span class="%s" style="background:%s;color:%s" aria-hidden="true"><span class="broker-logo-text">%s</span></span>' % (
        cls, e(b["color"]), text, e(letters))


def chips(items, tier1=False):
    return '<div class="chips">%s</div>' % "".join(
        '<span class="chip%s">%s</span>' % (" chip-tier1" if tier1 and r in TIER1 else "", e(r)) for r in items)


def cta(b, prefix="../", small=False):
    """Button to the broker: the affiliate link if set, otherwise its official site."""
    aff = AFFILIATE.get(b["id"])
    cls = "btn btn-primary" + (" btn-small-cta" if small else "")
    if aff:
        return ('<a class="%s" href="%s" target="_blank" rel="sponsored nofollow noopener">Open account'
                '<span class="sr-only"> with %s</span></a>') % (cls, e(aff), e(b["name"]))
    return ('<a class="%s" href="https://%s" target="_blank" rel="nofollow noopener">Visit %s</a>'
            % (cls, e(b["domain"]), e(b["name"])))


CTA_NOTE = '<p class="cta-note">Your capital is at risk. We may earn a commission if you open an account.</p>'

DATA_NOTICE = ('<p class="data-notice" role="note"><strong>Sample data.</strong> Broker figures and ratings on this '
               'page are placeholder data that have not been verified yet. Check every detail on the broker\'s '
               'own website.</p>')

NOT_ADVICE = ('<p class="advice-notice" role="note"><strong>Not financial advice.</strong> Our rankings and reviews '
              'are for general information only and are not a recommendation to open an account or to trade. '
              'Forex and CFDs are high-risk; consider independent advice and whether you can afford to lose your '
              'money.</p>')

DISCLOSURE = ('<p class="affiliate-disclosure"><strong>How we make money:</strong> some links on this page are '
              'affiliate links. If you open an account through them we may earn a commission, at no extra cost to '
              'you. This never affects our ratings, which follow our published <a href="../index.html#methodology">'
              'methodology</a>.</p>')


# ---------- "Best" guides ----------

def with_platform(name):
    return lambda b: name in b["platforms"]


# Each guide must rank a genuinely different set or order of brokers; near-duplicate
# lists (e.g. "low deposit", when most brokers have a $0-$50 minimum) hurt more than help.
GUIDES = [
    {"slug": "best-forex-brokers", "title": "Best Forex Brokers for {year}", "short": "Best Forex Brokers",
     "intro": "Our overall ranking of the forex brokers we review, from the highest score down. It is the best "
              "starting point if you don't yet know which features matter most to you.",
     "how": "Ranked by our overall score, a weighted average of fees (30%), trust and regulation (25%), platforms "
            "(20%), research and education (15%) and customer support (10%).",
     "keep": lambda b: True, "sort": lambda b: (-b["overall"], b["name"]), "facts": ["cost", "deposit", "regulators"]},
    {"slug": "best-low-spread-forex-brokers", "title": "Best Low Spread Forex Brokers for {year}",
     "short": "Best Low Spread Brokers",
     "intro": "Brokers with the lowest typical cost to trade EUR/USD, counting both the spread and any commission, "
              "so raw-spread and commission-free accounts are compared on equal terms.",
     "how": "Ranked by all-in cost per standard lot of EUR/USD (typical spread in pips × $10 + round-turn "
            "commission), cheapest first; ties go to the higher overall score.",
     "keep": lambda b: True, "sort": lambda b: (b["cost"], -b["overall"]), "facts": ["cost", "spread", "commission"]},
    {"slug": "best-forex-brokers-for-beginners", "title": "Best Forex Brokers for Beginners in {year}",
     "short": "Best Brokers for Beginners",
     "intro": "Brokers that suit people new to forex: a tier-1 regulator, a low minimum deposit and strong "
              "education to learn from.",
     "how": "Only brokers with at least one tier-1 regulator and a minimum deposit of $100 or less, ranked by "
            "research and education (40%), trust (30%) and fees (30%).",
     "keep": lambda b: b["tier1"] and b["minDeposit"] <= 100,
     "sort": lambda b: (-(b["ratings"]["education"] * .4 + b["ratings"]["trust"] * .3 + b["ratings"]["fees"] * .3),
                        b["name"]),
     "facts": ["education", "deposit", "regulators"]},
    {"slug": "most-trusted-forex-brokers", "title": "Most Trusted Forex Brokers for {year}",
     "short": "Most Trusted Brokers",
     "intro": "Brokers authorised by at least one tier-1 regulator, such as the FCA, ASIC or BaFin, ranked by our "
              "trust and regulation score.",
     "how": "Only brokers with at least one tier-1 regulator, ranked by our trust and regulation score, then "
            "by overall score.",
     "keep": lambda b: b["tier1"], "sort": lambda b: (-b["ratings"]["trust"], -b["overall"], b["name"]),
     "facts": ["trust", "regulators", "deposit"]},
    {"slug": "best-mt4-brokers", "title": "Best MetaTrader 4 (MT4) Brokers for {year}", "short": "Best MT4 Brokers",
     "intro": "Brokers that offer MetaTrader 4, the long-established platform for charting and automated trading "
              "with expert advisors.",
     "how": "Only brokers offering MT4, ranked by overall score.",
     "keep": with_platform("MT4"), "sort": lambda b: (-b["overall"], b["name"]), "facts": ["cost", "platforms", "deposit"]},
    {"slug": "best-mt5-brokers", "title": "Best MetaTrader 5 (MT5) Brokers for {year}", "short": "Best MT5 Brokers",
     "intro": "Brokers that offer MetaTrader 5, MT4's successor with more timeframes, an economic calendar and "
              "access to more asset classes.",
     "how": "Only brokers offering MT5, ranked by overall score.",
     "keep": with_platform("MT5"), "sort": lambda b: (-b["overall"], b["name"]), "facts": ["cost", "platforms", "deposit"]},
    {"slug": "best-tradingview-brokers", "title": "Best TradingView Brokers for {year}",
     "short": "Best TradingView Brokers",
     "intro": "Brokers you can connect to TradingView, so you can chart and place trades from the same screen.",
     "how": "Only brokers that integrate with TradingView, ranked by overall score.",
     "keep": with_platform("TradingView"), "sort": lambda b: (-b["overall"], b["name"]),
     "facts": ["cost", "platforms", "deposit"]},
    {"slug": "best-ctrader-brokers", "title": "Best cTrader Brokers for {year}", "short": "Best cTrader Brokers",
     "intro": "Brokers offering cTrader, a platform popular with scalpers and algorithmic traders for its "
              "depth-of-market view and cBots.",
     "how": "Only brokers offering cTrader, ranked by overall score.",
     "keep": with_platform("cTrader"), "sort": lambda b: (-b["overall"], b["name"]),
     "facts": ["cost", "platforms", "deposit"]},
]
MAX_LIST = 10


def guide_list(g):
    return sorted([b for b in BROKERS if g["keep"](b)], key=g["sort"])[:MAX_LIST]


def fact(b, key):
    return {
        "cost": ("EUR/USD cost", money(b["cost"], 2) + " /lot"),
        "spread": ("EUR/USD spread", "%.1f pips" % b["spread"]),
        "commission": ("Commission", money(b["commission"], 2) if b["commission"] else "None"),
        "deposit": ("Min deposit", money(b["minDeposit"])),
        "regulators": ("Regulators", "%d%s" % (len(b["regulators"]), " incl. tier-1" if b["tier1"] else "")),
        "education": ("Education score", "%.1f / 5" % b["ratings"]["education"]),
        "trust": ("Trust score", "%.1f / 5" % b["ratings"]["trust"]),
        "platforms": ("Platforms", ", ".join(b["platforms"][:3]) + (" +%d" % (len(b["platforms"]) - 3)
                                                                     if len(b["platforms"]) > 3 else "")),
    }[key]


def notices():
    return ("" if DATA_VERIFIED else DATA_NOTICE) + NOT_ADVICE


def build_guide(g):
    title = g["title"].format(year=YEAR)
    ranked = guide_list(g)
    path = "best/%s.html" % g["slug"]
    cards = []
    for i, b in enumerate(ranked):
        facts = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % tuple(map(str, fact(b, k))) for k in g["facts"])
        cards.append("""        <article class="rank-card" id="{id}">
          <div class="rank-num" aria-hidden="true">{n}</div>
          <div class="rank-main">
            <div class="rank-head">{logo}
              <div><h2><a href="../brokers/{id}.html">{name}</a></h2><p class="muted">{best_for}</p></div>
              <div class="rank-score"><strong>{score:.1f}</strong>{stars}</div>
            </div>
            <dl class="rank-facts">{facts}</dl>
            <ul class="pros rank-pros">{pros}</ul>
            <div class="rank-actions">
              <a class="btn btn-ghost" href="../brokers/{id}.html">Read {name} review</a>
              {cta}
            </div>
            {note}
          </div>
        </article>""".format(id=e(b["id"]), n=i + 1, logo=logo(b), name=e(b["name"]), best_for=e(b["bestFor"]),
                             score=b["overall"], stars=stars(b["overall"]), facts=facts, cta=cta(b), note=CTA_NOTE,
                             pros="".join("<li>%s</li>" % e(p) for p in b["pros"][:2])))
    toc = "".join('<li><a href="#%s">%s</a> <span class="muted">%.1f</span></li>' % (e(b["id"]), e(b["name"]), b["overall"])
                  for b in ranked)
    others = "".join('<li><a href="%s.html">%s</a></li>' % (o["slug"], e(o["title"].format(year=YEAR)))
                     for o in GUIDES if o is not g)
    body = """    <article class="section guide">
      <div class="container narrow">
        <p class="breadcrumb"><a href="../index.html">Home</a> / <a href="index.html">Best brokers</a></p>
        <h1 class="post-title">{title}</h1>
        <p class="post-meta">Updated {month} · {count} brokers ranked</p>
        {notices}
        <p class="lead-text">{intro}</p>
        <div class="how-box"><strong>How we ranked them:</strong> {how} <a href="../index.html#methodology">Our methodology</a>.</div>
        <nav class="toc" aria-label="Ranking"><h2>The list</h2><ol>{toc}</ol></nav>
{cards}
        {disclosure}
        <section class="more-guides" aria-labelledby="more-guides-title">
          <h2 id="more-guides-title">More broker guides</h2>
          <ul>{others}</ul>
        </section>
      </div>
    </article>""".format(title=e(title), month=MONTH, count=len(ranked), notices=notices(), intro=e(g["intro"]),
                         how=e(g["how"]), toc=toc, cards="\n".join(cards), disclosure=DISCLOSURE, others=others)
    item_list = {"@context": "https://schema.org", "@type": "ItemList", "name": title,
                 "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": b["name"],
                                      **({"url": abs_url("brokers/%s.html" % b["id"])} if SITE_URL else {})}
                                     for i, b in enumerate(ranked)]}
    desc = "%s %s" % (g["intro"], "Updated %s." % MONTH)
    crumbs = breadcrumbs([("Home", ""), ("Best brokers", "best/index.html"), (title, path)])
    return path, page("%s — %s" % (title, SITE), desc[:300], body, path, current="best",
                      jsonld=[x for x in [item_list, crumbs] if x], noindex=not DATA_VERIFIED)


# ---------- Reviews ----------

def guides_featuring(b):
    out = []
    for g in GUIDES:
        ranked = guide_list(g)
        if b in ranked:
            out.append((g, ranked.index(b) + 1))
    return sorted(out, key=lambda x: x[1])


def build_review(b):
    path = "brokers/%s.html" % b["id"]
    title = "%s Review %d: Fees, Spreads & Regulation" % (b["name"], YEAR)
    bars = "".join('<li><span>%s</span><span class="bar"><span style="width:%s%%"></span></span><b>%.1f</b></li>'
                   % (e(c["label"]), round(b["ratings"][c["key"]] / 5 * 100, 1), b["ratings"][c["key"]])
                   for c in CATEGORIES)
    facts = [("EUR/USD spread", "%.1f pips (%s account)" % (b["spread"], e(b["account"]))),
             ("Commission", money(b["commission"], 2) + " per lot round-turn" if b["commission"] else "None"),
             ("All-in cost", money(b["cost"], 2) + " per standard lot"),
             ("Minimum deposit", money(b["minDeposit"])),
             ("Max leverage", '1:%d <small class="muted">(varies by entity and country)</small>' % b["leverage"]),
             ("Instruments", "{:,}+".format(b["instruments"])),
             ("Founded", str(b["founded"])), ("Headquarters", e(b["hq"]))]
    featured = guides_featuring(b)
    featured_html = "".join('<li><a href="../best/%s.html">#%d in %s</a></li>' % (g["slug"], n, e(g["short"]))
                            for g, n in featured)
    idx = BY_RATING.index(b)
    others = [o for o in BY_RATING[max(0, idx - 3):idx + 4] if o is not b][:5]
    others_html = "".join('<li><a href="%s.html">%s review</a> <span class="muted">%.1f</span></li>'
                          % (e(o["id"]), e(o["name"]), o["overall"]) for o in others)
    body = """    <article class="section review-page">
      <div class="container narrow">
        <p class="breadcrumb"><a href="../index.html">Home</a> / <a href="../best/index.html">Broker reviews</a></p>
        <header class="review-head">{logo}
          <div><h1 class="post-title">{name} Review</h1>
          <p class="muted">{best_for} · Founded {founded} · {hq}</p></div>
          <div class="review-score"><strong>{score:.1f}</strong>{stars}<small>Overall</small></div>
        </header>
        {notices}
        <div class="cta-box">
          <div><strong>{name}</strong><span class="muted">Min deposit {deposit} · EUR/USD cost {cost}/lot</span></div>
          <div class="cta-box-action">{cta}{note}</div>
        </div>
        <p class="lead-text">{summary}</p>
        <div class="review-grid">
          <section><h2>Ratings breakdown</h2><ul class="bars">{bars}</ul>
            <p class="muted small"><a href="../index.html#methodology">How we rate brokers</a></p></section>
          <section><h2>Key facts</h2><dl class="facts">{facts}</dl></section>
        </div>
        <div class="review-grid">
          <section><h2>Pros</h2><ul class="pros">{pros}</ul></section>
          <section><h2>Cons</h2><ul class="cons">{cons}</ul></section>
        </div>
        <div class="review-grid">
          <section><h2>Regulation</h2>{regs}<p class="muted small">Highlighted = tier-1 regulator. Protection depends on
            the entity you open an account with.</p></section>
          <section><h2>Platforms</h2>{plats}</section>
        </div>
        {featured_block}
        <div class="cta-box">
          <div><strong>Ready to compare?</strong><span class="muted">See how {name} stacks up in our
            <a href="../index.html#compare">comparison table</a>.</span></div>
          <div class="cta-box-action">{cta}{note}</div>
        </div>
        {disclosure}
        <section class="more-guides" aria-labelledby="more-reviews-title">
          <h2 id="more-reviews-title">More broker reviews</h2>
          <ul>{others}</ul>
        </section>
      </div>
    </article>""".format(logo=logo(b, "lg"), name=e(b["name"]), best_for=e(b["bestFor"]), founded=b["founded"],
                         hq=e(b["hq"]), score=b["overall"], stars=stars(b["overall"]), notices=notices(),
                         deposit=money(b["minDeposit"]), cost=money(b["cost"], 2), cta=cta(b), note=CTA_NOTE,
                         summary=e(b["summary"]), bars=bars,
                         facts="".join("<div><dt>%s</dt><dd>%s</dd></div>" % f for f in facts),
                         pros="".join("<li>%s</li>" % e(p) for p in b["pros"]),
                         cons="".join("<li>%s</li>" % e(p) for p in b["cons"]),
                         regs=chips(b["regulators"], tier1=True), plats=chips(b["platforms"]),
                         featured_block=('<section class="more-guides"><h2>Featured in our guides</h2><ul>%s</ul></section>'
                                         % featured_html) if featured else "",
                         disclosure=DISCLOSURE, others=others_html)
    desc = ("%s review: %s. EUR/USD from %.1f pips, minimum deposit %s, regulated by %s. Overall score %.1f/5."
            % (b["name"], b["bestFor"].rstrip("."), b["spread"], money(b["minDeposit"]),
               ", ".join(b["regulators"][:3]), b["overall"]))
    crumbs = breadcrumbs([("Home", ""), ("Broker reviews", "best/index.html"), ("%s review" % b["name"], path)])
    logo_file = next((p for p in ("assets/logos/%s.svg" % b["id"], "assets/logos/%s.png" % b["id"])
                      if os.path.exists(os.path.join(ROOT, p))), None)
    return path, page("%s — %s" % (title, SITE), desc, body, path, current="best",
                      jsonld=[x for x in [crumbs] if x], noindex=not DATA_VERIFIED, image=logo_file)


# ---------- Hubs ----------

AWARD_ICON = ('<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.8" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="9" r="6"/>'
              '<path d="M9.5 9l1.8 1.8L15 7.5M8.5 14.2L7 22l5-3 5 3-1.5-7.8"/></svg>')


def hub_lists(prefix):
    """Guide and review link cards; prefix is the path from the page to the site root."""
    guides = "\n".join('          <li><a class="hub-card" href="%sbest/%s.html">%s<span class="hub-label">%s</span></a></li>'
                       % (prefix, g["slug"], AWARD_ICON, e(g["title"].format(year=YEAR))) for g in GUIDES)
    reviews = "\n".join('          <li><a class="hub-card" href="%sbrokers/%s.html">%s<span class="hub-label">%s Review</span>'
                        '<b class="hub-score">%.1f</b></a></li>'
                        % (prefix, b["id"], logo(b, "sm", prefix=prefix), e(b["name"]), b["overall"]) for b in BY_RATING)
    return guides, reviews


def build_hub():
    guides, reviews = hub_lists("../")
    path = "best/index.html"
    body = """    <section class="section">
      <div class="container">
        <div class="section-head">
          <p class="eyebrow">Guides &amp; reviews</p>
          <h1>Best forex brokers {year}: guides and reviews</h1>
          <p>Ranked lists for different needs, and an in-depth review of every broker we cover.</p>
        </div>
        {notices}
        <h2 class="hub-title">Broker guides</h2>
        <ul class="hub-grid">
{guides}
        </ul>
        <h2 class="hub-title">Broker reviews</h2>
        <ul class="hub-grid">
{reviews}
        </ul>
      </div>
    </section>""".format(year=YEAR, notices=notices(), guides=guides, reviews=reviews)
    return path, page("Best Forex Brokers %d: Guides and Reviews — %s" % (YEAR, SITE),
                      "Ranked guides to the best forex brokers for low spreads, beginners, MT4, MT5, TradingView and "
                      "more, plus in-depth reviews of %d brokers." % len(BROKERS), body, path, current="best",
                      jsonld=[x for x in [breadcrumbs([("Home", ""), ("Best brokers", path)])] if x],
                      noindex=not DATA_VERIFIED)


# ---------- Homepage ----------

def replace_between(text, name, content):
    start, end = "<!-- %s:start -->" % name, "<!-- %s:end -->" % name
    if start not in text or end not in text:
        print("note   index.html has no %s markers; skipped" % name)
        return text
    before, rest = text.split(start, 1)
    return before + start + content + end + rest.split(end, 1)[1]


def home_top_picks():
    """Static copy of the top picks the homepage script renders, so they're in the HTML."""
    medals = ["Best overall", "Runner-up", "Also great"]
    cards = []
    for i, b in enumerate(BY_RATING[:3]):
        cards.append(
            '<article class="pick-card"><span class="pick-badge">%s</span>'
            '<div class="pick-head">%s<div><h3>%s</h3><p class="muted">%s</p></div></div>'
            '<div class="pick-score"><strong>%.1f</strong>%s</div>'
            '<dl class="pick-facts"><div><dt>EUR/USD cost</dt><dd>%s/lot</dd></div>'
            '<div><dt>Min deposit</dt><dd>%s</dd></div><div><dt>Regulators</dt><dd>%d</dd></div></dl>'
            '<ul class="pick-pros">%s</ul>'
            '<a class="btn btn-primary btn-block" href="brokers/%s.html">Read review</a></article>'
            % (medals[i], logo(b, "lg", prefix=""), e(b["name"]), e(b["bestFor"]), b["overall"], stars(b["overall"]),
               money(b["cost"], 2), money(b["minDeposit"]), len(b["regulators"]),
               "".join("<li>%s</li>" % e(p) for p in b["pros"][:2]), e(b["id"])))
    return "".join(cards)


def home_hub():
    guides, reviews = hub_lists("")
    return """
    <section id="guides" class="section section-alt">
      <div class="container">
        <div class="section-head">
          <h2>Broker guides and reviews</h2>
          <p>Ranked lists for different trading needs, and a full review of every broker we cover.</p>
        </div>
        <h3 class="hub-title">Guides</h3>
        <ul class="hub-grid">
{guides}
        </ul>
        <h3 class="hub-title">Reviews</h3>
        <ul class="hub-grid">
{reviews}
        </ul>
        <p class="hub-more"><a class="btn btn-ghost" href="best/index.html">All guides and reviews</a></p>
      </div>
    </section>
    """.format(guides=guides, reviews=reviews)


def home_seo():
    tags = []
    if not DATA_VERIFIED:
        tags.append('<meta name="robots" content="noindex, follow" />')
    if SITE_URL:
        tags += ['<link rel="canonical" href="%s/" />' % e(SITE_URL), '<meta property="og:url" content="%s/" />' % e(SITE_URL)]
    tags += ['<meta property="og:site_name" content="%s" />' % e(SITE), '<meta property="og:type" content="website" />',
             '<meta property="og:title" content="Compare the Best Forex Brokers %d — %s" />' % (YEAR, e(SITE)),
             '<meta property="og:description" content="Compare spreads, commissions, regulation and platforms across '
             '%d forex brokers, with ranked guides and in-depth reviews." />' % len(BROKERS),
             '<meta name="twitter:card" content="summary" />']
    if SITE_URL:
        site = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": SITE_URL + "/"}
        tags.append('<script type="application/ld+json">%s</script>' % json.dumps(site))
    return "\n  " + "\n  ".join(tags) + "\n  "


def update_home():
    path = os.path.join(ROOT, "index.html")
    text = open(path, encoding="utf-8").read()
    new = replace_between(text, "seo", home_seo())
    new = replace_between(new, "top-picks", home_top_picks())
    new = replace_between(new, "guides", home_hub())
    if new != text:
        open(path, "w", encoding="utf-8").write(new)


# ---------- Data for the homepage scripts ----------

def write_data_js():
    brokers = []
    for b in DATA["brokers"]:
        b = dict(b)
        # Tell the homepage script which logo file exists ("" = none, show initials) so it
        # doesn't request missing files.
        b["logoExt"] = next((x for x in ("svg", "png")
                             if os.path.exists(os.path.join(ROOT, "assets", "logos", "%s.%s" % (b["id"], x)))), "")
        brokers.append(b)
    out = ("/*\n * Broker data for the homepage scripts. GENERATED by scripts/build_site.py from\n"
           " * content/brokers.json and content/affiliate-links.json; edit those files, not this one.\n"
           " * Figures are approximate sample data until content/site.json says dataVerified: true.\n */\n"
           "window.BROKERS = %s;\n\nwindow.TIER1_REGULATORS = %s;\n\nwindow.RATING_CATEGORIES = %s;\n\n"
           "window.AFFILIATE_LINKS = %s;\n") % (json.dumps(brokers, indent=2, ensure_ascii=False),
                                                json.dumps(TIER1), json.dumps(CATEGORIES, indent=2, ensure_ascii=False),
                                                json.dumps({k: v for k, v in AFFILIATE.items() if v}, indent=2))
    open(os.path.join(ROOT, "js", "data.js"), "w", encoding="utf-8").write(out)


# ---------- Sitemap and robots ----------

def write_sitemap():
    """sitemap.xml of indexable pages (needs siteUrl) and robots.txt."""
    robots = "User-agent: *\nAllow: /\n"
    if SITE_URL:
        robots += "\nSitemap: %s/sitemap.xml\n" % SITE_URL
    open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(robots)
    sitemap = os.path.join(ROOT, "sitemap.xml")
    if not SITE_URL:
        if os.path.exists(sitemap):
            os.remove(sitemap)
        return
    urls = []
    if DATA_VERIFIED:
        urls.append(("", None))
        urls += [(os.path.relpath(p, ROOT), None) for p in sorted(glob.glob(os.path.join(ROOT, "best", "*.html")))]
        urls += [(os.path.relpath(p, ROOT), None) for p in sorted(glob.glob(os.path.join(ROOT, "brokers", "*.html")))]
    urls += [("blog/index.html", None), ("blog/headlines.html", None)]
    for p in sorted(glob.glob(os.path.join(ROOT, "content", "posts", "*.json"))):
        post = json.load(open(p, encoding="utf-8"))
        urls.append(("blog/%s.html" % post["slug"], post["date"][:10]))
    rows = "".join("  <url><loc>%s</loc>%s</url>\n" % (e(abs_url(u)), "<lastmod>%s</lastmod>" % d if d else "")
                   for u, d in urls)
    open(sitemap, "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % rows)


# ---------- Main ----------

def write(path, html_text):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(html_text)


def main():
    write_data_js()
    keep = {"brokers": set(), "best": set()}
    for b in BROKERS:
        path, text = build_review(b)
        write(path, text)
        keep["brokers"].add(os.path.basename(path))
    for g in GUIDES:
        if len(guide_list(g)) < 3:
            print("skip   %s (fewer than 3 brokers qualify)" % g["slug"])
            continue
        path, text = build_guide(g)
        write(path, text)
        keep["best"].add(os.path.basename(path))
    path, text = build_hub()
    write(path, text)
    keep["best"].add("index.html")
    for folder, names in keep.items():  # remove pages for brokers/guides that no longer exist
        for f in glob.glob(os.path.join(ROOT, folder, "*.html")):
            if os.path.basename(f) not in names:
                os.remove(f)
    update_home()
    write_sitemap()
    print("Built site: %d reviews, %d guides%s." % (len(keep["brokers"]), len(keep["best"]) - 1,
                                                   "" if DATA_VERIFIED else " (sample data: noindex)"))


if __name__ == "__main__":
    main()
