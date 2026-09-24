"""
Builds terms/index.html from the three Stima Prova legal documents (.docx).

    python3 tools/legal_to_html.py \
        --tou  path/to/Stima_Prova_ToU_*.docx \
        --privacy path/to/Stima_Prova_Privacy_Policy_*.docx \
        --participant path/to/Stima_Prova_Participant_Terms_*.docx

The text is taken verbatim from the documents. Only structure is added:
Heading 1 and Heading 2 become section headings with anchors, list
paragraphs become lists, "(a)" items and "1.2" clauses get their own
styling, bold runs stay bold, tables stay tables.
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


def table_html(tbl) -> str:
    rows = []
    for i, tr in enumerate(tbl.iter(W + "tr")):
        cells = []
        for tc in tr.findall(W + "tc"):
            paras = [runs_html(p) for p in tc.findall(W + "p")]
            content = "<br>".join(x for x in paras if x.strip())
            cells.append(content)
        tag = "th" if i == 0 else "td"
        rows.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
    head, body = rows[0], rows[1:]
    return f'<div class="doc-table"><table><thead>{head}</thead><tbody>{"".join(body)}</tbody></table></div>'


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
    a = ap.parse_args()
    docs = [convert(Path(a.tou), "terms-of-use"), convert(Path(a.privacy), "privacy"), convert(Path(a.participant), "participant-terms")]
    out = ROOT / "terms" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page(docs))
    for d in docs:
        print(f'{d["key"]}: {d["title"]} | {d["meta"]} | {len(d["toc"])} sections')
    print("written", out)


if __name__ == "__main__":
    main()
