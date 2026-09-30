# Stima

The public site of [Stima Prova](https://mystima.io): the post-AI skill assessment, for hiring teams and for higher education.

## Contents

- `index.html`, `hiring-teams.html`, `higher-ed.html`: the Prova pages. Copy and design come from Marianna's repo [milkis-reckless-18/stima-prova-site](https://github.com/milkis-reckless-18/stima-prova-site); do not edit them here, re-import instead (below).
- `prova.css`: Tailwind compiled for those pages; `prova.js`: the "Talk to us" form and the plan buttons that start a message; `img/prova/`: their images.
- `paper.html`: the position paper page with its own email capture; `stima-prova-assessment-after-ai.pdf`: the paper itself.
- `leads.js`: posts forms to `/api/leads`, the Stima app on the same host (leads in `mystima.io/admin`).
- `terms/`: the binding legal documents; `consent.js`, `legal.js`, `legal.css`: cookie banner and legal popup (below).
- `mit/`, `nyc/`: short links for events, redirecting to `/` with UTM tags.

## Prova pages

To bring in a new version of Marianna's pages:

```bash
python3 tools/prova_import.py ~/WORK/stima-prova-site
npx -y tailwindcss@3.4.17 -c tools/prova-tailwind.config.js -i tools/prova.src.css -o prova.css --minify
```

The script pulls the embedded images into `img/prova/`, swaps the Tailwind CDN for `prova.css`, and adds what the site needs on mystima.io: cookie consent, footer links to `/terms/`, the contact form posting to `/api/leads`, plan buttons (hiring plans go to `/signup` and on to Stripe Checkout, campus plans and Enterprise to the form or the calendar), the trial as the app runs it, a Sign in link, links without .html, canonical and Open Graph tags (the home page's `og:title` is the tagline). Each change is anchored on her markup; when she changes that markup the script stops and names what it could not find.

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
