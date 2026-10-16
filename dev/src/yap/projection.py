"""Project saved placements without giving groups canonical domain identity."""

from . import catalog, perspectives


ROLES = {'group', 'context', 'category', 'lane'}
TONES = {'neutral', 'support', 'impact', 'governance', 'epistemics', 'strategy'}
STYLES = {'plain', 'chapter', 'card'}


def outline(definition, entries):
    """One saved tree owns ordering; annotations refer only to placement IDs.

    A group's heading-source consumes one direct child document leaf for display.
    It never assigns membership, source parentage, status inheritance or identity
    to the directory. Repeated sources become references after their first body.
    """
    perspectives.validate(definition, entries)
    presentation = definition.get('presentation', {})
    if not isinstance(presentation, dict) or set(presentation) - {'placements', 'board', 'flow'}:
        raise ValueError('Report presentation accepts only placements, board and flow.')
    annotations = presentation.get('placements', {})
    if not isinstance(annotations, dict):
        raise ValueError('Report presentation.placements requires a mapping.')
    if any(not isinstance(key, str) for key in annotations):
        raise ValueError('Presentation placement IDs must be text.')
    if any(not isinstance(fields, dict) for fields in annotations.values()):
        raise ValueError('Each placement annotation requires a mapping.')
    flat = {item['id']: item for item in perspectives.flatten(definition['entries']).values()}
    unknown = set(annotations) - set(flat)
    if unknown:
        raise ValueError('Unknown presentation placements: ' + ', '.join(sorted(unknown)))
    map_paths = set()
    for identifier, fields in annotations.items():
        if not isinstance(fields, dict) or set(fields) - {
                'role', 'heading-source', 'category', 'tone', 'document-style', 'map', 'map-path', 'board-card', 'board-label', 'board-rail-caption'}:
            raise ValueError(f'{identifier}: unknown presentation fields.')
        item = flat[identifier]
        group = 'entries' in item
        role = fields.get('role', 'group')
        if 'board-label' in fields and (not group or fields['board-label'] not in ('horizontal', 'vertical')):
            raise ValueError(f'{identifier}: board-label requires horizontal/vertical on a group.')
        if 'board-rail-caption' in fields and (not group or type(fields['board-rail-caption']) is not bool):
            raise ValueError(f'{identifier}: board-rail-caption requires a boolean on a group.')
        if not isinstance(role, str) or role not in ROLES or ('role' in fields and not group):
            raise ValueError(f'{identifier}: presentation roles apply only to groups.')
        if 'tone' in fields and (not isinstance(fields['tone'], str) or fields['tone'] not in TONES):
            raise ValueError(f'{identifier}: unknown tone.')
        style = fields.get('document-style', 'plain')
        if not isinstance(style, str) or style not in STYLES:
            raise ValueError(f'{identifier}: unknown document-style.')
        if 'map' in fields and (not group or fields['map'] != 'subtree'):
            raise ValueError(f'{identifier}: map requires subtree on a group.')
        if 'map-path' in fields and fields.get('map') != 'subtree':
            raise ValueError(f'{identifier}: map-path requires a subtree map.')
        if fields.get('map') == 'subtree':
            route = fields.get('map-path', identifier)
            if not isinstance(route, str):
                raise ValueError(f'{identifier}: map-path requires a text token.')
            catalog.stable_key(route, f'{identifier}: map-path', qualified=False)
            if route.casefold() in map_paths:
                raise ValueError(f'{identifier}: duplicate map-path {route!r}.')
            map_paths.add(route.casefold())
        if 'category' in fields and (role != 'category' or not isinstance(fields['category'], str)
                                     or not fields['category']):
            raise ValueError(f'{identifier}: category token requires category role.')
        if role == 'category' and 'category' not in fields:
            raise ValueError(f'{identifier}: category role requires a category token.')
        if 'board-card' in fields:
            if group or not isinstance(fields['board-card'], str) or fields['board-card'] not in {'always', 'tracked', 'never'}:
                raise ValueError(f'{identifier}: board-card requires always/tracked/never on a leaf.')
        if 'heading-source' in fields:
            children = {child['id']: child for child in item.get('entries', [])}
            source_id = fields['heading-source']
            selected = children.get(source_id) if isinstance(source_id, str) else None
            if selected is None or 'target' not in selected:
                raise ValueError(f'{identifier}: heading-source must name a direct child source leaf.')
            target = selected['target']
            entry = entries[target['entry']]
            if target.get('path', entry['source'].name) != entry['source'].name:
                raise ValueError(f'{identifier}: heading-source must target a complete source document.')
            if set(annotations.get(source_id, {})) - {'board-card'}:
                raise ValueError(f'{source_id}: heading-source display annotations belong on group '
                                 f'{identifier}; only board-card belongs on the consumed leaf.')
    board = presentation.get('board', {})
    if not isinstance(board, dict) or set(board) - {'category-order', 'flow', 'grouping'}:
        raise ValueError('Report presentation.board accepts only category-order, flow and grouping.')
    grouping = board.get('grouping', 'own')
    if grouping not in ('own', 'overview'):
        raise ValueError('Board grouping must be own or overview.')
    if grouping == 'overview' and (board.get('category-order') or board.get('flow')):
        raise ValueError('Board overview grouping inherits category-order and flow.')
    categories = {fields['category'] for fields in annotations.values() if 'category' in fields}
    order = board.get('category-order', [])
    if not isinstance(order, list) or any(not isinstance(c, str) or c not in categories for c in order) or len(set(order)) != len(order):
        raise ValueError('Board category-order requires distinct known category tokens.')
    flow = board.get('flow', [])
    if not isinstance(flow, list) or any(not isinstance(pair, list) or len(pair) != 2
                                       or any(not isinstance(c, str) or c not in categories for c in pair)
                                       or pair[0] == pair[1] for pair in flow):
        raise ValueError('Board flow requires pairs of distinct known category tokens.')

    result, published, context_categories = [], set(), {}

    def visit(items, parent='', depth=1, context='', category='', tone='neutral'):
        for item in items:
            identifier = item['id']
            fields = annotations.get(identifier, {})
            group = 'entries' in item
            source_leaf = flat[fields['heading-source']] if 'heading-source' in fields else None
            target = source_leaf['target'] if source_leaf else item.get('target')
            entry = entries[target['entry']] if target else None
            document = entry is not None and target.get('path', entry['source'].name) == entry['source'].name
            role = fields.get('role', 'group') if group else 'leaf'
            current_context = identifier if role == 'context' else context
            current_category = fields.get('category', category)
            current_tone = fields.get('tone', tone)
            if role == 'category':
                seen = context_categories.setdefault(current_context, set())
                if current_category in seen:
                    raise ValueError(f'{identifier}: duplicate category {current_category!r} in one context.')
                seen.add(current_category)
            options = annotations.get(source_leaf['id'], {}) if source_leaf else fields
            card_mode = options.get('board-card', 'never' if source_leaf or item.get('display', 'card') != 'card' else 'always')
            activity = document and entry['kind'] == 'activity'
            canonical_key = entry['key'] if entry else None
            render_body = document and canonical_key not in published
            if render_body:
                published.add(canonical_key)
            result.append(dict(placement=identifier, parent=parent, depth=depth, role=role,
                               entry=canonical_key, source_placement=source_leaf['id'] if source_leaf else None,
                               target=target, document=document, render_body=render_body,
                               label=item.get('alias', item['name']),
                               title=entry['title'] if document else item.get('alias', item['name']),
                               context=current_context, category=current_category, tone=current_tone,
                               document_style=fields.get('document-style', 'plain'),
                               subtree_map=fields.get('map') == 'subtree',
                               map_path=fields.get('map-path', identifier),
                               board_label=fields.get('board-label', 'horizontal'),
                               board_rail_caption=fields.get('board-rail-caption', True),
                               board_card=card_mode if activity else 'never'))
            if group:
                consumed = fields.get('heading-source')
                visit([child for child in item['entries'] if child['id'] != consumed],
                      identifier, depth + 1, current_context, current_category, current_tone)

    visit(definition['entries'])
    graph = presentation.get('flow', {})
    if not isinstance(graph, dict) or set(graph) - {'columns', 'lanes', 'realm-lanes', 'edge-ports', 'align-centers', 'node-order', 'offset-y', 'unframe'}:
        raise ValueError('Unknown Flow presentation field.')
    columns = graph.get('columns', [])
    if not isinstance(columns, list) or any(not isinstance(col, list) or not col for col in columns):
        raise ValueError('Flow columns requires a list of nonempty placement lists.')
    eligible = {p['placement']: p['entry'] for p in result
                if p['document'] and entries[p['entry']]['kind'] == 'activity'}
    seen = set()
    for col in columns:
        for identifier in col:
            if not isinstance(identifier, str) or identifier not in eligible:
                raise ValueError('Flow columns must reference selected activity placements.')
            key = eligible[identifier]
            if key in seen:
                raise ValueError('Flow columns contains a repeated activity: ' + key)
            seen.add(key)
    lanes = graph.get('lanes', [])
    if not isinstance(lanes, list):
        raise ValueError('Flow lanes requires a list.')
    lane_keys, lane_columns = set(), set()
    for lane in lanes:
        if not isinstance(lane, dict) or set(lane) != {'key', 'label', 'tone', 'columns'}:
            raise ValueError('Each Flow lane requires key, label, tone and columns.')
        if any(not isinstance(lane[k], str) or not lane[k] for k in ('key', 'label', 'tone')):
            raise ValueError('Flow lane key, label and tone must be nonempty text.')
        span = lane['columns']
        if (lane['key'] in lane_keys or lane['tone'] not in TONES or not isinstance(span, list)
                or not span or any(type(i) is not int or not 1 <= i <= len(columns) for i in span)
                or span != list(range(span[0], span[-1]+1)) or lane_columns.intersection(span)):
            raise ValueError('Flow lanes require unique keys, known tones and nonoverlapping contiguous columns.')
        lane_keys.add(lane['key']); lane_columns.update(span)
    if lanes and lane_columns != set(range(1, len(columns)+1)):
        raise ValueError('Flow lanes must cover all configured columns.')
    realms = graph.get('realm-lanes', [])
    groups = {p['placement']: p for p in result if p['role'] != 'leaf'
              and (not p['entry'] or entries[p['entry']]['kind'] != 'activity')}
    if not isinstance(realms, list):
        raise ValueError('Flow realm-lanes requires a list of realm placements and section lists.')
    realm_ids, section_ids = set(), set()
    for realm in realms:
        if (not isinstance(realm, dict) or set(realm) != {'placement', 'sections'}
                or not isinstance(realm['placement'], str) or realm['placement'] not in groups
                or realm['placement'] in realm_ids or not isinstance(realm['sections'], list)
                or not realm['sections']):
            raise ValueError('Flow realm-lanes requires distinct selected group placements and section lists.')
        realm_ids.add(realm['placement'])
        for section in realm['sections']:
            if (not isinstance(section, str) or section not in groups or section in section_ids
                    or groups[section]['parent'] != realm['placement']):
                raise ValueError('Flow realm-lanes sections must be distinct direct groups within their realm.')
            section_ids.add(section)
    if realms and (columns or lanes):
        raise ValueError('Flow realm-lanes owns its layout; do not combine it with fixed columns or lanes.')
    ports = graph.get('edge-ports', [])
    if not isinstance(ports, list):
        raise ValueError('Flow edge-ports requires a list.')
    resolved_ports, port_pairs = [], set()
    for port in ports:
        if (not isinstance(port, dict) or not {'source', 'target', 'exit'} <= set(port)
                or set(port) - {'source', 'target', 'exit', 'entry', 'exit-position', 'entry-position'}
                or any(not isinstance(port[k], str) for k in ('source', 'target', 'exit'))
                or not isinstance(port.get('entry', 'left'), str)
                or port['source'] not in eligible or port['target'] not in eligible
                or port['exit'] not in {'top', 'right', 'bottom', 'left'}
                or port.get('entry', 'left') not in {'top', 'right', 'bottom', 'left'}):
            raise ValueError('Flow edge-ports requires activity source/target placements and a valid exit side.')
        source, target = eligible[port['source']], eligible[port['target']]
        if (source, target) in port_pairs:
            raise ValueError('Repeated Flow edge-ports pair.')
        port_pairs.add((source, target))
        resolved = dict(source=source, target=target, exit=port['exit'], entry=port.get('entry', 'left'))
        for field in ('exit-position', 'entry-position'):
            if field in port:
                value = port[field]
                if type(value) not in (int, float) or not 0 < value < 1:
                    raise ValueError('Flow port positions must be numbers strictly between 0 and 1.')
                resolved[field.replace('-', '_')] = value
        resolved_ports.append(resolved)
    aligned = graph.get('align-centers', [])
    if (not isinstance(aligned, list) or any(not isinstance(pair, list) or len(pair) != 2
            or any(not isinstance(p, str) or p not in eligible for p in pair) or pair[0] == pair[1] for pair in aligned)):
        raise ValueError('Flow align-centers requires pairs of distinct activity placements.')
    node_order = graph.get('node-order', [])
    if (not isinstance(node_order, list)
            or any(not isinstance(p, str) or p not in eligible for p in node_order)
            or len({eligible[p] for p in node_order}) != len(node_order)):
        raise ValueError('Flow node-order requires distinct selected activity placements.')
    offsets = graph.get('offset-y', {})
    if (not isinstance(offsets, dict)
            or any(p not in eligible or type(value) is not int for p, value in offsets.items())
            or len({eligible[p] for p in offsets}) != len(offsets)):
        raise ValueError('Flow offset-y requires distinct activity placements mapped to integer layout units.')
    unframe = graph.get('unframe', [])
    if (not isinstance(unframe, list) or (unframe and not realms)
            or any(not isinstance(p, str) or p not in eligible for p in unframe)
            or len({eligible[p] for p in unframe}) != len(unframe)):
        raise ValueError('Flow unframe requires distinct activity placements within realm-lanes.')
    return {'nodes': result, 'category_order': order, 'flow': flow, 'board_grouping': grouping,
            'graph_unframe': [eligible[p] for p in unframe],
            'graph_offset_y': {eligible[p]: value for p, value in offsets.items()},
            'graph_node_order': [eligible[p] for p in node_order],
            'graph_columns': [[eligible[p] for p in col] for col in columns],
            'graph_lanes': lanes, 'graph_realms': realms, 'graph_edge_ports': resolved_ports,
            'graph_align_centers': [[eligible[p] for p in pair] for pair in aligned]}


def runtime_leaves(keys):
    """Keep synthetic placement names separate from qualified entry identities."""
    return [{'id': f'p{index:06d}', 'name': f'p{index:06d}', 'alias': key,
             'target': {'entry': key}} for index, key in enumerate(keys, 1)]


def load(root, model):
    """Select a saved report perspective, or show all entries without filing rules."""
    import json
    from pathlib import Path
    entries = {node['key']: dict(node, folder=(root / node['path']).parent,
                                source=root / node['path'], caption=node.get('board-caption', ''))
               for node in model['nodes']}
    name = catalog.literal(model['meta'], 'report-perspective', 'pfo/act/act.md')
    if name:
        path = perspectives.real_path(root, Path('pov') / perspectives.component(name) / perspectives.DEFINITION)
        if not path.is_file():
            raise ValueError(f'{path}: selected report perspective is missing.')
        definition = json.loads(path.read_text())
    else:
        definition = {'schema': 1, 'title': 'All', 'entries': runtime_leaves(sorted(entries))}
    result = outline(definition, entries)
    represented = {item['entry'] for item in result['nodes'] if item['document']}
    missing = sorted(set(entries) - represented)
    if missing:
        # Runtime-only placements share the same renderer; never save them into
        # the user's curated perspective or assign semantic membership.
        extra = outline({'schema': 1, 'title': 'Unassigned', 'entries': [
            {'id': 'p000000', 'name': 'Unassigned', 'alias': 'Nicht eingeordnet',
             'entries': runtime_leaves(missing)}]}, entries)
        for item in extra['nodes']:
            item['placement'] = 'unassigned-' + item['placement']
            if item['parent']:
                item['parent'] = 'unassigned-' + item['parent']
        result['nodes'].extend(extra['nodes'])
    return result
