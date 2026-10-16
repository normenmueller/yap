"""Readable browser hierarchy from the same placements as the static map."""

from html import escape

from . import footer, navigation, overview, palette, selections


STYLE = palette.css('''
:root{color-scheme:dark}*{box-sizing:border-box}
body{margin:0;background:@namBg;color:@namInk;font:14px/1.45 system-ui}
main{max-width:1280px;margin:36px auto 56px;padding:0 28px}
h1{font-size:28px;line-height:1.2;margin:0 0 28px}
.map-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px 44px}
.map-area{min-width:0;border-top:2px solid var(--tone);padding-top:12px}
.map-disclosure>summary{display:flex;align-items:center;gap:16px;cursor:pointer;list-style:none}
.map-disclosure>summary>div{min-width:0;flex:1}
.map-branch>summary,.map-versioned>summary{align-items:flex-start}
.map-branch>summary::after,.map-versioned>summary::after{margin-top:5px}
.map-disclosure>summary::-webkit-details-marker{display:none}
.map-disclosure>summary::after{content:'';width:8px;height:8px;border-right:1.5px solid @namMuted;
border-bottom:1.5px solid @namMuted;transform:rotate(-45deg);margin:0 6px 0 auto;flex-shrink:0}
.map-disclosure[open]>summary::after{transform:rotate(45deg)}
.map-disclosure>summary:focus-visible{outline:2px solid @namBrand;outline-offset:6px;border-radius:2px}
.map-area h2{font-size:19px;line-height:1.35;margin:0;font-weight:650;color:var(--tone)}
.map-area ul{list-style:none;margin:0;padding:0}
.map-area>.map-tree{margin-top:14px}
.map-tree .map-tree{margin-left:12px;padding-left:20px;border-left:1px solid @namLine}
.map-tree li{position:relative}
.map-tree .map-tree>li::before{content:'';position:absolute;top:18px;left:-20px;width:12px;border-top:1px solid @namLine}
.map-entry{padding:7px 10px;margin:4px 0;border:1px solid @namLine;
background:@namPanel;border-radius:5px;overflow-wrap:anywhere}
.map-heading{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:baseline;gap:12px}
.map-name{color:var(--tone);font-weight:600}
.map-subtitle{white-space:pre-line;color:@namMuted;font-size:13px;margin-top:2px}
.map-meta{display:flex;gap:12px;font-size:12px;color:@namMuted;white-space:nowrap}
.map-next{display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;
width:18px;height:18px;border:1px solid @namMuted;border-radius:50%;color:@namMuted;font-size:11px;line-height:1}
.map-versions{margin-top:8px;padding-top:4px;border-top:1px solid @namLine}
.map-version{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:3px 0}
.map-version-label{min-width:0;font-size:13px;color:@namMuted}
.map-wip{background:color-mix(in srgb,@namWip 7%,@namPanel);box-shadow:inset 2px 0 @namWip}
.tone-neutral{--tone:@namMuted}
.tone-support{--tone:@namSupport}.tone-impact{--tone:@namImpact}
.tone-governance{--tone:@namGovernance}.tone-strategy{--tone:@namStrategy}
.tone-epistemics{--tone:@namEpistemics}
@media(max-width:760px){main{margin-top:28px;padding:0 20px}.map-grid{grid-template-columns:1fr;gap:24px}
h1{font-size:26px;margin-bottom:24px}.map-tree .map-tree{margin-left:6px;padding-left:14px}
.map-tree .map-tree>li::before{left:-14px;width:8px}.map-entry{padding:7px 8px}}
@media print{.map-disclosure>.map-tree{display:block!important}.map-disclosure>summary::after{display:none}}
''')


def render(model):
    nodes = overview.map_nodes(model)
    children = {}
    for node in nodes:
        children.setdefault(node['parent'], []).append(node)
    selection = model.get('selection')
    title = 'Activity Map' + (' · ' + selection['label'] if selection and selection['key'] else '')

    def tone(node):
        value = node.get('tone', 'neutral')
        return value if value in ('support', 'impact', 'governance', 'epistemics', 'strategy') else 'neutral'

    def tracking(node):
        meta = []
        if node.get('status'):
            color = palette.HEX[palette.STATUS[node['status']]]
            meta.append(f'<span style="color:#{color}">{escape(node["status"])}</span>')
        if node.get('priority'):
            priority = str(node['priority'])
            color = {'p1': 'namAccent', 'p2': 'namMarkerOrange', 'p3': 'namBabyBlue', 'p4': 'namPriorityLow'}.get(priority, 'namMuted')
            meta.append(f'<span aria-label="Priorität {escape(priority, quote=True)}"><span aria-hidden="true" '
                        f'style="color:#{palette.HEX[color]}">●</span> {escape(priority)}</span>')
        if node.get('next'):
            rank = escape(str(node['next']), quote=True)
            meta.append(f'<span class="map-next" role="img" title="Als Nächstes: {rank}" '
                        f'aria-label="Als Nächstes: {rank}">{rank}</span>')
        return '<div class="map-meta">' + ''.join(meta) + '</div>' if meta else ''

    def content(node, root=False):
        title, caption = overview.map_text(node)
        tag = 'h2' if root else 'div'
        result = (f'<div class="map-heading"><{tag} class="map-name">{escape(title)}</{tag}>'
                  + tracking(node) + '</div>')
        if caption:
            result += '<div class="map-subtitle">' + escape(caption) + '</div>'
        return result

    def versions(node):
        if not node.get('versions'):
            return ''
        rows = ''.join('<div class="map-version"><span class="map-version-label">'
                       + escape(version['label']) + '</span>' + tracking(version) + '</div>'
                       for version in node['versions'])
        return '<div class="map-versions" role="group" aria-label="Versionen">' + rows + '</div>'

    def leaf(node, root=False):
        active = ' map-wip' if node.get('status') == 'wip' else ''
        if node.get('versions'):
            return (f'<details class="map-entry map-disclosure map-versioned{active}">'
                    + '<summary><div>' + content(node, root) + '</div></summary>'
                    + versions(node) + '</details>')
        return f'<div class="map-entry{active}">' + content(node, root) + '</div>'

    def tree(parent):
        if parent not in children:
            return ''
        rows = []
        for node in children[parent]:
            active = ' map-wip' if node.get('status') == 'wip' else ''
            if children.get(node['key']):
                entry = ('<details class="map-disclosure map-branch">'
                         + f'<summary class="map-entry{active}"><div>' + content(node)
                         + '</div></summary>' + versions(node) + tree(node['key']) + '</details>')
            else:
                entry = leaf(node)
            rows.append(f'<li class="tone-{tone(node)}">' + entry + '</li>')
        return '<ul class="map-tree">' + ''.join(rows) + '</ul>'

    areas = []
    for node in children.get('', []):
        if children.get(node['key']):
            areas.append(f'<details class="map-area map-disclosure tone-{tone(node)}" open><summary><div>'
                         + content(node, root=True) + '</div></summary>' + versions(node) + tree(node['key']) + '</details>')
        else:
            areas.append(f'<section class="map-area tone-{tone(node)}">'
                         + leaf(node, root=True) + '</section>')
    return ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            + navigation.head('map') + '<style>' + STYLE + navigation.STYLE + footer.STYLE + '</style></head><body class="yap-page">'
            + navigation.render('map', theme='dark', selection=selection, exports=(
                ('Map · PDF', 'views/activity-map/' + selections.filename(selection, 'map.pdf')),
                ('Map · PNG', 'views/activity-map/' + selections.filename(selection, 'map.png'))))
            + '<main><h1>' + escape(title) + '</h1><div class="map-grid">'
            + (''.join(areas) or '<p>Noch keine Aktivitäten vorhanden.</p>') + '</div></main>' + footer.render() + '</body></html>')
