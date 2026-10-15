#!/usr/bin/env python3
"""Check what tools/site_meta.py wrote: the JSON-LD and icons of every page, robots.txt, sitemap.xml, llms.txt,
llms-full.txt and the icon files.

    python3 tools/check_site_meta.py                            # the files in this checkout, offline
    python3 tools/check_site_meta.py --base https://mystima.io  # also what a host serves: status, type, charset
    python3 tools/check_site_meta.py --base http://localhost:8000   # tools/serve.py; app pages are skipped

Prints one line per problem and exits 1 if there is any.
"""
import json
import pathlib
import re
import struct
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import site_meta as sm  # noqa: E402

ROOT = sm.ROOT
ORIGIN = sm.ORIGIN
SCRIPT_RE = re.compile(r'<script type="application/ld\+json" id="site-meta">\n(.*?)\n</script>', re.S)
# Never disallowed: the app's public pages and the files pages need to render (practices of 15 October 2026).
MUST_STAY_OPEN = ["/", "/rubric", "/pricing", "/ob/issuer", "/ob/verify", "/s/x/y", "/_next/static/x.js", "/brand/stima-bimi.svg",
                  "/icon.svg", "/opengraph-image", "/login", "/signup", "/i/x", "/r/x", "/c/x", "/v/x", "/apple-touch-icon.png",
                  "/favicon.ico", "/llms.txt", "/sitemap.xml"]

problems = []


def problem(msg):
    problems.append(msg)


def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


def png_size(path):
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def ico_sizes(path):
    data = path.read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    if reserved != 0 or kind != 1:
        return None
    sizes = []
    for i in range(count):
        w, h = data[6 + 16 * i], data[7 + 16 * i]
        sizes.append((w or 256, h or 256))
    return sorted(sizes)


def sitemap_entries():
    try:
        tree = ET.parse(ROOT / "sitemap.xml")
    except (ET.ParseError, OSError) as e:
        problem(f"sitemap.xml: {e}")
        return {}
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    if tree.getroot().tag != ns + "urlset":
        problem("sitemap.xml: the root is not a sitemaps.org <urlset>")
    entries = {}
    for url in tree.getroot().findall(ns + "url"):
        loc = (url.findtext(ns + "loc") or "").strip()
        mod = url.findtext(ns + "lastmod")
        if loc in entries:
            problem(f"sitemap.xml: {loc} twice")
        if not loc.startswith(ORIGIN + "/"):
            problem(f"sitemap.xml: {loc} is not on {ORIGIN}")
        if mod is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", mod.strip()):
            problem(f"sitemap.xml: lastmod {mod!r} for {loc} is not a date")
        entries[loc] = mod
    expected = [p.url for p in sm.PAGES] + [ORIGIN + p for p in sm.APP_PAGES]
    if sorted(entries) != sorted(expected):
        problem(f"sitemap.xml: lists {sorted(entries)}, expected {sorted(expected)}")
    return entries


def check_pages(sitemap):
    shared = {}  # @id -> (file, node) of the nodes every page repeats
    defined, refs = set(), []
    for page in sm.PAGES:
        path = ROOT / page.file
        s = path.read_text(encoding="utf-8")
        head = s.split("</head>", 1)[0]
        f = page.file
        if s.count(sm.BLOCK_START) != 1 or s.count(sm.BLOCK_END) != 1 or sm.BLOCK_END not in head:
            problem(f"{f}: needs exactly one site-meta block, inside <head>")
            continue
        scripts = re.findall(r"application/ld\+json", s)
        found = SCRIPT_RE.findall(head)
        if len(found) != 1 or len(scripts) != 1:
            problem(f"{f}: needs exactly one JSON-LD script, the site-meta one (found {len(scripts)})")
            continue
        raw = found[0]
        if re.search(r"[<>&  ]", raw):
            problem(f"{f}: the JSON-LD holds a raw <, >, & or line separator")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            problem(f"{f}: the JSON-LD does not parse: {e}")
            continue
        if sm.ICON_LINKS not in head:
            problem(f"{f}: the icon links are missing")
        if "data:image" in "".join(re.findall(r"<link[^>]*rel=\"[^\"]*icon[^\"]*\"[^>]*>", head)):
            problem(f"{f}: still links a data: icon")
        meta = sm.head_meta(sm.BLOCK_RE.sub("", head), f)
        nodes = data.get("@graph", [])
        by_type = {}
        for n in nodes:
            by_type.setdefault(n.get("@type"), []).append(n)
        pages = [n for n in nodes if n.get("@type") in ("WebPage", "FAQPage")]
        if len(pages) != 1:
            problem(f"{f}: needs one WebPage node, has {len(pages)}")
            continue
        wp = pages[0]
        canonical = meta["canonical"]
        if canonical != page.url:
            problem(f"{f}: canonical {canonical} is not {page.url}")
        if wp.get("@id") != canonical + "#webpage" or wp.get("url") != canonical:
            problem(f"{f}: WebPage @id/url {wp.get('@id')} {wp.get('url')} do not follow the canonical {canonical}")
        if canonical not in sitemap:
            problem(f"{f}: canonical {canonical} is not in sitemap.xml")
        if wp.get("name") != meta["title"] or wp.get("description") != meta["description"]:
            problem(f"{f}: WebPage name/description differ from <title>/meta description")
        if meta["image"] and wp.get("primaryImageOfPage", {}).get("url") != meta["image"]:
            problem(f"{f}: primaryImageOfPage is not the og:image")
        for t in ("Organization", "WebSite", "WebApplication"):
            if len(by_type.get(t, [])) != 1:
                problem(f"{f}: needs one {t} node")
        if page.crumb and not by_type.get("BreadcrumbList"):
            problem(f"{f}: a sub-page needs a BreadcrumbList")
        text = sm.visible_text(s)
        for n in walk(nodes):
            if "@id" in n and len(n) > 1:
                defined.add(n["@id"])
            elif "@id" in n:
                refs.append((f, n["@id"]))
            for bad in ("aggregateRating", "review", "reviews"):
                if bad in n:
                    problem(f"{f}: {bad} in the JSON-LD (no ratings or reviews the site does not show)")
            if n.get("@type") == "Offer" and n.get("description") not in text:
                problem(f"{f}: the offer {n.get('name')!r} is not on the page as written")
            if n.get("@type") == "Question" and n.get("name") not in text:
                problem(f"{f}: the question {n.get('name')!r} is not on the page")
            if n.get("@type") == "FAQPage" and not page.file.startswith("faq"):
                problem(f"{f}: FAQPage on a page without a visible FAQ")
        for n in nodes:
            if n.get("@type") in ("Organization", "WebSite", "WebApplication"):
                node = {k: v for k, v in n.items() if k != "offers"}
                key = n.get("@id")
                if key in shared and shared[key][1] != node:
                    problem(f"{f}: {n.get('@type')} differs from the one on {shared[key][0]}")
                shared.setdefault(key, (f, node))
        org = by_type.get("Organization", [{}])[0]
        if org.get("logo", {}).get("url") != sm.LOGO_URL:
            problem(f"{f}: the Organization logo is not {sm.LOGO_URL}")
        if org.get("sameAs", []) != list(sm.SAME_AS):
            problem(f"{f}: sameAs differs from SAME_AS in tools/site_meta.py")
        # The page as site_meta.py would write it now: catches hand edits and a forgotten run.
        try:
            expected = sm.BLOCK_RE.sub("", s).replace("</head>", sm.block(sm.graph(page, meta, sm.visible_text(sm.BLOCK_RE.sub("", s)))) + "</head>", 1)
            if expected != s:
                problem(f"{f}: not what tools/site_meta.py writes; run it")
        except sm.Missing as e:
            problem(f"{f}: {e}")
    for f, r in refs:
        if r not in defined:
            problem(f"{f}: @id {r} is referenced but defined on no page")


def check_robots(sitemap):
    text = (ROOT / "robots.txt").read_text(encoding="utf-8")
    if text != sm.ROBOTS:
        problem("robots.txt: not what tools/site_meta.py writes; run it")
    agents = re.findall(r"(?im)^user-agent:\s*(.+)$", text)
    if agents != ["*"]:
        problem(f"robots.txt: one group for every crawler (User-agent: *), found {agents}")
    if f"Sitemap: {ORIGIN}/sitemap.xml" not in text.splitlines():
        problem("robots.txt: no Sitemap line")
    rules = re.findall(r"(?im)^disallow:\s*(\S*)\s*$", text)
    for path in sorted(set(MUST_STAY_OPEN) | {u[len(ORIGIN):] for u in sitemap}):
        for rule in rules:
            if rule and path.startswith(rule):
                problem(f"robots.txt: Disallow {rule} blocks {path}")


def check_llms(sitemap):
    text = (ROOT / "llms.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# ") or not any(l.startswith("> ") for l in lines[1:4]):
        problem("llms.txt: must open with an H1 and a blockquote summary")
    if text != sm.LLMS:
        problem("llms.txt: not what tools/site_meta.py writes; run it")
    allowed = set(sitemap) | {sm.PDF_URL, ORIGIN + "/llms-full.txt"}
    links = re.findall(r"\]\(([^)]+)\)", text)
    if not links:
        problem("llms.txt: no links")
    for url in links:
        if url.split("#", 1)[0] not in allowed:
            problem(f"llms.txt: {url} is not a sitemap URL, the PDF or llms-full.txt")
    full = ROOT / "llms-full.txt"
    if not full.exists():
        problem("llms-full.txt: missing")
        return
    full_text = full.read_text(encoding="utf-8")
    for src in re.findall(r"(?m)^Source: (\S+)$", full_text):
        if src not in sitemap:
            problem(f"llms-full.txt: {src} is not in sitemap.xml")
    want = [p.url for p in sm.PAGES if p.full_text]
    if re.findall(r"(?m)^Source: (\S+)$", full_text) != want:
        problem(f"llms-full.txt: the pages are not {want}")


def check_files():
    sizes = ico_sizes(ROOT / "favicon.ico") if (ROOT / "favicon.ico").exists() else None
    if sizes != [(16, 16), (32, 32), (48, 48)]:
        problem(f"favicon.ico: sizes {sizes}, expected 16, 32 and 48")
    for name, want in (("apple-touch-icon.png", (180, 180)), ("img/stima-logo-512.png", (512, 512))):
        got = png_size(ROOT / name) if (ROOT / name).exists() else None
        if got != want:
            problem(f"{name}: {got}, expected a {want[0]}x{want[1]} PNG")
    try:
        if not ET.parse(ROOT / "favicon.svg").getroot().tag.endswith("svg"):
            problem("favicon.svg: not an SVG")
    except (ET.ParseError, OSError) as e:
        problem(f"favicon.svg: {e}")


TEXT_TYPES = ("text/", "application/xml", "application/javascript")
EXPECTED_TYPE = {".html": "text/html", ".txt": "text/plain", ".xml": "xml", ".svg": "image/svg+xml", ".png": "image/png",
                 ".ico": "icon", ".pdf": "application/pdf"}


def check_host(base):
    base = base.rstrip("/")
    production = base == ORIGIN
    targets = [(p.url, ".html", True) for p in sm.PAGES]
    targets += [(ORIGIN + p, ".html", False) for p in sm.APP_PAGES]
    for name in ("robots.txt", "sitemap.xml", "llms.txt", "llms-full.txt", "favicon.ico", "favicon.svg",
                 "apple-touch-icon.png", "img/stima-logo-512.png", "stima-prova-assessment-after-ai.pdf"):
        targets.append((f"{ORIGIN}/{name}", pathlib.PurePosixPath(name).suffix, False))
    for url, ext, site_page in targets:
        if not production and not site_page and url[len(ORIGIN):] in sm.APP_PAGES:
            print(f"  skip {url} (served by the Stima app)")
            continue
        fetch = base + url[len(ORIGIN):]
        try:
            with urllib.request.urlopen(urllib.request.Request(fetch, headers={"User-Agent": "check_site_meta"}), timeout=30) as r:
                status, ctype, final, body = r.status, r.headers.get("Content-Type", ""), r.geturl(), r.read()
        except urllib.error.HTTPError as e:
            status, ctype, final, body = e.code, e.headers.get("Content-Type", ""), fetch, b""
        except (urllib.error.URLError, OSError) as e:
            problem(f"{fetch}: {e}")
            continue
        notes = []
        if status != 200:
            notes.append(f"status {status}")
        if final.rstrip("/") != fetch.rstrip("/"):
            notes.append(f"redirected to {final}")
        want = EXPECTED_TYPE.get(ext, "")
        if status == 200 and want and want not in ctype:
            notes.append(f"content-type {ctype!r}, expected {want}")
        if status == 200 and ctype.startswith(TEXT_TYPES) and "charset=utf-8" not in ctype.lower().replace(" ", ""):
            notes.append(f"no charset=utf-8 in {ctype!r} (Python requests would read it as ISO-8859-1)")
        if site_page and status == 200 and sm.BLOCK_START.encode() not in body:
            notes.append("served without the site-meta block (not deployed yet?)")
        print(f"  {status} {ctype or '-':40} {fetch}" + ("  <- " + "; ".join(notes) if notes else ""))
        if notes:
            problem(f"{fetch}: " + "; ".join(notes))


def main():
    args = sys.argv[1:]
    base = args[args.index("--base") + 1] if "--base" in args else None
    sitemap = sitemap_entries()
    check_pages(sitemap)
    check_robots(sitemap)
    check_llms(sitemap)
    check_files()
    if base:
        print(f"Fetching from {base}:")
        check_host(base)
    for p in problems:
        print("PROBLEM", p)
    print(f"check_site_meta: {len(sm.PAGES)} pages, {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
