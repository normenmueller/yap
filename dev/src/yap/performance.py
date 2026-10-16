"""Validate and present objective-owned KR proposals and recorded measurements."""

from datetime import date
from html import escape
import math
import re

from . import palette, kr_activities, work_progress
from .publication_links import activity_pdf, objective_pdf


def parse(fields, nodes, where):
    """Validate one KR document and its explicit contributions."""
    from .content import metadata
    allowed = {'key', 'title', 'measure', 'unit', 'target', 'current', 'previous', 'activities', 'metric', 'deadline'}
    if set(fields) - allowed:
        raise ValueError(where + ': unknown KR fields: ' + ', '.join(sorted(set(fields) - allowed)) + '.')
    row = {key: metadata(fields, key, where) for key in ('key', 'title', 'measure', 'unit')}
    if not all(row.values()) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', row['key']):
        raise ValueError(f'{where}: a unique KR key, title, measure, and unit are required.')
    for key in ('metric', 'deadline'):
        if key in fields:
            row[key] = metadata(fields, key, where)
            if not row[key]:
                raise ValueError(f'{where}: {key} must not be empty.')
    if 'deadline' in row:
        try:
            date.fromisoformat(row['deadline'])
        except ValueError:
            raise ValueError(f'{where}: deadline requires a date in YYYY-MM-DD format.') from None
    for key in ('target', 'current', 'previous'):
        if key not in fields and key != 'target':
            continue
        try:
            number = float(metadata(fields, key, where))
            if not math.isfinite(number) or number < 0 or (key == 'target' and number == 0):
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError(f'{where}: {key} requires a finite positive number (current and previous may also be 0).') from None
        row[key] = number
    if 'previous' in row and 'current' not in row:
        raise ValueError(f'{where}: previous requires current.')
    row['activities'] = kr_activities.parse(fields.get('activities', {'t': 'MetaList', 'c': []}), nodes, where)
    return row


def load(root, nodes, goals):
    """Discover KR files under folders named for their objective's stable key."""
    from .content import metadata, public_content, read
    folder = root / 'pfo/okr/obj'
    known = {goal['key']: goal for goal in goals}
    result = {}
    for directory in sorted(folder.iterdir()) if folder.exists() else []:
        if directory.name.startswith('.') or not directory.is_dir():
            continue
        where = directory.relative_to(root).as_posix()
        if directory.is_symlink():
            raise ValueError(where + ': symlinks are not KR sources.')
        if directory.name not in known:
            raise ValueError(where + ': KR folder has no matching objective key.')
        entries, keys = [], set()
        for path in sorted(directory.iterdir()):
            if path.name.startswith('.'):
                continue
            where = path.relative_to(root).as_posix()
            if path.is_symlink() or not path.is_file() or path.suffix != '.md':
                raise ValueError(where + ': expected a KR file (*.md); nested folders and symlinks are not supported.')
            doc = public_content(read(path))
            if doc['blocks']:
                raise ValueError(where + ': KR content belongs in YAML fields; use .internal blocks for source-only notes.')
            row = parse(doc['meta'], nodes, where)
            if row['key'] in keys:
                raise ValueError(where + ': duplicate KR key ' + repr(row['key']) + ' within objective ' + directory.name + '.')
            keys.add(row['key'])
            entries.append(row)
        if entries:
            result[directory.name] = entries
    for goal in goals:
        where = goal['path'] + ': kr-sequence'
        order = goal['meta'].get('kr-sequence', {'t': 'MetaList', 'c': []})
        if order['t'] != 'MetaList':
            raise ValueError(where + ': expected a list of KR keys.')
        keys = [metadata({'key': value}, 'key', where) for value in order['c']]
        known_keys = {row['key'] for row in result.get(goal['key'], [])}
        if any(not key or key not in known_keys for key in keys) or len(set(keys)) != len(keys):
            raise ValueError(where + ': unknown, empty, or duplicate KR key.')
        ranks = {key: index for index, key in enumerate(keys)}
        result.get(goal['key'], []).sort(key=lambda row: (ranks.get(row['key'], len(ranks)), row['key']))
    kr_activities.check_link_titles(result)
    return result


def _number(value):
    return f'{value:g}'.replace('.', ',')


def _progress(kr):
    return min(100, kr.get('current', 0)/kr['target']*100)


def _orb(percent, label=''):
    return ('<span class="okr-orb' + (' okr-orb-small' if not label else '') +
            '" style="--sweep:' + str(percent*3.6) + 'deg" aria-hidden="true"><span>' + label + '</span></span>')


def _metric(kr, active):
    measured = active and 'current' in kr
    if active and (outcome := kr.get('_presentation_outcome')) is not None:
        return ('<span class="okr-metric"><span class="okr-metric-label">Ergebnisstand</span>'
                '<span class="okr-result-state">' + _orb(100 if outcome['reached'] else 0) +
                ('Erreicht' if outcome['reached'] else 'Noch offen') + '</span>'
                '<span class="okr-target">' + escape(outcome['detail']) + '</span></span>')
    unit, target = escape(kr['unit']), _number(kr['target'])
    current = _number(kr['current']) if measured else '—'
    delta = ''
    if measured and 'previous' in kr:
        change = kr['current']-kr['previous']
        delta_unit = 'pp' if kr['unit'] == '%' else unit
        delta = ('<span class="okr-delta">' + ('+' if change > 0 else '') + _number(change) +
                 ' ' + delta_unit + '<span class="okr-sr-only"> gegenüber dem vorherigen Messstand</span></span>')
    return ('<span class="okr-metric"><span class="okr-metric-label">' + (escape(kr.get('metric', 'Aktueller Stand')) if active else 'Messung ausgesetzt') +
            '</span><span class="okr-value">' + (_orb(_progress(kr)) if measured else '') + current + ('<small>' if kr['unit'] == '%' else '<small class="okr-unit-block">') + unit + '</small></span>' +
            '<span class="okr-target">Ziel ' + target + ' ' + unit + delta + '</span></span>')


def render(model):
    key_results = work_progress.result_view(model)
    parts = ['<div class="okr-intro"><div><p class="okr-kicker">Vom Ziel zum Beitrag</p>'
             '<h2>Wirkung wird nachvollziehbar.</h2><p>Objectives beschreiben deine Ziele. Key Results machen ihre Erreichung messbar.<br>'
             'Kleine, nachvollziehbare Spuren deiner Arbeit nennen wir <strong>quips</strong>. Sie machen deinen Beitrag zu Aktivitäten und Zielen sichtbar.</p></div>'
             '<div class="okr-chain" aria-label="Objective, Key Result, Aktivität">'
             '<span>Objective</span><b aria-hidden="true">→</b><span>Key Result</span><b aria-hidden="true">→</b><span>Aktivität</span></div></div>']
    labels = {'active': 'Active', 'on hold': 'On hold', 'closed': 'Closed'}
    work = work_progress.render(model)
    if work:
        parts = [work, '<details class="work-goals"><summary><strong>Wozu deine Arbeit beiträgt</strong> · Ziele und Key Results</summary><div class="work-goals-body">']
    for status, label in labels.items():
        goals = [goal for goal in model['goals'] if goal['status'] == status]
        if not goals:
            continue
        parts.append(f'<details class="okr-section okr-{status.replace(" ", "-")}"' + (' open' if status == 'active' or model.get('selection', {}).get('key') else '') +
                     '><summary class="okr-section-heading"><h2>' + label + '</h2><span>' + str(len(goals)) +
                     (' Objective' if len(goals) == 1 else ' Objectives') + '</span><i class="okr-chevron" aria-hidden="true"></i></summary><div class="okr-objectives">')
        for goal in goals:
            krs = key_results.get(goal['key'], [])
            measured_count = sum('current' in kr for kr in krs)
            reached = sum(kr.get('current', -1) >= kr['target'] for kr in krs) if status == 'active' else 0
            key = escape(goal['key'], quote=True)
            parts.append(f'<details class="okr-objective" data-objective="{key}"' +
                         '><summary class="okr-summary"><span class="okr-heading"><span class="okr-kicker">Objective · ' + key +
                         '</span><span class="okr-title">' + escape(goal['title']) + '</span><span class="okr-meta">' + label)
            if goal.get('priority'):
                priority = escape(goal['priority'])
                parts.append(' · <i class="priority-dot priority-' + priority + '" aria-hidden="true"></i>' + priority)
            parts.append(' · ' + str(len(krs)) + ' Key Results</span></span><span class="okr-score">')
            if krs and status == 'active' and measured_count == len(krs):
                parts.append('<span class="okr-metric-label">Ergebnisse erreicht</span><span class="okr-score-orb">' +
                             _orb(reached/len(krs)*100, str(reached) + '<small>/' + str(len(krs)) + '</small>') +
                             '<span>' + str(reached) + ' von ' + str(len(krs)) + '<small>Ergebnissen erreicht</small></span></span><span class="okr-segments" aria-hidden="true">' + ''.join(
                                 '<i><b style="width:' + str(_progress(kr)) + '%"></b></i>' for kr in krs) + '</span>')
            elif krs and status == 'active':
                parts.append('<span class="okr-metric-label">Zielerreichung</span><strong class="okr-paused">' +
                             ('Noch kein Messstand' if not measured_count else 'Messstand unvollständig') +
                             '</strong><span class="okr-meta">Messstand für ' + str(measured_count) + ' von ' +
                             str(len(krs)) + ' Key Results</span>')
            else:
                parts.append('<span class="okr-metric-label">' + ('Key Results' if krs else 'Noch keine Key Results') +
                             '</span><strong class="okr-paused">' + ('Pausiert' if status == 'on hold' else 'Geschlossen' if status == 'closed' else 'Offen') +
                             '</strong><span class="okr-meta">' + ('Kein Zielerreichungswert' if status != 'active' else 'Messstruktur ergänzen') + '</span>')
            parts.append('</span><i class="okr-chevron" aria-hidden="true"></i></summary><div class="okr-objective-body">')
            deadlines = sorted({kr['deadline'] for kr in krs if kr.get('deadline')})
            horizon = ('Zielhorizont · ' + ' / '.join(date.fromisoformat(value).strftime('%d.%m.%Y') for value in deadlines)) if deadlines else ''
            timeframe = 'Zeitraum · ' + escape(goal['timeline']) if goal.get('timeline') else ''
            context = '<br>'.join(value for value in (timeframe, horizon) if value)
            source = ('<a href="' + escape(goal['url'], quote=True) + '">Quelle ↗</a> · ') if goal.get('url') else ''
            parts.append('<div class="okr-context"><span>' + context + '</span><span>' + source + '<a href="' +
                         escape(objective_pdf(goal), quote=True) + '">Zielunterlagen ↗</a></span></div>')
            for index, kr in enumerate(krs):
                active = status == 'active'
                parts.append('<details class="okr-kr" data-kr="' + key + '/' + kr['key'] + '"' +
                             '><summary class="okr-summary">'
                             '<span class="okr-heading"><span class="okr-kicker">KR ' + f'{index+1:02}' + (' · bis ' + date.fromisoformat(kr['deadline']).strftime('%d.%m.%Y') if kr.get('deadline') else '') + '</span>'
                             '<span class="okr-kr-title">' + escape(kr['title']) + '</span></span>' + _metric(kr, active) +
                             '<i class="okr-chevron" aria-hidden="true"></i>')
                if active and 'current' in kr:
                    parts.append('<span class="okr-progress" aria-hidden="true"><b style="width:' + str(_progress(kr)) + '%"></b></span>')
                parts.append('</summary><div class="okr-kr-body"><p class="okr-measure"><span>Woran wir es erkennen</span>' + escape(kr['measure']) + '</p>')
                parts.append('<div class="okr-work-heading"><h4>Beiträge aus deinem Wirkungsfeld</h4></div>' +
                             kr_activities.render(model, kr['activities']) + '</div></details>')
            # Objective links derive only from KR assignments, never from illustrative quips.
            actual = goal.get('activities', [])
            if actual:
                by_key = {node['key']: node for node in model['nodes']}
                parts.append('<p class="okr-confirmed">Mit diesem Objective verbunden: ' + ' · '.join(
                    '<a href="' + escape(activity_pdf(by_key[rel['key']], rel.get('anchor', '')), quote=True) + '">' +
                    escape(by_key[rel['key']].get('acronym') or by_key[rel['key']]['title']) + '</a>'
                    for rel in actual) + '</p>')
            elif not krs:
                parts.append('<p class="empty">Noch keine Key Results oder Aktivitäten zugeordnet.</p>')
            parts.append('</div></details>')
        parts.append('</div></details>')
    if work:
        parts.append('</div></details>')
    return ''.join(parts)


STYLE = palette.css("""
.okr-intro{display:flex;align-items:center;justify-content:space-between;gap:30px;margin:0 0 20px}.okr-intro h2{font-size:1.8rem;letter-spacing:-.035em;margin:3px 0 8px}.okr-intro p{margin:0;max-width:72ch;color:var(--muted);font-size:.9rem}.okr-kicker{display:block;font-size:.65rem;line-height:1.6;letter-spacing:.11em;text-transform:uppercase;color:@namPerformance}.okr-chain{display:flex;align-items:center;gap:10px;white-space:nowrap;color:var(--muted);font-size:.73rem}.okr-chain span{border-bottom:1px solid var(--line);padding:8px 0}.okr-chain b{font-weight:400;color:@namPerformance}

.okr-section{--okr-state:@namGoalActive;margin-bottom:30px}.okr-on-hold{--okr-state:@namHold}.okr-closed{--okr-state:@namGoalClosed}.okr-section-heading{display:flex;align-items:center;gap:12px;color:var(--okr-state);padding:10px 0;list-style:none;cursor:pointer}.okr-section-heading h2{font-size:1.05rem;margin:0}.okr-section-heading>span{font-size:.72rem;color:var(--muted)}.okr-orb{--orb-size:44px;display:inline-grid;place-items:center;width:var(--orb-size);height:var(--orb-size);flex:none;border-radius:50%;background:conic-gradient(@namPerformance var(--sweep),@namLine 0);position:relative;isolation:isolate}.okr-orb::before{content:"";position:absolute;inset:3px;background:var(--panel);border-radius:50%;z-index:-1}.okr-orb>span{font-size:1.05rem;color:@namPerformance;font-weight:500}.okr-orb small{font-size:.65rem;color:var(--muted);margin-left:1px}.okr-orb-small{--orb-size:19px;margin-right:9px;vertical-align:2px}.okr-orb-small::before{inset:2px;background:var(--bg)}.okr-score-orb{display:flex;gap:11px;align-items:center;margin-top:7px}.okr-score-orb>span:last-child{font-size:.85rem;color:@namPerformance}.okr-score-orb>span:last-child>small{display:block;font-size:.62rem;color:var(--muted)}
.okr-result-state{display:block;color:@namPerformance;font-size:1.05rem;font-weight:500;line-height:1.5;margin:4px 0 7px}.okr-section-heading>.okr-chevron{margin-left:auto}.okr-objectives{display:grid;gap:16px;padding-top:8px}.okr-objective{border:1px solid var(--line);border-left:3px solid var(--okr-state);border-radius:12px;background:var(--panel);overflow:hidden;min-width:0}.okr-summary{display:grid;grid-template-columns:minmax(0,1fr) 185px 12px;gap:22px;align-items:center;padding:24px;list-style:none;cursor:pointer;position:relative}.okr-summary:hover{background:color-mix(in srgb,@namPerformance 3%,transparent)}.okr-summary:focus-visible,.okr-section-heading:focus-visible{outline:2px solid @namBrand;outline-offset:-3px;border-radius:8px}.okr-summary::-webkit-details-marker,.okr-section-heading::-webkit-details-marker{display:none}.okr-heading{min-width:0;display:block}.okr-title{display:block;font-size:1.2rem;line-height:1.4;font-weight:600;letter-spacing:-.02em;margin:4px 0 10px}.okr-meta{display:block;font-size:.7rem;color:var(--muted);line-height:1.5}.okr-objective .priority-dot{width:6px;height:6px;margin-right:4px}.okr-score{display:block;padding-left:22px;border-left:1px solid var(--line)}.okr-metric-label{display:block;font-size:.63rem;color:var(--muted);line-height:1.6}.okr-score>strong{display:block;font-size:1.85rem;line-height:1.35;font-weight:500;color:@namPerformance}.okr-score strong small{font-size:1rem;color:var(--muted)}.okr-score .okr-paused{font-size:1.05rem;color:var(--okr-state);margin:7px 0}.okr-segments{display:flex;gap:5px;margin-top:6px}.okr-segments i{flex:1;height:3px;background:var(--line);overflow:hidden;border-radius:2px}.okr-segments b{display:block;height:100%;background:@namPerformance}
.okr-chevron{display:block;width:7px;height:7px;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:rotate(-45deg);color:var(--muted)}details[open]>.okr-summary>.okr-chevron,details[open]>.okr-section-heading>.okr-chevron{transform:rotate(45deg)}.okr-objective-body{border-top:1px solid var(--line);padding:0 20px 20px}.okr-context{display:flex;justify-content:space-between;gap:16px;padding:14px 2px;font-size:.7rem;color:var(--muted)}.okr-context a{white-space:nowrap}.okr-kr{border:1px solid var(--line);border-radius:9px;margin-top:12px;background:var(--bg);overflow:hidden}.okr-kr>.okr-summary{padding:18px 20px;gap:20px;grid-template-columns:minmax(0,1fr) 175px 10px}.okr-kr .okr-kicker{color:var(--muted);font-size:.6rem}.okr-kr-title{display:block;font-size:.94rem;line-height:1.45;font-weight:500;margin-top:5px}.okr-metric{display:block}.okr-value{display:block;color:@namPerformance;font-size:1.65rem;font-weight:500;line-height:1.3;white-space:nowrap}.okr-value small{font-size:.7rem;font-weight:400;color:var(--muted);margin-left:6px;white-space:normal}.okr-value .okr-unit-block{display:block;margin-left:0;overflow-wrap:anywhere}.okr-target{display:block;font-size:.68rem;color:var(--muted)}.okr-delta{display:inline-block;margin-left:10px;color:@namPerformance}.okr-on-hold .okr-value,.okr-closed .okr-value{color:var(--muted)}.okr-progress{position:absolute;bottom:0;inset-inline:0;height:2px;background:var(--line)}.okr-progress b{display:block;height:100%;background:@namPerformance}.okr-kr-body{padding:16px 18px 18px;border-top:1px solid var(--line)}.okr-measure{font-size:.79rem;color:var(--muted);margin:0 0 20px;max-width:85ch}.okr-measure>span{display:block;font-size:.63rem;text-transform:uppercase;letter-spacing:.07em;color:var(--ink);margin-bottom:5px}.okr-work-heading{display:flex;justify-content:space-between;align-items:baseline;gap:14px;margin-bottom:10px}.okr-work-heading h4{font-size:.78rem;font-weight:500;margin:0}.okr-work-heading>span{font-size:.64rem;color:var(--muted)}.kr-references{list-style:none;padding:0;margin:14px 0 0;display:grid;gap:8px}.kr-references li{padding:12px 14px;border:1px solid var(--line);border-radius:8px;background:var(--panel);font-size:.8rem;overflow-wrap:anywhere}.okr-confirmed{margin:20px 2px 0;color:var(--muted);font-size:.7rem}.okr-sr-only{position:absolute;width:1px;height:1px;clip-path:inset(50%);overflow:hidden}
@media(max-width:800px){.okr-intro{display:block}.okr-chain{margin-top:15px}.okr-summary{padding:20px;gap:15px;grid-template-columns:minmax(0,1fr) 155px 10px}.okr-title{font-size:1.05rem}.okr-kr>.okr-summary{grid-template-columns:minmax(0,1fr) 135px 10px}.okr-score{padding-left:15px}}
@media(max-width:550px){.okr-summary,.okr-kr>.okr-summary{grid-template-columns:minmax(0,1fr) 12px;gap:14px;padding:16px}.okr-heading{grid-column:1}.okr-summary>.okr-chevron{grid-column:2;grid-row:1}.okr-score,.okr-metric{grid-column:1;grid-row:2;border:0;padding:0}.okr-score{max-width:190px}.okr-score>strong{font-size:1.6rem}.okr-objective-body{padding:0 10px 12px}.okr-kr-body{padding:14px 10px}.okr-context{flex-wrap:wrap;gap:5px}.okr-work-heading{display:block}.okr-work-heading>span{display:block;margin-top:4px}.okr-title{font-size:1.02rem}.okr-kr-title{font-size:.91rem}.okr-section{margin-bottom:22px}}
@media print{.okr-section::details-content,.okr-objective::details-content,.okr-kr::details-content{content-visibility:visible;display:block}.okr-objective,.okr-kr{break-inside:avoid}}
""")
