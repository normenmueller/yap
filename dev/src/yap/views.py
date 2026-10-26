"""Small, derived views of the shared portfolio model; no source discovery here."""

from html import escape
from pathlib import Path
import json
import subprocess
from urllib.parse import quote, urlsplit

from . import footer, palette, navigation, overview, selections
from .documents import body as publication_body, pdf_target
from .publication_links import activity_pdf, objective_pdf


def _inlines(value):
    return [{"t": "Str", "c": str(value)}]


def _plain(value):
    if isinstance(value, list):
        return "".join(_plain(item) for item in value)
    if not isinstance(value, dict):
        return ""
    kind, content = value.get("t"), value.get("c", [])
    if kind in ("Space", "SoftBreak", "LineBreak"):
        return " "
    if kind == "Str":
        return content
    if kind in ("Code", "Math"):
        return content[-1]
    if kind == "Header":
        return _plain(content[2])
    if kind in ("Link", "Image", "Span"):
        return _plain(content[1])
    return _plain(content)


def _portable_blocks(goal, model):
    """Use the PDFs' publication rules, relative to the nested HTML view."""
    blocks = publication_body(
        goal.get("blocks", []), goal['path'], goal["id"], 3,
        model["nodes"], Path("../.."), external=True, goals=model["goals"], resource_prefix="", goal_source=model.get("goal_source"),
    )
    def walk(value):
        if isinstance(value, list):
            return [walk(item) for item in value]
        if not isinstance(value, dict):
            return value
        kind, content = value.get("t"), value.get("c")
        if kind == "Link":
            attr, label, target = content
            url = urlsplit(target[0])
            if not url.scheme and not url.netloc:
                if target[0].startswith("#"):
                    target[0] = "../../acc/pdf/Performance - mPM.pdf#nameddest=" + quote(target[0][1:], safe="-_")
                else:
                    target[0] = ("../../acc/pdf/" if url.path.endswith(".pdf") and not url.path.startswith("res/") else "../../") + target[0]
            return {"t": "Link", "c": [attr, walk(label), target]}
        return {key: walk(item) for key, item in value.items()}
    return walk(blocks)


def _goal_sections(blocks):
    """Fold top-level objective sections, preserving headings and their contents."""
    result = []
    opened = False
    for block in blocks:
        if block['t'] == 'Header' and block['c'][0] <= 4:
            if opened:
                result.append({'t': 'RawBlock', 'c': ['html', '</div></details>']})
            result.extend([
                {'t': 'RawBlock', 'c': ['html', '<details class="goal-detail"><summary>']},
                block,
                {'t': 'RawBlock', 'c': ['html', '</summary><div class="goal-detail-body">']},
            ])
            opened = True
        else:
            result.append(block)
    if opened:
        result.append({'t': 'RawBlock', 'c': ['html', '</div></details>']})
    return result


def _goal_cards(model):
    nodes = {node["key"]: node for node in overview.activity_nodes(model)}
    labels = {'active': 'Active', 'on hold': 'On hold', 'closed': 'Closed'}
    groups = {status: [] for status in labels}
    for goal in model["goals"]:
        blocks = _portable_blocks(goal, model)
        if blocks and blocks[0].get("t") == "Header" and _plain(blocks[0]).strip() == goal["title"].strip():
            blocks = blocks[1:]
        content = [
            {'t': 'RawBlock', 'c': ['html', '<details id="goal-' + escape(goal['id'], quote=True) +
                                     '" class="goal-card" open><summary>']},
            {"t": "Header", "c": [3, ["", [], []], _inlines(goal['title'])]},
            {'t': 'RawBlock', 'c': ['html', '</summary><div class="goal-card-body">']},
        ]
        metadata = []
        if goal.get('timeline'):
            metadata.append('<span>Zeitraum: ' + escape(goal['timeline']) + '</span>')
        if goal.get('url'):
            metadata.append('<a href="' + escape(goal['url'], quote=True) + '">Quelle ↗</a>')
        metadata.append('<a href="' + escape(objective_pdf(goal), quote=True) +
                        '" title="Ziel im mPM-PDF">Ziel · PDF</a>')
        if goal.get('priority'):
            priority = escape(goal['priority'], quote=True)
            metadata.append('<span class="goal-priority"><i class="priority-dot priority-' +
                            priority + '" aria-hidden="true"></i>Priorität ' + priority + '</span>')
        if metadata:
            content.append({'t': 'RawBlock', 'c': ['html', '<div class="goal-meta">' + ''.join(metadata) + '</div>']})
        content.extend(_goal_sections(blocks))
        links = []
        for relation in goal.get("activities", []):
            node = nodes.get(relation["key"])
            if node:
                label = relation.get("label") or node["title"]
                acronym = node.get('acronym')
                if acronym and acronym != label:
                    label = acronym + ' – ' + label
                elif label == node['title']:
                    detail = node.get('subtitle') or node.get('slogan')
                    if detail and detail != label:
                        label += ' – ' + detail
                link = {"t": "Link", "c": [["", [], []], _inlines(label), [activity_pdf(node, relation.get("anchor", "")), "Aktivität im Activity-PDF"]]}
                item = [{"t": "Plain", "c": [link]}]
                if note := relation.get('note'):
                    target = pdf_target(goal['id'] + '--' + note['section'])
                    item.append({'t': 'RawBlock', 'c': ['html',
                        '<small class="activity-note">' + escape(note['text']) +
                        ' <a href="#' + escape(target, quote=True) + '">' +
                        escape(note['label']) + '</a></small>']})
                links.append(item)
        if links:
            content.extend(_goal_sections([
                {'t': 'Header', 'c': [4, ['', [], []], _inlines('Verknüpfte Aktivitäten (' + str(len(links)) + ')')]},
                {'t': 'BulletList', 'c': links},
            ]))
        content.append({'t': 'RawBlock', 'c': ['html', '</div></details>']})
        groups.setdefault(goal.get('status') or 'Ohne Status', []).append(content)
    if not any(groups.values()):
        return '<p class="empty">Noch keine Ziele vorhanden.</p>'
    sections = []
    for status, cards in groups.items():
        if not cards:
            continue
        key = status.casefold().replace(' ', '-')
        heading_id = 'goals-' + key + '-title'
        count = str(len(cards)) + (' Ziel' if len(cards) == 1 else ' Ziele')
        heading = {"t": "Header", "c": [2, [heading_id, [], []], [
            *_inlines(labels.get(status, status)), {"t": "Space"},
            {"t": "Span", "c": [["", ["goal-count"], []], _inlines(count)]}]]}
        sections.extend([
            {"t": "RawBlock", "c": ["html", '<details id="goals-' + escape(key, quote=True) +
             '" class="goal-section goals-' + escape(key, quote=True) + '"' + (' open' if status == 'active' or model.get('selection', {}).get('key') else '') + '><summary>']},
            heading, {"t": "RawBlock", "c": ["html", '</summary>']},
            {"t": "Div", "c": [["", ["cards"], []], [block for card in cards for block in card]]},
            {"t": "RawBlock", "c": ["html", '</details>']}])
    document = {"pandoc-api-version": model["api"], "meta": {}, "blocks": sections}
    result = subprocess.run(
        ["pandoc", "--from=json", "--to=html5", "--wrap=none"],
        input=json.dumps(document), text=True, capture_output=True, check=True,
    )
    return result.stdout


def _goal_tracking(model):
    from .performance import render
    return render(model)


_STYLE = palette.css("""
:root{color-scheme:dark;--bg:@namBg;--panel:@namPanel;--ink:@namInk;--muted:@namMuted;--line:@namLine;--accent:@namBrand}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1160px;margin:auto;padding:28px 24px 72px}a{color:var(--accent);text-underline-offset:3px;overflow-wrap:anywhere}a:hover{color:var(--ink)}a:focus-visible,label:focus-visible{outline:2px solid var(--accent);outline-offset:5px}header{margin-bottom:24px}header p{max-width:66ch;color:var(--muted);margin:12px 0 0}h1{font-size:clamp(1.7rem,3vw,2rem);line-height:1.2;margin:0}h2{font-size:1.35rem}h3{line-height:1.35;margin:0 0 14px}h4,h5,h6{font-size:1rem}nav{display:flex;gap:20px;flex-wrap:wrap;font-size:.9rem}.panel{display:none}body:has(#graph:checked) #graph-panel,body:has(#cards:checked) #cards-panel,body:has(#tracking:checked) #tracking-panel{display:block}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,430px),1fr));gap:20px;align-items:start}.goal-card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:24px;min-width:0;overflow-wrap:anywhere}.goal-card h3 a{text-decoration:none}.goal-card p{margin:10px 0}.status{color:var(--accent);font-size:.78rem;text-transform:uppercase;letter-spacing:.07em}.goal-card ul,.goal-card ol{padding-left:22px}.goal-card blockquote{border-left:2px solid var(--line);margin:16px 0;padding-left:14px;color:var(--muted)}.goal-card table{border-collapse:collapse;display:block;overflow-x:auto;font-size:.88rem;width:100%;margin:18px 0}.goal-card th,.goal-card td{text-align:left;vertical-align:top;padding:9px;border-bottom:1px solid var(--line)}.goal-card pre{overflow-x:auto}.goal-card img{max-width:100%;height:auto}.related{margin-top:24px;border-top:1px solid var(--line);padding-top:12px}.related>p{color:var(--muted);font-size:.85rem}.empty,footer{color:var(--muted)}footer{margin-top:36px;font-size:.82rem}@media(max-width:600px){main{padding:28px 14px 48px}.goal-card{padding:18px}}@media print{body{background:white;color:black}nav,footer{display:none!important}.panel{display:block!important}.cards{display:block}.goal-card{background:white;border-color:#ccc;break-inside:avoid;margin-bottom:16px}a{color:inherit}.status{color:#444}}
.goal-section{--state:@namMuted;margin:0 0 36px;padding:22px;border:1px solid color-mix(in srgb,var(--state) 35%,var(--line));border-left:4px solid var(--state);border-radius:12px;background:color-mix(in srgb,var(--state) 4%,var(--bg))}
.goals-active{--state:@namGreen}.goals-on-hold{--state:@namHold}.goals-closed{--state:@namPriorityLow}
.goal-section>summary{display:flex;align-items:center;gap:14px;list-style:none;cursor:pointer;color:var(--state);font-size:1.3rem;line-height:1.4}
.goal-section>summary::-webkit-details-marker{display:none}.goal-section>summary h2{display:flex;align-items:center;gap:14px;margin:0;font-size:inherit;line-height:inherit}
.goal-section>summary::after{content:"";width:9px;height:9px;border-right:2px solid currentColor;border-bottom:2px solid currentColor;transform:rotate(-45deg);margin-left:auto;margin-right:4px;flex-shrink:0}
.goal-section[open]>summary{margin-bottom:20px}.goal-section[open]>summary::after{transform:rotate(45deg)}.goal-section>summary:focus-visible{outline:2px solid var(--state);outline-offset:6px;border-radius:3px}
.goal-count{font-size:.78rem;font-weight:400;color:var(--muted);border:1px solid color-mix(in srgb,var(--state) 30%,var(--line));border-radius:20px;padding:2px 10px}
.goal-section .status{color:var(--state)}.goal-section .cards{grid-template-columns:repeat(auto-fit,minmax(min(100%,400px),1fr))}
.goal-priority{font-size:.8rem;color:var(--muted)}.priority-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px}.priority-p1{background:@namAccent}.priority-p2{background:@namMarkerOrange}.priority-p3{background:@namBabyBlue}.priority-p4{background:@namPriorityLow}
.goal-meta{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 16px;color:var(--muted);font-size:.82rem;margin:0 0 18px}
.goal-card>summary{display:flex;align-items:flex-start;gap:16px;list-style:none;cursor:pointer;color:var(--accent)}
.goal-card>summary::-webkit-details-marker{display:none}.goal-card>summary h3{min-height:2.7em;margin:0;flex:1;min-width:0}
.goal-card[open]>summary{margin-bottom:14px}
.goal-card>summary::after{content:"";width:8px;height:8px;border-right:1.5px solid var(--muted);border-bottom:1.5px solid var(--muted);transform:rotate(-45deg);margin:7px 4px 0 0;flex-shrink:0}
.goal-card[open]>summary::after{transform:rotate(45deg)}
.goal-card>summary:focus-visible{outline:2px solid var(--accent);outline-offset:5px;border-radius:3px}
.activity-note{display:block;font-size:.75rem;line-height:1.5;color:var(--muted);margin:3px 0 6px}.activity-note a{color:inherit}.activity-note a:hover{color:var(--accent)}
.goal-detail{border-top:1px solid var(--line)}
.goal-detail>summary{display:flex;align-items:center;gap:16px;min-height:44px;padding:10px 0;cursor:pointer;list-style:none}
.goal-detail>summary::-webkit-details-marker{display:none}.goal-detail>summary :is(h3,h4){font-size:.9rem;line-height:1.5;margin:0;font-weight:600}
.goal-detail>summary::after{content:"";width:7px;height:7px;border-right:1.5px solid var(--muted);border-bottom:1.5px solid var(--muted);transform:rotate(-45deg);margin:0 4px 0 auto;flex-shrink:0}
.goal-detail[open]>summary::after{transform:rotate(45deg)}.goal-detail>summary:hover{color:var(--accent)}
.goal-detail>summary:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:3px}
.goal-detail-body{padding:0 0 12px}.goal-detail-body>:first-child{margin-top:4px}.goal-detail-body>:last-child{margin-bottom:4px}
.personal-addition{color:@namPersonalAddition}
.performance-heading{display:none}
body:has(#cards:checked) .heading-cards,body:has(#tracking:checked) .heading-tracking,body:has(#graph:checked) .heading-graph{display:inline}
@media(max-width:600px){.goal-section{padding:16px 12px;margin-bottom:28px}.goal-section>summary h2{gap:10px}.goal-section[open]>summary{margin-bottom:16px}}
@media print{.goal-detail::details-content{content-visibility:visible;display:block}.goal-detail>.goal-detail-body{display:block!important}.goal-detail>summary{break-after:avoid}.goal-detail>summary::after{display:none}.goal-meta{color:#444}.goal-card{break-inside:auto}}
@media print{.goal-card::details-content{content-visibility:visible;display:block}.goal-card>.goal-card-body{display:block!important}.goal-card>summary{color:inherit;break-after:avoid;margin-bottom:14px}.goal-card>summary::after{display:none}}
@media print{.goal-section{background:white;border-color:#bbb;break-inside:auto;padding:16px}.goal-section>summary{color:#222;break-after:avoid;margin-bottom:16px}.goal-section>summary::after{display:none}.goal-section::details-content{content-visibility:visible;display:block}.goal-section>.cards{display:block!important}.goal-count{color:#444;border-color:#bbb}}

""")


def render_mpm(model, destination: Path):
    for selected in selections.performance(model):
        _render_mpm_selection(selected, destination)


def _render_mpm_selection(model, destination: Path):
    """Write a portable, offline HTML view using the already parsed model."""
    from . import performance, performance_lanes, goaltree, work_progress
    cards = _goal_cards(model)
    tracking = _goal_tracking(model)
    meta = model['goal_meta']
    page_title = ' · '.join(_plain(meta[key]) for key in ('title', 'subtitle') if key in meta)
    html = '''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">''' + navigation.head('performance', page_title) + '''<style>''' + _STYLE + performance.STYLE + work_progress.STYLE + performance_lanes.STYLE + goaltree.STYLE + navigation.STYLE + footer.STYLE + '''</style></head>
<body class="yap-page">''' + navigation.render('performance', theme='dark', selection=model['selection']) + '''<main>
<header><h1><span class="performance-heading heading-cards">Ziele</span><span class="performance-heading heading-tracking">Zielfortschritt</span><span class="performance-heading heading-graph">Zusammenhänge</span></h1><p>Ziele, Key Results und ihre Beiträge.</p></header>
<section id="cards-panel" class="panel" aria-label="Ziele">''' + cards + '''</section>
<section id="tracking-panel" class="panel" aria-label="Zielfortschritt">''' + tracking + '''</section>
<section id="graph-panel" class="panel" aria-label="Zusammenhänge">''' + goaltree.render(model) + '''</section>
</main>''' + footer.render() + '''<script>
(() => {
  const radios = [...document.querySelectorAll('input[name="view"]')];
  const links = [...document.querySelectorAll('.perspective-options a')];
  function sync() {
    const id = radios.find(r => r.checked).id;
    links.forEach(a => { a.hash = id; });
  }
  function restore() {
    const selected = radios.find(r => '#' + r.id === location.hash);
    if (selected) { selected.checked = true; selected.dispatchEvent(new Event('change')); }
    const target = document.getElementById(location.hash.slice(1));
    if (target && target.closest('.goal-card')) {
      document.getElementById('cards').checked = true;
      for (let parent = target.parentElement; parent; parent = parent.parentElement) {
        if (parent.tagName === 'DETAILS') parent.open = true;
      }
      requestAnimationFrame(() => {
        target.scrollIntoView({block: 'center'});
        target.closest('summary')?.focus({preventScroll: true});
      });
    }
    sync();
  }
  radios.forEach(r => r.addEventListener('change', () => {
    sync();
    history.replaceState(null, '', '#' + r.id);
  }));
  window.addEventListener('hashchange', restore);
  restore();
})();
</script></body></html>
'''
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / selections.filename(model['selection'])).write_text(html, encoding="utf-8")


def _tex(value):
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(char, char) for char in str(value)).replace("\n", " ")


def map_tex(model, key=""):
    """Render an automatically sized hierarchy; all positions follow the tree."""
    all_nodes = overview.map_nodes(model)
    selected = {key} if key else {node['key'] for node in all_nodes}
    for node in all_nodes:
        if node['parent'] in selected:
            selected.add(node['key'])
    nodes = [node for node in all_nodes if node['key'] in selected]
    base = min((node["depth"] for node in nodes), default=1)
    lines = [r"\documentclass[tikz,border=12pt]{standalone}", r"\input{theme.tex}", r"\usetikzlibrary{calc}", r"\newcommand{\mapnext}[1]{\tikz[baseline=(n.base)]{\node[circle,draw=namMuted,text=namMuted,inner sep=0pt,minimum size=10pt,font=\scriptsize] (n) {#1};}}", r"\pagecolor{namBg}", r"\begin{document}", r"\begin{tikzpicture}[font=\sffamily,text=namInk,box/.style={anchor=north west,draw=namLine,fill=namPanel,rounded corners=3pt,inner sep=9pt,align=left}]"]
    title = overview.map_text(nodes[0])[0] if key and nodes else "Aktivitäten"
    if not key and model.get('selection', {}).get('key'):
        title += ' · ' + model['selection']['label']
    lines.append(r"\node[anchor=north west,font=\Large\bfseries,text=namResearch] (heading) at (0,0) {" + _tex(title) + "};")
    if not nodes:
        lines.append(r'\node[anchor=north west,text=namMuted] at (0,-.8) {Noch keine Aktivit\"aten vorhanden.};')
    positions = {}
    roots = [node["key"] for node in nodes if node["depth"] == base]
    column_count = min(2, len(roots))
    row_anchor = "heading"
    previous = {}
    root_for = {}
    for index, node in enumerate(nodes):
        depth = node["depth"] - base
        root = node["key"] if node["key"] in roots else root_for[node["parent"]]
        root_for[node["key"]] = root
        root_index = roots.index(root)
        column = root_index % column_count
        if node["key"] == root and root_index and column == 0:
            left, right = (previous[r] for r in roots[root_index - column_count:root_index])
            row_anchor = "band" + str(root_index // column_count)
            lines.append(r"\path let \p1=(" + left + r".south), \p2=(" + right
                         + r".south) in coordinate (" + row_anchor + r") at (0,{min(\y1,\y2)-0.65cm});")
        origin = column * 12.0
        x = min(depth, 12) * 0.55
        width = max(5.0, (10.5 if column_count > 1 else 17.0) - x)
        # Semantic colors remain stable in the full map and area submaps.
        color = "namMuted"
        color = {'support': 'namSupport', 'impact': 'namImpact', 'governance': 'namGovernance',
                 'epistemics': 'namEpistemics', 'strategy': 'namStrategy'}.get(node['tone'], color)
        options = "box,text width=" + str(width) + "cm"
        if node.get("status", "").lower() == "wip":
            options += ",draw=namWip,line width=.8pt,fill=namWip!7!namPanel"
        prior = previous.get(root)
        baseline = prior + ".south" if prior else row_anchor + (".south" if row_anchor == "heading" else "")
        lines.append(r"\coordinate (row" + str(index) + r") at (" + baseline + r");")
        # Take y from the previous node but x from the fixed heading origin.
        location = r"($(heading.west |- row" + str(index) + ")+(" + str(origin + x) + r",-0.22)$)"
        title, caption = overview.map_text(node)
        content = r"{\bfseries\color{" + color + "}" + _tex(title) + "}"
        if caption:
            content += r"\\[3pt]{\small\color{namMuted}" + r"\\".join(_tex(line) for line in caption.split('\n')) + "}"
        for item in node.get('versions') or [node]:
            meta = []
            if item.get("status"):
                color = palette.STATUS[item["status"]]
                meta.append(r"\textcolor{" + color + "}{" + _tex(item["status"]) + "}")
            if item.get("priority"):
                priority = str(item["priority"])
                marker = {"p1": "namAccent", "p2": "namMarkerOrange", "p3": "namBabyBlue", "p4": "namPriorityLow"}.get(priority)
                meta.append((r"\textcolor{" + marker + r"}{\textbullet}\ " if marker else "") + _tex(priority))
            if item.get('next'):
                meta.append(r"\mapnext{" + _tex(str(item['next'])) + "}")
            if meta:
                label = _tex(item['label']) + r"\quad " if node.get('versions') else ""
                content += r"\\[4pt]{\footnotesize\color{namMuted}" + label + r"\quad\textbullet\quad ".join(meta) + "}"
        name = "node" + str(index)
        lines.append(r"\node[" + options + "] (" + name + ") at " + location + " {" + content + "};")
        parent = positions.get(node.get("parent", ""))
        if parent:
            lines.append(r"\draw[namLine,line width=.5pt] ([xshift=-3mm]" + name + r".west) |- ([yshift=-1mm]" + parent + r".south west);")
        positions[node["key"]] = name
        previous[root] = name
    lines.extend([r"\end{tikzpicture}", r"\end{document}", ""])
    return "\n".join(lines)
