"""Keyed entries and explicit membership/publication, independent of presentation."""

from pathlib import Path, PurePosixPath

from . import catalog, content
from .files import LOCAL_NAMES


CONTROL = 'pfo/act/act.md'


def mapping(meta, field):
    value = meta.get(field, {'t': 'MetaMap', 'c': {}})
    if value['t'] != 'MetaMap':
        raise ValueError(f'{CONTROL}: {field} requires a mapping.')
    return value['c']


def memberships(meta, entries):
    """Explicit membership never follows source locations or perspective groups."""
    result = {}
    for key, value in mapping(meta, 'members').items():
        where = f'{CONTROL}: members[{key}]'
        if key not in entries:
            raise ValueError(f'{where}: unknown entry.')
        if value['t'] != 'MetaList':
            raise ValueError(f'{where}: expected a list of entry keys.')
        children = []
        for item in value['c']:
            child = catalog.literal({'key': item}, 'key', where)
            if child not in entries:
                raise ValueError(f'{where}: unknown member {child!r}.')
            if child in children:
                raise ValueError(f'{where}: duplicate member {child!r}.')
            children.append(child)
        result[key] = children
    visited, active = set(), set()

    def visit(key):
        if key in active:
            raise ValueError(f'{CONTROL}: members contains a cycle at {key!r}.')
        if key not in visited:
            active.add(key)
            for child in result.get(key, []):
                visit(child)
            active.remove(key)
            visited.add(key)

    for key in result:
        visit(key)
    return result


def descendants(members, key):
    result = []

    def visit(parent):
        for child in members.get(parent, []):
            if child not in result:
                result.append(child)
                visit(child)

    visit(key)
    return result


def leaf_selection(members, requested, eligible):
    """Expand within the consumer's eligible set, not another view's leaf rules."""
    eligible = set(eligible)
    leaves = {key for key in eligible if not eligible.intersection(descendants(members, key))}
    selected = set()
    for key in requested:
        children = leaves.intersection(descendants(members, key))
        selected.update(children or ({key} if key in eligible else set()))
    return selected


def publication(meta, entries):
    result, ids, routes = {}, set(), set()
    authored = mapping(meta, 'publication')
    for key in authored:
        if key not in entries:
            raise ValueError(f'{CONTROL}: publication[{key}]: unknown entry.')
    for key, entry in entries.items():
        where = f'{CONTROL}: publication[{key}]'
        value = authored.get(key, {'t': 'MetaMap', 'c': {}})
        if value['t'] != 'MetaMap' or set(value['c']) - {'id', 'resource-root'}:
            raise ValueError(f'{where}: allowed fields are id and resource-root.')
        fields = value['c']
        # Areas retain the act- address family when reclassified from activities.
        identifier = catalog.literal(fields, 'id', where) or ('note-' if entry['kind'] == 'note' else 'act-') + key
        if not identifier.startswith(('act-', 'note-')) or any(c.isspace() for c in identifier):
            raise ValueError(f'{where}: id must be a nonempty act-/note- identifier without whitespace.')
        if identifier in ids:
            raise ValueError(f'{where}: duplicate publication ID {identifier!r}.')
        ids.add(identifier)
        # Ordinary/private note attachments are never enrolled implicitly.
        route = catalog.literal(fields, 'resource-root', where) if 'resource-root' in fields else (
            None if entry['kind'] == 'note' else key)
        if route is not None:
            path = PurePosixPath(route)
            if not route or path.is_absolute() or any(part in {'', '..', '.', *LOCAL_NAMES} or part.startswith('.')
                                                    for part in route.split('/')) or '\\' in route:
                raise ValueError(f'{where}: resource-root requires a safe relative publication path.')
            if catalog.folded(route) in routes:
                raise ValueError(f'{where}: duplicate resource-root {route!r}.')
            routes.add(catalog.folded(route))
        result[key] = {'id': identifier, 'resource_root': route}
    return result


def load(root):
    """Build canonical entries; display parents/depths belong only to projections."""
    root = Path(root).resolve()
    entries = catalog.discover(root)
    control = root / CONTROL
    if control.is_symlink():
        raise ValueError(f'{control}: source control cannot be a symlink.')
    main = content.public_content(content.read(control))
    if {'sequence', 'board-sequence'} & set(main['meta']):
        raise ValueError(f'{CONTROL}: ordering belongs in the saved report perspective.')
    members = memberships(main['meta'], entries)
    addresses = publication(main['meta'], entries)
    nodes = []
    for key, entry in entries.items():
        doc, path = entry['document'], entry['source']
        for field in ('sequence', 'board-sequence', 'tracking', 'dgraph', 'members', 'publication'):
            if field in doc['meta']:
                raise ValueError(f'{path}: {field} belongs in {CONTROL}.')
        fields = content.entry_fields(doc['meta'], path, root)
        versions = content.activity_versions(doc['blocks'], path)
        if entry['kind'] != 'activity' and versions:
            raise ValueError(f'{path}: {entry["kind"]}s cannot own activity versions.')
        nodes.append(dict(key=key, kind=entry['kind'], path=path.relative_to(root).as_posix(),
                          meta=doc['meta'], blocks=doc['blocks'], versions=versions,
                          status='', priority='', **addresses[key], **fields))
    activities = [node for node in nodes if node['kind'] == 'activity']
    content.apply_activity_tracking(activities, content.activity_tracking(main['meta']))
    return dict(api=main['pandoc-api-version'], meta=main['meta'], nodes=nodes, members=members)
