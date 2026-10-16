"""Shared, offline navigation with stable view and document positions."""

from html import escape
from posixpath import dirname, relpath
from urllib.parse import quote


from . import palette, selections, instance


VIEWS = (
    ('home', 'yap', 'yap.html'),
    ('yapics', 'Yapics', 'views/yapics/index.html'),
    ('about', 'Über yap.', 'about.html'),
    ('board', 'Activity Board', 'views/activity-board/index.html'),
    ('map', 'Activity Map', 'views/activity-map/index.html'),
    ('graph', 'Activity Flow', 'views/dependency-graph/index.html'),
    ('performance', 'Performance', 'views/mPM-ish/index.html'),
)
PDFS = (
    ('Activity · Overview', 'acc/pdf/Activity - Overview.pdf'),
    ('Activity · Details', 'acc/pdf/Activity - Details.pdf'),
    ('Performance · mPM', 'acc/pdf/Performance - mPM.pdf'),
)

STYLE = palette.css("""
.yap-navigation{--nav-ink:#253238;--nav-muted:#647178;--nav-link:#716286;--nav-line:#dcdee3;--nav-active:#f1edf7;display:block;margin:0;border-bottom:1px solid var(--nav-line);font:14px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;text-align:left}
.yap-navigation[data-theme=dark]{--nav-ink:@namInk;--nav-muted:@namMuted;--nav-link:@namBrand;--nav-line:@namLine;--nav-active:#282435}
.yap-navigation .nav-inner{display:flex;flex-wrap:wrap;align-items:center;gap:8px 24px;max-width:1720px;box-sizing:border-box;margin:auto;padding:10px 28px}
.yap-navigation .nav-group{position:relative;display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 12px;min-width:0;max-width:100%}
.yap-navigation .nav-label{flex:none;color:var(--nav-muted);font-size:10px;letter-spacing:.1em;text-transform:uppercase;white-space:nowrap}
.yap-navigation .nav-links{display:flex;flex-wrap:wrap;gap:4px 8px;min-width:0}
.yap-navigation a{display:inline-block;padding:6px 8px;border-radius:5px;color:var(--nav-link);font-weight:500;text-decoration:underline;text-underline-offset:4px;white-space:nowrap;overflow-wrap:normal}
.yap-navigation a:hover{color:var(--nav-ink);background:var(--nav-active)}
.yap-navigation a[aria-current=page]{color:var(--nav-ink);background:var(--nav-active);text-decoration:none}
.yap-navigation a:focus-visible{outline:2px solid var(--nav-link);outline-offset:2px}
.yap-navigation .nav-presentation{position:relative;display:inline-block;padding:6px 8px;border-radius:5px;color:var(--nav-link);font-weight:500;text-decoration:underline;text-underline-offset:4px;cursor:pointer;white-space:nowrap}
.yap-navigation .nav-presentation input{position:absolute;width:1px;height:1px;clip-path:inset(50%);overflow:hidden}
.yap-navigation .nav-presentation:hover{color:var(--nav-ink);background:var(--nav-active)}
.yap-navigation .nav-presentation:has(input:checked){color:var(--nav-ink);background:var(--nav-active);text-decoration:none}
.yap-navigation .nav-presentation:has(input:focus-visible){outline:2px solid var(--nav-link);outline-offset:2px}
.yap-navigation .nav-brand{flex:none;width:max-content;padding:4px 6px;line-height:1;text-decoration:none}
.yap-navigation .nav-brand,.yap-navigation .nav-brand:hover,.yap-navigation .nav-brand[aria-current=page]{background:transparent;border:0;border-radius:0;box-shadow:none}
.yap-navigation .nav-brand img{display:block;width:50px;height:auto}
.yap-navigation .nav-identity{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}
.yap-navigation .nav-location{display:flex;align-items:baseline;gap:6px;color:var(--nav-ink)}
.yap-navigation .nav-location-separator{color:var(--nav-muted)}
.yap-navigation .nav-location-current{font-weight:500}
.yap-navigation .nav-menu{position:relative;min-width:0}
.yap-navigation .nav-menu summary{cursor:pointer;color:var(--nav-link);padding:6px 8px;min-height:32px;box-sizing:border-box;list-style:none;border-radius:5px}
.yap-navigation .nav-menu summary::-webkit-details-marker{display:none}
.yap-navigation .nav-menu summary::after{content:'⌄';margin-left:12px}
.yap-navigation .nav-menu summary:hover{background:var(--nav-active)}
.yap-navigation .nav-menu summary:focus-visible{outline:2px solid var(--nav-link);outline-offset:2px}
.yap-navigation .nav-menu-options{position:absolute;z-index:20;top:100%;left:0;min-width:100%;width:max-content;max-width:min(320px,85vw);box-sizing:border-box;padding:6px;background:var(--nav-active);border:1px solid var(--nav-line);border-radius:8px;box-shadow:0 8px 24px #0004}
.yap-navigation .nav-menu-options a{display:block;white-space:normal}
.yap-navigation .perspective-picker{position:static}
.yap-navigation .perspective-options{width:100%;max-width:100%}
.yap-navigation .output-picker{margin-left:auto;flex:none}
.yap-navigation .output-picker .nav-menu-options{left:auto;right:0}
.yap-navigation .output-section{padding:4px}
.yap-navigation .output-section+.output-section{border-top:1px solid var(--nav-line);margin-top:4px;padding-top:8px}
.yap-navigation .output-section h2{margin:4px 8px;color:var(--nav-muted);font:500 10px/1.5 system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase}
@media(max-width:650px){.yap-navigation .nav-inner{padding:8px 14px;gap:8px 20px}.yap-navigation .output-picker{margin-left:0}.yap-navigation .output-picker .nav-menu-options{left:0;right:auto}}
@media print{.yap-navigation{display:none!important}}
""")


FAVICON = 'acc/img/yap-favicon.svg'
LOGO = 'acc/img/yap-logo.svg'


def views():
    return tuple((key, instance.brand('title', 'yap.') if key == 'home' else
                  'Über ' + instance.brand('title', 'yap.') if key == 'about' else label,
                  instance.entry() if key == 'home' else path) for key, label, path in VIEWS)


def favicon():
    return instance.brand('favicon', FAVICON)


def logo():
    return instance.brand('logo', LOGO)


def head(current, title=None):
    """Shared tab identity and portable favicon link."""
    _, label, source = next(view for view in views() if view[0] == current)
    title = title or (instance.brand('tagline', 'your activity portfolio') if current == 'home' else label)
    icon = quote(relpath(favicon(), dirname(source) or '.'), safe='/')
    return ('<title>' + escape(instance.brand('title', 'yap.')) + ' ' + escape(title) + '</title>'
            '<link rel="icon" type="image/svg+xml" href="' + icon + '">')


def render(current, *, theme='light', exports=(), selection=None):
    source = next(path for key, _, path in views() if key == current)

    def link(label, path, active=False, brand=False):
        href = quote(relpath(path, dirname(source) or '.'), safe='/')
        state = ' aria-current="page"' if active else ''
        attributes = ' class="nav-brand" aria-label="' + escape(instance.brand('title', 'yap.')) + ' Startseite"' if brand else ''
        logo_path = quote(relpath(logo(), dirname(source) or '.'), safe='/')
        brand_title = escape(instance.brand('title', 'yap.'))
        text = f'<img src="{logo_path}" width="50" height="24" alt="{brand_title}">' if brand else escape(label)
        return f'<a href="{escape(href, quote=True)}"{state}{attributes}>{text}</a>'

    if current == 'home':
        selected = {'home', 'board', 'performance'}
        documents = ()
    elif current in {'yapics', 'about'}:
        selected = {'home', 'yapics'}
        documents = ()
    elif current == 'performance':
        selected = {'home', 'performance'}
        documents = PDFS[2:]
    else:
        selected = {'home', 'board', 'map', 'graph'}
        documents = PDFS[:2]
    groups = [('' if current == 'yapics' else 'Ansichten', ''.join(
        link('Aktivitäten' if current == 'home' and key == 'board' else label, path, key == current)
        for key, label, path in views() if key in selected and key != 'home'))]
    if current in {'yapics', 'about'}:
        groups = []
    if selection is not None:
        choices = ''.join(
            link(label, dirname(source) + '/' + selections.filename({'key': key}), key == selection['key'])
            for key, label in selection['options'])
        groups = [('Perspektive', '<details class="nav-menu perspective-picker"><summary title="Perspektive wählen / Choose perspective">'
                  + escape(selection['label']) + '</summary><div class="nav-menu-options perspective-options">' + choices + '</div></details>')]
        if current == 'performance':
            groups.append(('Darstellung', ''.join(
                '<label class="nav-presentation"><input type="radio" name="view" id="' + key +
                '" aria-controls="' + key + '-panel"' + (' checked' if key == 'cards' else '') +
                '><span>' + label + '</span></label>'
                for key, label in (('cards', 'Ziele'), ('tracking', 'Fortschritt'), ('graph', 'Zusammenhänge')))))
        else:
            groups.append(('Darstellung', ''.join(
                link({'board': 'Board', 'map': 'Map', 'graph': 'Flow'}[key],
                     dirname(path) + '/' + selections.filename(selection), key == current)
                for key, _, path in views() if key in {'board', 'map', 'graph'})))
    output_sections = []
    if exports:
        output_sections.append(('Aktuelle Perspektive', exports))
    if documents:
        output_sections.append(('Gesamtes Portfolio', documents))
    output_menu = ''
    if output_sections:
        output_menu = ('<details class="nav-menu output-picker"><summary title="Berichte und Exporte / Reports and exports">'
                       'Berichte &amp; Export</summary><div class="nav-menu-options">' + ''.join(
                           '<section class="output-section"><h2>' + label + '</h2>' +
                           ''.join(link(text, path) for text, path in items) + '</section>'
                           for label, items in output_sections) + '</div></details>')
    identity = link(instance.brand('title', 'yap.'), instance.entry(), current == 'home', brand=True)
    if current == 'about':
        identity += '<span class="nav-location-current">Über ' + escape(instance.brand('title', 'yap.')) + '</span>'
    elif current != 'home':
        location = link('Yapics', 'views/yapics/index.html', current == 'yapics')
        if current != 'yapics':
            location += ('<span class="nav-location-separator" aria-hidden="true">/</span>'
                         '<span class="nav-location-current">' +
                         ('Performance' if current == 'performance' else 'Aktivitäten') + '</span>')
        identity += '<div class="nav-location">' + location + '</div>'
    return ('<nav class="yap-navigation" data-theme="' + escape(theme, quote=True) +
            '" aria-label="Portfolio-Navigation"><div class="nav-inner">' +
            '<div class="nav-identity">' + identity + '</div>' + ''.join(
                ('<div class="nav-group" role="group" aria-label="' + label + '">'
                 '<span class="nav-label" aria-hidden="true">' + label + '</span>' if label else
                 '<div class="nav-group nav-group-unlabeled">') +
                '<div class="nav-links">' + links + '</div></div>' for label, links in groups) + output_menu + '</div></nav>')
