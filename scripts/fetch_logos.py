#!/usr/bin/env python3
"""Download a square logo for every broker in js/data.js into assets/logos/.

For each broker it tries, in order:
  1. The broker's own apple-touch-icon (usually a 180x180 square logo)
  2. Google's favicon service at 256px

Existing files are kept unless --force is passed. Standard library only.

    python3 scripts/fetch_logos.py [--force]
"""
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "js", "data.js")
OUT = os.path.join(ROOT, "assets", "logos")
UA = "Mozilla/5.0 (compatible; BrokerageReviewsLogoFetcher/1.0)"
MIN_BYTES = 400  # anything smaller is almost certainly a placeholder icon


def sources(domain):
    return [
        f"https://{domain}/apple-touch-icon.png",
        f"https://www.{domain}/apple-touch-icon.png",
        f"https://www.google.com/s2/favicons?domain={domain}&sz=256",
    ]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as res:
        return res.read()


def is_png(data):
    return data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= MIN_BYTES


def main():
    force = "--force" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    brokers = re.findall(r'id:\s*"([\w-]+)",\s*domain:\s*"([^"]+)"', open(DATA).read())
    failed = []
    for broker_id, domain in brokers:
        dest = os.path.join(OUT, broker_id + ".png")
        has_svg = os.path.exists(os.path.join(OUT, broker_id + ".svg"))
        if not force and (os.path.exists(dest) or has_svg):
            print(f"skip   {broker_id} (already have a logo)")
            continue
        for url in sources(domain):
            try:
                data = fetch(url)
            except Exception as exc:  # noqa: BLE001 - try the next source
                print(f"  miss {url} ({exc})")
                continue
            if is_png(data):
                with open(dest, "wb") as fh:
                    fh.write(data)
                print(f"saved  {broker_id} <- {url}")
                break
            print(f"  miss {url} (not a usable PNG)")
        else:
            failed.append(broker_id)
    if failed:
        print("\nNo logo found for: " + ", ".join(failed))
        print("Add them by hand as assets/logos/<id>.svg or .png")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
