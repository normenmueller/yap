"""Literal perspective capture and restoration, independent of report hierarchy.

Definitions use JSON-compatible YAML to preserve literal labels with the standard
library. General YAML input and path-independent live identity remain pending.
"""

from copy import deepcopy
from dataclasses import dataclass
import difflib
import hashlib
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata

from . import content
from .files import LOCAL_NAMES


DEFINITION = '.perspective.yaml'


def finder_metadata(path):
    return path.name == '.DS_Store' and path.is_file() and not path.is_symlink()


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def fingerprint(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def component(name):
    if (not isinstance(name, str) or not name or name.startswith('.')
            or name.endswith((' ', '.')) or any(c in name for c in '/\\:')
            or any(ord(c) < 32 for c in name) or name in LOCAL_NAMES):
        raise ValueError(f'Unsafe or reserved name: {name!r}')
    return name


def folded(name):
    return unicodedata.normalize('NFC', name).casefold()


def real_path(root, relative):
    """Reject symlink ancestors, including local state/control directories."""
    path = root
    for part in Path(relative).parts:
        if part in ('..', '/'):
            raise ValueError(f'Unsafe path: {relative}')
        path = path / part
        if path.is_symlink():
            raise ValueError(f'Symlink is not allowed here: {path}')
    return path


def read_bytes(path):
    return path.read_bytes() if path.exists() else None


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.pending-', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def catalog(root):
    """Use the single explicit source catalog for all navigation operations."""
    from .catalog import discover
    return discover(root)


def capture(root, title):
    """Title-only capture, with a readable key allocated once, without tracking."""
    if not isinstance(title, str) or not title.strip() or '\n' in title or '\r' in title:
        raise ValueError('A nonempty, single-line title is required')
    root = Path(root).resolve()
    base = real_path(root, 'pfo/act')
    base.mkdir(parents=True, exist_ok=True)
    known = catalog(root)
    slug = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', title)
                  .encode('ascii', 'ignore').decode().lower()).strip('-')[:64] or 'entry'
    if slug in LOCAL_NAMES:
        slug += '-entry'
    occupied = {folded(p.name) for p in base.iterdir()} | {folded(k) for k in known}
    index, key = 1, slug
    while folded(key) in occupied:
        index += 1
        key = f'{slug}-{index}'
    folder = base / key
    folder.mkdir()  # An intervening capture must fail, never replace another entry.
    source = folder / (key + '.md')
    source.write_text('---\nkey: ' + json.dumps(key) + '\nkind: activity\ntitle: ' +
                      json.dumps(title.strip(), ensure_ascii=False) + '\n---\n\n', encoding='utf-8')
    return source


def target_path(entries, target):
    if (not isinstance(target, dict) or set(target) - {'entry', 'path'}
            or not isinstance(target.get('entry'), str)
            or target.get('entry') not in entries):
        raise ValueError(f'Unknown canonical target: {target!r}')
    entry = entries[target['entry']]
    from .catalog import entry_root
    base = entry_root(entry)
    path = base
    subpath = target.get('path')
    if subpath is not None:
        if not isinstance(subpath, str) or not subpath:
            raise ValueError(f'Invalid target subpath: {subpath!r}')
        if base == entry['source'] and subpath != entry['source'].name:
            raise ValueError('A free-file note target must select its own Markdown document.')
        path = entry['folder']
        parts = subpath.split('/')
        for part in parts:
            component(part)
        if subpath != entry['source'].name and parts[0] != 'res':
            raise ValueError(f'Only entry Markdown and res targets are allowed: {subpath}')
        for part in parts:
            path = path / part
            if path.is_symlink():
                raise ValueError(f'Target traverses a symlink: {path}')
    if not path.exists():
        raise ValueError(f'Missing canonical target: {path}')
    return path


def identify(entries, link):
    stored = os.readlink(link)
    raw = Path(stored) if os.path.isabs(stored) else link.parent / stored
    # Inspect before normalization: work/../... must not hide a symlink traversal.
    current = Path(raw.anchor)
    for part in raw.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'{link}: target {stored!r} traverses a symlink ({current})')
    destination = Path(os.path.abspath(raw))
    from .catalog import entry_root
    for key, entry in sorted(entries.items(), key=lambda pair: -len(entry_root(pair[1]).parts)):
        base = entry_root(entry)
        if destination == base or (base == entry['folder'] and base in destination.parents):
            target = {'entry': key}
            if destination != base:
                target['path'] = destination.relative_to(entry['folder']).as_posix()
            try:
                target_path(entries, target)
            except ValueError as error:
                raise ValueError(f'{link}: target {stored!r}: {error}') from error
            return target
    raise ValueError(f'{link}: target {stored!r} is outside canonical entries or broken')


def scan(root, name, entries):
    """Inspect links without traversal; reject every unexpected real file."""
    view = real_path(root, Path('pov') / component(name))
    raw, warnings = {}, []

    def visit(directory):
        found, seen = [], set()
        for path in sorted(directory.iterdir(), key=lambda p: p.name):
            if finder_metadata(path):
                continue
            if path == view / DEFINITION:
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f'Expected a regular definition file: {path}')
                continue
            component(path.name)
            if folded(path.name) in seen:
                raise ValueError(f'Case-insensitive collision: {path}')
            seen.add(folded(path.name))
            relative = path.relative_to(view).as_posix()
            item = {'name': path.name}
            if path.is_symlink():
                raw[relative] = os.readlink(path)
                item['target'] = identify(entries, path)
                if os.path.isabs(raw[relative]):
                    warnings.append(f'{relative}: absolute local link; restore emits a relative link')
            elif path.is_dir():
                raw[relative] = None
                item['entries'] = visit(path)
            else:
                raise ValueError(f'{path}: unexpected real file; preserve it outside the perspective')
            found.append(item)
        if sum('entries' in item for item in found) > 7:
            raise ValueError(f'{directory}: more than seven sibling groups')
        return found

    tree = visit(view) if view.exists() else []
    return tree, raw, warnings


def flatten(items, prefix=''):
    result = {}
    for item in items:
        path = prefix + item['name']
        result[path] = item
        result.update(flatten(item.get('entries', []), path + '/'))
    return result


def literal(items):
    return [{key: literal(value) if key == 'entries' else value
             for key, value in item.items() if key in {'name', 'target', 'entries'}}
            for item in sorted(items, key=lambda i: i['name'])]


def validate(definition, entries):
    if (not isinstance(definition, dict) or type(definition.get('schema')) is not int
            or definition['schema'] != 1
            or set(definition) - {'schema', 'title', 'entries', 'presentation'}
            or not isinstance(definition.get('title'), str)):
        raise ValueError('Expected schema 1 perspective with title and entries')
    identifiers = set()

    def visit(items):
        if not isinstance(items, list):
            raise ValueError('Perspective entries must be a list')
        seen, groups = set(), 0
        for item in items:
            if not isinstance(item, dict) or set(item) - {'id', 'name', 'entries', 'target', 'alias', 'display', 'palette'}:
                raise ValueError(f'Unknown placement fields: {item!r}')
            name = component(item.get('name'))
            if folded(name) in seen:
                raise ValueError(f'Case-insensitive collision: {name}')
            seen.add(folded(name))
            identifier = item.get('id')
            if not isinstance(identifier, str) or not re.fullmatch(r'p[0-9]{6}', identifier) or identifier in identifiers:
                raise ValueError(f'Invalid or duplicate placement ID: {identifier!r}')
            identifiers.add(identifier)
            if ('entries' in item) == ('target' in item):
                raise ValueError(f'{name}: exactly one of entries or target is required')
            for field in ('alias', 'palette'):
                if field in item and (not isinstance(item[field], str) or not item[field]):
                    raise ValueError(f'{name}: {field} must be nonempty text')
            if 'palette' in item and item['palette'] not in {'neutral', 'support', 'impact', 'governance'}:
                raise ValueError(f'{name}: unknown palette role')
            if 'entries' in item:
                groups += 1
                if item.get('display', 'group') != 'group':
                    raise ValueError(f'{name}: directories have display role group')
                visit(item['entries'])
            else:
                target_path(entries, item['target'])
                if item.get('display', 'card') not in {'card', 'document', 'resource'}:
                    raise ValueError(f'{name}: unsupported display role')
        if groups > 7:
            raise ValueError('More than seven sibling groups')
    visit(definition.get('entries'))


def reconcile(tree, saved, matches):
    """Retain IDs, annotations and sibling order; require explicit rename matches."""
    old, new = flatten(saved['entries']), flatten(tree)
    by_id = {item['id']: (path, item) for path, item in old.items()}
    if set(matches) - set(new) or len(set(matches.values())) != len(matches):
        raise ValueError('Rename matches must name existing, distinct new placements')
    used, attached = set(), {}
    for path, item in new.items():
        previous = None
        if path in matches:
            if matches[path] not in by_id:
                raise ValueError(f'Unknown placement ID: {matches[path]}')
            previous = by_id[matches[path]][1]
        elif path in old and old[path]['id'] not in matches.values():
            previous = old[path]
        if previous:
            if ('entries' in previous) != ('entries' in item):
                raise ValueError(f'{path}: group/link replacement requires a distinct name')
            used.add(previous['id'])
            attached[path] = previous
    removed = {p: i for p, i in old.items() if i['id'] not in used}
    added = [p for p in new if p not in attached]
    if removed and added:
        candidates = ', '.join(f'{p}={i["id"]}' for p, i in removed.items())
        raise ValueError('Unresolved removal/rename and new placements: ' + ', '.join(added) +
                         '; match new/path=old-id explicitly, or save deletions first: ' + candidates)
    serial = max((int(i['id'][1:]) for i in old.values()), default=0)

    def visit(items, prefix=''):
        nonlocal serial
        result = []
        for item in sorted(items, key=lambda i: i['name']):
            path = prefix + item['name']
            previous = attached.get(path)
            copy = deepcopy(item)
            if previous:
                copy.update({k: v for k, v in previous.items() if k not in {'name', 'target', 'entries'}})
            else:
                serial += 1
                copy['id'] = f'p{serial:06d}'
            if 'entries' in copy:
                copy['entries'] = visit(copy['entries'], path + '/')
            result.append(copy)
        ranks = {i['id']: n for n, i in enumerate(old.values())}
        result.sort(key=lambda i: (ranks.get(i['id'], len(ranks)), i['name']))
        return result
    return dict(saved, entries=visit(tree))


@dataclass
class Plan:
    root: Path
    name: str
    operation: str
    definition_before: bytes | None
    state_before: bytes | None
    tree_before: dict
    definition: dict
    warnings: list

    def preview(self):
        before = self.definition_before.decode() if self.definition_before else ''
        changes = list(difflib.unified_diff(before.splitlines(), encode(self.definition).splitlines(),
                                           fromfile='saved', tofile='proposed', lineterm=''))
        navigation = []
        if self.operation == 'restore':
            entries = catalog(self.root)
            view, _, _ = locations(self.root, self.name)
            wanted = {relative: (os.path.relpath(target_path(entries, item['target']), (view / relative).parent)
                                 if 'target' in item else None)
                      for relative, item in flatten(self.definition['entries']).items()}
            for relative in sorted(set(wanted) | set(self.tree_before)):
                if relative not in self.tree_before:
                    navigation.append(dict(path=relative, action='create', target=wanted[relative]))
                elif relative not in wanted:
                    navigation.append(dict(path=relative, action='remove', target=self.tree_before[relative]))
                elif self.tree_before[relative] != wanted[relative]:
                    navigation.append(dict(path=relative, action='replace', before=self.tree_before[relative],
                                           target=wanted[relative]))
        return encode(dict(operation=self.operation, perspective=self.name,
                           warnings=self.warnings, definition_diff=changes,
                           navigation_changes=navigation, definition=self.definition))


def locations(root, name):
    view = real_path(root, Path('pov') / component(name))
    definition = real_path(root, view.relative_to(root) / DEFINITION)
    state = real_path(root, Path('.yap/local/state') / (name + '.json'))
    return view, definition, state


def plan(root, name, operation, *, choose=False, matches=None):
    root = Path(root).resolve()
    entries = catalog(root)
    view, definition, state = locations(root, name)
    before, state_before = read_bytes(definition), read_bytes(state)
    saved = json.loads(before) if before is not None else dict(schema=1, title=name, entries=[])
    validate(saved, entries)
    tree, raw, warnings = scan(root, name, entries)
    baseline = json.loads(state_before) if state_before else None
    if before is None and baseline and not choose:
        raise ValueError('Saved definition was removed; choose explicitly before recreating it')
    equal = literal(tree) == literal(saved['entries'])
    if operation == 'save':
        if before is not None and not equal and not choose:
            if baseline is None or baseline['definition'] != fingerprint(saved):
                raise ValueError('Definition changed or synchronization state is missing; compare and choose the tree explicitly')
        result = reconcile(tree, saved, matches or {})
    elif operation == 'restore':
        if before is None:
            raise ValueError('No saved perspective to restore')
        if not equal and raw and not choose:
            if baseline is None or baseline['tree'] != fingerprint(raw):
                raise ValueError('Unsaved perspective edits; compare and choose the saved definition explicitly')
        # An empty tree with known prior content can itself be an unsaved deletion.
        if not equal and not raw and baseline and baseline['tree'] != fingerprint(raw) and not choose:
            raise ValueError('Unsaved perspective deletion; choose the saved definition explicitly')
        result = saved
    else:
        raise ValueError(f'Unknown operation: {operation}')
    validate(result, entries)
    return Plan(root, name, operation, before, state_before, raw, result, warnings)


def apply(plan):
    """Revalidate the preview, then change navigation only; no source cleanup."""
    lock = real_path(plan.root, Path('.yap/local/state') / (plan.name + '.lock'))
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        _apply(plan)


def _apply(plan):
    entries = catalog(plan.root)
    view, definition, state = locations(plan.root, plan.name)
    _, raw, _ = scan(plan.root, plan.name, entries)
    if (raw != plan.tree_before or read_bytes(definition) != plan.definition_before
            or read_bytes(state) != plan.state_before):
        raise ValueError('Perspective changed since preview; inspect a new plan')
    validate(plan.definition, entries)
    view.mkdir(parents=True, exist_ok=True)
    if plan.operation == 'save':
        data = encode(plan.definition).encode()
        if data != plan.definition_before:
            atomic_write(definition, data)
    else:
        wanted = {}
        for relative, item in flatten(plan.definition['entries']).items():
            path = view / relative
            wanted[relative] = (os.path.relpath(target_path(entries, item['target']), path.parent)
                                if 'target' in item else None)
        # Deepest entries first. rmdir cannot erase user content; unlink never follows links.
        for relative in sorted(raw, key=lambda p: (-len(Path(p).parts), p)):
            if relative in wanted and raw[relative] == wanted[relative]:
                continue
            path = real_path(plan.root, (view / relative).parent.relative_to(plan.root)) / Path(relative).name
            if raw[relative] is None:
                metadata = path / '.DS_Store'
                if finder_metadata(metadata):
                    metadata.unlink()
                path.rmdir()
            elif path.is_symlink() and os.readlink(path) == raw[relative]:
                path.unlink()
            else:
                raise ValueError(f'{path}: changed during restore; preserved')
        for relative in sorted(wanted, key=lambda p: (len(Path(p).parts), p)):
            path = real_path(plan.root, (view / relative).parent.relative_to(plan.root)) / Path(relative).name
            if relative in raw and raw[relative] == wanted[relative]:
                continue
            if wanted[relative] is None:
                path.mkdir()
            else:
                path.symlink_to(wanted[relative])
    _, actual, _ = scan(plan.root, plan.name, entries)
    atomic_write(state, encode(dict(definition=fingerprint(plan.definition), tree=fingerprint(actual))).encode())
