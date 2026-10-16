"""Presentation of illustrative quips; never writes activity or KR measurements."""

from collections import Counter
from copy import deepcopy
from datetime import date, timedelta
from html import escape
import json
from pathlib import Path
import tempfile

from . import palette
from .publication_links import activity_pdf

PREVIEW = '.yap/cfg/progress-preview.json'
WEEKDAYS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')


def refresh_date(root, value, *, apply=False):
    """Explicitly re-date the illustrative scene; dry run unless requested."""
    from . import content
    end = date.fromisoformat(value)
    if value != end.isoformat():
        raise ValueError('Use YYYY-MM-DD for the demo date.')
    model = content.load(Path(root))  # Includes fixture/domain validation before any write.
    data = deepcopy(model.get('work_preview'))
    if data is None:
        raise ValueError(PREVIEW + ': no illustrative dataset to update.')
    start = date.fromisoformat(data['as_of'])
    delta = end - start
    data['as_of'] = end.isoformat()
    for quip in data['quips']:
        shifted = date.fromisoformat(quip['date']) + delta
        if 'weekday' in quip:
            shifted = end - timedelta(days=(end.weekday() - WEEKDAYS.index(quip['weekday'])) % 7)
        quip['date'] = shifted.isoformat()
    scene = project(dict(model, work_preview=data))
    summary = (f"Demo: {start.isoformat()} -> {end.isoformat()} ({delta.days:+d} days/Tage)\n"
               f"Window / Zeitraum: {scene['days'][0]} – {scene['days'][-1]}\n"
               f"{len(data['quips'])} quips shifted / verschoben; "
               f"{scene['total']} visible / sichtbar; {scene['today']} today / heute.\n"
               'Review weekdays, copy and current activity tracking / Wochentage, Texte und Tracking prüfen.\n')
    if apply and delta.days:
        path = Path(root) / PREVIEW
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix='.progress-preview-', suffix='.tmp', delete=False) as out:
                temporary = Path(out.name)
                out.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return summary + ('Saved / Gespeichert. Run / Danach: make report' if apply else
                      'Preview only / Nur Vorschau. Use --apply to save / Mit --apply speichern.')


def load_preview(root, nodes, key_results=None):
    path = Path(root) / PREVIEW
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or set(data) - {'provenance', 'as_of', 'quips', 'results'} or not {'provenance', 'as_of', 'quips'} <= set(data) or data['provenance'] != 'illustrative-not-collected':
        raise ValueError(PREVIEW + ': expected explicitly illustrative provenance, as_of and quips.')
    end = date.fromisoformat(data['as_of'])
    known, seen = {n['key'] for n in nodes}, set()
    if not isinstance(data['quips'], list):
        raise ValueError(PREVIEW + ': quips must be a list.')
    for row in data['quips']:
        required = {'id', 'activity', 'date', 'kind', 'title'}
        if not isinstance(row, dict) or not required <= set(row) or set(row) - required - {'weekday'} or any(not isinstance(v, str) or not v.strip() for v in row.values()):
            raise ValueError(PREVIEW + ': each quip needs id, activity, date, kind and title.')
        if 'weekday' in row and (row['weekday'] not in WEEKDAYS or
                                WEEKDAYS[date.fromisoformat(row['date']).weekday()] != row['weekday']):
            raise ValueError(PREVIEW + ': weekday must match the quip date (mon–sun).')
        if row['id'] in seen or row['activity'] not in known:
            raise ValueError(PREVIEW + ': duplicate quip ID or unknown activity.')
        if not end - timedelta(days=6) <= date.fromisoformat(row['date']) <= end:
            raise ValueError(PREVIEW + ': quip date must fall within the seven-day window ending at as_of.')
        seen.add(row['id'])
    results = data.get('results', {})
    if not isinstance(results, dict):
        raise ValueError(PREVIEW + ': results must map Objective/KR keys to illustrative outcomes.')
    known_results = {goal + '/' + kr['key']: kr for goal, rows in (key_results or {}).items() for kr in rows}
    for key, result in results.items():
        if key not in known_results or known_results[key]['target'] != 1 or known_results[key]['unit'] == '%':
            raise ValueError(PREVIEW + ': illustrative outcomes require a known binary KR with target 1: ' + key)
        if not isinstance(result, dict) or set(result) != {'reached', 'detail'} or type(result['reached']) is not bool or not isinstance(result['detail'], str) or not result['detail'].strip():
            raise ValueError(PREVIEW + ': each outcome needs a boolean reached and a nonempty detail.')
    return data


def result_view(model):
    """Apply example outcomes only to rendering copies, never to measured source values."""
    examples = (model.get('work_preview') or {}).get('results', {})
    result = {}
    for goal, rows in model.get('key_results', {}).items():
        result[goal] = []
        for kr in rows:
            row = dict(kr)
            example = examples.get(goal + '/' + kr['key'])
            if example is not None and 'current' not in kr:
                row.update(current=int(example['reached']), _presentation_outcome=example)
            result[goal].append(row)
    return result


def project(model):
    data = model.get('work_preview')
    if data is None:
        return None
    end = date.fromisoformat(data['as_of'])
    days = [(end - timedelta(days=i)).isoformat() for i in reversed(range(7))]
    nodes = {n['key']: n for n in model['nodes'] if n.get('kind') == 'activity' and n.get('status') == 'wip'}
    related = {entry for rows in model.get('key_results', {}).values() for kr in rows
               for entry in kr['activities'] if isinstance(entry, str)}
    if model.get('selection', {}).get('key'):
        nodes = {key: node for key, node in nodes.items() if key in related}
    # This illustrative current-work scene never fabricates action on paused work.
    quips = [q for q in data['quips'] if q['activity'] in nodes]
    counts = Counter(q['activity'] for q in quips)
    rows = []
    for key in sorted(counts, key=lambda key: (-counts[key], key)):
        daily = Counter(q['date'] for q in quips if q['activity'] == key)
        rows.append(dict(node=nodes[key], counts=[daily[day] for day in days], total=counts[key], linked=key in related))
    return dict(days=days, rows=rows, quips=quips, today=sum(q['date'] == days[-1] for q in quips),
                focus=sum(nodes[q['activity']].get('priority') == 'p1' for q in quips), total=len(quips))


def _feed(model, scene, key=''):
    nodes = {n['key']: n for n in model['nodes']}
    quips = [q for q in scene['quips'] if not key or q['activity'] == key]
    recent = sorted(enumerate(quips), key=lambda item: (item[1]['date'], item[0]), reverse=True)[:3]
    parts = []
    for _, q in recent:
        node = nodes[q['activity']]
        when = 'Heute' if q['date'] == scene['days'][-1] else date.fromisoformat(q['date']).strftime('%d.%m.')
        parts.append('<li><span class="quip-meta">' + escape(node.get('acronym') or node['title']) +
                     ' <span>· ' + when + ' · ' + escape(q['kind']) + '</span></span><p>' + escape(q['title']) + '</p></li>')
    goals = [g for g in model['goals'] if any(a['key'] == key for a in g['activities'])] if key else []
    if key:
        target = '<a class="quip-source" href="' + escape(activity_pdf(nodes[key]), quote=True) + '">Aktivität ansehen ↗</a>'
    else:
        target = '<span class="quip-source">Eine Aktivität in der Heatmap wählen, um ihre Schritte zu sehen.</span>'
    if goals:
        target += '<p class="quip-goals">Zielbezug: ' + ' · '.join('<a href="#goal-' + escape(g['id'], quote=True) + '">' + escape(g['key'].capitalize()) + '</a>' for g in goals) + '</p>'
    elif key:
        target += '<p class="quip-goals" title="Arbeitsspuren ohne direkte Zuordnung zu einem Ziel oder Key Result">Freie quips</p>'
    return '<ol class="quip-list">' + ''.join(parts) + '</ol>' + target


def render(model):
    scene = project(model)
    if scene is None:
        return ''
    end = date.fromisoformat(scene['days'][-1])
    period = date.fromisoformat(scene['days'][0]).strftime('%d.%m.') + '–' + end.strftime('%d.%m.%Y')
    if not scene['total']:
        return '<section class="work-progress"><p class="work-kicker">' + period + '</p><h2>Deine Arbeit in Bewegung.</h2><p>Für diese Auswahl liegen keine quips vor.</p></section>'
    focus = round(scene['focus'] / scene['total'] * 100)
    leader = scene['rows'][0]['node']
    leader_name = escape(leader.get('acronym') or leader['title'])
    selected = leader['key']
    parts = ['<section class="work-progress" aria-labelledby="work-title"><div class="work-heading"><div>'
             '<p class="work-kicker">Deine Arbeit in Bewegung</p><h2 id="work-title">Das hast <span class="work-you">Du</span> vorangebracht.</h2>'
             '<p>Ein Entwurf wird klarer. Ein Zusammenhang greifbar. Kleine Arbeitsspuren — deine <strong>quips</strong> — zeigen deinen Fortschritt.</p></div>'
             '<span class="work-period">' + period + '</span></div><dl class="work-metrics">'
             '<div><dt>Heute vorangebracht</dt><dd>' + str(scene['today']) + '<span>quips</span></dd><small>' + end.strftime('%d.%m.%Y') + '</small></div>'
             '<div><dt>In Bewegung</dt><dd>' + str(len(scene['rows'])) + '<span>Aktivitäten</span></dd><small>In den letzten 7 Tagen</small></div>'
             '<div><dt>Fokus auf p1</dt><dd>' + str(focus) + '<span>%</span></dd><small>' + str(scene['focus']) + ' von ' + str(scene['total']) + ' quips · 7 Tage</small></div></dl>'
             '<div class="work-detail"><div class="work-map"><div class="work-section-title"><h3>Wo gerade Bewegung entsteht</h3><span>7 Tage</span></div>'
             '<p class="work-insight"><strong>' + leader_name + '</strong> gibt den Takt vor. ' + str(scene['rows'][0]['total']) + ' quips in 7 Tagen.</p>'
             '<div class="heatmap-scroll"><table class="work-heatmap"><caption class="okr-sr-only">Arbeitsspuren je Aktivität und Tag. Helligkeit und Zahl zeigen die Anzahl der quips.</caption>'
             '<thead><tr><th scope="col">Aktivität</th>']
    for day in scene['days']:
        d = date.fromisoformat(day)
        parts.append('<th scope="col"><span>' + ['Mo','Di','Mi','Do','Fr','Sa','So'][d.weekday()] + '</span><small>' + d.strftime('%d.') + '</small></th>')
    parts.append('<th scope="col">Σ</th></tr></thead><tbody>')
    peak = max(n for row in scene['rows'] for n in row['counts'])
    for row in scene['rows']:
        node = row['node']; key = escape(node['key'], quote=True); name = escape(node.get('acronym') or node['title'])
        priority = escape(node.get('priority', ''))
        parts.append('<tr data-work-row="' + key + '"><th scope="row"><button type="button" data-work-select="' + key + '" aria-pressed="' + str(node['key'] == selected).lower() + '" aria-controls="work-feed"><b>' + name + '</b><small><span class="work-status">WIP</span>' + (' · <i class="priority-dot priority-' + priority + '"></i>' + priority if priority else '') + '</small></button></th>')
        for day, count in zip(scene['days'], row['counts']):
            level = 0 if not count else max(1, round(count / peak * 4))
            unassigned = count and not row['linked']
            label = name + ' · ' + day + ': ' + str(count) + ' quips' + (' · Freie quips (f-quips): ohne direkte Zuordnung zu einem Ziel oder Key Result' if unassigned else (' · Gebundene quips (b-quips): mit direkter Zielzuordnung' if count else ''))
            number = ('<span class="quip-unassigned">' + str(count) + '</span>') if unassigned else (str(count) if count else '·')
            parts.append('<td><span class="heat-cell heat-' + str(level) + '" title="' + label + '"' + (' aria-label="' + label + '"' if unassigned else '') + '>' + number + '</span></td>')
        parts.append('<td class="heat-total">' + str(row['total']) + '</td></tr>')
    binding_legend = ('<span class="heat-assignment-legend">'
                      '<span title="Freie quips: ohne direkte Zuordnung zu einem Ziel oder Key Result"><b class="quip-unassigned" aria-hidden="true">●</b> f-quips</span>'
                      '<span title="An Ziele gebundene quips: mit direkter Zuordnung zu einem Ziel oder Key Result"><b class="quip-bound" aria-hidden="true">●</b> b-quips</span></span>')
    parts.append('</tbody></table></div><div class="heat-legend">' + binding_legend + '<span class="heat-scale"><span>Weniger</span>' + ''.join('<i class="heat-cell heat-' + str(i) + '"></i>' for i in range(5)) + '<span>Mehr quips</span></span></div></div>'
                 '<div class="work-recent"><div class="work-section-title"><h3>Schritte, die bleiben</h3><button type="button" class="work-reset">Alle Aktivitäten</button></div><div id="work-feed" aria-live="polite" aria-atomic="true">')
    for key in ['', *[row['node']['key'] for row in scene['rows']]]:
        parts.append('<div data-work-feed="' + escape(key, quote=True) + '"' + (' hidden' if key != selected else '') + '>' + _feed(model, scene, key) + '</div>')
    parts.append('</div></div></div></section><script>' + Path(__file__).with_suffix('.js').read_text() + '</script>')
    return ''.join(parts)


STYLE = palette.css('''
.work-progress{margin:0 0 38px}.work-progress [hidden]{display:none!important}.work-heading{display:flex;justify-content:space-between;gap:28px;align-items:flex-start;margin-bottom:26px}.work-kicker{font-size:.65rem;letter-spacing:.13em;text-transform:uppercase;color:@namPerformance;margin:0 0 7px}.work-heading h2,.work-progress>h2{font-size:clamp(1.65rem,3.6vw,2.5rem);line-height:1.2;letter-spacing:-.04em;margin:0 0 12px}.work-heading p:last-child{max-width:62ch;color:var(--muted);font-size:.88rem;margin:0}.work-heading strong,.work-you{color:@namBrand}.work-period{font-size:.72rem;color:var(--muted);white-space:nowrap;margin-top:8px}.work-metrics{display:grid;grid-template-columns:repeat(3,1fr);margin:0 0 32px;padding:24px 0;border-block:1px solid var(--line)}.work-metrics>div{padding:0 28px;border-left:1px solid var(--line)}.work-metrics>div:first-child{border:0;padding-left:0}.work-metrics dt{font-size:.78rem;color:var(--muted)}.work-metrics dd{margin:4px 0;color:@namPerformance;font-size:clamp(2.4rem,4vw,3.4rem);font-weight:550;line-height:1.2;letter-spacing:-.04em}.work-metrics dd span{font-size:.85rem;font-weight:400;color:var(--muted);letter-spacing:0;margin-left:9px}.work-metrics small{font-size:.68rem;color:var(--muted)}.work-detail{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:38px}.work-section-title{display:flex;align-items:baseline;justify-content:space-between;gap:12px}.work-section-title h3{font-size:.9rem;font-weight:550;margin:0}.work-section-title>span{font-size:.65rem;color:var(--muted)}.work-insight{font-size:.76rem;color:var(--muted);margin:9px 0 16px}.work-insight strong{color:var(--ink);font-weight:500}.work-heatmap{border-collapse:separate;border-spacing:5px;width:100%;font-size:.72rem;table-layout:fixed}.work-heatmap th:first-child{width:110px;text-align:left}.work-heatmap th:last-child{width:26px}.work-heatmap thead th{font-weight:400;color:var(--muted);font-size:.62rem;text-align:center}.work-heatmap thead small{display:block;font-size:.58rem;opacity:.8}.work-heatmap tbody th{padding:0}.work-heatmap button{font:inherit;color:var(--ink);background:none;border:0;border-radius:6px;text-align:left;padding:7px 4px;cursor:pointer;width:100%;min-height:44px}.work-heatmap button b{display:block;font-size:.8rem;font-weight:550;overflow-wrap:anywhere}.work-heatmap button small{display:block;color:var(--muted);font-size:.58rem;margin-top:3px}.work-heatmap .priority-dot{width:5px;height:5px;margin:0 2px 0 1px;vertical-align:1px}.work-status{color:@namWip}.work-heatmap button:hover,.work-heatmap button[aria-pressed=true]{background:color-mix(in srgb,@namBrand 10%,transparent);color:@namBrand}.work-heatmap button:focus-visible,.work-reset:focus-visible{outline:2px solid @namBrand;outline-offset:2px}.heat-cell{display:flex;align-items:center;justify-content:center;width:100%;height:28px;border-radius:4px;font-size:.65rem;font-variant-numeric:tabular-nums}.heat-0{background:color-mix(in srgb,@namPerformance 5%,var(--bg));color:var(--muted)}.heat-1{background:color-mix(in srgb,@namPerformance 19%,var(--bg));color:@namInk}.heat-2{background:color-mix(in srgb,@namPerformance 40%,var(--bg));color:@namInk}.heat-3{background:color-mix(in srgb,@namPerformance 68%,var(--bg));color:@namBg}.heat-4{background:@namPerformance;color:@namBg}.heat-total{text-align:center;color:var(--muted);font-size:.67rem}.heat-legend{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:8px 16px;margin-top:12px;color:var(--muted);font-size:.6rem}.heat-scale{display:inline-flex;align-items:center;gap:4px}.heat-scale>span{margin-inline:4px}.heat-assignment-legend{display:inline-flex;gap:12px;margin-right:auto;white-space:nowrap}.quip-bound{color:@namInk}.quip-unassigned{color:@namUnassignedQuip;font-weight:600}.heat-assignment-legend b{margin-right:4px}.heat-2 .quip-unassigned{color:color-mix(in srgb,@namUnassignedQuip 35%,@namInk)}.heat-3 .quip-unassigned,.heat-4 .quip-unassigned{color:color-mix(in srgb,@namUnassignedQuip 25%,@namBg)}.heat-legend .heat-cell{width:11px;height:11px;border-radius:2px}.work-recent{border-left:1px solid var(--line);padding-left:32px}.quip-list{list-style:none;padding:0;margin:18px 0 12px}.quip-list li{border-top:1px solid var(--line);padding:13px 0}.quip-list li:first-child{border:0;padding-top:0}.quip-meta{font-size:.65rem;color:@namBrand}.quip-meta>span{color:var(--muted)}.quip-list p{font-size:.83rem;line-height:1.5;margin:5px 0 0}.quip-source,.quip-goals{font-size:.7rem;color:var(--muted)}a.quip-source,.quip-goals a{color:@namBrand;text-underline-offset:3px}.work-reset{font:inherit;font-size:.65rem;padding:6px 0;color:@namBrand;border:0;background:none;cursor:pointer;text-decoration:underline;text-underline-offset:3px}.work-goals{border-top:1px solid var(--line);padding-top:18px;margin-top:12px}.work-goals>summary{font-size:.86rem;color:var(--muted);cursor:pointer;min-height:44px;line-height:1.5;padding:8px 0}.work-goals>summary strong{color:var(--ink);font-weight:500}.work-goals>summary:focus-visible{outline:2px solid @namBrand;outline-offset:3px}.work-goals[open]>summary{margin-bottom:16px}
@media(max-width:850px){.work-detail{grid-template-columns:1fr;gap:28px}.work-recent{border:0;border-top:1px solid var(--line);padding:24px 0 0}.work-heading{display:block}.work-period{display:block;margin-top:14px}.work-metrics>div{padding:0 16px}}
@media(max-width:500px){.work-metrics{gap:12px;padding:18px 0}.work-metrics>div{border:0;padding:0}.work-metrics dt{font-size:.65rem}.work-metrics dd span{display:block;margin:5px 0;font-size:.72rem}.work-metrics small{font-size:.6rem;display:block}.work-heatmap{border-spacing:3px}.work-heatmap th:first-child{width:90px}.work-heatmap th:last-child{width:18px}.work-heatmap button b{font-size:.73rem}.heat-cell{height:25px}.work-section-title h3{font-size:.83rem}.work-insight{font-size:.72rem}}
@media print{.work-goals::details-content{content-visibility:visible;display:block}.work-goals>.work-goals-body{display:block!important}.work-recent [hidden]{display:none!important}.work-progress{break-inside:avoid}.work-reset{display:none}}
''')
