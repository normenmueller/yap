"""Read-only yapic perspectives; source facts and saved definitions stay unchanged."""

import json
import re

from . import catalog, perspectives, projection


GOAL_PERSPECTIVES = (
    ('', 'Alle Ziele', None),
    ('active', 'Aktive Ziele', 'active'),
    ('paused', 'Pausierte Ziele', 'on hold'),
    ('closed', 'Abgeschlossene Ziele', 'closed'),
)


def filename(selection=None, asset='index.html'):
    key = (selection or {}).get('key', '')
    if not key:
        return asset
    # Separate namespaces keep arbitrary saved names portable in HTML and TeX.
    stem = 'p-' + key if re.fullmatch(r'[A-Za-z0-9_-]+', key) else 'u-' + key.encode().hex()
    return stem + ('.html' if asset == 'index.html' else '-' + asset)


def prepare(root, model):
    """Read all saved activity perspectives, independently of unsaved local trees."""
    from . import dgraph
    entries = {node['key']: dict(node, folder=(root / node['path']).parent,
                                source=root / node['path']) for node in model['nodes']}
    selected = catalog.literal(model['meta'], 'report-perspective', 'pfo/act/act.md')
    reference = model['dgraph']
    reference_layout = dgraph.layout(reference) if reference.get('columns') else None
    result = [dict(key='', label='Überblick', report=model['report'], graph=model['dgraph'])]
    for path in sorted((root / 'pov').glob('*/' + perspectives.DEFINITION)):
        name = perspectives.component(path.parent.name)
        if name == selected:
            continue
        definition = json.loads(path.read_text())
        report = projection.outline(definition, entries)
        keys = {p['entry'] for p in report['nodes'] if p['document']
                and entries[p['entry']]['kind'] == 'activity'}
        graph = dependency_selection(dgraph.parse(model['meta'], model['nodes'], model['members'], report), keys)
        arrange_flow(graph, report, reference, reference_layout)
        board_report = (board_selection(model['report'], keys)
                        if report.get('board_grouping') == 'overview' else report)
        result.append(dict(key=name, label=definition['title'], report=report,
                           board_report=board_report, graph=graph))
    model['activity_perspectives'] = result


def board_selection(reference, keys):
    """Keep selected cards and their overview ancestors, never sibling cards."""
    by_id = {node['placement']: node for node in reference['nodes']}
    selected = [node for node in reference['nodes'] if node['document'] and node['entry'] in keys]
    missing = keys - {node['entry'] for node in selected}
    if missing:
        raise ValueError('Board overview grouping is missing activities: ' + ', '.join(sorted(missing)))
    keep = set()
    for node in selected:
        while node and node['placement'] not in keep:
            keep.add(node['placement'])
            node = by_id.get(node['parent'])
    nodes = [dict(node, board_card=node['board_card'] if node['entry'] in keys else 'never')
             for node in reference['nodes'] if node['placement'] in keep]
    return dict(reference, nodes=nodes)


def dependency_selection(graph, keys):
    """Induced subgraph of validated effective edges, never transitive shortcuts."""
    effective = [edge for edge in graph.get('effective_edges', graph['edges'])
                 if all(key in keys for key in edge)]
    by_key = {n['key']: n for n in graph['nodes']}
    nodes = []
    for node in graph['nodes']:
        if node['key'] not in keys:
            continue
        parent = node['parent']
        while parent and parent not in keys:
            parent = by_key[parent]['parent']
        nodes.append(dict(node, parent=parent))
    expansions = {node['key']: [node['key']] for node in nodes}
    edges, covered = [], set()
    for source, target in graph['edges']:
        a = graph.get('expansions', {}).get(source, [source])
        b = graph.get('expansions', {}).get(target, [target])
        if {source, target, *a, *b} <= keys:
            edges.append((source, target))
            expansions.update({source: a, target: b})
            covered.update((x, y) for x in a for y in b)
    edges.extend(tuple(edge) for edge in effective if tuple(edge) not in covered)
    return dict(graph, nodes=nodes, edges=edges, effective_edges=effective, expansions=expansions)


def realm_flow(graph, report):
    """Place saved realms in vertical lanes, with their explicit domain sections."""
    placements = {p['placement']: p for p in report['nodes']}
    nodes = {n['key']: n for n in graph['nodes']}
    unframed = set(report.get('graph_unframe', []))
    for key in unframed:
        if key not in nodes or not any(n['parent'] == key for n in nodes.values()):
            raise ValueError('Flow unframe requires a visible container with selected modules: ' + key)
        if any(key in edge for edge in graph['edges']):
            raise ValueError('Flow unframe cannot hide a dependency endpoint: ' + key)
    if unframed:
        for node in graph['nodes']:
            while node['parent'] in unframed:
                node['parent'] = nodes[node['parent']]['parent']
        graph['nodes'] = [node for node in graph['nodes'] if node['key'] not in unframed]
        nodes = {n['key']: n for n in graph['nodes']}
    sections, lanes, assignments = [], [], {}
    for realm in report['graph_realms']:
        group = placements[realm['placement']]
        first = len(sections)+1
        for identifier in realm['sections']:
            section = placements[identifier]
            sections.append(dict(key=identifier, label=section['label'], tone=section['tone'], roots=[]))
        lanes.append(dict(key=realm['placement'], label=group['label'], tone='neutral',
                          columns=list(range(first, len(sections)+1))))
    section_index = {s['key']: index for index, s in enumerate(sections)}
    for placement in report['nodes']:
        if not placement['document'] or placement['entry'] not in nodes:
            continue
        parent = placement
        while parent and parent['placement'] not in section_index:
            parent = placements.get(parent['parent'])
        if parent:
            index = section_index[parent['placement']]
            key = placement['entry']
            if key in assignments and assignments[key] != index:
                raise ValueError('An activity cannot occupy multiple Flow realm sections: ' + key)
            assignments[key] = index
    missing = set(nodes)-set(assignments)
    if missing:
        raise ValueError('Flow realm-lanes must cover every selected activity: ' + ', '.join(sorted(missing)))
    for node in graph['nodes']:
        while node['parent'] and assignments[node['parent']] != assignments[node['key']]:
            node['parent'] = nodes[node['parent']]['parent']
        if not node['parent']:
            sections[assignments[node['key']]]['roots'].append(node['key'])
    node_order = {key: index for index, key in enumerate(report.get('graph_node_order', []))}
    for section in sections:
        section['roots'].sort(key=lambda key: node_order.get(key, len(node_order)))
    graph.update(columns=[s['roots'] for s in sections], lanes=lanes, sections=sections,
                 edge_ports=[], align_centers=report.get('graph_align_centers', []),
                 offset_y=report.get('graph_offset_y', {}))
    for source, target in graph['edges']:
        if assignments[source] > assignments[target]:
            graph['edge_ports'].append(dict(source=source, target=target, exit='left', entry='right'))
    # Adjacent units in a realm section connect directly in either direction.
    # Cross-realm routes retain ordinary obstacle-aware side ports.
    for section in sections:
        for source, target in zip(section['roots'], section['roots'][1:]):
            if (source, target) in {tuple(edge) for edge in graph['edges']}:
                graph['edge_ports'].append(dict(source=source, target=target, exit='bottom', entry='top'))
            if (target, source) in {tuple(edge) for edge in graph['edges']}:
                graph['edge_ports'].append(dict(source=target, target=source, exit='top', entry='bottom'))
    for port in report.get('graph_edge_ports', []):
        pair = (port['source'], port['target'])
        if pair not in {tuple(edge) for edge in graph['edges']}:
            raise ValueError('Flow edge-ports must reference a selected dependency: ' + str(pair))
        graph['edge_ports'] = [p for p in graph['edge_ports']
                               if (p['source'], p['target']) != pair]
        graph['edge_ports'].append(dict(port))


def arrange_flow(graph, report, reference, reference_layout):
    """Realm owns its grouping; other selections reuse the report column order."""
    if report.get('graph_realms'):
        realm_flow(graph, report)
        return
    if reference_layout is None:
        return
    children = {}
    for node in reference['nodes']:
        children.setdefault(node['parent'], []).append(node['key'])
    columns = [list(col) for col in reference['columns']]
    assigned = {key for col in columns for key in col}
    remaining = [key for key in children.get('', []) if key not in assigned]
    if remaining:
        columns.append(remaining)
    order, widths = {}, []
    def visit(key, column):
        order[key] = (column, len(order))
        for child in children.get(key, []):
            visit(child, column)
    for index, col in enumerate(columns):
        widths.append(max(reference_layout['boxes'][key][2] for key in col))
        for key in col:
            visit(key, index)
    roots = [n['key'] for n in graph['nodes'] if not n['parent']]
    arranged = [[] for _ in columns]
    for key in sorted(roots, key=lambda key: order.get(key, (len(columns), len(order)))):
        column = order.get(key, (len(columns), 0))[0]
        if column == len(arranged):
            arranged.append([]); widths.append(132)
        arranged[column].append(key)
    nodes = {n['key'] for n in graph['nodes']}
    graph.update(columns=arranged, column_widths=widths, lanes=reference.get('lanes', []),
                 node_order=[key for key in reference.get('node_order', []) if key in nodes],
                 offset_y={key: value for key, value in reference.get('offset_y', {}).items() if key in nodes},
                 edge_ports=[p for p in reference.get('edge_ports', [])
                             if (p['source'], p['target']) in {tuple(edge) for edge in graph['edges']}],
                 align_centers=[pair for pair in reference.get('align_centers', [])
                                if all(key in nodes for key in pair)])


def activities(model):
    choices = model.get('activity_perspectives')
    if choices is None:
        yield model
        return
    options = [(item['key'], item['label']) for item in choices]
    for item in choices:
        graph = dict(item['graph'], title='Activity Flow · ' + item['label']) if item['key'] else item['graph']
        yield dict(model, report=item['report'], board_report=item.get('board_report', item['report']), dgraph=graph,
                   selection=dict(key=item['key'], label=item['label'], options=options))


def performance(model):
    options = [(key, label) for key, label, _ in GOAL_PERSPECTIVES]
    for key, label, status in GOAL_PERSPECTIVES:
        goals = [goal for goal in model['goals'] if status is None or goal['status'] == status]
        # The full source order supplies stable explorer numbers across filters.
        numbers = {goal['key']: index for index, goal in enumerate(model['goals'], 1)}
        yield dict(model, goals=goals, goal_numbers=numbers,
                   key_results={goal['key']: model.get('key_results', {}).get(goal['key'], []) for goal in goals},
                   selection=dict(key=key, label=label, options=options))
