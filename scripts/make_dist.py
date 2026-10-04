#!/usr/bin/env python3
"""Copy only the public website into dist/ for hosting (Cloudflare Pages).

The site is pre-built and committed, so this does not regenerate anything; it
just leaves out what must not be public: blog-inbox/ (raw downloaded emails),
content/, scripts/, apps-script/ and the README.

  Build command:          python3 scripts/make_dist.py
  Build output directory: dist
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PUBLIC_DIRS = ["assets", "best", "blog", "brokers", "css", "js"]
PUBLIC_FILES = ["index.html", "robots.txt", "sitemap.xml"]


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for d in PUBLIC_DIRS:
        shutil.copytree(ROOT / d, DIST / d)
    for f in PUBLIC_FILES:
        if (ROOT / f).exists():
            shutil.copy2(ROOT / f, DIST / f)
    count = sum(1 for p in DIST.rglob("*") if p.is_file())
    print("dist/: %d file(s)" % count)


if __name__ == "__main__":
    main()
