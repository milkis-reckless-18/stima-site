#!/usr/bin/env python3
"""Tell IndexNow search engines (Bing, Yandex, Seznam, Naver, Yep, the Internet Archive, Amazon; not Google) which
pages of mystima.io changed, after a deploy.

    python3 tools/indexnow.py --dry-run                     # show what would be sent, send nothing
    python3 tools/indexnow.py                               # every URL in sitemap.xml
    python3 tools/indexnow.py https://mystima.io/hiring-teams https://mystima.io/llms.txt

Send only pages that were added, changed or removed, and only once they are live: an engine fetches the key file
(the <32 hex digits>.txt at the site root, holding nothing but the key) to check the request comes from the site's
owner. Prints the HTTP status: 200 accepted, 202 accepted while the key is checked, 400 bad request, 403 key not
found or not matching, 422 URL not on mystima.io, 429 too many requests.
"""
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOST = "mystima.io"
ENDPOINT = "https://api.indexnow.org/indexnow"


def key():
    found = [p for p in ROOT.glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}", p.stem)]
    if len(found) != 1:
        sys.exit(f"indexnow: expected one <32 hex digits>.txt key file at the site root, found {len(found)}")
    k = found[0].read_text(encoding="utf-8").strip()
    if k != found[0].stem:
        sys.exit(f"indexnow: {found[0].name} must hold only its own name, the key")
    return k


def sitemap_urls():
    return re.findall(r"<loc>([^<]+)</loc>", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    urls = [a for a in args if a != "--dry-run"] or sitemap_urls()
    wrong = [u for u in urls if not u.startswith(f"https://{HOST}/")]
    if wrong:
        sys.exit("indexnow: not on https://mystima.io/: " + ", ".join(wrong))
    k = key()
    body = {"host": HOST, "key": k, "keyLocation": f"https://{HOST}/{k}.txt", "urlList": urls}
    if dry:
        print(f"POST {ENDPOINT}")
        print(json.dumps(body, indent=2))
        return
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, text = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode("utf-8", "replace")
    print(f"indexnow: HTTP {status} for {len(urls)} URLs" + (f": {text.strip()}" if text.strip() else ""))
    if status not in (200, 202):
        sys.exit(1)


if __name__ == "__main__":
    main()
