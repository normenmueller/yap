"""Generic instance homepage and portable application assets."""
from pathlib import Path
from html import escape
import shutil
import base64
import re
from urllib.parse import urlsplit
from . import card_inputs, footer, navigation, palette, instance, product
from .resources import ASSETS as RESOURCE_ASSETS

PORTRAIT = Path('acc/img/gertrud-ai4x.png')
ASSETS = (PORTRAIT, Path(navigation.FAVICON), Path(navigation.LOGO), Path('acc/img/yap-logo.png'))
PAGES = (Path('yap.html'), Path('views/yapics/index.html'), Path('about.html'))


def pages():
    return (Path(instance.entry()), *PAGES[1:])


def assets():
    return tuple(dict.fromkeys((*ASSETS, Path(navigation.logo()), Path(navigation.favicon()))))


def asset_source(asset):
    return Path(asset) if Path(asset).as_posix() in (navigation.logo(), navigation.favicon()) and Path(asset).is_file() else RESOURCE_ASSETS / Path(asset).name


def asset_sources():
    return list(dict.fromkeys([*(asset_source(asset) for asset in assets()), RESOURCE_ASSETS / Path(navigation.LOGO).name]))


def root_entry(site, destination):
    source = Path(site) / instance.entry()
    if not source.exists():
        return
    import os
    prefix = Path(os.path.relpath(site, Path(destination).parent)).as_posix() + '/'
    def target(match):
        value = match[2]
        address = urlsplit(value)
        if not address.path or address.scheme or address.netloc:
            return match[0]
        return match[1] + '="' + prefix + value + '"'
    html = re.sub(r'\b(href|src)="([^"]*)"', target, source.read_text())
    from .perspectives import atomic_write
    atomic_write(Path(destination), html.encode())


STYLE = palette.css(''':root{color-scheme:dark;--bg:@namBg;--ink:@namInk;--muted:@namMuted;--line:@namLine}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{display:flex;flex-direction:column;width:100%;max-width:1000px;margin:0 auto;padding:40px 28px 32px}.eyebrow{margin:0;color:var(--muted);font-size:.75rem;letter-spacing:.15em;text-transform:uppercase}
.eyebrow a{color:@namBrand;text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:5px}.eyebrow a:hover{color:var(--ink)}.eyebrow a:focus-visible{outline:2px solid @namBrand;outline-offset:6px;border-radius:2px}
.eyebrow,.intro,.ai-preview{width:100%;max-width:780px;margin-inline:auto}
.intro{padding:28px 0 56px}h1{margin:0;font-size:clamp(5rem,13vw,8.5rem);line-height:1;letter-spacing:-.08em;font-weight:650}h1 span{color:@namBrand}
.lead{font-size:clamp(1.35rem,3vw,2rem);line-height:1.4;margin:22px 0 14px;letter-spacing:-.025em}.description{max-width:52ch;margin:0;color:var(--muted)}
.ai-preview{margin:0 auto 56px;border-block:1px solid var(--line);padding:26px 0 28px}.request-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:16px}.request-heading label{display:flex;align-items:center;gap:9px;font-size:1rem;font-weight:600}.request-question{min-width:0;font-style:italic;font-weight:500}.request-scope{color:@namBrand}.request-mark{width:26px;height:26px;flex:none;color:@namBrand}.preview-badge{min-width:0;color:var(--muted);font-size:.68rem;letter-spacing:.04em;overflow-wrap:anywhere}.preview-badge span,.preview-badge a{color:@namBrand}.preview-badge a{text-underline-offset:3px}.preview-badge a:focus-visible{outline:2px solid @namBrand;outline-offset:4px}.request-box{display:flex;align-items:center;gap:14px;padding:16px 20px;border:1px solid #786992;border-radius:16px;background:linear-gradient(115deg,#272338,@namPanel 75%);box-shadow:0 6px 24px #00000014,inset 0 1px 0 #d8ccff0a;transition:border-color .15s,box-shadow .15s}.request-box:focus-within{border-color:@namBrand;box-shadow:0 0 0 3px #b5a5ff33}.request-box textarea{display:block;width:100%;min-width:0;height:48px;resize:none;border:0;padding:0;background:transparent;color:var(--ink);font:inherit;line-height:24px;outline:none}.request-box textarea::placeholder{color:#c3b6ed;opacity:1}.request-box button{display:grid;place-items:center;flex:0 0 44px;width:44px;height:44px;padding:0;border:1px solid #b5a5ff88;border-radius:50%;overflow:hidden;background:#faf6fc;cursor:default}.request-box button img{display:block;width:100%;height:100%;object-fit:contain}.request-note{margin:12px 2px 0;color:var(--muted);font-size:.82rem;line-height:1.7}

.portfolio-intro{padding:24px 0 30px}.portfolio-intro h1{font-size:clamp(2rem,5vw,3rem);letter-spacing:-.05em;line-height:1.15;color:@namBrand}.portfolio-intro p{margin:10px 0 0;color:var(--muted);font-size:.9rem}
.description a,.about a{color:@namBrand;text-underline-offset:4px}.description a:hover,.about a:hover{color:var(--ink)}.description a:focus-visible,.about a:focus-visible{outline:2px solid @namBrand;outline-offset:4px}.about{max-width:65ch;margin:24px auto}.about h1{font-size:clamp(2rem,5vw,3rem);letter-spacing:-.04em;line-height:1.2}.about h2{font-size:1.2rem;margin:32px 0 12px}.about p{color:var(--muted)}.about .product-term{color:@namBrand}.about .product-logo{display:block;width:64px;height:auto;margin:0 0 18px}

.tiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.tile{--accent:@namActivities;display:flex;flex-direction:column;min-height:240px;padding:26px;border:1px solid var(--line);border-top:2px solid var(--accent);border-radius:14px;background:@namPanel;color:var(--ink);text-decoration:none;transition:border-color .15s}
.tile.performance{--accent:@namGreen}.tile:hover{border-color:var(--accent)}.tile:focus-visible{outline:2px solid var(--accent);outline-offset:6px}
.tiles{gap:0 20px}.yapic{--accent:@namActivities;--tile-padding:26px;position:relative;display:grid;grid-template-rows:subgrid;grid-row:span 2;min-width:0}.yapic.performance{--accent:@namPerformance}.yapic-prompt{min-width:0}.yapic-prompt summary{position:absolute;z-index:1;left:50%;top:calc(var(--tile-padding) + .875rem);transform:translate(-50%,-50%);display:flex;align-items:center;gap:9px;width:fit-content;max-width:100%;padding:5px 2px;color:var(--muted);font-size:.76rem;list-style:none;cursor:pointer}.yapic-prompt summary::-webkit-details-marker{display:none}.yapic-prompt summary>svg{width:17px;height:17px;flex:none;color:var(--accent)}.yapic-prompt summary:hover,.yapic-prompt[open] summary{color:var(--accent)}.yapic-prompt summary:focus-visible{outline:2px solid var(--accent);outline-offset:4px;border-radius:3px}.prompt-chevron{width:6px;height:6px;border-right:1px solid currentColor;border-bottom:1px solid currentColor;transform:rotate(45deg);margin:0 4px 3px 5px}.yapic-prompt[open] .prompt-chevron{transform:rotate(225deg);margin-bottom:-3px}.prompt-context{position:absolute;width:1px;height:1px;clip-path:inset(50%);overflow:hidden}.prompt-bubble{--bubble-line:color-mix(in srgb,var(--accent) 38%,var(--line));position:absolute;z-index:2;inset-inline:12px;top:calc(var(--tile-padding) + 2.375rem);max-height:min(28rem,65vh,calc(100% - var(--tile-padding) - 3.125rem));display:flex;flex-direction:column;margin:0;padding:18px 20px;border:1px solid var(--bubble-line);border-radius:13px;background:@namPanel;box-shadow:0 12px 30px #00000055}.prompt-bubble::before{content:"";position:absolute;top:-6px;left:calc(50% - 36px);width:10px;height:10px;transform:rotate(45deg);border-left:1px solid var(--bubble-line);border-top:1px solid var(--bubble-line);background:@namPanel}.prompt-bubble p{margin:0;font-size:.85rem;line-height:1.75;color:var(--ink)}.prompt-bubble .prompt-byline{overflow-wrap:anywhere;margin-bottom:10px;font-size:.68rem;letter-spacing:.04em;color:var(--accent)}.prompt-byline span{margin:0 5px}.prompt-byline .prompt-quote{display:inline-block;margin:0 9px 0 0;font:2.5rem/.5 Georgia,serif;vertical-align:5px}.prompt-scroll{min-height:0;overflow:auto;scrollbar-width:thin;scrollbar-color:var(--bubble-line) transparent}.prompt-bubble blockquote{margin:0;font-size:.95rem;line-height:1.8;text-align:justify;hyphens:auto;overflow-wrap:anywhere}.prompt-scroll:focus-visible{outline:2px solid var(--accent);outline-offset:3px}.prompt-bubble blockquote p{white-space:pre-line;font-size:inherit;line-height:inherit;margin:0 0 12px}.prompt-bubble blockquote p:first-child{font-weight:500;text-align:left}.prompt-bubble blockquote p:last-child{margin-bottom:0}.yapic-prompt[open] .prompt-bubble{animation:prompt-appear .18s ease-out}@keyframes prompt-appear{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
.tile-head{min-height:1.75rem;display:flex;align-items:center;justify-content:space-between;color:var(--accent);font-size:.8rem;letter-spacing:.1em}.arrow{font-size:1.5rem;line-height:1}.tile h2{overflow-wrap:anywhere;font-size:clamp(1.5rem,3vw,1.75rem);line-height:1.25;margin:20px 0 10px;letter-spacing:-.02em}.tile p{color:var(--muted);margin:0 0 20px;max-width:36ch}.tile .tile-slogan{color:var(--accent);font-size:1.02rem;font-weight:600;line-height:1.4;margin:0 0 12px}.tile .insight-emphasis{color:var(--accent)}.tile-growth{display:flex;align-items:center;gap:7px;margin-top:auto;padding-top:14px;color:var(--muted);font-size:.72rem;line-height:1.4}.tile-growth svg{width:17px;height:17px;flex:none;color:var(--accent)}.growth-version{font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.yap-page>main>.ai-preview:last-child{margin-bottom:0}
@media(max-width:650px){main{padding:28px 20px}.intro{padding:18px 0 40px}.ai-preview{margin-bottom:40px}.request-heading{align-items:flex-start;flex-direction:column;gap:4px}.request-box{padding:14px 16px;gap:12px}.tiles{grid-template-columns:1fr;gap:0}.yapic{--tile-padding:22px}.yapic+.yapic{margin-top:18px}.tile{min-height:220px;padding:22px}.tile h2{margin-top:20px}}
@media(prefers-reduced-motion:reduce){.tile,.request-box{transition:none}.tile:hover{transform:none}.yapic-prompt[open] .prompt-bubble{animation:none}}
''')


def _page(current, body):
    return ('<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            + navigation.head(current) + '<style>' + STYLE + navigation.STYLE + footer.STYLE + '</style></head><body class="yap-page">'
            + (navigation.render(current, theme='dark') if current != 'home' else '') + '<main>' + body + '</main>'
            + footer.render(about_href='../../about.html' if current == 'yapics' else 'about.html') + '</body></html>')


def _growth(label: str) -> str:
    if not label:
        return ''
    return ('<span class="tile-growth"><svg viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true" focusable="false"><path d="M12 21v-9M12 16C6 16 3 12 3 7c6 0 9 3 9 9Z"/>'
            '<path d="M12 12c0-6 3-9 9-9 0 6-3 9-9 9Z"/></svg>'
            '<span>Gewachsen bis <span class="growth-version">' + escape(label) + '</span></span></span>')


def _need(need: card_inputs.Need | None, title: str) -> str:
    if need is None:
        return ''
    byline = escape(need.sender)
    if need.sender and need.recipient:
        byline += ' <span aria-hidden="true">→</span> '
    byline += escape(need.recipient)
    if byline:
        byline = ('<p class="prompt-byline"><span class="prompt-quote" aria-hidden="true">„</span>'
                  + byline + '</p>')
    paragraphs = ''.join('<p>' + escape(text) + '</p>' for text in need.paragraphs)
    return ('<details class="yapic-prompt"><summary><svg viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.4" aria-hidden="true" focusable="false">'
            '<path d="M5 4.5h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9l-5 4v-4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2Z"/>'
            '<path d="M7 9h10M7 13h6"/></svg>Need<span class="prompt-context"> · ' + escape(title)
            + '</span><span class="prompt-chevron" aria-hidden="true"></span></summary>'
            '<div class="prompt-bubble"><div class="prompt-scroll" tabindex="0" role="region" aria-label="Need · '
            + escape(title, quote=True) + '">' + byline + '<blockquote>' + paragraphs + '</blockquote></div></div></details>')


def _cards(prefix=''):
    cards = card_inputs.decode(instance.manifest().get('illustrative_cards', {}))
    return ('<nav class="tiles" aria-label="Yapics">'
            '<div class="yapic"><a class="tile" href="' + prefix + 'views/activity-board/index.html" '
            'aria-label="Aktivitäten – Perspektiven öffnen"><div class="tile-head"><span>01</span>'
            '<span class="arrow" aria-hidden="true">↗</span></div><h2>Aktivitäten</h2>'
            '<p class="tile-slogan">Arbeiten. Wirken. Nachlesen.</p>'
            '<p>To-do-Listen zeigen Absichten. Deine Arbeit hinterlässt Spuren. Doch was hat sie tatsächlich bewegt? Lies es nach — und nutze die Erkenntnisse, um morgen <span class="insight-emphasis">fokussierter</span> zu arbeiten.</p>'
            + _growth(cards.activity.growth_label) + '</a>' + _need(cards.activity.need, 'Aktivitäten') + '</div>'
            '<div class="yapic performance"><a class="tile performance" href="' + prefix + 'views/mPM-ish/index.html" '
            'aria-label="Performance – Perspektiven öffnen"><div class="tile-head"><span>02</span>'
            '<span class="arrow" aria-hidden="true">↗</span></div><h2>Performance</h2>'
            '<p class="tile-slogan">Dein Beitrag. An jedem Heute.</p>'
            '<p>Ziele zeigen die Richtung. Dein Beitrag zählt heute. Doch was bewirkt deine Arbeit für dein Unternehmen? Lies es nach — und nutze die Erkenntnisse, um morgen <span class="insight-emphasis">wirkungsvoller</span> zu arbeiten.</p>'
            + _growth(cards.performance.growth_label) + '</a>' + _need(cards.performance.need, 'Performance')
            + '</div></nav>')



def _request():
    """Render display metadata only; no assistant/provider is activated."""
    assistant = instance.brand('assistant', '').strip()
    credit = instance.brand('assistant_credit', '').strip()
    identity = '<span>' + escape(assistant) + '</span>' if assistant else ''
    if credit:
        identity += (' · ' if identity else '') + footer._credit(credit, instance.brand('footer_link', None))
    badge = '<span class="preview-badge">' + identity + '</span>' if identity else ''
    greeting = ('Hi, ich bin ' + assistant + '.\n' if assistant else '') + product.MOTTO
    mark = ('<svg class="request-mark" viewBox="0 0 28 28" fill="currentColor" aria-hidden="true" focusable="false">'
            '<path d="M10 5 12.6 12.4 20 15 12.6 17.6 10 25 7.4 17.6 0 15 7.4 12.4Z"/>'
            '<path d="m23 0 1.3 3.7L28 5l-3.7 1.3L23 10l-1.3-3.7L18 5l3.7-1.3Z" opacity=".75"/>'
            '<path d="m24 19 .8 2.2L27 22l-2.2.8L24 25l-.8-2.2L21 22l2.2-.8Z" opacity=".55"/></svg>')
    portrait = '<img src="' + PORTRAIT.as_posix() + '" alt="" width="44" height="44">' if assistant else mark
    return ('<section class="ai-preview" aria-label="yapic — Konzeptvorschau">'
            '<div class="request-heading"><label for="view-request">' + mark
            + '<span class="request-question">Was in deinem <span class="request-scope">Wirkungsfeld</span> willst Du klarer sehen?</span>'
            '</label>' + badge + '</div><div class="request-box">'
            '<textarea id="view-request" rows="2" aria-describedby="request-note" placeholder="'
            + escape(greeting, quote=True) + '"></textarea>'
            '<button type="button" disabled aria-label="yapic erstellen (Konzeptvorschau)" '
            'title="Konzeptvorschau — Erstellung noch ohne Funktion">' + portrait + '</button></div>'
            '<p class="request-note" id="request-note">Ein <em>yapic</em> verbindet deinen Bedarf mit passenden Perspektiven und '
            'Darstellungen auf dein Wirkungsfeld — eine Saat für neue Einsichten und klare Orientierung.</p></section>')


def _product_logo():
    # Embed unchanged application bytes: instance assets cannot replace this identity.
    data = base64.b64encode((RESOURCE_ASSETS / Path(navigation.LOGO).name).read_bytes()).decode('ascii')
    return '<img class="product-logo" src="data:image/svg+xml;base64,' + data + '" alt="yap." width="64" height="31">'


def render(destination):
    title = escape(instance.brand('title', 'yap.'))
    if title.endswith('.'):
        title = title[:-1] + '<span>.</span>'
    tagline = escape(instance.brand('tagline', 'your activity portfolio'))
    homepage = _page('home', '<p class="eyebrow"><a href="views/yapics/index.html" title="Alle yapics öffnen">'
                     + tagline + '</a></p><header class="intro"><h1>'
                     + title + '</h1><p class="lead">' + product.MISSION + '</p><p class="description">'
                     + product.DESCRIPTION + '</p></header>' + _request())
    portfolio = _page('yapics', '<header class="portfolio-intro"><h1>yapic Portfolio</h1><p>'
                      + product.COLLECTION + '</p></header>' + _cards('../../'))
    about = _page('about', '<article class="about">' + _product_logo() + product.ABOUT + '</article>')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for asset in assets():
        published = destination / asset
        published.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(asset_source(asset), published)
    for path, html in zip(pages(), (homepage, portfolio, about)):
        published = destination / path
        published.parent.mkdir(parents=True, exist_ok=True)
        published.write_text(html, encoding='utf-8')
