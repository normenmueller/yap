"""Read yap's authored tree and goals using Pandoc as the Markdown/YAML parser."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from urllib.parse import unquote, urlsplit


from .files import LOCAL_NAMES


STATUSES = {"ibx", "wip", "on hold", "released"}
PRIORITIES = {"p1", "p2", "p3", "p4"}
EXCLUDED = {"res", *LOCAL_NAMES}


def walk(value):
    """Yield all Pandoc AST objects, including nested table content."""
    if isinstance(value, dict):
        if "t" in value:
            yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def plain(value):
    """Plain text for metadata/labels without serializing Markdown syntax."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(plain(part) for part in value)
    if not isinstance(value, dict):
        return str(value)
    kind, content = value.get("t"), value.get("c")
    if kind in {"Space", "SoftBreak", "LineBreak"}:
        return " "
    if kind in {"Code", "CodeBlock", "Math"}:
        return content[1]
    if kind in {"Link", "Image", "Span"}:
        return plain(content[1])
    if kind == "Header":
        return plain(content[2])
    if kind == "Quoted":
        return plain(content[1])
    if kind in {"RawInline", "RawBlock"}:
        return ""
    return plain(content)


def read(path, reader="markdown-smart"):
    result = subprocess.run(
        ["pandoc", "--from=" + reader, "--to=json", str(path)],
        text=True, capture_output=True,
    )
    if result.returncode:
        raise ValueError(f"{path}: Pandoc: {result.stderr.strip()}")
    document = json.loads(result.stdout)
    if 'wsp' in document['meta']:
        from . import workspace_links
        source = Path(path)
        collection = next((parent for parent in source.parents
                           if parent.name == 'act' and parent.parent.name == 'pfo'), None)
        if (metadata(document['meta'], 'kind', path) not in {'activity', 'area'}
                or source.name != source.parent.name + '.md'
                or collection is None or source.parent == collection):
            raise ValueError(f'{path}: wsp belongs only in an activity or area source.')
        workspace_links.bindings(Path(path).read_bytes(), path, required=True)
        # No private path enters public_content traversal, model caches or renderers.
        document['meta'].pop('wsp')
    return document


def public_content(value):
    """Discard source-only blocks before validation, linking or rendering."""
    if isinstance(value, list):
        return [public_content(item) for item in value
                if not (isinstance(item, dict) and item.get("t") == "Div"
                        and {"navigation", "internal"}.intersection(item["c"][0][1]))]
    if isinstance(value, dict):
        return {key: public_content(child) for key, child in value.items()}
    return value


def metadata(meta, key, path):
    value = meta.get(key)
    if value and value["t"] not in {"MetaString", "MetaInlines"}:
        raise ValueError(f"{path}: {key} must be a single text value.")
    if key in {'slogan', 'board-caption'} and value:
        from copy import deepcopy
        value = deepcopy(value)
        for item in walk(value):
            if item['t'] in {'SoftBreak', 'LineBreak'}:
                item['t'], item['c'] = 'Str', '\n'
    return plain(value).strip()


def activity_tracking(meta):
    """Read explicit status/priority assignments, independently of ordering."""
    if "tracking" not in meta:
        return {}
    value = meta["tracking"]
    if value["t"] != "MetaMap":
        raise ValueError("pfo/act/act.md: tracking requires a mapping from activity keys to status/priority.")
    result = {}
    next_references = {}
    for key, entry in value["c"].items():
        label = f"pfo/act/act.md: tracking[{key}]"
        if entry["t"] != "MetaMap":
            raise ValueError(f"{label} requires a mapping with status and/or priority.")
        fields = entry["c"]
        for field in fields:
            if field not in {"status", "priority", "next"}:
                raise ValueError(f"{label}: unknown field {field!r}; allowed fields are status, priority, and next.")
        result[key] = {}
        for field, allowed in (("status", STATUSES), ("priority", PRIORITIES)):
            text = metadata(fields, field, label)
            if text and text not in allowed:
                raise ValueError(f"{label}: unknown {field}: {text}.")
            result[key][field] = text
        if result[key]['status'] == 'released' and 'priority' in fields:
            raise ValueError(f'{label}: status released does not allow priority; remove priority.')
        if 'next' in fields:
            rank = metadata(fields, 'next', label)
            if rank not in {'1', '2', '3'}:
                raise ValueError(f'{label}: next must be 1, 2, or 3; omit it when unassigned.')
            if result[key]['status'] != 'on hold':
                raise ValueError(f'{label}: next is allowed only with status on hold; remove next when changing status.')
            if rank in next_references:
                raise ValueError(f'{label}: next {rank} is already assigned to {next_references[rank]!r}; '
                                 'each number must be unique across the portfolio.')
            next_references[rank] = key
            result[key]['next'] = int(rank)
    return result


def anchors(blocks, path):
    result = set()
    for item in walk(blocks):
        kind = item["t"]
        attr = (item["c"][1] if kind == "Header" else item["c"][0]
                if kind in {"Div", "Span", "CodeBlock", "Table", "Figure"} else None)
        if attr and attr[0]:
            if attr[0] in result:
                raise ValueError(f"{path}: duplicate anchor #{attr[0]}.")
            result.add(attr[0])
        if kind == "Header":
            attrs = dict(item["c"][1][2])
            if 'next' in attrs:
                raise ValueError(f'{path}: next belongs in pfo/act/act.md tracking, not heading attributes.')
            for field, allowed in (("status", STATUSES), ("priority", PRIORITIES)):
                if attrs.get(field) and attrs[field] not in allowed:
                    raise ValueError(f"{path}: unknown {field}: {attrs[field]}.")
            if attrs.get('status') == 'released' and 'priority' in attrs:
                raise ValueError(f'{path}#{attr[0]}: status released does not allow priority; remove priority.')
    return result


def activity_versions(blocks, path):
    """Explicit version sections are board views of one activity, never nodes."""
    versions = []
    labels = set()
    for item in walk(blocks):
        if item['t'] != 'Header' or 'version' not in item['c'][1][1]:
            continue
        level, (anchor, _, pairs), title = item['c']
        label = plain(title).strip()
        attrs = dict(pairs)
        if level != 2 or not label or not anchor:
            raise ValueError(f'{path}: .version requires a ## heading with a version name and anchor.')
        if label in labels:
            raise ValueError(f'{path}: duplicate version {label!r}.')
        if {'status', 'priority', 'next'} & attrs.keys():
            raise ValueError(f'{path}#{anchor}: version status, priority, and next belong in '
                             'pfo/act/act.md tracking under activity-key#anchor.')
        labels.add(label)
        versions.append(dict(anchor=anchor, label=label))
    return versions


def apply_activity_tracking(nodes, tracking):
    """Resolve central tracking to activities or public versions, never both."""
    by_key = {node['key']: node for node in nodes}
    for reference, fields in tracking.items():
        key, separator, anchor = reference.partition('#')
        where = f'pfo/act/act.md: tracking[{reference}]'
        if key not in by_key:
            raise ValueError(f'{where}: unknown activity key {key!r}.')
        node = by_key[key]
        if separator:
            version = next((v for v in node['versions'] if v['anchor'] == anchor), None)
            if version is None:
                raise ValueError(f'{where}: unknown public version anchor {anchor!r}.')
            version.update(fields)
        else:
            if node['versions']:
                raise ValueError(f'{where}: versioned activities must be tracked only by '
                                 'activity-key#anchor; remove the activity-level entry.')
            node.update(fields)
    for node in nodes:
        for version in node['versions']:
            if not version.get('status'):
                reference = node['key'] + '#' + version['anchor']
                raise ValueError(f'pfo/act/act.md: tracking[{reference}]: '
                                 'each public version requires a status.')


def local_target(target, source, root, aspiration_sources=()):
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        if parts.scheme.casefold() not in {"http", "https", "mailto", "tel"}:
            raise ValueError(f"{source.relative_to(root)}: nonportable link {target!r}.")
        return None
    if parts.path.startswith(("/", "~")):
        raise ValueError(f"{source.relative_to(root)}: absolute link {target!r}.")
    lexical = Path(os.path.normpath(source.parent / unquote(parts.path))) if parts.path else source
    dest = (source.parent / unquote(parts.path)).resolve() if parts.path else source
    selected_source = lexical in aspiration_sources and dest == lexical
    for name in LOCAL_NAMES:
        if name in Path(unquote(parts.path)).parts and not selected_source:
            raise ValueError(f"{source.relative_to(root)}: {name} is for local navigation only: {target!r}.")
    if not dest.is_relative_to(root):
        raise ValueError(f"{source.relative_to(root)}: link outside the project: {target!r}.")
    return dest, unquote(parts.fragment)


def entry_fields(meta, source, root):
    """Validate shared authored fields without assigning identity or hierarchy."""
    fields = {key: metadata(meta, key, source) for key in
              ("title", "acronym", "board-caption", "subtitle", "slogan", "url")}
    for field in (*LOCAL_NAMES, 'file'):
        if field in meta:
            raise ValueError(f'{source.relative_to(root)}: {field} bindings require a source-owned wsp mapping.')
    synonyms = meta.get('synonyms', {'t': 'MetaList', 'c': []})
    if synonyms['t'] != 'MetaList':
        raise ValueError(f'{source.relative_to(root)}: synonyms requires a list of alternative names.')
    fields['synonyms'] = []
    for value in synonyms['c']:
        synonym = metadata({'synonym': value}, 'synonym', source)
        if not synonym or synonym in fields['synonyms']:
            raise ValueError(f'{source.relative_to(root)}: synonyms contains an empty or duplicate name.')
        fields['synonyms'].append(synonym)
    if not fields["title"]:
        raise ValueError(f"{source.relative_to(root)}: title is missing.")
    for field in ("status", "priority", "next"):
        if field in meta:
            raise ValueError(f"{source.relative_to(root)}: {field} is maintained under tracking in pfo/act/act.md.")
    if fields["url"]:
        url = urlsplit(fields["url"])
        if url.scheme not in {"http", "https"} or not url.netloc:
            raise ValueError(f"{source.relative_to(root)}: url requires a complete HTTP(S) address.")
    return fields


def reject_objective_graph(meta, source, objective_folder):
    for field in ('igraph', 'impact-graph'):
        if field in meta:
            raise ValueError(f'{source}: {field} is no longer supported; define activities in '
                             f'{objective_folder}/<objective-key>/<kr-key>.md. '
                             'Objective assignments are derived from KR activities.')


def load(root: Path, *, entries=None) -> dict:
    root = Path(root).resolve()
    from . import portfolio, projection
    from .files import resource_plan
    from .aspirations import resolve
    aspiration_paths = resolve(root)
    goal_source = aspiration_paths.goals.as_posix()
    objective_folder = aspiration_paths.objectives.as_posix()
    model = portfolio.load(root, entries=entries)
    nodes = model['nodes']
    main = {'meta': model['meta'], 'pandoc-api-version': model['api']}
    resources = resource_plan(root, model)
    published_resources = {path.resolve() for path in resources.values()}
    report = projection.load(root, model)
    sources = {root / node["path"]: node for node in nodes}
    known_anchors = {path: anchors([node["meta"].get("slogan", {}), node["blocks"]], path.relative_to(root))
                     for path, node in sources.items()}
    goal_path = root / aspiration_paths.goals
    goal_doc = public_content(read(goal_path))
    for field in ('title', 'subtitle', 'author', 'date', 'lang', 'tags'):
        value = metadata(goal_doc['meta'], field, goal_source)
        if field == 'title' and not value:
            raise ValueError(f'{goal_source}: title is missing from the YAML header.')
    control = goal_doc['meta']
    reject_objective_graph(control, goal_source, objective_folder)
    if 'okr-preview' in control:
        raise ValueError(f'{goal_source}: okr-preview has moved to {objective_folder}/<objective-key>/<kr-key>.md.')
    sequence = control.get('sequence', {'t': 'MetaList', 'c': []})
    if sequence['t'] != 'MetaList':
        raise ValueError(f'{goal_source}: sequence requires a list of objective keys.')
    order = []
    for item in sequence['c']:
        key = metadata({'item': item}, 'item', goal_source + ': sequence')
        if not key or key in order:
            raise ValueError(f'{goal_source}: sequence contains an empty or duplicate entry.')
        order.append(key)
    tracking = control.get('tracking', {'t': 'MetaMap', 'c': {}})
    if tracking['t'] != 'MetaMap':
        raise ValueError(f'{goal_source}: tracking requires a mapping.')
    assignments = {}
    for key, value in tracking['c'].items():
        label = f'{goal_source}: tracking[{key}]'
        if value['t'] != 'MetaMap' or set(value['c']) - {'status', 'priority'}:
            raise ValueError(label + ': allowed fields are status and priority.')
        fields = {field: metadata(value['c'], field, label) for field in ('status', 'priority')}
        if fields['status'] not in {'active', 'on hold', 'closed'}:
            raise ValueError(label + ': status requires active, on hold, or closed.')
        if fields['priority'] and fields['priority'] not in PRIORITIES:
            raise ValueError(label + ': priority requires p1 through p4.')
        assignments[key] = fields
    folder = root / aspiration_paths.objectives
    goals = []
    known_anchors[goal_path] = set()
    for path in sorted(folder.iterdir()) if folder.exists() else []:
        if path.name.startswith('.'):
            continue
        if path.is_dir() and not path.is_symlink():
            continue  # KR folders are validated after all objective keys are known.
        if path.is_symlink() or not path.is_file() or path.suffix != '.md':
            raise ValueError(f'{path.relative_to(root)}: expected an objective file (*.md).')
        doc = public_content(read(path))
        label = path.relative_to(root).as_posix()
        if 'okr-preview' in doc['meta']:
            raise ValueError(f'{label}: define KRs in {objective_folder}/{metadata(doc["meta"], "key", label)}/<kr-key>.md.')
        reject_objective_graph(doc['meta'], label, objective_folder)
        for field in ('status', 'priority', 'tracking', 'sequence'):
            if field in doc['meta']:
                raise ValueError(f'{label}: {field} is maintained centrally in {goal_source}.')
        title = metadata(doc['meta'], 'title', label)
        key = metadata(doc['meta'], 'key', label)
        if not title or not key:
            raise ValueError(f'{label}: title and a stable key are missing from the YAML header.')
        fields = {field: metadata(doc['meta'], field, label) for field in ('url', 'timeline')}
        if fields['url']:
            url = urlsplit(fields['url'])
            if url.scheme not in {'http', 'https'} or not url.netloc:
                raise ValueError(f'{label}: url requires a complete HTTP(S) address.')
        if any(not (char.isascii() and (char.isalnum() or char in '-_')) for char in key):
            raise ValueError(f'{label}: key allows letters, digits, hyphens, and underscores.')
        identifier = 'goal-' + key
        if key not in assignments:
            raise ValueError(f'{goal_source}: tracking[{key}]: status is missing.')
        body_anchors = anchors(doc['blocks'], label)
        if identifier in body_anchors or identifier in known_anchors[goal_path]:
            raise ValueError(f'{label}: duplicate objective ID {identifier}.')
        duplicates = known_anchors[goal_path] & body_anchors
        if duplicates:
            raise ValueError(f'{label}: duplicate anchors: {", ".join(sorted(duplicates))}.')
        known_anchors[path] = {identifier, *body_anchors}
        known_anchors[goal_path].update(known_anchors[path])
        goals.append(dict(key=key, path=label, id=identifier, title=title,
                          meta=doc['meta'], blocks=doc['blocks'], activities=[], **fields, **assignments[key]))
    keys = {goal['key'] for goal in goals}
    for key in [*order, *assignments]:
        if key not in keys:
            raise ValueError(f'{goal_source}: unknown objective {key!r}.')
    ranks = {key: index for index, key in enumerate(order)}
    goals.sort(key=lambda goal: (ranks.get(goal['key'], len(ranks)), goal['key'].casefold(), goal['key']))

    # Local anchors and node IDs can each be unique yet collide once combined:
    # a parent heading #y and its child x/y both used to publish act-x--y.
    from .documents import pdf_target
    for entries, include_slogan in ((nodes, True), (goals, False)):
        destinations = {}
        for entry in entries:
            blocks = [entry['blocks']]
            if include_slogan:
                blocks.append(entry['meta'].get('slogan', {}))
            for anchor in ['', *sorted(anchors(blocks, entry['path']))]:
                target = pdf_target(entry['id'] + ('--' + anchor if anchor else ''))
                source = entry['path'] + ('#' + anchor if anchor else '')
                if target in destinations:
                    raise ValueError(f'Duplicate PDF destination {target}: {destinations[target]} and {source}. '
                                     'Rename one of the anchors or keys.')
                destinations[target] = source

    aspiration_sources = {goal_path, *(root / goal['path'] for goal in goals)}

    def validate(blocks, path):
        for item in walk(blocks):
            if item["t"] not in {"Link", "Image"}:
                continue
            target = item["c"][2][0]
            local = local_target(target, path, root, aspiration_sources=aspiration_sources)
            if local is None:
                continue
            dest, anchor = local
            if not dest.is_file():
                raise ValueError(f"{path.relative_to(root)}: Link target is missing: {target!r}.")
            if dest in known_anchors:
                if item["t"] == "Image":
                    raise ValueError(f"{path.relative_to(root)}: Markdown document is not an image: {target!r}.")
                if anchor and anchor not in known_anchors[dest]:
                    raise ValueError(f"{path.relative_to(root)}: Anchor is missing: {target!r}.")
            elif dest not in published_resources:
                raise ValueError(f"{path.relative_to(root)}: Link target is not published: {target!r}.")

    for path, node in sources.items():
        validate(node["meta"].get("slogan", {}), path)
        validate(node["blocks"], path)
    for goal in goals:
        validate(goal["blocks"], root / goal["path"])
    from .dgraph import parse as dependency_graph
    from .impact import assign as assign_objective_activities
    from .performance import load as key_results
    activities = [node for node in nodes if node['kind'] == 'activity']
    model.update(goals=goals, report=report, goal_meta=goal_doc['meta'], goal_source=goal_source,
                 key_results=key_results(root, activities, goals, aspiration_paths),
                 dgraph=dependency_graph(main['meta'], nodes, model['members'], report))
    assign_objective_activities(goals, model['key_results'], activities)
    from .work_progress import load_preview
    model['work_preview'] = load_preview(root, activities, model['key_results'])
    for goal in goals:
        notes = goal['meta'].get('activity-notes')
        if notes is None:
            continue
        label = goal['path'] + ': activity-notes'
        if notes['t'] != 'MetaMap':
            raise ValueError(label + ': expected activity keys mapped to text and section.')
        relations = {item['key']: item for item in goal['activities']}
        sections = {item['c'][1][0]: plain(item['c'][2]) for item in goal['blocks']
                    if item['t'] == 'Header' and item['c'][0] == 2}
        for key, note in notes['c'].items():
            if key not in relations:
                raise ValueError(f'{label}: {key!r} is not linked to this objective.')
            if note['t'] != 'MetaMap' or set(note['c']) != {'text', 'section'}:
                raise ValueError(f'{label}[{key}]: expected text and section.')
            text = metadata(note['c'], 'text', label)
            section = metadata(note['c'], 'section', label)
            if not text or section not in sections:
                raise ValueError(f'{label}[{key}]: text and an existing level-two section are required.')
            relations[key]['note'] = dict(text=text, section=section, label=sections[section])
    return model
