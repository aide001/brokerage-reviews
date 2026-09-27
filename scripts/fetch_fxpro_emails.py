#!/usr/bin/env python3
"""Download FxPro commentary emails and their attachments from Gmail.

Each new email is saved to blog-inbox/<slug>/ (email.json + attachments),
ready for import_commentary.py. Emails already in blog-inbox/ or already
published are skipped. Uses the Gmail API directly; standard library only.

One-time setup (see README "Market News"):
  1. Create a Google Cloud OAuth client of type "Desktop app" with the Gmail API enabled.
  2. export GMAIL_CLIENT_ID=... GMAIL_CLIENT_SECRET=...
  3. python3 scripts/fetch_fxpro_emails.py --authorize
     Sign in in the browser; the script prints a refresh token.
  4. export GMAIL_REFRESH_TOKEN=<that token>

Then:
  python3 scripts/fetch_fxpro_emails.py [--limit 5] [--sender e.kalman@fxpro.com]
"""
import argparse
import base64
import glob
import http.server
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, "blog-inbox")
POSTS = os.path.join(ROOT, "content", "posts")
API = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
DEFAULT_SENDER = "e.kalman@fxpro.com"


def env(name):
    value = os.environ.get(name)
    if not value:
        sys.exit("Missing environment variable %s (see the setup notes at the top of this file)." % name)
    return value


def post_form(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


# ---------- OAuth ----------

def authorize():
    client_id, client_secret = env("GMAIL_CLIENT_ID"), env("GMAIL_CLIENT_SECRET")
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result["code"] = (qs.get("code") or [None])[0]
            result["error"] = (qs.get("error") or [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Done. You can close this tab and return to the terminal.")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = "http://127.0.0.1:%d" % server.server_port
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redirect, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent",
    })
    print("Open this link, sign in and allow read-only Gmail access:\n\n" + url + "\n")
    server.handle_request()
    if not result.get("code"):
        sys.exit("Authorization failed: %s" % (result.get("error") or "no code returned"))
    tokens = post_form(TOKEN_URL, {
        "code": result["code"], "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect, "grant_type": "authorization_code",
    })
    print("Refresh token (store it as GMAIL_REFRESH_TOKEN; keep it secret):\n\n" + tokens["refresh_token"])


def access_token():
    return post_form(TOKEN_URL, {
        "client_id": env("GMAIL_CLIENT_ID"), "client_secret": env("GMAIL_CLIENT_SECRET"),
        "refresh_token": env("GMAIL_REFRESH_TOKEN"), "grant_type": "refresh_token",
    })["access_token"]


def api(token, path, **params):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.load(res)


# ---------- Parsing ----------

def b64(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def walk(part):
    yield part
    for p in part.get("parts", []) or []:
        yield from walk(p)


def plain_text(payload):
    for p in walk(payload):
        if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
            return b64(p["body"]["data"]).decode("utf-8", "replace")
    return ""


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:70].rstrip("-")


def describe(subject, body, date):
    """Work out the post title, type and author from the email."""
    nice = "%d %s %d" % (date.day, date.strftime("%B"), date.year)
    topic = re.search(r"Topic:\s*(.+)", body)
    author = re.search(r"Senior Market Analyst\s+([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+)+)", body)
    author = re.sub(r"[.,]+$", "", author.group(1).strip()) if author else "FxPro Analyst Team"
    if topic:
        return topic.group(1).strip(), "Market Comment", author
    if "weekly market performance" in subject.lower():
        return "Weekly Market Performance: " + nice, "Weekly Performance", author
    if "market summary" in subject.lower():
        return "FxPro Market Summary: " + nice, "Market Summary", author
    title = re.sub(r"^FxPro Market Comment\s*-\s*", "", subject, flags=re.I).strip()
    return title or subject, "Market Comment", author


ATTACHMENT_EXTS = (".docx", ".png", ".jpg", ".jpeg", ".gif", ".webp")


def has_attachments(folder):
    return any(f.lower().endswith(ATTACHMENT_EXTS) for f in os.listdir(folder))


def known_messages():
    """Map Gmail message id -> inbox folder still waiting for its files (or
    None when the email is already fully downloaded or published)."""
    known = {}
    for path in glob.glob(os.path.join(POSTS, "*.json")):
        known[(json.load(open(path, encoding="utf-8")).get("source") or {}).get("gmailMessageId")] = None
    for path in glob.glob(os.path.join(INBOX, "*", "email.json")):
        msg_id = json.load(open(path, encoding="utf-8")).get("gmailMessageId")
        if msg_id in known:
            continue
        folder = os.path.dirname(path)
        known[msg_id] = None if has_attachments(folder) else folder
    return known


def save_message(token, msg, folder=None):
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
    subject = headers.get("subject", "(no subject)")
    date = datetime.fromtimestamp(int(msg["internalDate"]) / 1000, tz=timezone.utc)
    iso = date.strftime("%Y-%m-%dT%H:%M:%SZ")
    title, kind, author = describe(subject, plain_text(msg["payload"]), date)
    slug = os.path.basename(folder) if folder else iso[:10] + "-" + slugify(title)
    folder = folder or os.path.join(INBOX, slug)
    os.makedirs(folder, exist_ok=True)

    saved = []
    for part in walk(msg["payload"]):
        name = part.get("filename")
        body = part.get("body", {})
        if not name or not (body.get("attachmentId") or body.get("data")):
            continue
        if body.get("attachmentId"):
            data = api(token, "/messages/%s/attachments/%s" % (msg["id"], body["attachmentId"]))["data"]
        else:
            data = body["data"]
        safe = os.path.basename(name).replace("/", "-")
        with open(os.path.join(folder, safe), "wb") as fh:
            fh.write(b64(data))
        saved.append(safe)

    meta_path = os.path.join(folder, "email.json")
    if os.path.exists(meta_path):  # a slot prepared earlier: keep its details
        meta = json.load(open(meta_path, encoding="utf-8"))
        meta["expectedAttachments"] = saved
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        return slug, saved
    meta = {
        "slug": slug, "title": title, "date": iso, "type": kind,
        "author": author, "authorRole": "Senior Market Analyst",
        "from": headers.get("from"), "subject": subject,
        "gmailMessageId": msg["id"], "gmailThreadId": msg["threadId"], "receivedAt": iso,
        "expectedAttachments": saved, "includeImages": None,
    }
    with open(os.path.join(folder, "email.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return slug, saved


def fetch(limit, sender):
    token = access_token()
    listing = api(token, "/messages", q="from:%s has:attachment" % sender, maxResults=limit)
    known = known_messages()
    new = 0
    for ref in listing.get("messages", []):
        if ref["id"] in known and known[ref["id"]] is None:
            print("skip   %s (already downloaded)" % ref["id"])
            continue
        msg = api(token, "/messages/%s" % ref["id"], format="full")
        slug, files = save_message(token, msg, known.get(ref["id"]))
        print("saved  %s (%d attachment(s))" % (slug, len(files)))
        new += 1
    print("\n%d new email(s). Next: python3 scripts/import_commentary.py" % new)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--authorize", action="store_true", help="get a refresh token (one-time setup)")
    parser.add_argument("--limit", type=int, default=5, help="how many recent emails to check (default 5)")
    parser.add_argument("--sender", default=DEFAULT_SENDER, help="sender address (default %s)" % DEFAULT_SENDER)
    args = parser.parse_args()
    if args.authorize:
        authorize()
    else:
        fetch(args.limit, args.sender)


if __name__ == "__main__":
    main()
