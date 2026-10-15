#!/usr/bin/env python3
"""What search engines and AI crawlers read about Stima Prova on mystima.io, kept in one place.

    python3 tools/site_meta.py

Updates, from the data below:
  - every page in PAGES: just before </head>, the icon links and one JSON-LD graph
    (<script type="application/ld+json" id="site-meta">) between <!-- site-meta --> and <!-- /site-meta -->,
    replacing the block a previous run wrote;
  - robots.txt, sitemap.xml, llms.txt and llms-full.txt at the site root.
Running it again changes nothing. tools/prova_import.py and tools/legal_to_html.py run it at their end, so a
re-import keeps all of it; tools/check_site_meta.py checks the result.

Every statement about Stima Prova here is one the site, the app's public pages (/rubric, /pricing) or the position
paper already make. The comment beside each value names the fact it rests on (ids from the facts list of
15 October 2026) and the page that says it. Nothing else goes in: no ratings, reviews, customers, founders,
founding dates or profiles that the site does not show. Offers repeat the price lists word for word, and the
script stops when a price list no longer says what an offer claims.
"""
import datetime
import html
import html.parser
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORIGIN = "https://mystima.io"

ORG_ID = ORIGIN + "/#organization"
LOGO_ID = ORIGIN + "/#logo"
WEBSITE_ID = ORIGIN + "/#website"
SOFTWARE_ID = ORIGIN + "/#software"
# The scale lives at /rubric (the app); the app's own JSON-LD there uses the same ids.
SCALE_ID = ORIGIN + "/rubric#scale"
LOGO_URL = ORIGIN + "/img/stima-logo-512.png"  # tools/make_icons.sh
PDF_URL = ORIGIN + "/stima-prova-assessment-after-ai.pdf"

# Profiles that the company runs, that call themselves Stima Prova and link back to mystima.io. None is confirmed
# yet (15 October 2026), so the Organization carries no sameAs. Add one URL per line when it is, for example
# "https://www.linkedin.com/company/<page>", then run this script.
SAME_AS = []

ICON_LINKS = ('<link rel="icon" href="/favicon.ico" sizes="32x32">\n'
              '<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
              '<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n')
BLOCK_START = "<!-- site-meta: icons and JSON-LD for search engines and AI crawlers, written by tools/site_meta.py -->"
BLOCK_END = "<!-- /site-meta -->"
BLOCK_RE = re.compile(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END) + r"\n?", re.S)


class Missing(Exception):
    pass


# ---------------------------------------------------------------- pages

class Page:
    def __init__(self, file, path, crumb, **kw):
        self.file, self.path, self.crumb = file, path, crumb  # crumb: breadcrumb name of a sub-page
        self.offers = kw.get("offers")          # offers shown on this page
        self.scale = kw.get("scale", False)     # the page shows the whole scale
        self.report = kw.get("report", False)   # the position paper
        self.full_text = kw.get("full_text", False)  # goes into llms-full.txt
        self.skip_ids = kw.get("skip_ids", ())  # elements left out of llms-full.txt

    @property
    def url(self):
        return ORIGIN + self.path


# ---------------------------------------------------------------- the entity

LEGAL_NAME = "Milkis Strategic Partners LLC"  # legal-entity, legal-footer (terms/index.html, footer of the Prova pages)
EMAIL = "info@mystima.io"  # contact-email (terms/index.html)
# definition-hero (index.html hero), audiences (terms/index.html: employers and instructors)
DEFINITION = ("Stima Prova turns the assignment or take-home that a hiring team or an instructor already uses into an "
              "AI-allowed session, grading the work on the customer's rubric and the AI use on a published scale, "
              "every score cited to the record.")
# legal-entity, name-short-stima ("operates the Stima Prova assessment platform at mystima.io"), category,
# audience-hiring, audience-higher-ed
ORG_DESCRIPTION = ("Milkis Strategic Partners LLC, an Arizona limited liability company trading as Stima, operates "
                   "Stima Prova, the post-AI skill assessment for hiring teams and higher education, at mystima.io.")
# category-platform ("an assessment platform"), audiences, legal-entity. What it is not follows from what it is.
DISAMBIGUATION = ("Stima Prova is skill-assessment software for hiring teams and higher education at mystima.io, "
                  "run by Milkis Strategic Partners LLC, an Arizona limited liability company. "
                  "It is not accounting, tax or invoicing software.")
SITE_DESCRIPTION = ("The post-AI skill assessment. AI-allowed by design, measured on a published scale, "
                    "every score cited to the record.")  # tagline-footer (footer of the Prova pages)
FEATURES = [
    # how-adapt (index.html), how-hiring-1 (hiring-teams.html)
    "Builds the task from the assignment, take-home or role description you already use, plus a planted difficulty a blind copy-paste gets wrong",
    "One focused, timed work session with AI explicitly allowed, recorded with consent",  # how-session (index.html)
    "Quality of the work: a 0–100 score on the deliverable, graded blind on your rubric",  # score-quality, score-blind
    "AI collaboration: Delegator, Operator or Director on a published scale, read against what the task needed",  # score-collaboration
    "Every score cites a moment in the session record",  # score-cited (index.html)
    "A human confirms every outcome; participants can dispute",  # human-confirms (index.html)
    "Workspace-only recording: no video recording, no keystroke logging, no lockdown browser",  # recording-consent-first
    "Grades and decisions export as CSV for your LMS or ATS",  # int-csv (index.html)
    "A verifiable credential (Open Badges 3.0) and a shareable result page for each assignment",  # credential-ob3 (higher-ed.html)
    "Hosted in the EU",  # data-summary (index.html)
]
AUDIENCES = [
    {"@type": "BusinessAudience", "audienceType": "Hiring teams"},  # audience-hiring
    {"@type": "EducationalAudience", "audienceType": "Higher education", "educationalRole": "instructor"},  # audience-higher-ed, campus-instructor
]
SCALE = {
    "name": "Stima collaboration rubric",  # rubric-public-url (/rubric)
    "alternateName": ["The AI-collaboration scale", "Delegator, Operator, Director scale"],  # index.html, scale-levels
    "version": "collab-2.0.0",  # rubric-version (/rubric)
    # scale-levels, scale-higher-not-better (/rubric), scale-reads (index.html)
    "description": ("Three levels of AI collaboration: Delegator, Operator and Director. Higher is not better: what counts "
                    "is whether the way of working fit what the task called for. The scale reads how much thinking was "
                    "handed to the model (prompts, edits, verification, model switching, time); the grade is calibration, "
                    "the observed level against what the task demanded."),
    "levels": [
        # scale-delegator-site, scale-operator-site, scale-director-site (index.html, the level cards)
        ("delegator", "Delegator", "Level 1, hands work to AI. Restates the brief, accepts the first answer. Right for verifiable, low-stakes work."),
        ("operator", "Operator", "Level 2, works with AI. Iterates, corrects, edits substantively. The right default for mixed, everyday work."),
        ("director", "Director", "Level 3, leads the work. Sets the approach first, verifies the parts most likely wrong, owns the outcome."),
    ],
}
REPORT = {
    "name": "Assessment After AI",  # paper-title (paper.html)
    "alternateName": "Stima Prova Position Paper No. 01",  # paper-title
    # paper-summary (paper.html)
    "description": ("Why banning AI from assessment tests a world that no longer exists, what to measure instead, and how "
                    "a credential survives when any answer can be generated."),
    "datePublished": "2026",  # paper-edition ("2026 · PRE-LAUNCH EDITION"); no day or month is published
    "audience": "Academic leaders, assessment designers, credentialing bodies and employers",  # audience-paper (the PDF)
}


# ---------------------------------------------------------------- offers, exactly as the price lists show them

def quantity(unit_text, unit_code=None, value=1):
    q = {"@type": "QuantitativeValue", "value": value}
    if unit_code:
        q["unitCode"] = unit_code  # UN/CEFACT: MON month, ANN year, DAY day
    q["unitText"] = unit_text
    return q


def unit_price(name, price=None, per="completed assessment", code=None, billed=None, minimum=None, subscription=False):
    """price per one `per`; billed: ISO 8601 duration the price is billed for (billingDuration); minimum: a "from" price."""
    spec = {"@type": "UnitPriceSpecification", "name": name}
    if price is not None:
        spec["price"] = price
    if minimum is not None:
        spec["minPrice"] = minimum
    spec["priceCurrency"] = "USD"  # the price lists show "$"; the app bills in US dollars (PER_COMPLETION_USD in its src/billing/plans.ts)
    if subscription:
        spec["priceComponentType"] = "https://schema.org/Subscription"
    spec["referenceQuantity"] = quantity(per, code)
    if billed:
        spec["billingDuration"] = billed
    return spec


def monthly(price):
    return unit_price("Monthly platform fee", price, "month", "MON", "P1M", subscription=True)


def yearly(price, name="Annual platform fee"):
    return unit_price(name, price, "year", "ANN", "P1Y", subscription=True)


class Offer:
    def __init__(self, name, shown, description, price=None, specs=(), **extra):
        self.name, self.shown, self.description, self.price, self.specs, self.extra = name, shown, description, price, list(specs), extra

    def node(self, page):
        o = {"@type": "Offer", "name": self.name, "description": self.description, "url": page.url + "#pricing"}
        if self.price is not None:
            o["price"] = self.price
            o["priceCurrency"] = "USD"
        if self.specs:
            o["priceSpecification"] = self.specs if len(self.specs) > 1 else self.specs[0]
        o.update(self.extra)
        o["offeredBy"] = {"@id": ORG_ID}
        return o


# hiring-teams.html, "Start here" (price-payg, price-team, price-comply, price-enterprise, trial-hiring)
HIRING_OFFERS = [
    Offer("Free trial", ["Free trial", "$0"],
          "One role, 10 completions, 14 days. Card on file; cancel before the trial ends and nothing is charged.",
          0, eligibleDuration=quantity("days", "DAY", 14)),
    Offer("Pay as you go", ["Pay as you go", "$29 each"],
          "Per completed assessment. No minimum, no credits, no lock-in.",
          29, [unit_price("Per completed assessment", 29)]),
    Offer("Team", ["Team", "$299 / mo"],
          "10 completions a month included, then $29 each. Reviewer roles, decision trail. Or $2,990 a year.",
          299, [monthly(299), yearly(2990), unit_price("Each completed assessment after the 10 included a month", 29)]),
    Offer("Comply", ["Comply", "$690 / mo"],
          "25 completions included. DPA on request, org structure, extended data storage. Or $6,900 a year.",
          690, [monthly(690), yearly(6900)]),
    Offer("Enterprise", ["Enterprise", "From $15K / yr"],
          "Annual contract plus committed volume. White label, SSO and integrations as add-ons.",
          None, [unit_price("Annual contract", None, "year", "ANN", "P1Y", minimum=15000)]),
]
# higher-ed.html, "For your campus" (campus-instructor, campus-department, campus-college, campus-institution,
# campus-terms: "Annual billing, paid upfront.")
CAMPUS_OFFERS = [
    Offer("Instructor", ["Instructor", "Free"],
          "One course, up to 250 student sessions per term. No card, no IT ticket.", 0),
    Offer("Department", ["Department", "$12K / yr"],
          "Up to 1,500 enrollments a year. Works out to $8 per student per course.", 12000, [yearly(12000, "Annual licence")]),
    Offer("College", ["College", "$35K / yr"],
          "Up to 5,000 enrollments a year. Works out to $7 per student per course.", 35000, [yearly(35000, "Annual licence")]),
    Offer("Institution", ["Institution", "$90K / yr"],
          "Up to 15,000 enrollments a year. Works out to $6 per student per course.", 90000, [yearly(90000, "Annual licence")]),
]
CAMPUS_FINE_PRINT = "Annual billing, paid upfront."  # what makes billingDuration one year on the campus plans

PAGES = [
    Page("index.html", "/", None, scale=True, full_text=True, skip_ids=("taskPanel",)),
    Page("hiring-teams.html", "/hiring-teams", "For Hiring Teams", offers=HIRING_OFFERS, full_text=True),
    Page("higher-ed.html", "/higher-ed", "For Higher Education", offers=CAMPUS_OFFERS, full_text=True),
    Page("paper.html", "/paper", "Assessment After AI", report=True, full_text=True,
         skip_ids=("rail", "paperDone", "paperDl")),
    Page("terms/index.html", "/terms/", "Legal"),
]
# Public pages of the Stima app on the same host (deploy/nginx-paths.conf in the app repo): in the sitemap,
# without lastmod (this repo cannot date them).
APP_PAGES = ["/rubric", "/pricing"]


# ---------------------------------------------------------------- reading pages

def head_meta(s, file):
    def one(pattern, what, required=True):
        m = re.search(pattern, s)
        if not m:
            if required:
                raise Missing(f"{file}: no {what} in <head>")
            return None
        return html.unescape(m.group(1)).strip()
    return {
        "title": one(r"<title>(.*?)</title>", "<title>"),
        "description": one(r'<meta name="description" content="([^"]*)">', "meta description"),
        "canonical": one(r'<link rel="canonical" href="([^"]+)">', "canonical link"),
        "image": one(r'<meta property="og:image" content="([^"]+)">', "og:image", required=False),
    }


class Visible(html.parser.HTMLParser):
    """The text a reader sees: no scripts, styles, comments or tags."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip, self.out = 0, []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg", "template"):
            self.skip += 1
        self.out.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg", "template"):
            self.skip -= 1
        self.out.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def visible_text(s):
    v = Visible()
    v.feed(s)
    text = re.sub(r"\s+", " ", "".join(v.out)).strip()
    return re.sub(r" ([,.;:!?])", r"\1", text)


# ---------------------------------------------------------------- the graph

def ref(i):
    return {"@id": i}


def organization():
    node = {
        "@type": "Organization", "@id": ORG_ID,
        "name": "Stima Prova",  # name-brand; the footer: "Stima Prova by Milkis Strategic Partners LLC" (legal-footer)
        "alternateName": "Stima",  # name-short-stima (terms: "trading as Stima")
        "legalName": LEGAL_NAME,
        "url": ORIGIN + "/",  # website
        "logo": {"@type": "ImageObject", "@id": LOGO_ID, "url": LOGO_URL, "contentUrl": LOGO_URL,
                 "width": 512, "height": 512, "caption": "Stima Prova"},
        "image": ref(LOGO_ID),
        "email": EMAIL,
        "description": ORG_DESCRIPTION,
        "disambiguatingDescription": DISAMBIGUATION,
        "knowsAbout": ["Post-AI skill assessment", "AI-allowed assessment"],  # category, tagline-secondary
    }
    if SAME_AS:
        node["sameAs"] = list(SAME_AS)
    return node


def website():
    return {
        "@type": "WebSite", "@id": WEBSITE_ID, "url": ORIGIN + "/",
        "name": "Stima Prova",  # the <title> and og:site_name of the Prova pages
        "alternateName": ["Stima", "mystima.io"],  # name-short-stima; the footer shows mystima.io
        "description": SITE_DESCRIPTION,
        "publisher": ref(ORG_ID),
        "inLanguage": "en",
    }


def software(page):
    node = {
        "@type": "WebApplication", "@id": SOFTWARE_ID,
        "name": "Stima Prova", "alternateName": "Stima",  # name-brand, name-short-stima
        "url": ORIGIN + "/",
        "description": DEFINITION,
        "disambiguatingDescription": DISAMBIGUATION,
        "applicationCategory": "BusinessApplication",
        "applicationSubCategory": "Post-AI skill assessment",  # category
        "operatingSystem": "Web browser",  # data-he-it-review ("nothing to install on your network"), recording-not ("this page")
        "featureList": FEATURES,
        "audience": AUDIENCES,
        "inLanguage": "en",
        "image": ref(LOGO_ID),
        "publisher": ref(ORG_ID),
        "provider": ref(ORG_ID),
    }
    if page.offers:
        node["offers"] = [o.node(page) for o in page.offers]
    return node


def scale():
    terms = [{"@type": "DefinedTerm", "@id": f"{ORIGIN}/rubric#{key}", "name": name, "description": text,
              "inDefinedTermSet": ref(SCALE_ID)} for key, name, text in SCALE["levels"]]
    return {
        "@type": "DefinedTermSet", "@id": SCALE_ID, "url": ORIGIN + "/rubric",
        "name": SCALE["name"], "alternateName": SCALE["alternateName"], "version": SCALE["version"],
        "description": SCALE["description"], "publisher": ref(ORG_ID), "inLanguage": "en",
        "hasDefinedTerm": terms,
    }


def report(page, webpage_id):
    return {
        "@type": "Report", "@id": page.url + "#report",
        "name": REPORT["name"], "headline": REPORT["name"], "alternateName": REPORT["alternateName"],
        "description": REPORT["description"],
        "url": page.url,
        "author": ref(ORG_ID), "publisher": ref(ORG_ID),
        "datePublished": REPORT["datePublished"],
        "inLanguage": "en",
        "isAccessibleForFree": True,  # paper-format ("Free with your email")
        "audience": {"@type": "Audience", "audienceType": REPORT["audience"]},
        "encoding": {"@type": "MediaObject", "@id": PDF_URL, "contentUrl": PDF_URL, "encodingFormat": "application/pdf",
                     "name": "Assessment After AI (PDF, 9 pages)"},  # paper-pages
        "mainEntityOfPage": ref(webpage_id),
    }


def graph(page, meta, text):
    if meta["canonical"] != page.url:
        raise Missing(f"{page.file}: the canonical link is {meta['canonical']}, not {page.url}")
    webpage_id = page.url + "#webpage"
    webpage = {
        "@type": "WebPage", "@id": webpage_id, "url": page.url,
        "name": meta["title"], "description": meta["description"],
        "isPartOf": ref(WEBSITE_ID), "about": ref(SOFTWARE_ID), "inLanguage": "en",
    }
    nodes = [webpage]
    if meta["image"]:
        webpage["primaryImageOfPage"] = {"@type": "ImageObject", "@id": page.url + "#primaryimage",
                                         "url": meta["image"], "contentUrl": meta["image"]}
    if page.crumb:
        webpage["breadcrumb"] = ref(page.url + "#breadcrumb")
        nodes.append({"@type": "BreadcrumbList", "@id": page.url + "#breadcrumb", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Stima Prova", "item": ORIGIN + "/"},
            {"@type": "ListItem", "position": 2, "name": page.crumb, "item": page.url},
        ]})
    nodes += [organization(), website(), software(page)]
    if page.scale:
        for _, name, desc in SCALE["levels"]:
            for part in desc.split(". ", 1)[1:]:
                if part.rstrip(".") not in text:
                    raise Missing(f"{page.file}: the {name} card no longer says {part!r}")
        webpage["mentions"] = ref(SCALE_ID)
        nodes.append(scale())
    if page.report:
        webpage["mainEntity"] = ref(page.url + "#report")
        nodes.append(report(page, webpage_id))
    if page.offers:
        for o in page.offers:
            for bit in o.shown + [o.description]:
                if bit not in text:
                    raise Missing(f"{page.file}: the price list no longer shows {bit!r} ({o.name})")
        if page.offers is CAMPUS_OFFERS and CAMPUS_FINE_PRINT not in text:
            raise Missing(f"{page.file}: the price list no longer says {CAMPUS_FINE_PRINT!r}")
    return {"@context": "https://schema.org", "@graph": nodes}


def script_json(data):
    """JSON for a <script> element: no "<", ">" or "&" in it, so no string can close the element; still valid JSON."""
    def dump(x):
        return json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    text = '{"@context":' + dump(data["@context"]) + ',"@graph":[\n' + ",\n".join(dump(n) for n in data["@graph"]) + "\n]}"
    for ch, esc in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), (" ", "\\u2028"), (" ", "\\u2029")):
        text = text.replace(ch, esc)
    return text


def block(data):
    return (BLOCK_START + "\n" + ICON_LINKS + '<script type="application/ld+json" id="site-meta">\n'
            + script_json(data) + "\n</script>\n" + BLOCK_END + "\n")


def update_page(page):
    path = ROOT / page.file
    s = path.read_text(encoding="utf-8")
    bare = BLOCK_RE.sub("", s)
    head = bare.split("</head>", 1)[0]
    if bare.count("</head>") != 1:
        raise Missing(f"{page.file}: needs exactly one </head>")
    if "application/ld+json" in head:
        raise Missing(f"{page.file}: JSON-LD outside the site-meta block (move it into tools/site_meta.py)")
    if re.search(r'<link rel="(?:shortcut )?icon"|<link rel="apple-touch-icon"', head):
        raise Missing(f"{page.file}: an icon link outside the site-meta block (tools/prova_import.py drops her data: icon)")
    text = visible_text(bare)
    new = bare.replace("</head>", block(graph(page, head_meta(head, page.file), text)) + "</head>", 1)
    if new != s:
        path.write_text(new, encoding="utf-8")
    return new


# ---------------------------------------------------------------- robots.txt, sitemap.xml

ROBOTS = f"""# mystima.io: the Stima Prova site, with the Stima app on the same host.
# Search engines, AI search and assistant crawlers, and AI training crawlers are all welcome on every public page.
# One group on purpose: a crawler named in a group of its own would ignore every rule below.
# Disallowed: the signed-in parts of the app and its API, which have nothing public. The app's public pages
# (/pricing, /rubric, /ob, shared results under /s) and its files (/_next, /brand, /icon.svg) stay open; the
# pages behind personal links send noindex themselves rather than being blocked here.
User-agent: *
Disallow: /app/
Disallow: /admin
Disallow: /api/
Disallow: /identity/

Sitemap: {ORIGIN}/sitemap.xml
"""


def git(*args):
    try:
        r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def lastmod(file):
    """The day the page last changed: today while the change is not committed yet, else the date of the last commit
    that touched the file (so the same tree gives the same sitemap); None outside git."""
    status = git("status", "--porcelain", "--", file)
    if status is None:
        return None
    if status:
        return datetime.date.today().isoformat()
    return git("log", "-1", "--format=%cs", "--", file) or None


def sitemap():
    rows = []
    for p in PAGES:
        day = lastmod(p.file)
        rows.append(f"  <url>\n    <loc>{p.url}</loc>\n" + (f"    <lastmod>{day}</lastmod>\n" if day else "") + "  </url>\n")
    for path in APP_PAGES:
        rows.append(f"  <url>\n    <loc>{ORIGIN}{path}</loc>\n  </url>\n")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(rows) + "</urlset>\n")


# ---------------------------------------------------------------- llms.txt

LLMS = f"""# Stima Prova

> Stima Prova is the post-AI skill assessment: it turns the assignment or take-home that a hiring team or an instructor already uses into an AI-allowed work session, grades the work on the customer's rubric and the AI use on a published scale (Delegator, Operator, Director), and cites every score to the session record.

Stima Prova is built for hiring teams (AI-allowed take-homes, with evidence) and for higher education (AI-allowed coursework, measured). It is run by Milkis Strategic Partners LLC, an Arizona limited liability company trading as Stima, at {ORIGIN}.

How it works, in four steps:

1. Adapt: bring one assignment or role question. It is reshaped with you: same goals, same rubric, plus a planted difficulty a blind copy-paste gets wrong.
2. Session: the person works one focused, timed session with AI explicitly allowed, recorded with consent. No video recording, no keystroke logging, no lockdown browser.
3. Two scores: the work on your rubric (0–100, graded blind) and the process on the published Delegator, Operator, Director scale, read against what the task needed. Higher is not better. Every score cites a moment in the session record.
4. Confirm: a human confirms every outcome before it counts. Grades and decisions export as CSV for your LMS or ATS.

Pricing for hiring teams: a 14-day free trial (one role, 10 completions), then $29 per completed assessment (pay as you go), Team at $299 a month with 10 completions a month included, Comply at $690 a month with 25 completions included, or Enterprise from $15K a year. Candidates are always free.
Pricing for higher education: free for instructors (one course, up to 250 student sessions per term); campus plans are priced per student, from Department at $12K a year (up to 1,500 enrollments) to Institution at $90K a year (up to 15,000).

Stima Prova is skill-assessment software. It is not accounting, tax or invoicing software. It is not a proctoring tool or an AI detector either: AI is allowed by design, and the assessment measures how well it was used.

## Pages

- [Stima Prova, the post-AI skill assessment]({ORIGIN}/): overview, how it works, the AI-collaboration scale, trust and privacy
- [Stima Prova for Hiring Teams]({ORIGIN}/hiring-teams): AI-allowed take-homes built from your role description, an explained report per candidate, a decision trail HR can defend
- [Stima Prova for Higher Education]({ORIGIN}/higher-ed): AI-allowed coursework on your rubric, grades ready for your LMS, a verifiable credential (Open Badges 3.0) for each assignment

## The scale

- [Stima collaboration rubric]({ORIGIN}/rubric): the published Delegator, Operator, Director scale (version collab-2.0.0), how a level is judged from the session record and how its fit to the task is scored

## Pricing

- [Hiring plans]({ORIGIN}/hiring-teams#pricing): free trial, pay as you go, Team, Comply and Enterprise
- [Campus plans]({ORIGIN}/higher-ed#pricing): Instructor (free), Department, College and Institution
- [Pricing for hiring teams]({ORIGIN}/pricing): the hiring plans side by side, and what counts as a completed assessment

## Research

- [Assessment After AI]({ORIGIN}/paper): Stima's position paper No. 01: why banning AI from assessment tests a world that no longer exists, what to measure instead, and how a credential survives when any answer can be generated
- [Assessment After AI (PDF, 9 pages)]({PDF_URL}): the paper itself

## Legal

- [Terms of Use, Privacy Policy and Participant Terms]({ORIGIN}/terms/): the documents customers and participants accept, with the sub-processors and how long data is kept

## Optional

- [Full text of the main pages]({ORIGIN}/llms-full.txt): the overview, hiring teams, higher education and position paper pages as Markdown
"""
# Sources of llms.txt, top to bottom: category, definition-hero, scale-levels, score-cited; audience-hiring,
# audience-higher-ed, legal-entity; how-adapt, how-session, recording-consent-first, how-two-scores, score-quality,
# score-collaboration, scale-higher-not-better-home, how-confirm, int-csv; trial-hiring, price-payg, price-team,
# price-comply, price-enterprise, candidates-free; campus-instructor, campus-per-student, campus-department,
# campus-institution; category-platform, no-proctoring, tagline-principles ("Evidence over detection"),
# ai-allowed-by-design; how-hiring-1, how-hiring-4, how-he-3, how-he-4, credential-ob3; rubric-public-url,
# rubric-blind-level, score-composite; session-completed-definition; paper-title, paper-summary, paper-pages;
# legal-three-docs, data-host, data-retention.


# ---------------------------------------------------------------- llms-full.txt

class Markdown(html.parser.HTMLParser):
    """The main content of a page as Markdown: headings, paragraphs and list items. Left out: <head>, header and nav,
    footer, forms, scripts, images, aria-hidden parts, the marquee strip (the same words twice) and links styled as
    buttons. Price rows become one line each, the short labels in a row of chips become list items, the tips on the
    picture dots become "title: text", and the example tasks of the scale say which level each one calls for."""
    SKIP_TAGS = {"head", "script", "style", "noscript", "svg", "template", "header", "nav", "footer", "form", "img", "iframe"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
    BLOCK = {"p", "div", "section", "article", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
             "table", "tr", "td", "th", "details", "summary", "dl", "dt", "dd", "figure", "figcaption", "main", "aside", "button"}
    HEADINGS = {"h1": "## ", "h2": "### ", "h3": "#### ", "h4": "##### "}
    BUTTON_LINK = re.compile(r"\bh-\[(?:40|46|48)px\]")
    LEVELS = {"delegator": "Delegator", "operator": "Operator", "director": "Director"}

    def __init__(self, skip_ids=()):
        super().__init__(convert_charrefs=True)
        self.skip_ids = set(skip_ids)
        self.stack = []   # one dict per open element
        self.blocks = []  # (kind, text, group): kind is a heading tag, "li" or None; list items of one container share a group
        self.cur = []
        self.kind = None
        self.row = None   # cells of a price row while inside one
        self.serial = 0   # numbers the elements, so list items know which container they belong to

    def skipping(self):
        return bool(self.stack) and self.stack[-1]["skip"]

    def flush(self, kind=None, group=None):
        text = re.sub(r"\s+", " ", "".join(self.cur)).strip()
        text = re.sub(r" ([,.;:!?%])", r"\1", text)
        self.cur = []
        if text:
            if self.row is not None:
                self.row.append(text)
            else:
                self.blocks.append((kind or self.kind, text, group))
        self.kind = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        parent = self.stack[-1] if self.stack else {}
        self.serial += 1
        el = {"tag": tag, "n": self.serial, "row": "num-row" in classes, "chips": tag == "div" and ("flex-wrap" in classes or "hero-meta" in classes),
              "item": tag == "span" and parent.get("chips", False), "suffix": None}
        el["group"] = parent.get("n", 0) if el["item"] or el["row"] or tag in ("li", "button") else None
        el["skip"] = (self.skipping() or tag in self.SKIP_TAGS or a.get("aria-hidden") == "true" or a.get("id") in self.skip_ids
                      or "marquee-track" in classes or "arrow-link" in classes and tag == "span"
                      or tag == "a" and bool(self.BUTTON_LINK.search(a.get("class") or ""))
                      or self.row is not None and tag == "div" and "md:col-span-2" in classes)
        if tag not in self.VOID:
            self.stack.append(el)
        if el["skip"]:
            return
        if tag == "br" or "block" in classes:
            self.cur.append(" ")
        if tag in self.BLOCK or el["item"]:
            self.flush()
            self.kind = self.HEADINGS.get(tag) and tag or ("li" if tag == "li" or el["item"] else None)
            if el["row"]:
                self.row = []
        if tag == "button" and a.get("data-level") in self.LEVELS and a.get("data-why"):
            # The scale's example tasks: the level and the reason show only after a click.
            self.kind = "li"
            el["suffix"] = f": {self.LEVELS[a['data-level']]}. {a['data-why']}"
        if "t-title" in classes:
            self.kind = "li"
            el["suffix"] = ": "

    def handle_endtag(self, tag):
        if tag in self.VOID or not any(e["tag"] == tag for e in self.stack):
            return
        while True:
            el = self.stack.pop()
            if el["tag"] == tag:
                break
        if el["skip"]:
            return
        if el["suffix"]:
            self.cur.append(el["suffix"])
        if tag in self.BLOCK or el["item"]:
            self.flush("li" if el["item"] else None, el["group"])
            if el["row"] and self.row is not None:
                if self.row:
                    self.blocks.append(("li", " · ".join(self.row), el["group"]))
                self.row = None
        elif el["suffix"] == ": ":
            self.kind = "li"

    def handle_data(self, data):
        if not self.skipping():
            self.cur.append(data)

    def markdown(self):
        self.flush()
        out, last, last_group = [], None, None
        for kind, text, group in self.blocks:
            text = re.sub(r" +:", ":", text).replace(":.", ".")
            line = self.HEADINGS.get(kind, "- " if kind == "li" else "") + text
            if line == last:
                continue
            if out and (kind != "li" or not out[-1].startswith("- ") or group != last_group):
                out.append("")
            out.append(line)
            last, last_group = line, group
        return "\n".join(out)


def full_text(pages_html):
    parts = []
    for page, s in pages_html:
        m = Markdown(page.skip_ids)
        m.feed(s)
        title = head_meta(s.split("</head>", 1)[0], page.file)["title"]
        parts.append(f"# {title}\n\nSource: {page.url}\n\n{m.markdown()}\n")
    return "\n".join(parts)


# ---------------------------------------------------------------- main

def write(name, text):
    path = ROOT / name
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != text:
        path.write_text(text, encoding="utf-8")
        print(f"{name}: written")


def run():
    """Update the pages and the files; returns what could not be found (nothing when all went well). A page that
    fails keeps its previous block, and the files at the root are left alone until every page goes through."""
    failed, done = [], []
    for page in PAGES:
        try:
            done.append((page, update_page(page)))
        except Missing as e:
            failed.append(f"site_meta: {e}")
    if failed:
        return failed
    write("robots.txt", ROBOTS)
    write("llms.txt", LLMS)
    write("llms-full.txt", full_text([(p, s) for p, s in done if p.full_text]))
    write("sitemap.xml", sitemap())
    print(f"site_meta: {len(done)} pages, robots.txt, sitemap.xml, llms.txt and llms-full.txt up to date")
    return []


def main():
    failed = run()
    if failed:
        print("\n".join(failed), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
