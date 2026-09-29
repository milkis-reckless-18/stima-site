#!/usr/bin/env python3
"""Bring Marianna's Stima Prova pages (milkis-reckless-18/stima-prova-site) onto mystima.io.

    python3 tools/prova_import.py ~/WORK/stima-prova-site
    npx -y tailwindcss@3.4.17 -c tools/prova-tailwind.config.js -i tools/prova.src.css -o prova.css --minify

Her pages are the source of the copy and the design. On the way in they get:
  - images pulled out of base64 into img/prova/<hash>.<ext> (shared across pages, cached), with
    corrected copies from tools/prova-image-fixes/ where one exists;
  - the compiled prova.css instead of the Tailwind CDN (built by the second command);
  - consent.js (Google Analytics only after consent), the legal popup (legal.js) and
    footer links to the binding documents on /terms/ instead of her short terms/privacy pages;
  - the "Talk to us" form posting to /api/leads (saved in the admin leads dashboard and
    emailed to info@mystima.io) instead of opening the visitor's mail app;
  - plan buttons on the price lists: hiring plans go to /signup and on to Stripe Checkout,
    campus plans and Enterprise to the form or the calendar;
  - the trial described as the app runs it (14 days, 10 completions, card up front);
  - a Sign in link, root-relative home links, canonical and Open Graph tags.

Every edit is anchored on her markup and fails loudly when that markup has changed,
so a new version of her pages is re-imported by running this again and fixing what it names.
"""
import base64
import hashlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "img" / "prova"
# Corrected copies of her images, named by the hash of the image they replace (see tools/prova-image-fixes/README.md).
FIXES_DIR = ROOT / "tools" / "prova-image-fixes"
SITE = "https://mystima.io"

PAGES = {
    # file: (published path, section name sent with the contact form)
    "index.html": ("/", "Overview"),
    "hiring-teams.html": ("/hiring-teams.html", "Hiring teams"),
    "higher-ed.html": ("/higher-ed.html", "Higher education"),
}

EXT = {"png": "png", "jpeg": "jpg", "jpg": "jpg", "webp": "webp"}


class Missing(Exception):
    pass


def sub_once(pattern, repl, s, what, flags=0, count=1):
    new, n = re.subn(pattern, repl, s, count=count, flags=flags)
    if n == 0:
        raise Missing(what)
    return new


def replace_once(old, new, s, what):
    if old not in s:
        raise Missing(what)
    return s.replace(old, new, 1)


def extract_images(s):
    def save(m):
        kind, data = m.group(1), m.group(2)
        raw = base64.b64decode(data)
        name = hashlib.sha256(raw).hexdigest()[:12] + "." + EXT[kind]
        fixed = FIXES_DIR / name
        if fixed.exists():
            # A corrected copy of her image, e.g. a product screenshot without the "Made with Lovable" badge.
            raw = fixed.read_bytes()
            name = hashlib.sha256(raw).hexdigest()[:12] + fixed.suffix
        path = IMG_DIR / name
        if not path.exists():
            path.write_bytes(raw)
        return f'src="/img/prova/{name}"'

    return re.sub(r'src="data:image/(png|jpeg|jpg|webp);base64,([A-Za-z0-9+/=]+)"', save, s)


def lazy_images(s):
    """Everything below the header and hero loads lazily; carousel slides stay eager (they slide in sideways)."""
    head, sep, rest = s.partition("<!-- marquee -->") if "<!-- marquee -->" in s else s.partition('<div class="bg-plum border-t border-white/10 py-4 overflow-hidden relative">')
    if not sep:
        raise Missing("marquee after the hero")
    track = re.search(r'<div id="track">.*?</div>\s*</div>\s*</div>', rest, re.S)
    def lazy(m):
        tag = m.group(0)
        if "loading=" in tag or (track and track.start() <= m.start() < track.end()):
            return tag
        return tag.replace("<img ", '<img loading="lazy" decoding="async" ', 1)
    return head + sep + re.sub(r"<img [^>]*>", lazy, rest)


def head_tags(s, path, section):
    s = sub_once(r'<script src="https://cdn\.tailwindcss\.com"></script>\s*<script>\s*tailwind\.config = .*?</script>',
                 '<link rel="stylesheet" href="/prova.css">\n<link rel="stylesheet" href="/legal.css">', s, "Tailwind CDN and config", re.S)
    s = replace_once("<head>\n", "<head>\n<script src=\"/consent.js\"></script>\n", s, "<head>")
    title = re.search(r"<title>(.*?)</title>", s).group(1)
    desc = re.search(r'<meta name="description" content="([^"]*)">', s)
    if not desc:
        raise Missing("meta description")
    hero = re.search(r'<section[^>]*>.*?<img [^>]*src="(/img/prova/[^"]+)"', s, re.S)
    og = (f'<link rel="canonical" href="{SITE}{path}">\n'
          f'<meta property="og:type" content="website">\n'
          f'<meta property="og:site_name" content="Stima Prova">\n'
          f'<meta property="og:title" content="{title}">\n'
          f'<meta property="og:description" content="{desc.group(1)}">\n'
          f'<meta property="og:url" content="{SITE}{path}">\n'
          + (f'<meta property="og:image" content="{SITE}{hero.group(1)}">\n<meta name="twitter:card" content="summary_large_image">\n' if hero else ""))
    s = s.replace(desc.group(0), desc.group(0) + "\n" + og.rstrip("\n"), 1)
    s = replace_once('<body class="font-sans">', f'<body class="font-sans" data-section="{section}">', s, "<body>")
    return s


def links(s):
    s = re.sub(r'href="index\.html(#[^"]*)?"', lambda m: f'href="/{m.group(1) or ""}"', s)
    s = re.sub(r'href="(higher-ed|hiring-teams)\.html', r'href="/\1.html', s)
    # Footer and mobile menu: the binding documents on /terms/ (her short versions are not published).
    s = sub_once(r'<li><a href="terms\.html" class="([^"]*)">Terms of Use</a></li>\s*<li><a href="privacy\.html" class="[^"]*">Privacy Policy</a></li>',
                 lambda m: (f'<li><a href="/terms/#terms-of-use" data-legal="terms-of-use" class="{m.group(1)}">Terms of Use</a></li>\n'
                            f'        <li><a href="/terms/#privacy" data-legal="privacy" class="{m.group(1)}">Privacy Policy</a></li>\n'
                            f'        <li><a href="/terms/#participant-terms" data-legal="participant-terms" class="{m.group(1)}">Participant Terms</a></li>\n'
                            f'        <li><a href="#" data-cookie-settings class="{m.group(1)}">Cookie settings</a></li>'),
                 s, "footer legal links", re.S)
    s = sub_once(r'<a href="terms\.html" class="block text-plum">Terms of Use</a>\s*<a href="privacy\.html" class="block text-plum">Privacy Policy</a>',
                 '<a href="/terms/#terms-of-use" data-legal="terms-of-use" class="block text-plum">Terms of Use</a>\n'
                 '      <a href="/terms/#privacy" data-legal="privacy" class="block text-plum">Privacy Policy</a>',
                 s, "mobile menu legal links", re.S)
    if re.search(r'href="(terms|privacy)\.html', s):
        raise Missing("another link to terms.html or privacy.html")
    return s


SIGN_IN = ('<a href="/login" class="hidden min-[1100px]:inline-flex items-center whitespace-nowrap text-sm font-semibold text-muted hover:text-plum px-2 h-[42px] transition-colors">Sign in</a>\n      ')


def nav(s, file):
    s = replace_once('<div class="flex items-center gap-3">\n      <a href="https://calendly.com',
                     '<div class="flex items-center gap-3">\n      ' + SIGN_IN + '<a href="https://calendly.com', s, "header actions")
    s = sub_once(r'(<a href="https://demo\.mystima\.io/" target="_blank" rel="noopener" class="block text-plum">Live demo</a>)',
                 r'\1\n      <a href="/login" class="block text-plum">Sign in</a>', s, "mobile menu Resources")
    # Between 1024 and 1100 px the header has no room for Sign in, so Resources carries it too.
    s = sub_once(r'(<a href="#contact" class="drop-item flex flex-col gap-0\.5 px-4 py-3 rounded-sm2"><span class="font-semibold text-plum">Contact</span><span class="text-\[13px\] text-muted">[^<]*</span></a>)',
                 r'\1\n            <a href="/login" class="drop-item flex flex-col gap-0.5 px-4 py-3 rounded-sm2"><span class="font-semibold text-plum">Sign in</span><span class="text-[13px] text-muted">Your campaigns and results</span></a>',
                 s, "Resources menu")
    # At 1024 px her header wrapped "On this page" and the button onto two lines.
    s = replace_once('<nav class="hidden lg:flex items-center gap-1 text-[14px] font-medium"', '<nav class="hidden lg:flex items-center gap-1 whitespace-nowrap text-[14px] font-medium"', s, "primary nav")
    s = replace_once('class="hidden sm:inline-flex items-center gap-2 text-sm font-semibold px-5 h-[42px]', 'class="hidden sm:inline-flex items-center gap-2 whitespace-nowrap text-sm font-semibold px-5 h-[42px]', s, "header button")
    if file == "index.html":
        # Two price lists, one per audience: Pricing opens a choice instead of jumping to the campus list.
        s = replace_once('<a href="/higher-ed.html#pricing" class="px-4 py-2 rounded-sm2 text-muted hover:text-plum transition-colors">Pricing</a>',
                         '<div class="has-drop relative">\n'
                         '        <button class="nav-btn px-4 py-2 rounded-sm2 text-muted hover:text-plum transition-colors inline-flex items-center gap-1.5" aria-haspopup="true">Pricing\n'
                         '          <svg class="w-3.5 h-3.5 opacity-60" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5"/></svg></button>\n'
                         '        <div class="drop absolute left-0 top-full pt-3 w-[300px]">\n'
                         '          <div class="bg-white rounded-md2 shadow-float border border-divider p-2">\n'
                         '            <a href="/hiring-teams.html#pricing" class="drop-item flex flex-col gap-0.5 px-4 py-3 rounded-sm2"><span class="font-semibold text-plum">For Hiring Teams</span><span class="text-[13px] text-muted">Free trial, then from $29 per assessment</span></a>\n'
                         '            <a href="/higher-ed.html#pricing" class="drop-item flex flex-col gap-0.5 px-4 py-3 rounded-sm2"><span class="font-semibold text-plum">For Higher Education</span><span class="text-[13px] text-muted">Free for instructors, campus plans per student</span></a>\n'
                         '          </div>\n'
                         '        </div>\n'
                         '      </div>',
                         s, "index Pricing link")
    return s


BTN = "inline-flex items-center justify-center h-[40px] px-4 rounded-sm2 text-sm font-semibold whitespace-nowrap transition-colors"
PRIMARY = BTN + " bg-coral text-white hover:bg-[#e84a5d]"
GHOST = BTN + " border border-white/25 text-white hover:bg-white/10"
YEAR = 'class="underline decoration-coral decoration-2 underline-offset-4 text-white/80 hover:text-white"'

HIRING_PLANS = [
    # plan name in her list, button, where it goes, extra text after her description
    ("Free trial", "Start free", "/signup", ""),
    ("Pay as you go", "Start", "/signup?plan=payg", ""),
    ("Team", "Choose Team", "/signup?plan=team&amp;period=month",
     f' Or <a href="/signup?plan=team&amp;period=year" {YEAR}>$2,990 a year</a>.'),
    ("Comply", "Choose Comply", "/signup?plan=comply&amp;period=month",
     f' Or <a href="/signup?plan=comply&amp;period=year" {YEAR}>$6,900 a year</a>.'),
    ("Enterprise", "Talk to us", "https://calendly.com/mariannamilkis/30-min", ""),
]

CAMPUS_PLANS = [
    ("Instructor", "Bring an assignment", "I would like to try Stima Prova in one of my courses (Instructor, free)."),
    ("Department", "Talk to us", "We are interested in the Department plan ($12K a year, up to 1,500 enrollments)."),
    ("College", "Talk to us", "We are interested in the College plan ($35K a year, up to 5,000 enrollments)."),
    ("Institution", "Talk to us", "We are interested in the Institution plan ($90K a year, up to 15,000 enrollments)."),
]


def price_row(s, name, button_html, extra=""):
    pat = (r'(<div class="md:col-span-3 font-serif text-2xl">' + re.escape(name) + r'</div><div class="md:col-span-3 [^"]*">[^<]*</div>\s*)'
           r'<div class="md:col-span-6 text-white/60 text-sm">(.*?)</div>')
    return sub_once(pat, lambda m: (m.group(1) + f'<div class="md:col-span-4 text-white/60 text-sm">{m.group(2)}{extra}</div>\n'
                                    f'          <div class="md:col-span-2 md:text-right mt-3 md:mt-0">{button_html}</div>'),
                    s, f"price row {name}", re.S)


def pricing(s, file):
    if file == "hiring-teams.html":
        for i, (name, label, href, extra) in enumerate(HIRING_PLANS):
            cls = GHOST if href.startswith("https://calendly") else PRIMARY
            s = price_row(s, name, f'<a href="{href}" class="{cls}">{label}</a>', extra)
        s = sub_once(r'(Candidates always free, one practice session every 90 days\.)',
                     r'\1 Self-serve plans are paid by card through Stripe and can be cancelled from your billing page.', s, "hiring fine print")
    elif file == "higher-ed.html":
        for name, label, msg in CAMPUS_PLANS:
            cls = PRIMARY if name == "Instructor" else GHOST
            s = price_row(s, name, f'<a href="#contact" data-plan="{msg}" class="{cls}">{label}</a>')
    return s


# The trial as the app runs it (14 days, 1 role, 10 completions, card up front through a Stripe trial);
# the user chose on 29 September 2026 to keep the app's terms and bring the pages in line.
TRIAL_TEXT = {
    "index.html": [("No card to start</span>", "14-day free trial for teams</span>")],
    "hiring-teams.html": [
        ("Free trial, no card needed</span>", "14-day free trial</span>"),
        ("One role, 5 completions, 30 days. No card needed.",
         "One role, 10 completions, 14 days. Card on file; cancel before the trial ends and nothing is charged."),
    ],
}


def trial_terms(s, file):
    for old, new in TRIAL_TEXT.get(file, []):
        s = replace_once(old, new, s, f"trial text {old!r}")
    return s


def contact_form(s):
    s = sub_once(r'\n?// contact form -> mailto compose\ndocument\.getElementById\(\'contactForm\'\)\.addEventListener\(\'submit\', e => \{.*?\n\}\);\n',
                 "\n", s, "mailto form handler", re.S)
    s = replace_once('<input id="cfName" type="text" required placeholder="Your name"',
                     '<input id="cfName" name="name" type="text" required maxlength="120" autocomplete="name" placeholder="Your name"', s, "name field")
    s = replace_once('<input id="cfEmail" type="email" required placeholder="Work email"',
                     '<input id="cfEmail" name="email" type="email" required maxlength="254" autocomplete="email" placeholder="Work email"', s, "email field")
    s = replace_once('<textarea id="cfMsg" rows="3" required',
                     '<textarea id="cfMsg" name="message" rows="3" required maxlength="4000"', s, "message field")
    s = sub_once(r'(<textarea id="cfMsg".*?</textarea>)',
                 r'\1\n          <div aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden"><label>Website <input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>'
                 r'\n          <p id="cfStatus" role="status" class="hidden text-sm mb-4"></p>', s, "form status", re.S)
    return s


def scripts(s):
    return replace_once("</body>", '<script src="/leads.js"></script>\n<script src="/prova.js"></script>\n<script src="/legal.js"></script>\n</body>', s, "</body>")


def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / "stima-prova-site").expanduser()
    rev = subprocess.run(["git", "-C", str(src), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    failed = []
    for file, (path, section) in PAGES.items():
        s = (src / file).read_text()
        try:
            s = extract_images(s)
            s = lazy_images(s)
            s = head_tags(s, path, section)
            s = links(s)
            s = nav(s, file)
            s = trial_terms(s, file)
            s = pricing(s, file)
            s = contact_form(s)
            s = scripts(s)
            s = s.replace("<head>\n", f"<head>\n<!-- Imported from milkis-reckless-18/stima-prova-site@{rev} by tools/prova_import.py; edit there or in the script. -->\n", 1)
        except Missing as e:
            failed.append(f"{file}: could not find {e}")
            continue
        if "base64," in s:
            failed.append(f"{file}: an embedded image is left (not png/jpeg/webp?)")
        (ROOT / file).write_text(s)
        print(f"{file}: {len(s):,} bytes")
    used = set()
    for file in PAGES:
        used |= set(re.findall(r"/img/prova/([0-9a-f]{12}\.\w+)", (ROOT / file).read_text()))
    for p in IMG_DIR.iterdir():
        if p.name not in used:
            p.unlink()
    print(f"img/prova: {len(used)} images, {sum((IMG_DIR / n).stat().st_size for n in used):,} bytes; source {rev}")
    if failed:
        print("\n".join(failed), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
