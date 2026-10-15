# Stima

The public site of [Stima Prova](https://mystima.io): the post-AI skill assessment, for hiring teams and for higher education.

## Contents

- `index.html`, `hiring-teams.html`, `higher-ed.html`: the Prova pages. Copy and design come from Marianna's repo [milkis-reckless-18/stima-prova-site](https://github.com/milkis-reckless-18/stima-prova-site); do not edit them here, re-import instead (below).
- `prova.css`: Tailwind compiled for those pages; `prova.js`: the "Talk to us" form and the plan buttons that start a message; `img/prova/`: their images.
- `paper.html`: the position paper page with its own email capture; `stima-prova-assessment-after-ai.pdf`: the paper itself.
- `leads.js`: posts forms to `/api/leads`, the Stima app on the same host (leads in `mystima.io/admin`).
- `terms/`: the binding legal documents; `consent.js`, `legal.js`, `legal.css`: cookie banner and legal popup (below).
- `mit/`, `nyc/`: short links for events, redirecting to `/` with UTM tags.
- `robots.txt`, `sitemap.xml`, `llms.txt`, `llms-full.txt` and the icons: for search engines and AI crawlers, written by `tools/site_meta.py`; `<32 hex digits>.txt`: the IndexNow key (both below).

## Prova pages

To bring in a new version of Marianna's pages:

```bash
python3 tools/prova_import.py ~/WORK/stima-prova-site
npx -y tailwindcss@3.4.17 -c tools/prova-tailwind.config.js -i tools/prova.src.css -o prova.css --minify
```

The script pulls the embedded images into `img/prova/`, swaps the Tailwind CDN for `prova.css`, and adds what the site needs on mystima.io: cookie consent, footer links to `/terms/`, the contact form posting to `/api/leads`, plan buttons (hiring plans go to `/signup` and on to Stripe Checkout, campus plans and Enterprise to the form or the calendar), the trial as the app runs it, a Sign in link, links without .html, canonical and Open Graph tags (the home page's `og:title` is the tagline), and a `*` on the required fields of the form. Her data: icon gives way to the icon files, and at the end it runs `tools/site_meta.py` (below). Each change is anchored on her markup; when she changes that markup the script stops and names what it could not find.

Her short `terms.html` and `privacy.html` are not published: the footer points to the documents on `/terms/`, which are the ones people accept in the app.

The contact form: the app saves the message as a lead (source `contact`, with name and message) and emails it to `info@mystima.io` with Marianna in copy (`CONTACT_EMAIL`, `CONTACT_CC` in the app's environment), reply-to the visitor.

## Addresses without .html

Pages are published without the extension: `/hiring-teams`, `/higher-ed`, `/paper`. Links, canonical and `og:url` use those addresses (for the Prova pages the import writes them, from the file name). On the server nginx serves `/hiring-teams` from `hiring-teams.html` and redirects `/hiring-teams.html` to `/hiring-teams` with any query string (`deploy/nginx-paths.conf` in the app repo; the steps are in the app's `docs/runbook.md`).

## Run locally

```bash
python3 tools/serve.py 8000
```

Then open http://localhost:8000. It serves `/hiring-teams` from `hiring-teams.html` as nginx does. The forms and plan buttons need the Stima app behind the same host, as nginx does on the server (`deploy/nginx-paths.conf` in the app repo).

## Deploy

Push to `main`, then `ssh mystima "cd /var/www/stima-site && git pull"`.

The server's web root is this checkout, `.git` included, so nginx has to keep the repository's own files out: `/.git` and the other dotfiles, `/tools/` and this README. The rule goes in the site's `server` block, above `location ~ \.txt$` (in path mode, the app's `deploy/nginx-paths.conf`); change the server as the app's `docs/runbook.md` does for nginx, with a backup, `nginx -t`, a reload and the rollback:

```nginx
# The web root is the site's git checkout: keep the repository's own files out (/.well-known stays open).
location ~ /\.(?!well-known/)|^/(tools/|README\.md$) {
    return 404;
}
```

`python3 tools/check_site_meta.py --base https://mystima.io` reports each of these files that is still served.

## Legal documents (/terms)

`terms/index.html` is generated from the three .docx files (Terms of Use, Privacy Policy, Participant Terms). The home page and the position paper open them in a popup (`legal.js`, `legal.css`) through links with `data-legal="terms-of-use|privacy|participant-terms"`; without JS the links open the full page.

To publish a new version, build the page from the new files and deploy as usual:

```bash
python3 tools/legal_to_html.py --tou ToU.docx --privacy Privacy_Policy.docx --participant Participant_Terms.docx --date "24 September 2026"
```

The text is taken verbatim; the page layout lives in `tools/terms-template.html`.

Placeholders the documents leave open (vendor names and regions in the sub-processor tables, the cookie table) are filled at build time from `ROW_FILLS`, `EXTRA_ROWS` and `COOKIE_ROWS` in `tools/legal_to_html.py`. Change them there when the infrastructure changes.

## Cookie consent

`consent.js` shows the cookie banner and loads Google Analytics (`G-CBQTM9PBQE`) only after the visitor accepts. The choice lives in localStorage (`stima-consent`); any link with `data-cookie-settings` reopens the banner, and declining removes the `_ga` cookies. Every page includes `consent.js` in `<head>` instead of the Google tag snippet.

## Search engines and AI crawlers

What search engines and AI assistants read about Stima Prova, besides the pages themselves. All of it is written by `tools/site_meta.py` from the data at its top; nothing in these files is edited by hand.

- In every page's `<head>`, between `<!-- site-meta ... -->` and `<!-- /site-meta -->`: the icon links and one JSON-LD graph (`<script type="application/ld+json" id="site-meta">`). It describes the company (Organization: Stima Prova, legal name Milkis Strategic Partners LLC, logo, contact email), the site (WebSite), the product (WebApplication, with the plans as offers on `/hiring-teams` and `/higher-ed`, one offer per billing period, in the same shapes as the app's `/pricing`), the Delegator, Operator, Director scale on the home page (DefinedTermSet `https://mystima.io/rubric#scale`: only its name and levels, because `/rubric` in the app describes it under the same `@id`s), the position paper on `/paper` (Report, with the PDF) and the page itself (WebPage, breadcrumbs on sub-pages). The nodes link by `@id` (`https://mystima.io/#organization`, `#website`, `#software`), and the app's `/rubric` and `/pricing` use the same ones; a node written in both places must say the same thing in both, which `tools/check_site_meta.py` checks.
- `robots.txt`: one group for every crawler. Search, assistant and training crawlers are welcome; only the signed-in parts of the app (`/app/`, `/admin`, `/api/`, `/identity/`) are disallowed. Named groups (`User-agent: GPTBot`) would make that crawler ignore the shared rules, so there are none. Sign-in and the pages behind personal links (`/login`, `/signup`, `/i`, `/c`, `/r`, `/v`) stay crawlable because the app marks them noindex, which a crawler only sees on a page it may fetch: the app's `ai-visibility` branch does that, so it goes live before or with this site.
- `sitemap.xml`: the canonical addresses of the site's pages and the app's public `/rubric` and `/pricing`. A page's `lastmod` is the date of the last commit that changed its file (today while the change is not committed).
- `llms.txt` (the [llmstxt.org](https://llmstxt.org/) format): what Stima Prova is, who it is for, how it works, the prices, what it is not, and the pages worth reading. `llms-full.txt`: the main text of the overview, the two audience pages and the paper page as Markdown, made from the HTML, without the few words in `LLMS_FULL_OMIT` that nothing backs (a practice session the app does not have; a reference count and an order of principles the PDF contradicts) until the page itself is corrected.
- `favicon.ico`, `favicon.svg`, `apple-touch-icon.png` and `img/stima-logo-512.png` (the Organization logo): the ring mark as files search engines can fetch. They are made from `favicon.svg` with ImageMagick 7 by `sh tools/make_icons.sh`.
- `<32 hex digits>.txt` and `tools/indexnow.py`: the IndexNow key and the script that tells Bing, Yandex and the other IndexNow engines (not Google) which pages changed.

After changing a page, run:

```bash
python3 tools/site_meta.py          # running it twice changes nothing
python3 tools/check_site_meta.py    # offline: one JSON-LD block per page that parses, @ids, canonical = sitemap, robots, llms.txt links, icon sizes, the fact list
```

To compare with the app's pages before either is deployed, build the app with `APP_URL=https://mystima.io` (or none: production is the fallback; a localhost `APP_URL` gives other `@id`s) and add `--app-html <app>/.next/server/app`: every `@id` its `/rubric` and `/pricing` share with the site must have the same values.

`tools/prova_import.py` and `tools/legal_to_html.py` run `site_meta.py` at their end, so a re-import keeps all of it. The script stops, like the import, when a page no longer says what the JSON-LD claims (a price, a level of the scale), so a new price list cannot leave old prices in the markup: change the offer in `tools/site_meta.py` to match.

Where the facts come from: every statement is one the site, the app's public pages or the position paper already make, and the comment beside each value in `tools/site_meta.py` names the fact by its id in `tools/site_facts.json` (the fact list of 15 October 2026), which gives the page that says it and its exact words. `tools/check_site_meta.py` stops when a comment cites an id the list does not have, or when a page of this repo no longer says what a fact quotes: then correct the value, or the fact if the page changed for the better. Do not add ratings, reviews, customers, founders, founding dates or profiles the site does not show.

What Google's Rich Results Test and Search Console will report, and why it stays that way: the product node is a software application, for which Google asks for `aggregateRating` or `review` before it shows a rich result, so every page reports an invalid "Software app" item; there are no ratings or reviews to mark up, so do not add any. The Enterprise offer reports a missing `price`, because the price list says "From $15K / yr" (`minPrice`), not an exact amount. Neither affects indexing.

To add a profile (LinkedIn, Crunchbase, X...) once it exists, is run by the company and links back to mystima.io: add its URL to `SAME_AS` in `tools/site_meta.py`, run the two commands above and deploy. It goes into the Organization's `sameAs`.

After a deploy that changed pages, tell the IndexNow engines (only changed URLs, only once they are live):

```bash
python3 tools/indexnow.py --dry-run                           # what would be sent
python3 tools/indexnow.py https://mystima.io/hiring-teams     # or no URL for the whole sitemap
```

Then check what the server sends: status and content type; `charset=utf-8` on the `.txt` files (nginx's `location ~ \.txt$` block); the pages and the sitemap declare UTF-8 themselves, so a missing charset there is a note, not a problem; the block on each page; the app's `/rubric` and `/pricing` JSON-LD against the site's; and the noindex on sign-in and the personal-link pages that `robots.txt` leaves crawlable:

```bash
python3 tools/check_site_meta.py --base https://mystima.io
```

Google does not take IndexNow: submit `https://mystima.io/sitemap.xml` in Google Search Console (and Bing Webmaster Tools) once the site is verified there.
