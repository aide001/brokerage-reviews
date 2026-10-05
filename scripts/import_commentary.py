#!/usr/bin/env python3
"""Turn FxPro commentary emails in blog-inbox/ into blog posts.

Each email lives in its own folder, blog-inbox/<slug>/, holding:
  email.json   Details of the email (written by fetch_fxpro_emails.py or by hand)
  *.docx       The commentary itself (an "ENG" file is preferred if there are several)
  *.pdf        Or a PDF newsletter, used when there is no .docx (needs pypdf)
  *.png/*.jpg  Charts sent with the email

For every folder with its attachments present, this writes
content/posts/<slug>.json and copies images to assets/blog/<slug>/, then
rebuilds the blog pages. Folders already imported are skipped unless
--force is given. Standard library only, except that PDF newsletters need
the pypdf package (installed system-wide here).

    python3 scripts/import_commentary.py [--force]
"""
import html
import json
import os
import re
import shutil
import sys
import struct
import zipfile
import zlib
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

# ---------- PDF -> HTML ----------

class PdfConverter:
    """Converts a text-based PDF newsletter: headings (bold lines), paragraphs
    (by line spacing), bold lead-in labels, check-mark bullet lists and the
    charts/tables on each page. The cover page, the running header/footer and
    images repeated on several pages (logos) are left out. Each page's images
    follow that page's text."""

    def __init__(self, path, image_dir, image_url):
        sys.modules.setdefault("cryptography", None)  # the system package is broken; pypdf then uses its own crypto
        import pypdf
        self.reader = pypdf.PdfReader(path)
        self.image_dir = image_dir
        self.image_url = image_url
        self.images = []

    # --- text ---
    def _lines(self, page):
        height = float(page.mediabox.height)
        width = float(page.mediabox.width)
        chunks = []

        def text_width(text, font, size):
            """Width of text in points, from the font's /Widths table (else ~0.5em a character)."""
            font = font or {}
            widths, first = font.get("/Widths"), int(font.get("/FirstChar", 0) or 0)
            if hasattr(widths, "get_object"):
                widths = widths.get_object()
            total = 0.0
            for ch in text:
                i = ord(ch) - first
                total += float(widths[i]) if widths is not None and 0 <= i < len(widths) else 500.0
            return total * size / 1000.0

        def visit(text, cm, tm, font, size):
            if not text.strip() or text.count("\n") > 1:
                return
            y = tm[5] * cm[3] + cm[5]
            x = tm[4] * cm[0] + cm[4]
            if not (45 < y < height - 50) or not (0 <= x <= width):
                return  # page-number footer, or text drawn off the page
            name = str((font or {}).get("/BaseFont", ""))
            eff = abs(size * tm[3]) or size
            clean = text.replace("\n", "")
            chunks.append((round(y, 1), x, "Bold" in name, eff, clean, x + text_width(clean, font, eff)))

        page.extract_text(visitor_text=visit)
        lines = []
        used = set()
        for y in sorted({c[0] for c in chunks}, reverse=True):
            parts = sorted((c for c in chunks if abs(c[0] - y) < 1.5 and id(c) not in used), key=lambda c: c[1])
            if not parts:
                continue
            used.update(id(c) for c in parts)
            text = self._join(parts)
            if text:
                lines.append({"y": y, "parts": parts, "text": text, "size": max(c[3] for c in parts),
                              "bold": all(c[2] for c in parts if c[4].strip())})
        return lines

    @staticmethod
    def _join(parts):
        """Join a line's text pieces. Words are sometimes placed with a gap instead of a
        space character (justified text), so a gap of about a third of a space or more
        becomes a space."""
        if not parts:
            return ""
        pieces = [parts[0][4]]
        for prev, cur in zip(parts, parts[1:]):
            if cur[1] - prev[5] > 0.1 * cur[3] and not prev[4].endswith(" ") and not cur[4].startswith(" "):
                pieces.append(" ")
            pieces.append(cur[4])
        return re.sub(r"\s+", " ", "".join(pieces)).strip()

    def _page_blocks(self, lines):
        blocks, para, items, heading = [], [], [], None
        prev = None

        def flush():
            nonlocal para, items, heading
            if heading:
                blocks.append(heading)
                heading = None
            if para:
                # A word broken at the end of a line ("stronger-than-" / "expected") is joined back up.
                blocks.append("<p>%s</p>" % re.sub(r"(?<=[A-Za-z]-) (?=[a-z])", "", " ".join(para)))
                para = []
            if items:
                blocks.append("<ul>%s</ul>" % "".join("<li>%s</li>" % i for i in items))
                items = []

        for line in lines:
            text = html.escape(line["text"])
            gap = (prev["y"] - line["y"]) if prev else 999
            new_block = gap > line["size"] * 1.6
            if items and not new_block and not text.startswith("✓"):
                items[-1] += " " + text  # bullet text continues on the next line
            elif line["bold"]:
                tag = "h2" if line["size"] >= 15 else "h3"
                if heading and heading.startswith("<" + tag) and not new_block:
                    heading = heading[:-len("</%s>" % tag)] + " " + text + "</%s>" % tag  # heading over two lines
                else:
                    flush()
                    heading = "<%s>%s</%s>" % (tag, text, tag)
            elif text.startswith("✓"):
                if heading or para:
                    flush()
                items.append(text.lstrip("✓ ").strip())
            else:
                parts = line["parts"]
                n_lead = next((i for i, c in enumerate(parts) if not c[2] and c[4].strip()), len(parts))
                if 0 < n_lead < len(parts):
                    # "EUR/USD The euro edged higher...": bold label starting a paragraph.
                    # A closing bracket set in the regular font still belongs to the label.
                    while n_lead < len(parts) and parts[n_lead][4].strip() in (")", "]"):
                        n_lead += 1
                    label = html.escape(self._join(parts[:n_lead]))
                    rest = html.escape(self._join(parts[n_lead:]))
                    flush()
                    para = ["<strong>%s</strong> %s" % (label, rest)]
                else:
                    if new_block or heading or items:
                        flush()
                    para.append(text)
            prev = line
        flush()
        return blocks

    # --- images ---
    def _page_images(self, page):
        found = []
        xobjects = page["/Resources"].get("/XObject") or {}
        for ref in xobjects.values():
            obj = ref.get_object()
            if obj.get("/Subtype") == "/Image":
                found.append(obj)
        return found

    @staticmethod
    def _key(obj):
        return (obj.get("/Width"), obj.get("/Height"), len(obj.get_data()))

    def _save(self, obj, name):
        filters = obj.get("/Filter")
        filters = [str(f) for f in (filters if isinstance(filters, list) else [filters])]
        data = obj.get_data()
        width, height = int(obj["/Width"]), int(obj["/Height"])
        if "/DCTDecode" in filters:
            fname, payload = name + ".jpg", data
        else:
            colorspace = obj.get("/ColorSpace")
            space = colorspace.get_object() if hasattr(colorspace, "get_object") else colorspace
            channels = {"/DeviceRGB": 3, "/DeviceGray": 1}.get(str(space))
            if channels is None and isinstance(space, list) and str(space[0]) == "/ICCBased":
                channels = int(space[1].get_object().get("/N", 3))
            if channels not in (1, 3) or int(obj.get("/BitsPerComponent", 8)) != 8 or len(data) < width * height * channels:
                return None
            stride = width * channels
            if min(data[::97]) > 245:  # a blank (all-white) panel
                return None
            rows = b"".join(b"\x00" + data[r * stride:(r + 1) * stride] for r in range(height))

            def chunk(tag, body):
                return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
            payload = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2 if channels == 3 else 0, 0, 0, 0))
                       + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))
            fname = name + ".png"
        os.makedirs(self.image_dir, exist_ok=True)
        with open(os.path.join(self.image_dir, fname), "wb") as fh:
            fh.write(payload)
        self.images.append(fname)
        return fname

    def convert(self):
        pages = self.reader.pages
        per_page = [self._page_images(p) for p in pages]
        seen = {}
        for imgs in per_page:
            for k in {self._key(o) for o in imgs}:
                seen[k] = seen.get(k, 0) + 1
        page_lines = [self._lines(p) for p in pages]
        counts = {}
        for lines in page_lines:
            for k in {re.sub(r"\W+", "", l["text"]).lower() for l in lines}:
                counts[k] = counts.get(k, 0) + 1
        blocks, last_text = [], None
        for n, page in enumerate(pages):
            lines = [l for l in page_lines[n] if counts[re.sub(r"\W+", "", l["text"]).lower()] < 3]  # running header
            if n == 0 and len(pages) > 2 and sum(len(l["text"]) for l in lines) < 300:
                continue  # cover page
            page_blocks = self._page_blocks(lines)
            # A paragraph that runs on from the previous page starts with a lower-case letter.
            if page_blocks and last_text is not None and re.match(r"<p>[a-z]", page_blocks[0]):
                blocks[last_text] = blocks[last_text][:-len("</p>")] + " " + page_blocks.pop(0)[len("<p>"):]
            blocks += page_blocks
            texts = [i for i, b in enumerate(blocks) if b.startswith("<p>")]
            last_text = texts[-1] if texts and blocks[-1].startswith("<p>") else None
            for i, obj in enumerate(per_page[n]):
                if seen[self._key(obj)] > 1 or int(obj.get("/Width", 0)) < 300:
                    continue  # logo repeated on every page, or a small icon
                fname = self._save(obj, "page%d-%d" % (n + 1, i + 1))
                if fname:
                    blocks.append('<figure><img src="%s%s" alt="" loading="lazy"></figure>' % (self.image_url, fname))
        # The publisher's sign-off ("FxPro Market Research & Education / Next edition: ... / fxpro.com").
        for i, b in enumerate(blocks):
            if re.match(r"<(h\d|p)>Next edition\b", b):
                drop = {i}
                if i > 0 and blocks[i - 1].startswith("<h") and len(strip_tags(blocks[i - 1])) < 60:
                    drop.add(i - 1)
                if i + 1 < len(blocks) and re.match(r"<p>[\w.-]+\.(com|net|org|co\.uk)</p>$", blocks[i + 1]):
                    drop.add(i + 1)
                blocks = [b for j, b in enumerate(blocks) if j not in drop]
                break
        return blocks


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
    pdf = None if docx else next((f for f in files if f.lower().endswith(".pdf")), None)
    attached_images = [f for f in files if f.lower().endswith(IMAGE_EXTS)]
    if meta.get("includeImages") is not None:
        attached_images = [f for f in meta["includeImages"] if f in attached_images]
    if not docx and not pdf and not attached_images:
        expected = ", ".join(meta.get("expectedAttachments", [])) or "a .docx or images"
        return "wait", "waiting for attachments (" + expected + ")"

    image_dir = os.path.join(IMAGES, slug)
    if os.path.isdir(image_dir):
        shutil.rmtree(image_dir)
    image_url = "../assets/blog/%s/" % slug

    blocks, doc_images = [], []
    if docx or pdf:
        conv = (DocxConverter if docx else PdfConverter)(os.path.join(folder, docx or pdf), image_dir, image_url)
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
        for i, name in enumerate(doc_images):
            caption_for.setdefault(i, image_captions.get(name))
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
