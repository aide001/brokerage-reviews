#!/usr/bin/env python3
"""Turn FxPro commentary emails in blog-inbox/ into blog posts.

Each email lives in its own folder, blog-inbox/<slug>/, holding:
  email.json   Details of the email (written by fetch_fxpro_emails.py or by hand)
  *.docx       The commentary itself (an "ENG" file is preferred if there are several)
  *.png/*.jpg  Charts sent with the email

For every folder with its attachments present, this writes
content/posts/<slug>.json and copies images to assets/blog/<slug>/, then
rebuilds the blog pages. Folders already imported are skipped unless
--force is given. Standard library only.

    python3 scripts/import_commentary.py [--force]
"""
import html
import json
import os
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, "blog-inbox")
POSTS = os.path.join(ROOT, "content", "posts")
IMAGES = os.path.join(ROOT, "assets", "blog")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp")

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
W = "{%s}" % NS["w"]
R = "{%s}" % NS["r"]


def slugify(text):
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:80].rstrip("-")


def safe_href(url):
    return url if re.match(r"^(https?:|mailto:)", url or "", re.I) else None


# ---------- DOCX -> HTML ----------

class DocxConverter:
    """Converts the parts of a .docx that commentary uses: headings,
    paragraphs, bold/italic, links, lists, tables and inline images."""

    def __init__(self, path, image_dir, image_url):
        self.zip = zipfile.ZipFile(path)
        self.image_dir = image_dir
        self.image_url = image_url
        self.rels = self._rels()
        self.images = []

    def _rels(self):
        try:
            root = ET.fromstring(self.zip.read("word/_rels/document.xml.rels"))
        except KeyError:
            return {}
        return {r.get("Id"): (r.get("Target"), r.get("TargetMode")) for r in root}

    def convert(self):
        body = ET.fromstring(self.zip.read("word/document.xml")).find(W + "body")
        blocks, list_items = [], []

        def flush_list():
            if list_items:
                blocks.append("<ul>" + "".join("<li>%s</li>" % li for li in list_items) + "</ul>")
                list_items.clear()

        for el in body:
            if el.tag == W + "p":
                kind, content = self._paragraph(el)
                if not content:
                    continue
                if kind == "li":
                    list_items.append(content)
                    continue
                flush_list()
                blocks.append("<%s>%s</%s>" % (kind, content, kind) if kind != "raw" else content)
            elif el.tag == W + "tbl":
                flush_list()
                blocks.append(self._table(el))
        flush_list()
        return blocks

    def _paragraph(self, p):
        style = p.find("w:pPr/w:pStyle", NS)
        style = (style.get(W + "val") if style is not None else "") or ""
        is_list = p.find("w:pPr/w:numPr", NS) is not None or style.lower().startswith("list")
        parts, images = [], []
        for child in p:
            if child.tag == W + "r":
                parts.append(self._run(child, images))
            elif child.tag == W + "hyperlink":
                target = self.rels.get(child.get(R + "id"), (None, None))[0]
                inner = "".join(self._run(r, images) for r in child.findall("w:r", NS))
                href = safe_href(target)
                parts.append('<a href="%s" rel="nofollow noopener">%s</a>' % (html.escape(href), inner) if href else inner)
        text = "".join(parts).strip()
        figures = "".join(images)
        if not text:
            return ("raw", figures) if figures else (None, "")
        # Typed bullets ("•    text") are list items too.
        text, bullets = re.subn(r"^((?:<[^>]+>)*)[•·▪]+[\s\xa0]*", r"\1", text)
        is_list = is_list or bool(bullets)
        low = style.lower()
        # Some documents use heading styles for whole paragraphs; real headings are short.
        long_text = len(strip_tags(text)) > 120
        if low in ("title", "heading1", "heading 1") and not long_text:
            kind = "h2"
        elif low.startswith("heading") and not long_text:
            kind = "h3"
        else:
            kind = "li" if is_list else "p"
        if figures:  # keep images as their own blocks after the text
            return "raw", "<%s>%s</%s>%s" % (kind if kind != "li" else "p", text, kind if kind != "li" else "p", figures)
        return kind, text

    def _run(self, r, images):
        out = []
        for node in r:
            if node.tag == W + "t":
                out.append(html.escape(node.text or ""))
            elif node.tag == W + "tab":
                out.append(" ")
            elif node.tag in (W + "br", W + "cr"):
                out.append("<br>")
            elif node.tag == W + "drawing":
                for blip in node.iter("{%s}blip" % NS["a"]):
                    src = self._image(blip.get(R + "embed"))
                    if src:
                        images.append('<figure><img src="%s" alt="" loading="lazy"></figure>' % src)
        text = "".join(out)
        if not text.strip():
            return text
        rpr = r.find("w:rPr", NS)
        if rpr is not None:
            if self._on(rpr.find("w:b", NS)):
                text = "<strong>%s</strong>" % text
            if self._on(rpr.find("w:i", NS)):
                text = "<em>%s</em>" % text
        return text

    @staticmethod
    def _on(el):
        return el is not None and el.get(W + "val", "true").lower() not in ("0", "false", "none")

    def _image(self, rel_id):
        target = self.rels.get(rel_id, (None, None))[0]
        if not target:
            return None
        name = "word/" + target.lstrip("/") if not target.startswith("word/") else target
        name = os.path.normpath(name).replace(os.sep, "/")
        try:
            data = self.zip.read(name)
        except KeyError:
            return None
        filename = "doc-%d%s" % (len(self.images) + 1, os.path.splitext(name)[1].lower())
        os.makedirs(self.image_dir, exist_ok=True)
        with open(os.path.join(self.image_dir, filename), "wb") as fh:
            fh.write(data)
        self.images.append(filename)
        return self.image_url + filename

    def _table(self, tbl):
        rows = []
        for tr in tbl.findall("w:tr", NS):
            cells = []
            for tc in tr.findall("w:tc", NS):
                texts = [self._paragraph(p)[1] for p in tc.findall("w:p", NS)]
                cells.append("<td>%s</td>" % "<br>".join(t for t in texts if t))
            rows.append("<tr>%s</tr>" % "".join(cells))
        return '<div class="table-scroll"><table>%s</table></div>' % "".join(rows)


# ---------- Import ----------

def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


CAPTION_RE = re.compile(r"^Fig(?:ure)?\.?\s*(\d+)\.?\s*(.+)$", re.I | re.S)
TICKERS_RE = re.compile(r"^[A-Za-z0-9$_.&/-]+(?:\s*,\s*[A-Za-z0-9$_.&/-]+)+$")
# Shorthand FxPro uses in chart file names, spelt out as the captions write it.
ALIASES = {
    "btc": "bitcoin", "eth": "ethereum", "cryptocap": "crypto market capitalisation",
    "nfp": "nonfarm payrolls", "boj": "bank japan", "cpi": "consumer inflation",
    "usdx": "dollar index", "xau": "gold",
}
STOPWORDS = {"vs", "the", "and", "of", "a", "an", "in", "on", "at", "to", "is", "its", "has", "us", "fig", "png", "jpg", "jpeg"}


def plain_lines(block):
    return [l.strip() for l in strip_tags(re.sub(r"<br\s*/?>", "\n", block)).split("\n") if l.strip()]


def extract_extras(blocks):
    """Pull figure captions, the "Summary:" line and the trailing ticker list out of the body."""
    captions, summary, kept = {}, None, []
    for i, b in enumerate(blocks):
        if b.startswith("<p>"):
            lines = [part.strip() for l in plain_lines(b) for part in re.split(r"(?=Fig(?:ure)?\.\s*\d+\.)", l) if part.strip()]
            matches = [CAPTION_RE.match(l) for l in lines]
            if lines and all(matches):
                for m in matches:
                    captions[int(m.group(1))] = m.group(2).strip()
                continue
            text = " ".join(lines)
            if re.match(r"^Summary\s*:", text, re.I):
                summary = re.sub(r"^Summary\s*:\s*", "", text, flags=re.I)
                continue
            if i == len(blocks) - 1 and TICKERS_RE.match(text):
                continue
        kept.append(b)
    return kept, captions, summary


def words(text):
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 1 and w not in STOPWORDS}


def camel_words(name):
    stem = os.path.splitext(name)[0]
    letters = re.sub(r"[^a-z]", "", stem.lower())
    extra = " ".join(v for k, v in ALIASES.items() if k in letters)
    return words(" ".join(re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+", stem)) + " " + extra)


def match_captions(labels, captions):
    """Map caption number -> figure index. Chart names are matched to caption
    wording first, since documents sometimes number figures out of order;
    anything left over is paired by number."""
    scores = sorted(((len(camel_words(lbl) & words(cap)), n, i)
                     for n, cap in captions.items() for i, lbl in enumerate(labels) if lbl), reverse=True)
    assigned, used = {}, set()
    for score, n, i in scores:
        if score and n not in assigned and i not in used:
            assigned[n] = i
            used.add(i)
    for n in sorted(captions):
        if n not in assigned:
            free = [i for i in range(len(labels)) if i not in used]
            if not free:
                break
            i = n - 1 if n - 1 in free else free[0]
            assigned[n] = i
            used.add(i)
    return assigned


def figure_html(src, caption, alt):
    cap = "<figcaption>%s</figcaption>" % html.escape(caption) if caption else ""
    return '<figure><img src="%s" alt="%s" loading="lazy">%s</figure>' % (src, html.escape(caption or alt), cap)


def number_prefix(name):
    m = re.match(r"^(\d+)[_ -]", name)
    return int(m.group(1)) if m else None


def pick_docx(files):
    docs = [f for f in files if f.lower().endswith(".docx") and not f.startswith("~$")]
    eng = [f for f in docs if re.search(r"eng", f, re.I)]
    return (eng or docs or [None])[0]


def import_folder(folder, force=False):
    meta_path = os.path.join(folder, "email.json")
    if not os.path.exists(meta_path):
        return "skip", "no email.json"
    meta = json.load(open(meta_path, encoding="utf-8"))
    slug = meta.get("slug") or os.path.basename(folder)
    out_path = os.path.join(POSTS, slug + ".json")
    if os.path.exists(out_path) and not force:
        return "skip", "already imported"

    files = sorted(os.listdir(folder))
    docx = pick_docx(files)
    attached_images = [f for f in files if f.lower().endswith(IMAGE_EXTS)]
    if meta.get("includeImages") is not None:
        attached_images = [f for f in meta["includeImages"] if f in attached_images]
    if not docx and not attached_images:
        expected = ", ".join(meta.get("expectedAttachments", [])) or "a .docx or images"
        return "wait", "waiting for attachments (" + expected + ")"

    image_dir = os.path.join(IMAGES, slug)
    if os.path.isdir(image_dir):
        shutil.rmtree(image_dir)
    image_url = "../assets/blog/%s/" % slug

    blocks, doc_images = [], []
    if docx:
        conv = DocxConverter(os.path.join(folder, docx), image_dir, image_url)
        blocks = conv.convert()
        doc_images = conv.images
        # Drop a leading heading/paragraph that just repeats the title.
        if blocks and slugify(strip_tags(blocks[0])) == slugify(meta["title"]):
            blocks = blocks[1:]

    blocks, captions, doc_summary = extract_extras(blocks)
    # Order attached charts by their number prefix ("1_Fed-ECB.png"), else by name,
    # unless includeImages gives the order explicitly.
    if meta.get("includeImages") is None:
        attached_images.sort(key=lambda f: (number_prefix(f) is None, number_prefix(f) or 0, f))
    # Captions for images that don't have a "Fig. N" line, keyed by file name.
    image_captions = meta.get("imageCaptions") or {}

    figures = []
    if doc_images:
        # Embedded images have no useful names; borrow the numbered attachment names for matching.
        by_number = {number_prefix(f): f for f in attached_images if number_prefix(f)}
        labels = [by_number.get(i + 1, "") for i in range(len(doc_images))]
        order = match_captions(labels, captions)
        caption_for = {i: captions[n] for n, i in order.items()}
        body = "\n".join(blocks)
        for i, name in enumerate(doc_images):
            old_fig = '<figure><img src="%s%s" alt="" loading="lazy"></figure>' % (image_url, name)
            body = body.replace(old_fig, figure_html(image_url + name, caption_for.get(i), meta["title"]))
        blocks = body.split("\n")
    else:
        # Attached charts are added when the document doesn't embed its own images.
        os.makedirs(image_dir, exist_ok=True)
        dests = []
        for name in attached_images:
            dest = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
            shutil.copyfile(os.path.join(folder, name), os.path.join(image_dir, dest))
            dests.append(dest)
        order = match_captions(attached_images, captions)
        ranked = sorted(range(len(dests)), key=lambda i: min([n for n, j in order.items() if j == i] or [999 + i]))
        caption_for = {i: captions[n] for n, i in order.items()}
        for i, name in enumerate(attached_images):
            caption_for.setdefault(i, image_captions.get(name))
        figures = [dests[i] for i in ranked]
        fig_blocks = [figure_html(image_url + dests[i], caption_for.get(i), meta["title"]) for i in ranked]
        # Charts illustrate the opening overview, so they go before the second section heading.
        headings = [k for k, b in enumerate(blocks) if b.startswith(("<h2>", "<h3>"))]
        at = headings[1] if len(headings) > 1 else len(blocks)
        blocks[at:at] = fig_blocks

    paragraphs = [strip_tags(b) for b in blocks if b.startswith("<p>")]
    summary = meta.get("summary") or doc_summary or (paragraphs[0] if paragraphs else "")
    if len(summary) > 220:
        summary = summary[:217].rsplit(" ", 1)[0] + "…"

    post = {
        "slug": slug,
        "title": meta["title"],
        "date": meta["date"],
        "type": meta.get("type", "Market Comment"),
        "author": meta.get("author", "FxPro Analyst Team"),
        "authorRole": meta.get("authorRole", "Senior Market Analyst"),
        "provider": "FxPro",
        "summary": summary,
        "image": (image_url + (doc_images or figures)[0]) if (doc_images or figures) else None,
        "bodyHtml": "\n".join(blocks),
        "source": {
            "from": meta.get("from"),
            "subject": meta.get("subject"),
            "gmailMessageId": meta.get("gmailMessageId"),
            "gmailThreadId": meta.get("gmailThreadId"),
            "receivedAt": meta.get("receivedAt"),
        },
        # Set when the published link has been emailed back to the sender.
        "linkSentAt": None,
    }
    old = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    if old.get("linkSentAt"):
        post["linkSentAt"] = old["linkSentAt"]
    os.makedirs(POSTS, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(post, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return "ok", "%d blocks, %d images" % (len(blocks), len(doc_images or figures))


def main():
    force = "--force" in sys.argv
    if not os.path.isdir(INBOX):
        print("No blog-inbox/ folder.")
        return 1
    imported = 0
    for name in sorted(os.listdir(INBOX)):
        folder = os.path.join(INBOX, name)
        if not os.path.isdir(folder) or name.startswith((".", "_")):
            continue
        status, detail = import_folder(folder, force)
        imported += status == "ok"
        print("%-6s %s: %s" % (status, name, detail))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_blog
    build_blog.main()
    print("\nImported %d post(s)." % imported)
    return 0


if __name__ == "__main__":
    sys.exit(main())
