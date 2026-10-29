"""Literal source-owned workspace bindings and bounded local navigation.

The ``wsp`` namespace contains generated shortcuts only. This module never
discovers sources through a shortcut or inspects a workspace's contents.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile


LEGACY_NAMES = ('repo', 'shlf', 'zbox')
HEADER = re.compile(r'\A\ufeff?---[ \t]*\r?\n(?P<yaml>.*?)(?=^(?:---|\.\.\.)[ \t]*\r?$)', re.M | re.S)


def _yaml():
    try:
        import yaml
    except ImportError as error:
        raise ValueError('Workspace YAML requires PyYAML; install requirements.txt in your Python environment.') from error
    return yaml


def safe_path(path):
    """Check a write path without following symlinks in its ancestry."""
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f'{part}: symlinks are not allowed in navigation/configuration paths.')
        if part != path and part.exists() and not part.is_dir():
            raise ValueError(f'{part}: expected a directory.')


def snapshot(path):
    safe_path(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f'{path}: expected a regular file.')
    return path.read_bytes()


def name(value, where='wsp'):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', value):
        raise ValueError(f'{where}: link names require letters, digits, hyphens or underscores, starting with a letter or digit.')
    return value


def target(root, value, where='wsp'):
    if (not isinstance(value, str) or not value.strip() or value != value.strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or '\\' in value or '$' in value or re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', value)
            or value.startswith('~') and not value.startswith('~/')):
        raise ValueError(f'{where}: expected a literal directory path (absolute, ~/ or relative to the instance root).')
    path = Path(value).expanduser()
    return Path(os.path.abspath(path if path.is_absolute() else root / path))


def _header(data, source):
    yaml = _yaml()
    text = data.decode('utf-8')
    match = HEADER.match(text)
    if not match:
        raise ValueError(f'{source}: expected initial YAML front matter.')
    try:
        node = yaml.compose(match['yaml'], Loader=yaml.SafeLoader)
    except yaml.YAMLError as error:
        raise ValueError(f'{source}: invalid YAML: {error}') from error
    if not isinstance(node, yaml.MappingNode):
        raise ValueError(f'{source}: expected a YAML mapping.')
    seen = set()
    for key, _ in node.value:
        if not isinstance(key, yaml.ScalarNode) or key.tag != 'tag:yaml.org,2002:str':
            raise ValueError(f'{source}: front matter keys must be text.')
        if key.value in seen:
            raise ValueError(f'{source}: duplicate YAML field {key.value!r}.')
        seen.add(key.value)
    return text, match, node


def bindings(data, source, *, required=False):
    """Read YAML scalars literally, including spaces and Markdown characters."""
    yaml = _yaml()
    _, _, header = _header(data, source)
    workspace = next((value for key, value in header.value if key.value == 'wsp'), None)
    if workspace is None:
        if required:
            raise ValueError(f'{source}: wsp must be in the initial YAML front matter.')
        return {}
    if not isinstance(workspace, yaml.MappingNode):
        raise ValueError(f'{source}: wsp requires a flat mapping of link names to directory paths.')
    result, folded = {}, set()
    for key, value in workspace.value:
        if not isinstance(key, yaml.ScalarNode) or key.tag != 'tag:yaml.org,2002:str':
            raise ValueError(f'{source}: wsp link names must be text.')
        label = name(key.value, f'{source}: wsp')
        if label.casefold() in folded:
            raise ValueError(f'{source}: duplicate or case-insensitive wsp name {label!r}.')
        if not isinstance(value, yaml.ScalarNode) or value.tag != 'tag:yaml.org,2002:str':
            raise ValueError(f'{source}: wsp[{label}] requires a text directory path.')
        target(Path('/'), value.value, f'{source}: wsp[{label}]')
        result[label] = value.value
        folded.add(label.casefold())
    return result


def add_bindings(data, source, additions):
    """Insert new pairs without rewriting existing YAML or authored Markdown."""
    current = bindings(data, source)
    for key, value in additions.items():
        name(key, str(source))
        target(Path('/'), value, str(source))
        if key.casefold() in {item.casefold() for item in current}:
            raise ValueError(f'{source}: wsp[{key}] already exists; resolve explicitly.')
    if not additions:
        return data
    text, match, header = _header(data, source)
    yaml = _yaml()
    workspace = next((value for key, value in header.value if key.value == 'wsp'), None)
    newline = '\r\n' if '\r\n' in text else '\n'
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    if workspace is not None:
        pair_key = next(key for key, _ in header.value if key.value == 'wsp')
        if workspace.start_mark.index < pair_key.end_mark.index:
            raise ValueError(f'{source}: edit an aliased wsp map manually before adding bindings.')
        if any(isinstance(token, yaml.tokens.AnchorToken)
               and workspace.start_mark.index <= token.start_mark.index < workspace.end_mark.index
               for token in yaml.scan(match['yaml'])):
            raise ValueError(f'{source}: edit an anchored wsp map manually before adding bindings.')
    if workspace is None:
        offset = match.end()
        insertion = 'wsp:' + newline + ''.join(f'  {quote(key)}: {quote(value)}{newline}' for key, value in additions.items())
    elif workspace.flow_style:
        # An alias refers to a different node span; changing it would change
        # another field. Reject it rather than rewriting shared authored YAML.
        offset = match.start('yaml') + workspace.end_mark.index - 1
        insertion = (', ' if workspace.value else '') + ', '.join(f'{quote(key)}: {quote(value)}' for key, value in additions.items())
    else:
        if not workspace.value:
            raise ValueError(f'{source}: use wsp: {{}} for an empty map.')
        last = workspace.value[-1][1]
        offset = text.find('\n', match.start('yaml') + last.end_mark.index)
        if offset < 0:
            raise ValueError(f'{source}: cannot append to the workspace map.')
        offset += 1
        indent = ' ' * workspace.value[0][0].start_mark.column
        insertion = ''.join(f'{indent}{quote(key)}: {quote(value)}{newline}' for key, value in additions.items())
    result = (text[:offset] + insertion + text[offset:]).encode('utf-8')
    expected = dict(current, **additions)
    if bindings(result, source) != expected:
        raise ValueError(f'{source}: wsp insertion would change existing bindings; edit the map manually.')
    return result


def legacy(root):
    config = root / '.yap/cfg/machine.json'
    before = snapshot(config)
    try:
        settings = json.loads(before) if before is not None else {}
    except (ValueError, UnicodeError) as error:
        raise ValueError(f'{config}: invalid JSON.') from error
    if not isinstance(settings, dict) or not isinstance(settings.get('links', {}), dict):
        raise ValueError(f'{config}: expected a links mapping.')
    return config, before, settings


def require_migrated(root):
    config, _, settings = legacy(root)
    if settings.get('links'):
        raise ValueError(f'{config}: legacy bindings require `workspace migrate` (preview; --apply executes it).')


def link_state(path):
    safe_path(path.parent)
    if path.is_symlink():
        return os.readlink(path)
    if path.exists():
        raise ValueError(f'{path}: navigation path is not a symlink; preserve real content and resolve explicitly.')
    return None


@dataclass(frozen=True)
class Link:
    path: Path
    before: str | None
    target: Path | None


def link_change(path, destination):
    safe_path(path.parent)
    if path.parent.exists():
        if not path.parent.is_dir():
            raise ValueError(f'{path.parent}: expected a workspace directory.')
        if any(sibling.name.casefold() == path.name.casefold() and sibling.name != path.name
               for sibling in path.parent.iterdir()):
            raise ValueError(f'{path}: case-insensitive navigation collision.')
    if destination is not None:
        resolved = destination.resolve()
        parent = path.parent.resolve()
        if (resolved == parent or resolved in parent.parents
                or destination == path or path in destination.parents
                or resolved == parent / path.name or parent / path.name in resolved.parents):
            raise ValueError(f'{path}: binding target would contain its own navigation link (cycle).')
        if destination.exists() and not destination.is_dir():
            raise ValueError(f'{path}: workspace target is not a directory.')
    return Link(path, link_state(path), destination)


def validate_targets(changes):
    """A workspace target cannot depend on another generated shortcut."""
    paths = {change.path for change in changes}
    for change in changes:
        if change.target is None:
            continue
        for destination in (change.target, change.target.resolve()):
            if any(destination == path or path in destination.parents for path in paths):
                raise ValueError(f'{change.path}: workspace target traverses generated navigation (cycle).')


def plan_entry(root, entry, values=None):
    values = entry['workspace'] if values is None else values
    folder = entry['folder'] / 'wsp'
    safe_path(folder)
    if folder.exists() and not folder.is_dir():
        raise ValueError(f'{folder}: expected a workspace directory.')
    changes, messages = [], []
    for label, value in values.items():
        destination = target(root, value, f'{entry["source"]}: wsp[{label}]')
        changes.append(link_change(folder / label, destination))
        if not destination.is_dir():
            messages.append(f'{entry["key"]}/{label}: local target unavailable ({value}).')
    if folder.is_dir():
        declared = {label.casefold() for label in values}
        for path in sorted(folder.iterdir()):
            if path.is_symlink() and path.name.casefold() not in declared:
                messages.append(f'{entry["key"]}/{path.name}: undeclared workspace shortcut preserved; remove it explicitly if obsolete.')
            elif path.name.casefold() in declared and path.name not in values:
                raise ValueError(f'{path}: case-insensitive navigation collision.')
    validate_targets(changes)
    return changes, messages


def plan(root, entries):
    root = Path(root).resolve()
    require_migrated(root)
    changes, messages = [], []
    for entry in entries.values():
        if entry['kind'] not in {'activity', 'area'}:
            continue
        for old in LEGACY_NAMES:
            if (entry['folder'] / old).is_symlink():
                raise ValueError(f'{entry["folder"] / old}: legacy navigation requires `workspace migrate`.')
        planned, warnings = plan_entry(root, entry)
        changes.extend(planned)
        messages.extend(warnings)
    validate_targets(changes)
    return changes, messages


def sync(changes):
    """Validate every path before the first mutation, then recheck each write."""
    validate_targets(changes)
    for change in changes:
        if link_state(change.path) != change.before:
            raise ValueError(f'{change.path}: navigation changed since planning; create a new plan.')
    for change in changes:
        path = change.path
        if link_state(path) != change.before:
            raise ValueError(f'{path}: navigation changed during reconciliation.')
        if change.target is not None and change.before == str(change.target):
            continue
        if path.is_symlink():
            path.unlink()
        if change.target is not None:
            safe_path(path.parent)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(change.target, target_is_directory=True)
    for folder in {change.path.parent for change in changes if change.path.parent.name == 'wsp'}:
        safe_path(folder)
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()


def write(path, before, after):
    """Replace one checked file atomically, retaining its permission bits."""
    if snapshot(path) != before:
        raise ValueError(f'{path}: source/configuration changed since planning.')
    if before == after:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.wsp-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(after)
        if path.exists():
            temporary.chmod(path.stat().st_mode & 0o777)
        if snapshot(path) != before:
            raise ValueError(f'{path}: source/configuration changed during write.')
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
