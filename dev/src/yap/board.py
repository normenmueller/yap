"""Status columns and area lanes, shared by the offline HTML and PNG board."""

from html import escape
from pathlib import Path

from . import footer, palette, navigation, overview, selections
from .views import _tex
from .publication_links import activity_pdf


COLUMNS = (("ibx", "ibx · Icebox"), ("wip", "WIP"),
           ("on hold", "On hold"), ("released", "Released"))
STATUS_COLORS = {status: palette.HEX[token] for status, token in palette.STATUS.items()}
STATUS_COLORS[''] = palette.HEX['namMuted']
PRIORITIES = {"p1": 1, "p2": 2, "p3": 3, "p4": 4}
DOTS = {"p1": "namAccent", "p2": "namMarkerOrange", "p3": "namBabyBlue", "p4": "namPriorityLow"}
TONES = {"ace": "namViolet", "gov": "namOrange", "imp": "namGreen",
         "ops": "namGreen", "sup": "namViolet"}
INTRO = {
    'sup': ('Support', 'Voraussetzungen schaffen — Methoden, Werkzeuge, Fähigkeiten.'),
    'imp': ('Impact', 'Diese Fähigkeiten einsetzen und Wirkung erzielen.'),
    'gov': ('Governance', 'Orientierung, Kohärenz und Verlässlichkeit sichern.'),
}
LANE_CAPTIONS = {'sup': 'Voraussetzungen schaffen', 'imp': 'Wirkung erzielen',
                 'gov': 'Orientierung & Verlässlichkeit sichern'}


def impact_direction(rows, key):
    keys = [lane['key'] for lane in rows]
    target = next((lane.get('toward', '') for lane in rows if lane['key'] == key), '')
    if target not in keys:
        return ''
    return 'down' if keys.index(key) < keys.index(target) else 'up'


def rail_caption(lane):
    return (LANE_CAPTIONS.get(lane['key'], '')
            if lane['kind'] == 'category' and lane.get('show_rail_caption', True) else '')


def rail_text(lane):
    text = _tex(lane['title'])
    if caption := rail_caption(lane):
        text += r'\\[3pt]{\footnotesize\normalfont\color{namMuted}' + _tex(caption) + '}'
    return text


def intro_items(rows):
    """Describe visible categories; both enabling roles point toward Impact."""
    if any(lane['key'] not in INTRO for lane in rows):
        return
    previous = None
    for lane in rows:
        key = lane['key']
        if key not in INTRO:
            continue
        arrow = ('→' if key == 'imp' else '←' if previous == 'imp' else '') if previous else ''
        yield lane, arrow
        previous = key


def activity_cards(node):
    """Keep activity identity; only the card's version, tracking and PDF target vary."""
    card = {field: node[field] for field in ('key', 'id', 'title', 'status', 'priority')}
    card.update(title=node.get('acronym') or node['title'], context='',
                caption=node.get('board-caption', ''), version='', next=node.get('next'))
    if not node.get('versions'):
        return [card]
    return [dict(card, id=node['id'] + '--' + version['anchor'],
                 version=version['label'], status=version['status'], priority=version['priority'],
                 next=version.get('next'))
            for version in node['versions']]


def card_title(card):
    label = escape(card['title'])
    if card.get('version'):
        label += ' <span class="card-version">' + escape(card['version']) + '</span>'
    return label


def priority_label(card):
    """Priority applies only to unreleased work; release validation owns the constraint."""
    return '' if card['status'] == 'released' else card['priority'] or 'Ohne Prio'


def priority_marker(card, css_class='priority'):
    """Only the dot is visible; retain the meaning for hover and assistive technology."""
    label = priority_label(card)
    if not label:
        return ''
    label = 'Priorität ' + label if card['priority'] else label
    dot = ('<i style="background:#' + palette.HEX[DOTS[card['priority']]] +
           '" aria-hidden="true"></i>') if card['priority'] in DOTS else ''
    return ('<span class="' + css_class + '" role="img" title="' + escape(label, quote=True) +
            '" aria-label="' + escape(label, quote=True) + '">' + dot + '</span>')


def next_marker(card):
    """Keep the global resumption number unchanged in filtered boards."""
    if not card.get('next'):
        return ''
    rank = str(card['next'])
    label = 'Als Nächstes: ' + rank
    return ('<span class="next-marker" role="img" title="' + label +
            '" aria-label="' + label + '">' + rank + '</span>')


def lanes(model):
    """Pivot explicit presentation categories; canonical entries own every card."""
    sources = {node['key']: node for node in model['nodes']}
    report = model.get('board_report', model['report'])
    placements = report['nodes']
    by_id = {node['placement']: node for node in placements}
    categories, containers = {}, {}
    tones = {'support': 'namViolet', 'impact': 'namGreen', 'governance': 'namOrange',
             'epistemics': 'namEpistemics', 'strategy': 'namStrategy', 'neutral': 'namMuted'}

    def group(key, title, tone, kind='lane', caption=''):
        return dict(key=key, title=title, tone=tone, kind=kind, caption=caption,
                    cells={status: [] for status, _ in (('', 'Ohne Status'), *COLUMNS)}, sublanes=[])

    def chain(placement):
        result = []
        while placement:
            result.insert(0, placement)
            placement = by_id.get(placement['parent'])
        return result

    for placement in placements:
        source = sources.get(placement['entry'])
        mode = placement['board_card']
        if not source or mode == 'never' or (mode == 'tracked' and not (
                source['status'] or source['priority'] or source.get('versions'))):
            continue
        ancestors = chain(placement)
        category_key = placement['category'] or 'all'
        category_node = next((node for node in ancestors if node['role'] == 'category'), None)
        if category_key not in categories:
            category = group(category_key, category_node['title'] if category_node else 'Aktivitäten',
                             tones.get(category_node['tone'] if category_node else 'neutral', 'namMuted'), 'category')
            category['toward'] = next((b for a, b in report['flow'] if a == category_key), '')
            category['show_rail_caption'] = category_node.get('board_rail_caption', True) if category_node else True
            categories[category_key] = category
        lane = categories[category_key]
        context = by_id.get(placement['context'])
        if context:
            context_key = (category_key, context['placement'])
            if context_key not in containers:
                child = group(context['placement'], context['label'], lane['tone'], 'context')
                child['description'] = context['title']
                lane['sublanes'].append(child)
                containers[context_key] = child
            lane = containers[context_key]
        for ancestor in ancestors:
            if ancestor['role'] not in {'lane', 'group'}:
                continue
            identifier = ancestor['placement']
            lane_key = (category_key, identifier)
            if lane_key not in containers:
                content = sources.get(ancestor['entry'], {})
                child = group(identifier, content.get('acronym') or ancestor['title'],
                              tones.get(ancestor['tone'], lane['tone']),
                              caption=content.get('board-caption', ''))
                child['vertical_label'] = ancestor.get('board_label') == 'vertical'
                lane['sublanes'].append(child)
                containers[lane_key] = child
            lane = containers[lane_key]
        for card in activity_cards(source):
            lane['cells'][card['status']].append(card)

    def sort_cards(lane):
        for cards in lane['cells'].values():
            cards.sort(key=lambda card: (card.get('next') or 4, PRIORITIES.get(card['priority'], 5)))
        for child in lane['sublanes']:
            sort_cards(child)
    for category in categories.values():
        sort_cards(category)
    ranks = {key: index for index, key in enumerate(report['category_order'])}
    return sorted(categories.values(), key=lambda lane: ranks.get(lane['key'], len(ranks)))


def display_rows(lanes):
    """Flatten only for measuring; retain the complete enclosing lane path."""
    def visit(lane, path):
        path = [*path, lane]
        if any(lane['cells'].values()):
            terminal = lane['kind'] == 'lane' and not lane['sublanes'] and not lane.get('vertical_label')
            yield dict(lane, rails=path[:-1] if terminal else path,
                       label=lane if terminal else None)
        for child in lane['sublanes']:
            yield from visit(child, path)
    for lane in lanes:
        yield from visit(lane, [])


def columns(rows):
    """Unassigned is a presentation of missing tracking, never an inferred status."""
    return ((('', 'Ohne Status'), *COLUMNS) if any(row['cells'].get('')
            for row in display_rows(rows)) else COLUMNS)


STYLE = palette.css("""
.card>.next-marker{grid-area:2/2;align-self:end;justify-self:end;display:flex;align-items:center;justify-content:center;width:18px;height:18px;border:1px solid @namMuted;border-radius:50%;color:@namMuted;font-size:.65rem;line-height:1;font-weight:500}
.card-version{margin-left:.35em;font-size:.72em;font-weight:400;color:@namMuted}
:root{color-scheme:dark;--bg:@namBg;--panel:@namBoardPanel;--ink:@namInk;--muted:@namMuted;--line:@namLine;--accent:@namBrand}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1720px;margin:auto;padding:36px 24px}h1{font-size:2.4rem;margin:0}p{color:var(--muted)}a{color:var(--accent);text-underline-offset:3px}a:hover{color:var(--ink)}a:focus-visible,.board:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.legend{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px 24px;margin:24px 4px 8px;font-size:.85rem;color:var(--muted)}.legend>span{white-space:nowrap}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px}.p1{background:@namAccent}.p2{background:@namMarkerOrange}.p3{background:@namBabyBlue}.p4{background:@namPriorityLow}
.board{overflow-x:auto}.board-sheet{position:relative;min-width:1320px;--rail:42px;--labels:310px}.status-head,.board-row{display:grid;grid-template-columns:var(--remaining,var(--labels)) repeat(var(--status-count,5),minmax(0,1fr))}.status-head{min-height:46px;align-items:center;font-weight:650}.status-head>div{padding:10px 14px}.status-head .status{margin:0 4px;border-radius:7px 7px 0 0;background:color-mix(in srgb,var(--status) 12%,var(--bg))}.column-frames{position:absolute;inset:0 0 0 var(--labels);display:grid;grid-template-columns:repeat(var(--status-count,5),minmax(0,1fr));pointer-events:none;z-index:2}.column-frames>span{margin:0 4px;border:1.5px solid var(--status);border-radius:7px}.lane{--rail:42px;position:relative;display:grid;grid-template-columns:var(--rail) minmax(0,1fr);background:var(--lane)}.lane::after{content:"";position:absolute;inset:4px 5px;border:1px solid @namFrame;border-radius:6px;pointer-events:none}.lane.category{--rail:52px;margin-top:10px}.lane.category::after{border-color:color-mix(in srgb,var(--tone) 65%,var(--bg))}.lane.context+.lane.context{margin-top:8px}.lane.context::after{border-color:@namContextFrame}.lane-body{min-width:0;padding:5px 0}.lane-rail{display:flex;align-items:center;justify-content:center;margin:5px 0;border-right:1px solid @namLine;min-height:80px}.rail-label{writing-mode:vertical-rl;transform:rotate(180deg);white-space:nowrap;padding:10px 0;font-size:.82rem;font-weight:650;color:var(--tone)}.context>.lane-rail .rail-label{font-size:.68rem;letter-spacing:.12em;color:var(--ink)}.lane-namViolet{--lane:@namVioletFill;--tone:@namBrand}.lane-namOrange{--lane:@namOrangeFill;--tone:@namGovernance}.lane-namGreen{--lane:@namGreenFill;--tone:@namGreen}.lane-namMuted{--lane:@namMutedFill;--tone:@namMuted}.lane-namEpistemics{--lane:@namEpistemicsFill;--tone:@namEpistemics}.namEpistemics{color:@namEpistemics}.namViolet{color:@namBrand}.namOrange{color:@namGovernance}.namGreen{color:@namGreen}.namMuted{color:var(--muted)}.board-row{position:relative;min-height:86px}.board-row.labelled{background:color-mix(in srgb,var(--lane) 55%,var(--bg))}.board-row.labelled::after{content:"";position:absolute;inset:4px 5px;border:1px solid @namFrame;border-radius:5px;pointer-events:none}.project-label{display:flex;align-items:center;padding:12px 14px}.area-title{display:block;padding:4px 0 4px 10px;border-left:2px solid var(--tone);font-size:.95rem;font-weight:650;color:var(--tone)}.lane-caption,.card-caption{display:block;margin-top:4px;font-size:.68rem;line-height:1.35;font-weight:400;white-space:pre-line;color:var(--muted)}.status-cell{display:flex;align-items:flex-start;padding:12px 16px}.cards{list-style:none;margin:0;padding:0;width:100%;display:grid;gap:6px;justify-items:center}.card{display:grid;grid-template-rows:minmax(var(--card-title-height,1.3rem),max-content) minmax(var(--card-caption-height,1.836rem),max-content);grid-template-columns:minmax(0,1fr) 18px;gap:4px 6px;align-content:start;box-sizing:border-box;background:var(--panel);border:1px solid @namCardLine;border-radius:6px;padding:8px 10px;width:100%;max-width:240px;overflow-wrap:anywhere}.card>a{grid-area:1/1;min-width:0;display:block;color:var(--ink);font-weight:600;text-decoration:none;line-height:1.3}.card>a:hover{text-decoration:underline}.card>.card-caption{grid-area:2/1;min-width:0;margin:0}.card>.priority{grid-area:1/2;align-self:start;justify-self:center;display:flex;align-items:center;justify-content:center;height:1.3rem}.priority i{display:block;width:8px;height:8px;border-radius:50%}footer{color:var(--muted);font-size:.8rem;margin-top:20px}
.area-intro{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:32px;max-width:850px;margin:24px 0}.area-intro>div{position:relative;border-left:2px solid currentColor;padding-left:12px}.area-intro dt{font-size:.9rem;font-weight:650;margin-bottom:5px}.area-intro dd{margin:0;color:var(--muted);font-size:.82rem;line-height:1.55}.relation-arrow{position:absolute;left:-26px;top:0;color:var(--muted);font-weight:400}
.category>.lane-rail{position:relative;padding:28px 0}.category>.lane-rail .rail-label{padding:0;text-align:center;font-size:.9rem}.rail-caption{display:block;margin-block-start:4px;font-size:.64rem;font-weight:400;color:var(--muted)}.impact-arrow{position:absolute;left:50%;transform:translateX(-50%);font-size:1.25rem;line-height:1;color:var(--tone)}.impact-arrow.down{bottom:6px}.impact-arrow.up{top:6px}
@media(max-width:650px){.area-intro{grid-template-columns:1fr;gap:30px;margin:20px 0}.relation-arrow{left:10px;top:-28px;transform:rotate(90deg)}}
.lane-toggle{display:flex;align-items:center;justify-content:center;align-self:stretch;width:100%;border:0;padding:0;background:none;color:inherit;font:inherit;cursor:pointer}.lane-toggle:focus-visible{outline:2px solid var(--accent);outline-offset:-3px}.lane-chevron{position:absolute;top:12px;left:calc(50% - 4px);width:8px;height:8px;border-right:1.5px solid var(--tone);border-bottom:1.5px solid var(--tone);transform:rotate(45deg)}.lane.category.collapsed{display:block}.category.collapsed>.lane-rail{padding:14px 18px;min-height:0;border:0}.collapsed>.lane-rail .lane-toggle{justify-content:flex-start}.collapsed>.lane-rail .rail-label{writing-mode:horizontal-tb;transform:none;text-align:left}.collapsed>.lane-rail .rail-caption,.collapsed>.lane-rail .impact-arrow{display:none}.collapsed>.lane-rail .lane-chevron{top:calc(50% - 4px);left:auto;right:18px;transform:rotate(-45deg)}
@media print{.lane.category.collapsed{display:grid}.category.collapsed>.lane-body[hidden]{display:block}.category.collapsed>.lane-rail{padding:28px 0;border-right:1px solid var(--line);min-height:80px}.collapsed>.lane-rail .rail-label{writing-mode:vertical-rl;transform:rotate(180deg);text-align:center}.collapsed>.lane-rail .rail-caption{display:block}.collapsed>.lane-rail .lane-toggle{justify-content:center}.lane-chevron{display:none}}
@media(max-width:650px){main{padding:24px 12px}}@media print{main{padding:0}.board{overflow:visible}nav{display:none}}
""")


FOLD_SCRIPT = """<script>
document.querySelectorAll('.board-sheet > .lane.category').forEach((lane, index) => {
    const rail = lane.querySelector(':scope > .lane-rail');
    const body = lane.querySelector(':scope > .lane-body');
    body.id = 'board-lane-' + index;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'lane-toggle';
    button.setAttribute('aria-expanded', 'true');
    button.setAttribute('aria-controls', body.id);
    button.setAttribute('aria-label', lane.getAttribute('aria-label'));
    while (rail.firstChild) button.append(rail.firstChild);
    const chevron = document.createElement('span');
    chevron.className = 'lane-chevron';
    chevron.setAttribute('aria-hidden', 'true');
    button.append(chevron);
    rail.append(button);
    button.addEventListener('click', () => {
        const collapsed = button.getAttribute('aria-expanded') === 'true';
        button.setAttribute('aria-expanded', String(!collapsed));
        body.hidden = collapsed;
        lane.classList.toggle('collapsed', collapsed);
    });
});
</script>"""


def render_html(rows, destination, *, selection=None):
    shown_columns = columns(rows)
    status_style = ''.join('.status-' + status.replace(' ', '-') + '{--status:#' + color + '}'
                           for status, color in STATUS_COLORS.items())
    parts = ['<!doctype html><html lang="de"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             navigation.head('board'), '<style>', STYLE, navigation.STYLE + footer.STYLE, status_style, '</style></head><body class="yap-page">',
             navigation.render('board', theme='dark', selection=selection,
                               exports=(('Board · PNG', 'views/activity-board/' + selections.filename(selection, 'board.png')),)),
             '<main>',
             '<header class="board-header"><div class="board-intro"><h1>Activity Board' +
             (' · ' + escape(selection['label']) if selection and selection['key'] else '') + '</h1>',
             '<p>Aktivitäten nach Status und Bereich. Höhere Prioritäten stehen oben.</p>']
    intro = list(intro_items(rows))
    if intro:
        parts.append('<dl class="area-intro" aria-label="Support und Governance unterstützen Impact">')
        for lane, arrow in intro:
            title, description = INTRO[lane['key']]
            relation = '<span class="relation-arrow" aria-hidden="true">' + arrow + '</span>' if arrow else ''
            parts.append('<div class="' + lane['tone'] + '"><dt>' + relation + escape(title) +
                         '</dt><dd>' + escape(description) + '</dd></div>')
        parts.append('</dl>')
    parts.append('</div>')
    shown = list(display_rows(rows))
    rail_count = max((len(row['rails']) for row in shown), default=2)
    label_width = 184 + 42*rail_count + 10
    parts.append('</header>')
    parts.extend([
             '<div class="legend" aria-label="Prioritäten">',
             '<span><i class="dot p1" aria-hidden="true"></i>p1</span>',
             '<span><i class="dot p2" aria-hidden="true"></i>p2</span>',
             '<span><i class="dot p3" aria-hidden="true"></i>p3</span>',
             '<span><i class="dot p4" aria-hidden="true"></i>p4</span></div>'])
    parts.extend(['<div class="board" tabindex="0" role="region" aria-label="Statusboard mit horizontaler Bildlaufleiste">',
                  '<div class="board-sheet" style="--labels:' + str(label_width) + 'px;--status-count:' + str(len(shown_columns)) + '">',
                  '<div class="column-frames" aria-hidden="true">'])
    parts.extend('<span class="status-' + status.replace(' ', '-') + '"></span>' for status, _ in shown_columns)
    parts.append('</div><div class="status-head"><div>Bereich / Aktivität</div>')
    parts.extend('<div class="status status-' + status.replace(' ', '-') + '">' + label + '</div>'
                 for status, label in shown_columns)
    parts.append('</div>')

    def render_row(lane, depth, label):
        parts.append('<div class="board-row' + (' labelled' if label else '') + ' lane-' + lane['tone'] + '" data-lane="' + escape(lane['key'], quote=True) +
                     '" style="--remaining:calc(var(--labels) - ' + str(42*depth + (10 if depth else 0)) + 'px)">')
        caption = ('<span class="lane-caption">' + escape(lane['caption']) + '</span>') if lane['caption'] else ''
        parts.append('<div class="project-label">' + ('<span class="area-title">' +
                     escape(lane['title']) + caption + '</span>' if label else '') + '</div>')
        for status, status_label in shown_columns:
            parts.append('<div class="status-cell" aria-label="' + status_label + '"><ul class="cards">')
            for card in lane['cells'][status]:
                parts.append('<li class="card" data-activity="' + escape(card['key'], quote=True) + '">')
                parts.append('<a href="' + escape(activity_pdf(card), quote=True) + '">' + card_title(card) + '</a>')
                if card['caption']:
                    parts.append('<span class="card-caption">' + escape(card['caption']) + '</span>')
                parts.append(priority_marker(card))
                parts.append(next_marker(card))
                parts.append('</li>')
            parts.append('</ul></div>')
        parts.append('</div>')

    def render_lane(lane, depth=0):
        if lane['kind'] == 'lane' and not lane['sublanes'] and not lane.get('vertical_label'):
            render_row(lane, depth, True)
            return
        parts.append('<section class="lane ' + lane['kind'] + ' lane-' + lane['tone'] +
                     '" data-group="' + escape(lane['key'], quote=True) + '" aria-label="' +
                     escape(lane.get('description', lane['title']), quote=True) + '">')
        caption, arrow = '', ''
        if lane['kind'] == 'category':
            if text := rail_caption(lane):
                caption = '<span class="rail-caption">' + escape(text) + '</span>'
            direction = impact_direction(rows, lane['key'])
            if direction:
                arrow = '<span class="impact-arrow ' + direction + '" role="img" aria-label="Unterstützt Impact">' + ('↓' if direction == 'down' else '↑') + '</span>'
        parts.append('<div class="lane-rail"><span class="rail-label">' + escape(lane['title']) +
                     caption + '</span>' + arrow + '</div><div class="lane-body">')
        if any(lane['cells'].values()):
            render_row(lane, depth+1, False)
        for child in lane['sublanes']:
            render_lane(child, depth+1)
        parts.append('</div></section>')

    for lane in rows:
        render_lane(lane)
    if not rows:
        parts.append('<p>Noch keine Aktivitäten vorhanden.</p>')
    parts.append('</div></div></main>' + footer.render() + FOLD_SCRIPT + '</body></html>')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / selections.filename(selection)).write_text(''.join(parts), encoding='utf-8')


def card_tex_parts(card):
    title = _tex(card['title'])
    if card.get('version'):
        title += r'\ {\normalfont\scriptsize\color{namMuted}' + _tex(card['version']) + '}'
    caption = r'\\'.join(_tex(line) for line in card['caption'].splitlines())
    priority = ''
    if priority_label(card) and card['priority'] in DOTS:
        priority = r'\textcolor{' + DOTS[card['priority']] + r'}{\textbullet}'
    return title, caption, priority


def tex(rows, *, title='Activity Board'):
    """Measure cards and enclosing rails with the same hierarchy as HTML."""
    shown_columns = columns(rows)
    shown = list(display_rows(rows))
    rail_count = max((len(row['rails']) for row in shown), default=2)
    rail_width, category_extra, column_width = 1.0, .25, 6.2
    lane_width = rail_count*rail_width + category_extra + 4.8
    width = lane_width + len(shown_columns)*column_width
    lines = [r'\documentclass[tikz,border=14pt]{standalone}', r'\input{theme.tex}',
             r'\newsavebox{\boardcaption}', r'\usetikzlibrary{calc,backgrounds}',
             r'\colorlet{namPanel}{namBoardPanel}\colorlet{boardFrame}{namFrame}',
             r'\colorlet{boardCardLine}{namCardLine}', r'\pagecolor{namBg}',
             r'\begin{document}', r'\hyphenpenalty=10000\exhyphenpenalty=10000',
             r'\sffamily\fontsize{11}{13}\selectfont',
             r'\newdimen\boardtitleheight\boardtitleheight=13pt',
             r'\newdimen\boardcaptionheight\boardcaptionheight=18pt',
             r'\newcommand{\measureboardslot}[4]{\setbox0=\vbox{\hsize=#2\parindent=0pt\raggedright#3\strut #4\strut\par}\ifdim\dimexpr\ht0+\dp0\relax>#1 #1=\dimexpr\ht0+\dp0\relax\fi}',
             r'\newcommand{\boardslot}[4]{\vbox to #1{\hsize=#2\parindent=0pt\raggedright#3\strut #4\strut\par\vfil}}',
             r'\newcommand{\boardnext}[1]{\tikz[baseline=(n.base)]{\node[circle,draw=namMuted,text=namMuted,inner sep=0pt,minimum size=10pt,font=\scriptsize] (n) {#1};}}',
             r'\newcommand{\boardheading}[2]{\hbox to 4.8cm{\boardslot{\boardtitleheight}{4.2cm}{\bfseries}{#1}\hfil\boardslot{\boardtitleheight}{.4cm}{\normalfont\centering}{#2}}}',
             r'\newcommand{\boardcaptionrow}[2]{\hbox to 4.8cm{\boardslot{\boardcaptionheight}{4.2cm}{\scriptsize\color{namMuted}}{#1}\hfil\vbox to \boardcaptionheight{\vfil\hbox to .4cm{\hfil #2\hfil}\kern0pt}}}']
    slots = ((r'\boardtitleheight', '4.2cm', r'\bfseries'),
             (r'\boardcaptionheight', '4.2cm', r'\scriptsize\color{namMuted}'))
    for row in shown:
        for cards in row['cells'].values():
            for card in cards:
                for (height, slot_width, font), value in zip(slots, card_tex_parts(card)):
                    lines.append(r'\measureboardslot{' + height + '}{' + slot_width + '}{' + font + '}{' + value + '}')
    lines.extend([
             r'\begin{tikzpicture}[font=\sffamily\fontsize{11}{13}\selectfont,text=namInk,card/.style={anchor=north west,draw=boardCardLine,fill=namPanel,rounded corners=3pt,inner sep=5pt,text width=4.8cm,align=left}]',
             r'\node[anchor=north west,font=\huge\bfseries] at (0,0) {' + _tex(title) + '};',
             r'\node[anchor=north west,text=namMuted] at (0,-.8) {Aktivitäten nach Status und Bereich};'])
    intro = list(intro_items(rows))
    intro_width = min(25, width)
    for index, (lane, arrow) in enumerate(intro):
        title, description = INTRO[lane['key']]
        slot = intro_width/len(intro)
        x = index*slot
        lines.extend([
            r'\draw[' + lane['tone'] + r',line width=1pt] (' + str(x) + r',-1.65) -- (' + str(x) + r',-3.55);',
            r'\node[anchor=north west,align=left,text width=' + str(slot-1.25) +
            r'cm,inner sep=0pt] at (' + str(x+.25) + r',-1.65) {\textcolor{' + lane['tone'] +
            r'}{\bfseries ' + _tex(title) + r'}\\[5pt]{\color{namMuted}' + _tex(description) + '}};'])
        if arrow:
            lines.append(r'\node[anchor=north,text=namMuted,inner sep=0pt] at (' + str(x-.55) +
                         r',-1.65) {$' + (r'\rightarrow' if arrow == '→' else r'\leftarrow') + '$};')
    lines.append(r'\begin{scope}[yshift=' + ('-4cm' if intro else '-1.2cm') + ']')
    lines.append(r'\node[anchor=south east,inner sep=0pt,text=namMuted] at (' + str(width-.15) + r',-1.2) {\textcolor{namAccent}{\textbullet}\ p1\quad\textcolor{namMarkerOrange}{\textbullet}\ p2\quad\textcolor{namBabyBlue}{\textbullet}\ p3\quad\textcolor{namPriorityLow}{\textbullet}\ p4};')
    lines.append(r'\node[anchor=north west,font=\bfseries] at (0,-1.65) {Bereich / Aktivität};')
    for index, (status, label) in enumerate(shown_columns):
        x = lane_width + column_width*index
        color = 'boardStatus' + str(index)
        lines.extend([r'\definecolor{' + color + '}{HTML}{' + STATUS_COLORS[status] + '}',
                      r'\fill[' + color + r'!12!namBg,rounded corners=3pt] (' + str(x) + r',-1.48) rectangle (' + str(x+column_width-.15) + r',-2.3);',
                      r'\node[anchor=north west,font=\bfseries] at (' + str(x+.15) + r',-1.65) {' + _tex(label) + '};'])
    lines.append(r'\coordinate (rowtop) at (0,-2.4);')
    spans = {}
    for index, row in enumerate(shown):
        for depth, rail in enumerate(row['rails']):
            if (depth, rail['key']) not in spans:
                spans[depth, rail['key']] = dict(first=index, last=index, depth=depth, rail=rail, name='group'+str(len(spans)))
            spans[depth, rail['key']]['last'] = index
    for index, row in enumerate(shown):
        starts = [g for g in spans.values() if g['first'] == index]
        ends = [g for g in spans.values() if g['last'] == index]
        if index and any(g['rail']['kind'] == 'category' for g in starts):
            lines.append(r'\coordinate (rowtop) at ([yshift=-.25cm]rowtop);')
        elif index and any(g['rail']['kind'] == 'context' for g in starts):
            lines.append(r'\coordinate (rowtop) at ([yshift=-.15cm]rowtop);')
        lines.append(r'\coordinate (lanetop) at (rowtop);')
        for g in starts:
            lines.extend([r'\coordinate (' + g['name'] + r'top) at (rowtop);',
                          r'\node[align=center,inner sep=' + ('22pt' if g['rail']['kind']=='category' else '8pt') + r',font=\small\bfseries,opacity=0,overlay] (' + g['name'] + 'measure) at (0,0) {' + rail_text(g['rail']) + '};'])
        lines.append(r'\coordinate (rowbottom) at ([yshift=-1.8cm]rowtop);')
        left = len(row['rails'])*rail_width + category_extra
        label = row['label']
        if label:
            text = r'{\normalsize\bfseries\color{' + row['tone'] + '}' + _tex(label['title']) + '}'
            if label['caption']:
                captions = [r'\sbox{\boardcaption}{\scriptsize ' + _tex(line) +
                            r'}\ifdim\wd\boardcaption>\linewidth\resizebox{\linewidth}{!}{\usebox{\boardcaption}}\else\usebox{\boardcaption}\fi'
                            for line in label['caption'].splitlines()]
                text += r'\\[3pt]{\color{namMuted}' + r'\\'.join(captions) + '}'
            name = 'label'+str(index)
            lines.append(r'\node[anchor=north west,text width=' + str(lane_width-left-.6) + 'cm,align=left,inner sep=5pt] (' + name + ') at ([xshift=' + str(left+.25) + r'cm,yshift=-.3cm]rowtop) {' + text + '};')
            lines.append(r'\path let \p1=(' + name + r'.south),\p2=(rowbottom) in coordinate (rowbottom) at (0,{min(\y1,\y2)});')
        for column, (status, _) in enumerate(shown_columns):
            previous = None
            for card_index, card in enumerate(row['cells'][status]):
                name = f'card{index}x{column}x{card_index}'
                position = (r'([yshift=-.16cm]' + previous + '.south west)' if previous else
                            r'([xshift=' + str(lane_width+column*column_width+.35) + r'cm,yshift=-.3cm]rowtop)')
                title, caption, priority = card_tex_parts(card)
                next_number = r'\boardnext{' + str(card['next']) + '}' if card.get('next') else ''
                text = (r'\vbox{\boardheading{' + title + '}{' + priority + r'}\vskip3pt '
                        r'\boardcaptionrow{' + caption + '}{' + next_number + '}}')
                lines.append(r'\node[card] (' + name + ') at ' + position + ' {' + text + '};')
                lines.append(r'\path let \p1=(rowbottom),\p2=(' + name + r'.south) in coordinate (rowbottom) at (0,{min(\y1,\y2)});')
                previous = name
        for g in ends:
            name = g['name']
            lines.append(r'\path let \p1=(rowbottom),\p2=(' + name + r'top),\p3=(' + name + r'measure.east),\p4=(' + name + r'measure.west) in coordinate (rowbottom) at (0,{min(\y1,\y2-\x3+\x4)});')
        lines.append(r'\coordinate (rowtop) at ([yshift=-.25cm]rowbottom);')
        lines.append(r'\begin{scope}[on background layer]\fill[' + row['tone'] + ('!5!namBg]' if label else '!9!namBg]') + ' (' + str(left) + r',0 |- lanetop) rectangle (' + str(width) + r',0 |- rowtop);\end{scope}')
        if label:
            lines.append(r'\draw[boardFrame,rounded corners=3pt] ([xshift=' + str(left+.1) + r'cm,yshift=-.1cm]lanetop) rectangle ([xshift=' + str(width-.1) + r'cm,yshift=.1cm]rowtop);')
        for g in ends:
            name, depth, rail = g['name'], g['depth'], g['rail']
            x = depth*rail_width + (category_extra if depth else 0)
            band_width = rail_width + (category_extra if rail['kind'] == 'category' else 0)
            color = 'namInk' if rail['kind'] == 'context' else rail['tone']
            lines.extend([r'\node[rotate=90,align=center,font=' + (r'\normalsize' if rail['kind'] == 'category' else r'\small') + r'\bfseries,text=' + color + '] at ($ (' + name + 'top)!.5!(rowtop) + (' + str(x+band_width/2) + ',0) $) {' + rail_text(rail) + '};',
                          r'\begin{scope}[on background layer]\fill[' + rail['tone'] + '!9!namBg] (' + str(x) + ',0 |- ' + name + 'top) rectangle (' + str(x+band_width) + r',0 |- rowtop);\end{scope}',
                          r'\draw[' + (rail['tone']+'!65!namBg' if rail['kind']=='category' else 'boardFrame') + ',rounded corners=3pt] ([xshift=' + str(x+.04) + 'cm,yshift=-.04cm]' + name + 'top) rectangle ([xshift=' + str(width-.04) + r'cm,yshift=.04cm]rowtop);'])
            direction = impact_direction(rows, rail['key']) if rail['kind'] == 'category' else ''
            if direction:
                position = ('[xshift=.625cm,yshift=.35cm]rowtop' if direction == 'down' else '[xshift=.625cm,yshift=-.35cm]' + name + 'top')
                lines.append(r'\node[text=' + color + '] at (' + position + ') {$' +
                             (r'\downarrow' if direction == 'down' else r'\uparrow') + '$};')
    if not rows:
        lines.append(r'\node[anchor=north west,text=namMuted] at (0,-2.8) {Noch keine Aktivitäten vorhanden.};')
    for column in range(len(shown_columns)):
        x = lane_width + column*column_width
        lines.append(r'\draw[boardStatus' + str(column) + r',line width=.8pt,rounded corners=3pt] (' + str(x) + r',-1.48) rectangle (' + str(x+column_width-.15) + r',0 |- rowtop);')
    lines.extend([r'\end{scope}', r'\end{tikzpicture}', r'\end{document}', ''])
    return '\n'.join(lines)
