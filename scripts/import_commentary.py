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
        low = style.lower()
        if low in ("title", "heading1", "heading 1"):
            kind = "h2"
        elif low.startswith("heading"):
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
        attached_images = [f for f in attached_images if f in meta["includeImages"]]
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

    # Attached charts are added when the document doesn't embed its own images.
    figures = []
    if not doc_images:
        os.makedirs(image_dir, exist_ok=True)
        for name in attached_images:
            dest = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
            shutil.copyfile(os.path.join(folder, name), os.path.join(image_dir, dest))
            figures.append(dest)
            blocks.append('<figure><img src="%s%s" alt="" loading="lazy"></figure>' % (image_url, dest))

    paragraphs = [strip_tags(b) for b in blocks if b.startswith("<p>")]
    summary = meta.get("summary") or (paragraphs[0] if paragraphs else "")
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
