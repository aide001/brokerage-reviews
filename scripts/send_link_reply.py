#!/usr/bin/env python3
"""Email FxPro the link to a published post, through the Apps Script web app.

Replies in the thread of the FxPro email the post came from, with a short
"it's now live" note and the plain post URL (the Gmail connector would wrap
the link in a google.com redirect). The Apps Script only sends to FxPro's
sender, only links to brokeragereviews.net/blog/, and never sends the same
link twice in a thread. On success it records linkSentAt in the post JSON.

    python3 scripts/send_link_reply.py <slug> [<slug> ...]

Needs FXPRO_SCRIPT_URL and FXPRO_SCRIPT_KEY. Run build_blog.py afterwards.
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "content", "posts")
SITE = "https://brokeragereviews.net/blog/"


def env(name):
    value = os.environ.get(name)
    if not value:
        sys.exit("%s is not set" % name)
    return value


def reply_link(message_id, url):
    data = json.dumps({"key": env("FXPRO_SCRIPT_KEY"), "action": "replyLink",
                       "id": message_id, "url": url}).encode()
    req = urllib.request.Request(env("FXPRO_SCRIPT_URL"), data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.load(res)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    failed = False
    for slug in sys.argv[1:]:
        path = os.path.join(POSTS, slug + ".json")
        with open(path, encoding="utf-8") as f:
            post = json.load(f)
        source = post.get("source") or {}
        message_id = source.get("gmailMessageId") or source.get("gmailThreadId")
        if not message_id:
            print("skip   %s (not from an email)" % slug)
            continue
        result = reply_link(message_id, SITE + slug + ".html")
        if result.get("error"):
            print("error  %s: %s" % (slug, result["error"]))
            failed = True
            continue
        post["linkSentAt"] = result["date"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(post, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("%-6s %s" % ("sent" if result["status"] == "sent" else "had", slug))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
