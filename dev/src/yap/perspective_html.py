"""Read-only card/list presentation of saved perspectives."""

from html import escape
import json
import os
from pathlib import Path
from urllib.parse import quote

from . import footer, board, navigation, perspectives as p, documents, publication_links


COPY = {
    'de': dict(title='Perspektiven', all='Alle Einträge', remainder='Nicht zugeordnet',
               unique='eindeutige Einträge', placements='Platzierungen',
               unsaved='Ungespeicherte Änderungen', saved='Gespeicherter Stand',
               intro='Ordner und Verknüpfungen bestimmen deine Perspektiven.',
               prototype='Isolierter Prototyp'),
    'en': dict(title='Perspectives', all='All entries', remainder='Unassigned',
               unique='unique entries', placements='placements',
               unsaved='Unsaved changes', saved='Saved snapshot',
               intro='Folders and shortcuts define your perspectives.',
               prototype='Isolated prototype'),
}


STYLE = """
main{max-width:1100px}.perspective{margin:32px 0;padding:24px;border:1px solid var(--line);border-radius:10px}
.group{margin:20px 0;padding:0 0 0 18px;border-left:2px solid var(--line)}
.collection{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin:16px 0}
.card{max-width:none;min-height:82px}.card-caption{grid-column:1/-1!important}
.notice{border-left:2px solid var(--accent);padding-left:12px}
nav{display:flex;gap:20px;flex-wrap:wrap}h2{font-size:1.4rem}h3{font-size:1.05rem}
@media(max-width:650px){.perspective{padding:14px}.group{padding-left:12px}}
"""


def draft_state(root):
    """Fingerprint navigation for dirty notices without traversing shortcuts."""
    result = []
    base = p.real_path(root, 'pov')
    for directory, dirs, files in os.walk(base, followlinks=False):
        for name in sorted([*dirs, *files]):
            path = p.real_path(root, Path(directory).relative_to(root)) / name
            if p.finder_metadata(path):
                continue
            result.append((str(path.relative_to(base)), os.readlink(path) if path.is_symlink()
                           else 'directory' if path.is_dir() else 'file'))
    return sorted(result)


def render(root, destination=None, model=None):
    entries = p.catalog(root)
    output = Path(destination) if destination is not None else root
    output.mkdir(parents=True, exist_ok=True)
    published = {node['key']: node for node in model['nodes']} if model is not None else None
    names = ('index.html', 'index.en.html') if model is not None else (navigation.instance.entry(), navigation.instance.entry().replace('.html', '.en.html'))
    perspectives = []
    base = p.real_path(root, 'pov')
    if base.exists():
        for folder in sorted(base.iterdir()):
            if p.finder_metadata(folder):
                continue
            p.component(folder.name)
            _, definition, _ = p.locations(root, folder.name)
            if not definition.exists():
                continue
            saved = json.loads(definition.read_bytes())
            p.validate(saved, entries)
            try:
                tree, _, warnings = p.scan(root, folder.name, entries)
                dirty = p.literal(tree) != p.literal(saved['entries'])
            except ValueError:
                dirty = True  # A broken draft cannot prevent saved-only rendering.
            perspectives.append((folder.name, saved, dirty))

    for language, words in COPY.items():
        def link(target):
            source = p.target_path(entries, target)
            if published is not None:
                entry = entries[target['entry']]
                if source in {entry['folder'], entry['source']}:
                    return escape(publication_links.activity_pdf(published[target['entry']]), quote=True)
                route = documents.destination(source.relative_to(root), model['nodes'])
                if route is None or source.is_dir():
                    # Resource directories are navigation containers, not public files.
                    return escape(publication_links.activity_pdf(published[target['entry']]), quote=True)
                return escape(quote('../../' + route, safe='/'), quote=True)
            return escape(quote(os.path.relpath(source, output), safe='/'), quote=True)

        def label(item):
            if 'alias' in item:
                return item['alias']
            target = item.get('target')
            if target and 'path' not in target:
                entry = entries[target['entry']]
                if item['name'] == entry['folder'].name:
                    return entry['acronym'] or entry['title']
            return item['name']

        def card(item):
            entry = entries[item['target']['entry']]
            target = item['target']
            if 'path' not in target:
                target = dict(target, path=entry['source'].name)
            return ('<article class="card" data-entry="' + escape(entry['key'], quote=True) + '">'
                    '<a href="' + link(target) + '">' + escape(label(item)) + '</a>'
                    '<span class="card-caption">' + escape(entry['caption']) + '</span></article>')

        def project(items):
            output, cards = [], []

            def flush():
                if cards:
                    output.append('<div class="collection">' + ''.join(cards) + '</div>')
                    cards.clear()

            for item in items:
                if 'entries' in item:
                    flush()
                    output.append('<section class="group" data-placement="' + item['id'] + '"><h3>' +
                                  escape(label(item)) + '</h3>' + project(item['entries']) + '</section>')
                else:
                    cards.append(card(item))
            flush()
            return ''.join(output)

        def collection(keys):
            return '<div class="collection">' + ''.join(card(dict(name=entries[key]['folder'].name,
                                                                  target={'entry': key})) for key in keys) + '</div>'

        parts = ['<!doctype html><html lang="' + language + '"><head><meta charset="utf-8">',
                 '<meta name="viewport" content="width=device-width,initial-scale=1">',
                 ('<link rel="icon" type="image/svg+xml" href="../../' + quote(navigation.favicon(), safe='/') + '">') if model is not None else '',
                 '<title>' + escape(navigation.instance.brand('title', 'yap.')) + ' ' + words['title'] + '</title><style>' + board.STYLE + STYLE + footer.STYLE +
                 '</style></head><body class="yap-page"><main><nav>',
                 '<a href="../../' + navigation.instance.entry() + '">' + escape(navigation.instance.brand('title', 'yap.')) + '</a>' if model is not None else '',
                 '<a href="' + names[0] + '" lang="de">Deutsch</a>',
                 '<a href="' + names[1] + '" lang="en">English</a><a href="#all">' + words['all'] + '</a></nav>',
                 ('<p>' + words['prototype'] + '</p>') if model is None else '',
                 '<h1>' + words['title'] + '</h1><p>' + words['intro'] + '</p>']
        for name, saved, dirty in perspectives:
            flat = p.flatten(saved['entries'])
            used = {item['target']['entry'] for item in flat.values() if 'target' in item}
            count = sum('target' in item for item in flat.values())
            parts.extend(['<section class="perspective" id="' + escape(name, quote=True) + '"><h2>' +
                          escape(saved['title']) + '</h2><p>' + str(len(used)) + ' ' + words['unique'] +
                          ' · ' + str(count) + ' ' + words['placements'] + '</p>',
                          '<p class="notice">' + words['saved'] + (' · ' + words['unsaved'] if dirty else '') + '</p>',
                          project(saved['entries']), '<details><summary>' + words['remainder'] +
                          ' (' + str(len(set(entries) - used)) + ')</summary>',
                          collection(sorted(set(entries) - used)), '</details></section>'])
        parts.extend(['<section id="all"><h2>' + words['all'] + ' (' + str(len(entries)) + ')</h2>',
                      collection(sorted(entries)), '</section></main>' + footer.render(language) + '</body></html>'])
        path = output / names[0 if language == 'de' else 1]
        if path.is_symlink():
            raise ValueError(f'Generated page cannot be a symlink: {path}')
        p.atomic_write(path, ''.join(parts).encode())
