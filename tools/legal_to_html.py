"""
Builds terms/index.html from the three Stima Prova legal documents (.docx).

    python3 tools/legal_to_html.py \
        --tou  path/to/Stima_Prova_ToU_*.docx \
        --privacy path/to/Stima_Prova_Privacy_Policy_*.docx \
        --participant path/to/Stima_Prova_Participant_Terms_*.docx \
        --date "24 September 2026"

The text is taken verbatim from the documents. Only structure is added:
Heading 1 and Heading 2 become section headings with anchors, list
paragraphs become lists, "(a)" items and "1.2" clauses get their own
styling, bold runs stay bold, tables stay tables. --date fills the
"[date]" placeholders the documents carry for their effective date.
"""
import argparse
import html
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ROOT = Path(__file__).resolve().parent.parent


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "section"


def runs_html(p) -> str:
    out = []
    for r in p.iter(W + "r"):
        text = "".join(t.text or "" for t in r.iter(W + "t"))
        if not text:
            continue
        rpr = r.find(W + "rPr")
        esc = html.escape(text, quote=False)
        if rpr is not None and rpr.find(W + "b") is not None and (rpr.find(W + "b").get(W + "val") not in ("0", "false")):
            esc = f"<strong>{esc}</strong>"
        out.append(esc)
    s = "".join(out)
    return s.replace("</strong><strong>", "")


def style_of(p) -> str:
    ppr = p.find(W + "pPr")
    if ppr is None:
        return ""
    ps = ppr.find(W + "pStyle")
    return ps.get(W + "val") if ps is not None else ""


def is_list(p) -> bool:
    ppr = p.find(W + "pPr")
    return ppr is not None and ppr.find(W + "numPr") is not None


# Facts the documents leave as placeholders, filled from our actual infrastructure.
# Keyed by the first cell of a vendor row; each maps placeholder -> value within that row.
ROW_FILLS = {
    "Anthropic": {"[region]": "United States"},
    "OpenAI": {"[region]": "United States"},
    "[Hosting provider]": {"[Hosting provider]": "Scalaxy B.V."},
    "[Email provider]": {"[Email provider]": "Scaleway SAS", "[region]": "France (EU)"},
    "[Identity provider]": {"[Identity provider]": "Sonavera (when enabled for a campaign)", "[region]": "To be confirmed before first use"},
    "[Analytics provider]": {"[Analytics provider]": "Google LLC (Google Analytics 4)", "[region]": "United States"},
}
# Processors missing from the documents, appended to the tables whose first header matches.
EXTRA_ROWS = {
    ("Sub-processor", "Recipient"): [
        ["Stripe, Inc.", "Payments and billing for customer accounts", "United States"],
        ["Microsoft Corporation (Microsoft 365)", "Email for mystima.io addresses, including privacy and data requests", "United States"],
    ],
}
COOKIE_PLACEHOLDER = "[Cookie table to be inserted: name, purpose, duration, first or third party.]"
COOKIE_ROWS = [
    ["Name", "Purpose", "Duration", "First or third party"],
    ["stima_session", "Keeps a customer user signed in to Stima Prova. Strictly necessary.", "7 days", "First party"],
    ["stima-consent (browser storage)", "Remembers your choice in the cookie banner. Strictly necessary.", "Until you change the choice or clear site data", "First party"],
    ["_ga", "Google Analytics: tells visits from different browsers apart. Set only if you accept analytics.", "2 years", "First party, set by Google Analytics"],
    ["_ga_CBQTM9PBQE", "Google Analytics: keeps the state of a visit. Set only if you accept analytics.", "2 years", "First party, set by Google Analytics"],
]


def rows_html(rows: list[list[str]]) -> str:
    head = "<tr>" + "".join(f"<th>{c}</th>" for c in rows[0]) + "</tr>"
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f'<div class="doc-table"><table><thead>{head}</thead><tbody>{body}</tbody></table></div>'


def table_html(tbl) -> str:
    rows = []
    for tr in tbl.iter(W + "tr"):
        cells = []
        for tc in tr.findall(W + "tc"):
            paras = [runs_html(p) for p in tc.findall(W + "p")]
            cells.append("<br>".join(x for x in paras if x.strip()))
        fills = ROW_FILLS.get(re.sub(r"<[^>]+>", "", cells[0]).strip() if cells else "", {})
        for k, v in fills.items():
            cells = [c.replace(k, html.escape(v)) for c in cells]
        rows.append(cells)
    first = re.sub(r"<[^>]+>", "", rows[0][0]).strip()
    for heads, extra in EXTRA_ROWS.items():
        if first in heads:
            rows += [[html.escape(c) for c in r] for r in extra]
    return rows_html(rows)


def convert(path: Path, key: str) -> dict:
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    body = root.find(W + "body")
    blocks = list(body)
    title_lines: list[str] = []
    parts: list[str] = []
    toc: list[tuple[str, str]] = []
    list_buf: list[str] = []
    used_ids: set[str] = set()

    def flush_list():
        if list_buf:
            parts.append("<ul>" + "".join(f"<li>{x}</li>" for x in list_buf) + "</ul>")
            list_buf.clear()

    def anchor(text: str) -> str:
        base = f"{key}-{slug(text)}"
        a, n = base, 2
        while a in used_ids:
            a, n = f"{base}-{n}", n + 1
        used_ids.add(a)
        return a

    for el in blocks:
        if el.tag == W + "tbl":
            flush_list()
            parts.append(table_html(el))
            continue
        if el.tag != W + "p":
            continue
        text = "".join(t.text or "" for t in el.iter(W + "t")).strip()
        if not text:
            continue
        # The first three plain paragraphs are the title block: STIMA PROVA / TITLE / Version line.
        if len(title_lines) < 3 and not parts and style_of(el) == "":
            title_lines.append(text)
            continue
        st = style_of(el)
        inner = runs_html(el).strip()
        if st == "Heading1":
            flush_list()
            a = anchor(text)
            toc.append((a, text))
            m = re.match(r"^(\d+)\.\s+(.*)$", text)
            label = f'<span class="h-no">{m.group(1)}</span>{html.escape(m.group(2))}' if m else html.escape(text)
            parts.append(f'<h2 id="{a}">{label}</h2>')
        elif st == "Heading2":
            flush_list()
            a = anchor(text)
            parts.append(f'<h3 id="{a}">{html.escape(text)}</h3>')
        elif st == "ListParagraph" or is_list(el):
            list_buf.append(inner)
        else:
            flush_list()
            m = re.match(r"^(\d+\.\d+(?:\.\d+)?)\s+", text)
            if m:
                no = m.group(1)
                rest = inner[inner.find(no) + len(no):].lstrip()
                parts.append(f'<p class="clause"><span class="cl-no">{no}</span>{rest}</p>')
            elif re.match(r"^\([a-z]{1,4}\)\s", text):
                parts.append(f'<p class="item">{inner}</p>')
            elif text == COOKIE_PLACEHOLDER:
                parts.append(rows_html([[html.escape(c) for c in r] for r in COOKIE_ROWS]))
            else:
                parts.append(f"<p>{inner}</p>")
    flush_list()
    brand, title, meta = (title_lines + ["", "", ""])[:3]
    return {"key": key, "brand": brand, "title": title, "meta": meta, "toc": toc, "html": "\n".join(parts)}


DOCS = [
    ("terms-of-use", "Terms of Use", "For customers"),
    ("privacy", "Privacy Policy", "For everyone"),
    ("participant-terms", "Participant Terms", "For participants"),
]


def title_case(t: str) -> str:
    return " ".join(w.capitalize() if w.isupper() and len(w) > 2 else w for w in t.split())


def page(docs: list[dict]) -> str:
    tabs = "".join(
        f'<a class="lg-tab" href="#{d["key"]}" data-doc="{d["key"]}" role="tab"><span class="lg-tab-for">{label_for}</span><span class="lg-tab-name">{name}</span></a>'
        for d, (_, name, label_for) in zip(docs, DOCS)
    )
    articles = []
    for d, (key, name, label_for) in zip(docs, DOCS):
        toc = "".join(f'<li><a href="#{a}">{html.escape(t)}</a></li>' for a, t in d["toc"])
        articles.append(f'''
<article class="lg-doc" id="{key}" data-doc="{key}" data-title="{html.escape(name)}" data-meta="{html.escape(d["meta"])}">
  <aside class="lg-toc" aria-label="Sections of the {html.escape(name)}">
    <div class="lg-toc-label">On this page</div>
    <ol>{toc}</ol>
  </aside>
  <div class="lg-body">
    <header class="lg-doc-head">
      <div class="lg-kicker">{html.escape(label_for)}</div>
      <h2 class="lg-doc-title">{html.escape(name)}</h2>
      <p class="lg-meta">{html.escape(d["meta"])}</p>
    </header>
    <div class="lg-text">
{d["html"]}
    </div>
  </div>
</article>''')
    template = (ROOT / "tools" / "terms-template.html").read_text()
    return template.replace("<!--TABS-->", tabs).replace("<!--ARTICLES-->", "\n".join(articles))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tou", required=True)
    ap.add_argument("--privacy", required=True)
    ap.add_argument("--participant", required=True)
    ap.add_argument("--date", help='replaces every "[date]" placeholder, e.g. "24 September 2026"')
    a = ap.parse_args()
    docs = [convert(Path(a.tou), "terms-of-use"), convert(Path(a.privacy), "privacy"), convert(Path(a.participant), "participant-terms")]
    out = ROOT / "terms" / "index.html"
    out.parent.mkdir(exist_ok=True)
    text = page(docs)
    if a.date:
        text = text.replace("[date]", html.escape(a.date))
    out.write_text(text)
    for d in docs:
        print(f'{d["key"]}: {d["title"]} | {d["meta"]} | {len(d["toc"])} sections')
    print("written", out)


if __name__ == "__main__":
    main()
