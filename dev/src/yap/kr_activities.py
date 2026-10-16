"""Explicit KR contributions: managed paths, web links, or local named notes."""

from html import escape
from urllib.parse import urlsplit

from .publication_links import activity_pdf


def parse(value, nodes, where):
    from .content import metadata, plain, walk
    if value['t'] != 'MetaList':
        raise ValueError(f'{where}: activities requires a list of activity keys, Markdown links, or title entries.')
    known = {node['key'] for node in nodes}
    result = []
    for item in value['c']:
        if item['t'] == 'MetaMap':
            fields = item['c']
            if set(fields) != {'title'}:
                raise ValueError(f'{where}: a named contribution requires only title.')
            title = metadata(fields, 'title', where)
            if not title:
                raise ValueError(f'{where}: contribution title must not be empty.')
            entry = dict(title=title)
        elif item['t'] == 'MetaInlines' and len(item['c']) == 1 and item['c'][0]['t'] == 'Link':
            _, label, target = item['c'][0]['c']
            title, url = plain(label).strip(), target[0]
            try:
                address = urlsplit(url)
                # Accessing port validates its syntax/range without opening the URL.
                _ = address.port
                valid = address.scheme in {'http', 'https'} and bool(address.hostname)
            except ValueError:
                valid = False
            if not title or not valid or any(char.isspace() for char in url):
                raise ValueError(f'{where}: an activity link requires a title and an absolute HTTP(S) URL.')
            entry = dict(title=title, url=url)
        else:
            if any(part['t'] in {'Link', 'Image'} for part in walk(item)):
                raise ValueError(f'{where}: an activity link must occupy the entire list item.')
            entry = metadata({'activity': item}, 'activity', where)
            if entry not in known:
                raise ValueError(f'{where}: unknown activity {entry!r}; use an existing key, '
                                 'an explicit Markdown link, or a title entry for a named contribution.')
        if entry not in result:
            result.append(entry)
    return result


def check_link_titles(results):
    """One exact URL is one shared reference; do not silently discard its label."""
    labels = {}
    for objective, rows in results.items():
        for kr in rows:
            for entry in kr['activities']:
                if isinstance(entry, dict) and 'url' in entry:
                    previous = labels.setdefault(entry['url'], entry['title'])
                    if previous != entry['title']:
                        raise ValueError(f"{objective}/{kr['key']}: activity link {entry['url']!r} "
                                         'has conflicting titles; use the same title for a shared link.')


def project(entry, scope, index, by_key):
    """Resolve presentation without creating workflow state or consulting Git."""
    if isinstance(entry, str):
        node = by_key[entry]
        title, acronym = node['title'], node.get('acronym', '')
        if acronym and acronym != title:
            title = acronym + ' – ' + title
        return dict(id='a:' + entry, title=title, url=activity_pdf(node))
    if 'url' in entry:
        return dict(id='link:' + entry['url'], title=entry['title'], url=entry['url'])
    return dict(id=f'note:{scope}/{index}', title=entry['title'], source='note')


def render(model, entries):
    """Keep real activity lanes; show explicit links/notes without invented status."""
    from . import performance_lanes
    paths = [entry for entry in entries if isinstance(entry, str)]
    parts = [performance_lanes.render(model, paths)] if paths or not entries else []
    references = [entry for entry in entries if isinstance(entry, dict)]
    if references:
        parts.append('<ul class="kr-references">')
        for entry in references:
            title = escape(entry['title'])
            if 'url' in entry:
                title = '<a href="' + escape(entry['url'], quote=True) + '">' + title + '</a>'
            parts.append('<li>' + title + '</li>')
        parts.append('</ul>')
    return ''.join(parts)
