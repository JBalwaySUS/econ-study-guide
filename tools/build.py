"""Build the study-guide website (src/) and the PDF from the content fragments.

Usage:  python tools/build.py          # site + PDF
        python tools/build.py --no-pdf # site only

Content lives in tools/content/NN-slug.html. Each fragment starts with an <h1>,
and may use these shortcodes:
    {{fig:name|Caption text}}   inline SVG figure from figures.py (auto-numbered)
    {{flow:transmission}}        HTML flow diagram defined in FLOWS below
"""
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
SRC = ROOT / "src"
CONTENT = TOOLS / "content"
PDF_NAME = "Economics_Study_Guide_L5-L8_Welfare.pdf"

sys.path.insert(0, str(TOOLS))
from figures import all_figures, flow  # noqa: E402

KATEX = "https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9"

FLOWS = {
    "transmission": flow([
        ["<b>Central bank changes the policy rate</b><br>(RBI repo rate)"],
        ["Market interest rates<br>(lending, bond yields)", "Asset prices<br>(shares, housing, bonds)",
         "Expectations &amp; confidence", "Exchange rate"],
        ["Consumption &amp; investment<br>(domestic demand)", "Wealth effects on consumption",
         "Spending &amp; price-setting plans", "Net exports &amp; import prices"],
        ["<b>Aggregate demand</b> &rarr; output &amp; employment &rarr; domestic inflationary pressure"],
        ["<b>Inflation</b> (with import prices feeding in directly)"],
    ]),
}

SITE_TITLE = "Economics Study Guide"
SITE_SUB = "Inflation &amp; Monetary Policy &middot; Microeconomics &middot; Market Structures &middot; Welfare"


def slugify(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s_]+", "-", s)


def load_chapters():
    chapters = []
    for path in sorted(CONTENT.glob("*.html")):
        raw = path.read_text(encoding="utf8")
        m = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.S)
        title = m.group(1).strip() if m else path.stem
        kicker = re.search(r'<p class="kicker">(.*?)</p>', raw, re.S)
        slug = re.sub(r"^\d+-", "", path.stem)
        chapters.append({"n": len(chapters) + 1, "slug": slug, "file": f"{slug}.html",
                         "title": title, "kicker": kicker.group(1) if kicker else "", "raw": raw})
    return chapters


def render_body(ch, figs):
    html = ch["raw"]
    counter = {"n": 0}

    def fig_sub(m):
        name, cap = m.group(1), (m.group(2) or "").strip()
        counter["n"] += 1
        num = f'{ch["n"]}.{counter["n"]}'
        if name not in figs:
            raise KeyError(f"unknown figure {name} in {ch['file']}")
        return (f'<figure class="figure" id="fig-{name}">{figs[name]}'
                f'<figcaption><b>Figure {num}.</b> {cap}</figcaption></figure>')

    html = re.sub(r"\{\{fig:([\w-]+)(?:\|(.*?))?\}\}", fig_sub, html, flags=re.S)
    html = re.sub(r"\{\{flow:(\w+)\}\}", lambda m: FLOWS[m.group(1)], html)

    # ids for h2/h3 + section numbering on h2
    toc = []
    sec = {"n": 0}
    used = set()

    def h_sub(m):
        level, attrs, inner = m.group(1), m.group(2) or "", m.group(3)
        if "id=" in attrs:
            hid = re.search(r'id="([^"]+)"', attrs).group(1)
        else:
            base = f'c{ch["n"]}-' + slugify(inner)[:60]
            hid, k = base, 2
            while hid in used:
                hid, k = f"{base}-{k}", k + 1
            attrs += f' id="{hid}"'
        used.add(hid)
        if level == "2":
            sec["n"] += 1
            num = f'{ch["n"]}.{sec["n"]}'
            toc.append((num, re.sub(r"<[^>]+>", "", inner), hid))
            return f'<h2{attrs}><span class="secnum">{num}</span> {inner}</h2>'
        return f"<h{level}{attrs}>{inner}</h{level}>"

    html = re.sub(r"<h([23])((?:\s[^>]*)?)>(.*?)</h\1>", h_sub, html, flags=re.S)
    # chapter number into h1
    html = re.sub(r"<h1([^>]*)>(.*?)</h1>",
                  lambda m: f'<h1{m.group(1)}><span class="chapnum">Chapter {ch["n"]}</span>{m.group(2)}</h1>',
                  html, count=1, flags=re.S)
    return html, toc


HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{katex}/katex.min.css">
<link rel="stylesheet" href="assets/style.css">
<script>try{{var t=localStorage.getItem('sg-theme');if(t)document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
</head>
"""

MATH_JS = """<script defer src="{katex}/katex.min.js"></script>
<script defer src="{katex}/contrib/auto-render.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function () {{
  function go() {{
    if (!window.renderMathInElement) return setTimeout(go, 50);
    renderMathInElement(document.body, {{
      delimiters: [{{left: '$$', right: '$$', display: true}}, {{left: '\\\\[', right: '\\\\]', display: true}},
                   {{left: '\\\\(', right: '\\\\)', display: false}}],
      ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'svg'],
      throwOnError: false
    }});
    document.documentElement.classList.add('math-ready');
  }}
  go();
}});
</script>
"""


def sidebar(chapters, active=None):
    items = ['<a class="nav-home{}" href="index.html">Overview &amp; how to use</a>'.format(" active" if active is None else "")]
    for c in chapters:
        cls = " active" if active and c["slug"] == active["slug"] else ""
        items.append(f'<a class="nav-ch{cls}" href="{c["file"]}"><span class="nav-n">{c["n"]}</span>'
                     f'<span><span class="nav-k">{c["kicker"]}</span>{re.sub(r"<[^>]+>", "", c["title"])}</span></a>')
    items.append(f'<a class="nav-pdf" href="{PDF_NAME}" download>&#8595; Download the full PDF</a>')
    return "\n".join(items)


def page(title, chapters, body, toc, active=None, prev=None, nxt=None):
    toc_html = ""
    if toc:
        toc_html = '<nav class="ontoc" aria-label="On this page"><div class="ontoc-h">On this page</div>' + "".join(
            f'<a href="#{hid}"><span>{num}</span> {t}</a>' for num, t, hid in toc) + "</nav>"
    pn = ""
    if prev or nxt:
        pn = '<nav class="prevnext">'
        pn += (f'<a class="prev" href="{prev["file"]}"><small>Previous</small>{prev["title"]}</a>' if prev else "<span></span>")
        pn += (f'<a class="next" href="{nxt["file"]}"><small>Next</small>{nxt["title"]}</a>' if nxt else "<span></span>")
        pn += "</nav>"
    return (HEAD.format(title=title, katex=KATEX) +
            f"""<body>
<header class="topbar">
  <button class="menu-btn" aria-label="Open chapter menu" onclick="document.body.classList.toggle('nav-open')">&#9776;</button>
  <a class="brand" href="index.html">{SITE_TITLE}</a>
  <div class="top-actions">
    <a class="pdf-link" href="{PDF_NAME}" download>PDF</a>
    <button class="theme-btn" aria-label="Toggle dark mode" onclick="toggleTheme()">&#9680;</button>
  </div>
</header>
<div class="layout">
<aside class="sidebar">{sidebar(chapters, active)}</aside>
<main class="content">
{body}
{pn}
</main>
{toc_html}
</div>
<script>
function toggleTheme(){{
  var r=document.documentElement, cur=r.getAttribute('data-theme');
  var dark = cur ? cur==='dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  var nt = dark ? 'light' : 'dark'; r.setAttribute('data-theme', nt);
  try{{localStorage.setItem('sg-theme', nt);}}catch(e){{}}
}}
document.querySelectorAll('.sidebar a').forEach(function(a){{a.addEventListener('click',function(){{document.body.classList.remove('nav-open');}});}});
</script>
{MATH_JS.format(katex=KATEX)}
</body>
</html>
""")


def index_body(chapters):
    cards = "".join(
        f'<a class="card" href="{c["file"]}"><span class="card-n">Chapter {c["n"]}</span>'
        f'<span class="card-k">{c["kicker"]}</span><span class="card-t">{re.sub(r"<[^>]+>", "", c["title"])}</span></a>'
        for c in chapters)
    intro = (CONTENT.parent / "index_intro.html").read_text(encoding="utf8")
    return f"""<section class="hero">
<p class="kicker">Course study guide &middot; from Lecture 5 onwards</p>
<h1>{SITE_TITLE}</h1>
<p class="lede">{SITE_SUB}</p>
</section>
<div class="cards">{cards}</div>
{intro}"""


def build_site():
    figs = all_figures()
    chapters = load_chapters()
    SRC.mkdir(exist_ok=True)
    (SRC / "assets").mkdir(exist_ok=True)
    shutil.copy(TOOLS / "style.css", SRC / "assets" / "style.css")

    rendered = []
    for i, ch in enumerate(chapters):
        body, toc = render_body(ch, figs)
        rendered.append((ch, body, toc))
        prev = chapters[i - 1] if i else None
        nxt = chapters[i + 1] if i + 1 < len(chapters) else None
        html = page(f'{re.sub(r"<[^>]+>", "", ch["title"])} · {SITE_TITLE}', chapters,
                    f'<article class="chapter">{body}</article>', toc, ch, prev, nxt)
        (SRC / ch["file"]).write_text(html, encoding="utf8")

    (SRC / "index.html").write_text(page(SITE_TITLE, chapters, index_body(chapters), None), encoding="utf8")

    # ---- print version (single document) -----------------------------------
    toc_items = []
    for ch, body, toc in rendered:
        toc_items.append(f'<li class="ptoc-ch"><a href="#{ch["slug"]}">Chapter {ch["n"]}. {re.sub(r"<[^>]+>", "", ch["title"])}</a>'
                         + "<ol>" + "".join(f'<li><a href="#{hid}">{num} {t}</a></li>' for num, t, hid in toc) + "</ol></li>")
    chapters_html = "\n".join(f'<article class="chapter" id="{ch["slug"]}">{body}</article>' for ch, body, _ in rendered)
    chapters_html = chapters_html.replace("<details", "<details open")
    intro = (CONTENT.parent / "index_intro.html").read_text(encoding="utf8")
    print_html = (HEAD.format(title=SITE_TITLE, katex=KATEX).replace('assets/style.css', 'assets/style.css" media="all')
                  + f"""<body class="print-doc">
<section class="cover">
  <p class="kicker">Course study guide &middot; Lecture 5 onwards</p>
  <h1>{SITE_TITLE}</h1>
  <p class="lede">{SITE_SUB}</p>
  <p class="cover-meta">Main reference: CORE Econ, <i>The Economy: South Asia</i>; with Mitchell, Wray &amp; Watts, <i>Macroeconomics</i> (Ch. 17&ndash;18) and Goodwin et al., <i>Principles of Economics in Context</i> (Ch. 4&ndash;6, 9, 16&ndash;18).</p>
  <p class="cover-meta">Compiled {date.today().strftime('%d %B %Y')}</p>
</section>
<section class="ptoc"><h2 class="ptoc-h">Contents</h2><ol>{''.join(toc_items)}</ol></section>
<section class="pintro">{intro}</section>
{chapters_html}
{MATH_JS.format(katex=KATEX)}
</body></html>""")
    (SRC / "print.html").write_text(print_html, encoding="utf8")
    print(f"site: {len(chapters)} chapters, {len(figs)} figures -> {SRC}")
    return chapters


def build_pdf():
    edge = None
    for cand in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if Path(cand).exists():
            edge = cand
            break
    if not edge:
        print("No Edge/Chrome found; skipping PDF")
        return
    out = SRC / PDF_NAME
    url = (SRC / "print.html").as_uri()
    cmd = [edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
           "--virtual-time-budget=20000", f"--print-to-pdf={out}", url]
    subprocess.run(cmd, check=True, timeout=180)
    shutil.copy(out, ROOT / PDF_NAME)
    print("pdf:", out, f"{out.stat().st_size / 1e6:.1f} MB (copied to project root)")


if __name__ == "__main__":
    build_site()
    if "--no-pdf" not in sys.argv:
        build_pdf()
