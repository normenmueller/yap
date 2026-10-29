"""Discover explicitly identified portfolio entries, independent of filing depth.

Areas and activities live under act; explicitly managed notes live under nts. Ordinary notes
and folders remain ordinary files. This module does not assign tracking, membership
or presentation roles.
"""

from pathlib import Path
import os
import re
import unicodedata

from . import content
from .files import LOCAL_NAMES
from . import workspace_links


KINDS = {'act': ('area', 'activity'), 'nts': ('note',)}
EXCLUDED = {'res', *LOCAL_NAMES}


def folded(value):
    return unicodedata.normalize('NFC', value).casefold()


def stable_key(value, source, *, qualified=True):
    segment = r'[A-Za-z0-9][A-Za-z0-9_-]*'
    pattern = segment + (rf'(?:/{segment})*' if qualified else '')
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        qualification = ('Slash-separated module segments are allowed; # is reserved for anchors. '
                         if qualified else 'Expected a single token without slashes. ')
        raise ValueError(f'{source}: key requires letters, digits, hyphens or underscores, '
                         'starting each segment with a letter or digit; '
                         + qualification + 'Keys are independent of paths.')
    return value


def literal(meta, field, source):
    """Identity fields must not be silently normalized by Markdown formatting."""
    value = meta.get(field)
    if value and (value['t'] != 'MetaString' and
                  (value['t'] != 'MetaInlines' or
                   any(item['t'] != 'Str' for item in value['c']))):
        raise ValueError(f'{source}: {field} must be a literal text token without Markdown '
                         'formatting; use plain text without emphasis or escapes.')
    return content.metadata(meta, field, source)


def discover(root):
    """Return the unique keyed catalog; never traverse local/external shortcuts."""
    root = Path(root).resolve()
    entries, keys = {}, {}
    for collection, allowed_kinds in KINDS.items():
        base = root / 'pfo' / collection
        for ancestor in (root / 'pfo', base):
            if ancestor.is_symlink():
                raise ValueError(f'{ancestor}: source collection cannot be a symlink.')
        if not base.exists():
            continue
        if not base.is_dir():
            raise ValueError(f'{base}: expected a source collection directory.')

        def fail(error):
            raise ValueError(f'Cannot scan source directory {error.filename}: {error.strerror}') from error

        for current, directories, files in os.walk(base, followlinks=False, onerror=fail):
            folder = Path(current)
            directories[:] = sorted(name for name in directories
                                     if name not in EXCLUDED and not name.startswith('.')
                                     and not (folder / name).is_symlink())
            names = {}
            for name in directories:
                normalized = folded(name)
                if normalized in names:
                    raise ValueError(f'{folder}: case-insensitive folder collision: '
                                     f'{names[normalized]!r}, {name!r}.')
                names[normalized] = name
            # Activities own same-named folders; notes are explicitly marked files.
            candidates = (sorted(folder / name for name in files
                                 if name.endswith('.md') and not name.startswith('.'))
                          if collection == 'nts' else
                          [] if folder == base else [folder / (folder.name + '.md')])
            for source in candidates:
                if source.is_symlink() or not source.is_file():
                    continue
                document = content.public_content(content.read(source))
                meta = document['meta']
                kind = literal(meta, 'kind', source)
                if not kind:
                    continue
                if kind not in allowed_kinds:
                    raise ValueError(f'{source}: kind must be {" or ".join(allowed_kinds)} in pfo/{collection}.')
                key = stable_key(literal(meta, 'key', source), source)
                title = content.metadata(meta, 'title', source)
                if not title:
                    raise ValueError(f'{source}: title is required for {kind}.')
                if folded(key) in keys:
                    raise ValueError(f'{source}: duplicate entry key {key!r}; already used by {keys[folded(key)]}.')
                keys[folded(key)] = source
                entries[key] = dict(key=key, kind=kind, title=title, folder=folder,
                                    source=source, document=document,
                                    workspace=workspace_links.bindings(source.read_bytes(), source) if kind in {'area', 'activity'} else {},
                                    acronym=content.metadata(meta, 'acronym', source),
                                    caption=content.metadata(meta, 'board-caption', source))
    return entries


def entry_root(entry):
    """A free-file note owns its document, never the containing topic directory."""
    return (entry['folder'] if entry['source'].name == entry['folder'].name + '.md'
            and entry['folder'].parent.name != 'pfo'
            else entry['source'])
