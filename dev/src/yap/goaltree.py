"""An offline Objective → KR → Activity explorer with shared activity identity."""

import json
from html import escape
from pathlib import Path

from . import palette, kr_activities
from .publication_links import objective_pdf


def graph_data(model):
    """Project authored KR relationships, preserving shared activity identity."""
    nodes, edges = [], []
    activities = {node['key']: node for node in model['nodes']}
    used = set()
    for goal_index, goal in enumerate(model['goals'], 1):
        goal_index = model.get('goal_numbers', {}).get(goal['key'], goal_index)
        goal_id = 'o:' + goal['key']
        nodes.append(dict(id=goal_id, kind='objective', title=goal['title'], label=f'O {goal_index}',
                          status=goal.get('status', ''), url=objective_pdf(goal)))
        for index, kr in enumerate(model.get('key_results', {}).get(goal['key'], []), 1):
            kr_id = 'kr:' + goal['key'] + '/' + kr['key']
            nodes.append(dict(id=kr_id, kind='kr', title=kr['title'],
                              label=f'KR {index}', measure=kr['measure']))
            edges.append([goal_id, kr_id])
            for position, entry in enumerate(kr.get('activities', [])):
                activity = kr_activities.project(entry, goal['key'] + '/' + kr['key'], position, activities)
                activity_id = activity['id']
                edges.append([kr_id, activity_id])
                if activity_id not in used:
                    used.add(activity_id)
                    nodes.append(dict(kind='activity', **activity))
    return dict(nodes=nodes, edges=edges)


STYLE = palette.css('''
.explorer [hidden]{display:none!important}
.explorer-description{position:absolute;width:1px;height:1px;clip-path:inset(50%);overflow:hidden}
.explorer-intro{color:var(--muted);max-width:75ch;margin:0 0 16px}
.explorer-toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px}
.explorer-filters{display:flex;flex-wrap:wrap;gap:4px;font-size:.8rem}
.explorer-filters label{padding:8px 10px;border-radius:7px;color:var(--muted);min-height:44px;display:flex;align-items:center;gap:7px;cursor:pointer}
.explorer-filters label:has(input:checked){background:var(--panel);color:var(--ink)}
.explorer-filters label:has(input:disabled){opacity:.45;cursor:default}
.explorer-filters input{accent-color:var(--accent)}
.explorer-toolbar button,.explorer-toggle{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:8px;cursor:pointer;min-height:44px}
.explorer-toolbar button{padding:8px 14px;font-size:.85rem}
.explorer-toolbar [data-action=collapse]{margin-left:auto}
.explorer-toolbar button:disabled{opacity:.45;cursor:default}
.explorer-zoom{display:flex;align-items:center;gap:4px;margin-left:auto}.explorer-zoom button{padding:5px 10px;min-width:36px;font-size:.75rem}.explorer-zoom [data-action=zoom-reset]{min-width:56px;font-variant-numeric:tabular-nums}.explorer-toolbar .explorer-zoom+[data-action=collapse]{margin-left:0}
.explorer-toolbar button:hover,.explorer-toggle:hover{border-color:var(--accent);color:var(--accent)}
.explorer-zoom button[aria-pressed=true]{border-color:var(--accent);color:var(--accent)}
.explorer button:focus-visible,.explorer-viewport:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.explorer-status{color:var(--muted);font-size:.8rem}
.explorer-viewport{overflow:auto;border:1px solid var(--line);border-radius:14px;background:var(--bg);max-height:80vh;overscroll-behavior-x:contain}
.explorer-canvas{position:relative;overflow:hidden;min-height:1px}.explorer-stage{position:absolute;top:0;left:0;min-height:220px;transform-origin:0 0}
.explorer-stage svg{position:absolute;inset:0;pointer-events:none;overflow:visible}
.explorer-edge{fill:none;stroke:var(--muted);stroke-width:1.5;opacity:.55}
.explorer-edge.is-highlighted{stroke:var(--accent);stroke-width:2.5;opacity:1}
.explorer-stage.has-highlight .explorer-edge:not(.is-highlighted){opacity:.38}
.explorer-level{position:absolute;left:24px;color:var(--muted);font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;margin:0}
.explorer-node{position:absolute;display:flex;flex-direction:column;width:232px;padding:15px;background:var(--panel);border:1px solid var(--line);border-radius:11px;overflow-wrap:anywhere;border-top:3px solid @namPerformance}
.explorer-node[data-kind=kr]{border-top-color:@namBrand}
.explorer-node[data-kind=activity]{border-top-color:@namActivities}
.explorer-node[data-status="on hold"]{border-top-color:@namHold}
.explorer-node[data-status=closed]{border-top-color:@namGoalClosed}
.explorer-node.is-highlighted{outline:1px solid var(--accent);outline-offset:2px}
.explorer-node h3{font-size:.9rem;line-height:1.45;margin:8px 0 12px;text-align:left;hyphens:auto;word-break:normal}
.explorer-kicker{font-size:.7rem;color:var(--muted);letter-spacing:.03em}
.explorer-node-footer{display:flex;gap:8px;align-items:center;justify-content:space-between;font-size:.75rem;color:var(--muted);margin-top:auto;min-height:44px;flex-shrink:0}
.explorer-toggle{padding:4px 10px;font-size:.75rem}
.explorer-node a{font-size:.75rem}
.explorer-empty{padding:24px;color:var(--muted)}
@media print{#graph-panel{display:none!important}}
''')


def render(model):
    # Escape HTML delimiters even inside JSON strings in the raw-text script element.
    data = json.dumps(graph_data(model), ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    script = Path(__file__).with_suffix('.js').read_text(encoding='utf-8')
    available = {goal.get('status', '') for goal in model['goals']}
    filters = ''.join(
        '<label><input type="checkbox" data-status-filter value="' + escape(status, quote=True) +
        '"' + (' checked' if status in available else ' disabled') + '>' + label + '</label>'
        for status, label in [('active', 'Active'), ('on hold', 'On hold'), ('closed', 'Closed')])
    return '''<div class="explorer" id="goal-explorer">
<p class="explorer-intro">Vom Ziel zum Beitrag: Öffne ein Objective und dann seine Key Results per Doppelklick oder über +.
Gemeinsame Beiträge erscheinen einmal und verbinden die geöffneten Key Results.</p>
<div class="explorer-toolbar" hidden><div class="explorer-filters" role="group" aria-label="Zielstatus / Objective status">
<button type="button" data-action="all-statuses">Alle</button>''' + filters + '''</div>
<span class="explorer-status" role="status" aria-live="polite"></span>
<div class="explorer-zoom" role="group" aria-label="Graph-Zoom / Graph zoom">
<button type="button" data-action="zoom-out" aria-label="Verkleinern / Zoom out" title="Verkleinern (−)">−</button>
<button type="button" data-action="zoom-reset" aria-label="Originalgröße / Reset to 100 percent" title="Originalgröße (0)">100%</button>
<button type="button" data-action="zoom-in" aria-label="Vergrößern / Zoom in" title="Vergrößern (+)">+</button>
<button type="button" data-action="zoom-fit" aria-pressed="false" title="Gesamten geöffneten Graphen einpassen (F)">Einpassen</button>
</div>
<button type="button" data-action="collapse">Alles einklappen</button></div>
<noscript><p>Die interaktive Ansicht Zusammenhänge benötigt JavaScript. Ziele und Fortschritt stehen ohne JavaScript zur Verfügung.</p></noscript>
<div class="explorer-viewport" tabindex="0" role="region" aria-label="Zusammenhänge, bei Bedarf seitlich verschieben" hidden>
<div class="explorer-canvas"><div class="explorer-stage"></div></div></div>
<script type="application/json" id="goal-explorer-data">''' + data + '</script>\n<script>' + script + '</script>'
