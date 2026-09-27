# Brokerage Reviews

A forex broker comparison website. It's a static site (plain HTML, CSS and JavaScript) with no build step and no dependencies.

## Features

- **Top picks**: the three highest-rated brokers, highlighted.
- **Comparison table**: filter by regulator, platform, minimum deposit and tier-1 regulation, and sort by rating, EUR/USD cost, deposit, instruments or name.
- **Side-by-side compare**: tick up to 3 brokers, then compare them in a table that highlights the best value in each row.
- **Review pages**: ratings breakdown, key facts, pros and cons, regulators and platforms for each broker. Each review has a shareable link (`#broker/<id>`).
- **Trading cost calculator**: estimates the monthly EUR/USD cost at each broker from your number of trades and lot size.
- **Methodology and FAQ** sections, plus a risk warning and a disclaimer.
- Light and dark mode, with a layout that adapts from phone to desktop.

## Run locally

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

You can also open `index.html` directly in a browser.

## Deploy

Upload the repository contents to any static host, such as GitHub Pages (Settings → Pages → deploy from branch), Netlify, Vercel or Cloudflare Pages.

## Editing broker data

All broker data is in [`js/data.js`](js/data.js). Each broker has a spread, commission, minimum deposit, leverage, regulators, platforms, pros and cons, and editorial ratings from 1 to 5. The site calculates these values:

- **Overall rating**: a weighted average (fees 30%, trust 25%, platforms 20%, education 15%, support 10%). Change the weights in `CATEGORIES` in `js/app.js`.
- **All-in cost**: `spread (pips) × $10 + round-turn commission`, per standard lot of EUR/USD.

> ⚠️ The included figures are approximate sample values. Spreads, deposits, leverage and product availability change often and vary by country and by legal entity. **Check every value against each broker's official website before publishing.**

## Broker logos

Each broker's logo is loaded from `assets/logos/<id>.svg`, or `assets/logos/<id>.png` if there's no SVG. The `<id>` is the broker's `id` in `js/data.js`, for example `pepperstone.png`. Brokers without a logo file show their initials instead. Square logos (app-icon style) look best.

To download logos automatically, run this on a machine with internet access:

```bash
python3 scripts/fetch_logos.py          # add --force to replace existing files
```

For each broker it tries the official site's `apple-touch-icon.png` first, then Google's favicon service. Any logo it can't find can be added by hand. Logos are trademarks of their owners, so check each broker's brand or affiliate guidelines before publishing.

## Project structure

```
index.html          Page markup
css/styles.css      Styles (theme tokens, layout, responsive rules)
js/data.js          Broker dataset
js/app.js           Rendering, filters, compare, modal, calculator
assets/favicon.svg  Logo / favicon
assets/logos/       Broker logos (<id>.svg or <id>.png)
scripts/            fetch_logos.py downloads broker logos
```
