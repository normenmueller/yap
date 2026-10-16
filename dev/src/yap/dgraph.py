"""Authored dependencies, deterministic layered layout and lean SVG/TikZ views."""

from collections import deque
from html import escape
from heapq import heappop, heappush
from pathlib import Path
import re
import textwrap

from . import footer, navigation, palette, selections
from .content import metadata
from .views import _tex
from .publication_links import activity_pdf


CAPTION = 'Pfeile zeigen: Grundlage → darauf aufbauendes Vorhaben'
MODULE_EXPLANATION = ('Aktivitäten können weitere Aktivitäten als Module enthalten. '
                      'Ein Pfeil auf die übergeordnete Aktivität gilt für alle zugeordneten Module.')
COLORS = {key: palette.HEX[token] for key, token in {
    'sup': 'namSupport', 'ace': 'namSupport', 'gov': 'namGovernance',
    'imp': 'namImpact', 'ops': 'namImpact'}.items()}
PALETTES = {palette.HEX[tone]: (palette.HEX[tone], palette.HEX[fill])
            for tone, fill in (('namViolet', 'namVioletFill'), ('namOrange', 'namOrangeFill'),
                               ('namGreen', 'namGreenFill'), ('namStrategy', 'namStrategyFill'),
                               ('namEpistemics', 'namEpistemicsFill'), ('namMuted', 'namMutedFill'))}
CARD_WIDTH, CARD_HEIGHT = 132, 54
TONE_COLORS = {key: palette.HEX[token] for key, token in {
    'neutral': 'namMuted', 'support': 'namSupport', 'impact': 'namImpact',
    'governance': 'namGovernance', 'epistemics': 'namEpistemics', 'strategy': 'namStrategy'}.items()}


def _spec_text(value):
    """Keep YAML literal-block line breaks instead of flattening Pandoc text."""
    if isinstance(value, list):
        return ''.join(_spec_text(item) for item in value)
    kind, child = value['t'], value.get('c')
    if kind in ('MetaString', 'Str'):
        return child
    if kind == 'Space':
        return ' '
    if kind in ('SoftBreak', 'LineBreak'):
        return '\n'
    if kind in ('MetaBlocks', 'MetaInlines'):
        return _spec_text(child)
    if kind in ('Para', 'Plain'):
        return _spec_text(child) + '\n'
    raise ValueError('pfo/act/act.md: dgraph.spec requires a text block with one A -> B edge per line.')


def parse(meta, nodes, members=None, report=None):
    graph = dict(nodes=[], edges=[], prop='horizontal-alignment')
    members = members or {}
    report = report or {'nodes': []}
    from .portfolio import leaf_selection, descendants
    value = meta.get('dgraph')
    if value is None:
        value = {'t': 'MetaMap', 'c': {'spec': {'t': 'MetaString', 'c': ''}}}
    label = 'pfo/act/act.md: dgraph'
    if value['t'] != 'MetaMap':
        raise ValueError(label + ' requires prop and spec as a mapping.')
    fields = value['c']
    for field in fields:
        if field not in {'prop', 'spec'}:
            raise ValueError(f'{label}: unknown field {field!r}.')
    prop = metadata(fields, 'prop', label) or graph['prop']
    if prop != 'horizontal-alignment':
        raise ValueError(label + '.prop: allowed value is horizontal-alignment (left to right).')
    if 'spec' not in fields:
        raise ValueError(label + ': spec is missing; expected spec: | followed by edges.')
    by_key = {node['key']: node for node in nodes}
    aliases = {}
    for node in nodes:
        for alias in {node['key'], node.get('acronym', '')} - {''}:
            aliases.setdefault(alias, set()).add(node['key'])

    def resolve(name, line):
        if name in by_key:
            return name
        candidates = aliases.get(name, set())
        if not candidates:
            raise ValueError(f'{label}.spec, line {line}: unknown activity {name!r}.')
        if len(candidates) > 1:
            raise ValueError(f'{label}.spec, line {line}: {name!r} is ambiguous; '
                             'use the stable key: ' + ', '.join(sorted(candidates)))
        return next(iter(candidates))

    used, edges = {}, []
    source_placements = {}
    for p in report['nodes']:
        if p['entry']:
            source_placements.setdefault(p['entry'], p)

    def include_source(key, parent='', placement=None):
        if key in used:
            return
        node = by_key[key]
        # A source card cannot visually own unrelated activities: that would
        # make arrows to a semantic leaf look like group-wide dependencies.
        while parent and key not in descendants(members, parent):
            parent = used[parent]['parent']
        used[key] = dict(key=key, id=node['id'], title=node['title'],
                         label=node.get('acronym') or node['title'], parent=parent,
                         color=TONE_COLORS.get(placement['tone'] if placement else '', palette.HEX['namMuted']),
                         category=placement['category'] if placement else '')

    # Project every selected activity before resolving edges so nesting is not
    # determined by which endpoint happens to be encountered first.
    owners = {}
    for p in report['nodes']:
        parent = owners.get(p['parent'], '')
        if p['document'] and p['entry'] and by_key[p['entry']]['kind'] == 'activity':
            include_source(p['entry'], parent, p)
            owners[p['placement']] = p['entry']
        else:
            owners[p['placement']] = parent

    def include(key):
        include_source(key, placement=source_placements.get(key))

    def leaves(key):
        eligible = {n['key'] for n in nodes if n['kind'] == 'activity'}
        return sorted(leaf_selection(members, [key], eligible))

    for number, line in enumerate(_spec_text(fields['spec']).splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r'\s*([^\s<>]+?)\s*->\s*([^\s<>]+)\s*', line)
        if not match:
            raise ValueError(f'{label}.spec, line {number}: expected A -> B, received: {line!r}.')
        edge = tuple(resolve(name, number) for name in match.groups())
        if edge[0] == edge[1]:
            raise ValueError(f'{label}.spec, line {number}: self-reference {edge[0]!r}.')
        if edge not in edges:
            edges.append(edge)
        for key in edge:
            if by_key[key]['kind'] != 'activity':
                raise ValueError(f'{label}: dependency endpoints must be activities: {key!r}.')
            include(key)
    # An edge on a container abbreviates all pairs of contained leaf modules.
    effective = list(dict.fromkeys((a, b) for source, target in edges
                                  for a in leaves(source) for b in leaves(target)))
    if any(a == b for a, b in effective):
        raise ValueError(label + ': self-reference after expanding a project group.')
    for a, b in effective:
        for key in (a, b):
            if key not in used:
                include(key)
    graph.update(nodes=list(used.values()), edges=edges, effective_edges=effective, prop=prop,
                 expansions={key: leaves(key) for edge in edges for key in edge})
    graph['node_order'] = report.get('graph_node_order', [])
    graph['offset_y'] = report.get('graph_offset_y', {})
    if report.get('graph_columns'):
        graph['columns'] = report['graph_columns']
    if report.get('graph_lanes'):
        graph['lanes'] = report['graph_lanes']
    if report.get('graph_align_centers'):
        graph['align_centers'] = report['graph_align_centers']
    if report.get('graph_edge_ports'):
        for port in report['graph_edge_ports']:
            if (port['source'], port['target']) not in edges:
                raise ValueError('Flow edge-ports must reference an authored dependency.')
        graph['edge_ports'] = report['graph_edge_ports']
    _ranks(dict(nodes=graph['nodes'], edges=effective))
    return graph


def _ranks(graph):
    incoming = {node['key']: 0 for node in graph['nodes']}
    outgoing = {key: [] for key in incoming}
    rank = dict.fromkeys(incoming, 0)
    for source, target in graph['edges']:
        incoming[target] += 1
        outgoing[source].append(target)
    queue = deque(key for key in incoming if not incoming[key])
    seen = 0
    while queue:
        key = queue.popleft()
        seen += 1
        for target in outgoing[key]:
            rank[target] = max(rank[target], rank[key] + 1)
            incoming[target] -= 1
            if not incoming[target]:
                queue.append(target)
    if seen != len(incoming):
        raise ValueError('pfo/act/act.md: dgraph contains a cycle; '
                         'dependencies must be acyclic: ' +
                         ', '.join(key for key, degree in incoming.items() if degree))
    return rank


def _flat_layout(graph, sizes=None, column_gap=112):
    """Reserve routing slots for long edges; keep arrows out of intervening cards."""
    ranks = _ranks(graph)
    layers = [[] for _ in range(max(ranks.values(), default=0) + 1)]
    for key, rank in ranks.items():
        layers[rank].append(key)
    chains = []
    for index, (source, target) in enumerate(graph['edges']):
        chain = [source]
        for rank in range(ranks[source] + 1, ranks[target]):
            dummy = ('route', index, rank)
            layers[rank].append(dummy)
            chain.append(dummy)
        chains.append(chain + [target])
    before, after = {}, {}
    for chain in chains:
        for source, target in zip(chain, chain[1:]):
            after.setdefault(source, []).append(target)
            before.setdefault(target, []).append(source)
    for _ in range(4):
        for indices, neighbors in ((range(1, len(layers)), before),
                                   (range(len(layers)-2, -1, -1), after)):
            order = {key: i for layer in layers for i, key in enumerate(layer)}
            for index in indices:
                layers[index].sort(key=lambda key: sum(order[n] for n in neighbors.get(key, [])) /
                                   len(neighbors[key]) if neighbors.get(key) else order[key])
                order.update({key: i for i, key in enumerate(layers[index])})
    # Prefer the space between units to an exterior detour for a skipped rank.
    for layer in layers:
        real = [key for key in layer if isinstance(key, str)]
        if len(real) >= 2:
            routes = [key for key in layer if not isinstance(key, str)]
            if routes:
                middle = len(real)//2
                layer[:] = real[:middle] + routes + real[middle:]
    lines = {node['key']: textwrap.wrap(node['label'], width=18) or [''] for node in graph['nodes']}
    card_height = max(CARD_HEIGHT, max((len(value)*20+24 for value in lines.values()), default=0))
    sizes = sizes or {key: (CARD_WIDTH, card_height) for key in ranks}
    def size(key):
        return sizes.get(key, (CARD_WIDTH, 24))
    heights = [sum(size(key)[1] + 24 for key in layer) - 24 for layer in layers]
    height = max(heights) + 48
    positions = {}
    columns = {}
    left = 24
    for rank, layer in enumerate(layers):
        width = max((size(key)[0] for key in layer), default=CARD_WIDTH)
        top = (height - heights[rank])/2
        for key in layer:
            positions[key] = (left + width/2, top + size(key)[1]/2)
            columns[key] = (left, left+width)
            top += size(key)[1] + 24
        left += width + column_gap
    return dict(width=left-column_gap+24, height=height,
                positions=positions, columns=columns, lines=lines, card_height=card_height, chains=chains)


def _column_layout(graph, sizes, columns, widths=(), sections=(), lanes=()):
    """Place activity columns under vertical lanes and optional domain headings."""
    roots = {node['key'] for node in graph['nodes']}
    selected = [key for column in columns for key in column]
    if len(set(selected)) != len(selected) or any(key not in roots for key in selected):
        raise ValueError('Flow columns must name distinct outer activity containers or standalone activities.')
    columns = [list(column) for column in columns]
    remaining = [node['key'] for node in graph['nodes'] if node['key'] not in selected]
    if remaining:
        columns.append(remaining)
    positions, bounds, spans = {}, {}, []
    left = 56
    for index, column in enumerate(columns):
        if index:
            same_realm = any(index in lane['columns'] and index+1 in lane['columns']
                             for lane in lanes)
            left += (64 if same_realm else 112) if sections else 72
        width = max([sizes[key][0] for key in column] +
                    [widths[index] if index < len(widths) else CARD_WIDTH])
        if sections:
            width = max([width] + [len(lane['label'])*11-16 for lane in lanes
                                   if lane['columns'] == [index+1]])
        spans.append((left, left+width))
        left += width
    total_width = left+56
    top = 120 if sections else 80 if lanes else 56
    bottom, labels = top, []
    for index, (column, (lo, hi)) in enumerate(zip(columns, spans)):
        y = top
        if index < len(sections):
            section = sections[index]
            labels.append(dict(label=section['label'], x=lo, y=56,
                               width=len(section['label'])*11, height=28,
                               color=TONE_COLORS[section['tone']]))
        for key in column:
            positions[key] = ((lo+hi)/2, y+sizes[key][1]/2)
            bounds[key] = (lo, hi)
            y += sizes[key][1]+40
        bottom = max(bottom, y-40)
    panels = []
    for lane in lanes:
        lo = spans[lane['columns'][0]-1][0]-24
        hi = spans[lane['columns'][-1]-1][1]+24
        panels.append(dict(key=lane['key'], label=lane['label'], color=TONE_COLORS[lane['tone']],
                           x=lo, y=8, width=hi-lo, height=bottom+40))
    return dict(width=total_width, height=bottom+56, positions=positions, lane_panels=panels,
                columns=bounds, column_bounds=spans, section_labels=labels,
                chains=[list(edge) for edge in graph['edges']], fixed_columns=True)


def _category_layout(graph, sizes):
    """Keep Support together, Impact stacked, Governance above Support.

    Use the ordinary layered layout for graphs without these three categories.
    Routing slots in skipped columns stay outside the project containers.
    """
    categories = {name: [] for name in ('sup', 'imp', 'gov')}
    for node in graph['nodes']:
        category = node.get('category', '')
        if category not in categories:
            return None
        categories[category].append(node['key'])
    if not all(categories.values()):
        return None
    support, impact, governance = (categories[name] for name in ('sup', 'imp', 'gov'))
    # Respect dependency order among support projects without changing authored edges.
    ordered = []
    pending = list(support)
    while pending:
        ready = next((key for key in pending if not any(
            target == key and source in pending for source, target in graph['edges'])), pending[0])
        ordered.append(ready)
        pending.remove(ready)
    support = ordered
    layers = [[support[0], *governance], *[[key] for key in support[1:]], impact]
    positions, columns, occupied = {}, {}, {}
    gov_height = sum(sizes[key][1] + 24 for key in governance) - 24
    support_top = 24 + gov_height + 62
    left, bottom = 40, 0
    for rank, layer in enumerate(layers):
        width = max(sizes[key][0] for key in layer)
        occupied[rank] = []
        top = 24
        for key in layer:
            height = sizes[key][1]
            y = support_top if key in support else top
            positions[key] = (left + width/2, y + height/2)
            columns[key] = (left, left + width)
            occupied[rank].append((y, y + height))
            bottom = max(bottom, y + height)
            if key not in support:
                top += height + 24
        left += width + 112
    ranks = {key: rank for rank, layer in enumerate(layers) for key in layer}
    chains = []
    for index, (source, target) in enumerate(graph['edges']):
        start, end = ranks[source], ranks[target]
        chain = [source]
        for rank in range(start + 1, end):
            fraction = (rank-start)/(end-start)
            ideal = positions[source][1]*(1-fraction) + positions[target][1]*fraction
            intervals = occupied[rank]
            candidates = [ideal, 24, *(edge + offset for lo, hi in intervals
                                       for edge, offset in ((lo, -24), (hi, 24))) ]
            free = [y for y in candidates if y >= 24 and all(
                y <= lo-24 or y >= hi+24 for lo, hi in intervals)]
            y = min(free, key=lambda value: abs(value-ideal))
            key = f'route-{index}-{rank}'
            bounds = columns[layers[rank][0]]
            columns[key] = bounds
            positions[key] = ((bounds[0]+bounds[1])/2, y)
            occupied[rank].append((y-6, y+6))
            bottom = max(bottom, y)
            chain.append(key)
        chains.append([*chain, target])
    return dict(width=left-112+24, height=bottom+24, positions=positions,
                columns=columns, chains=chains)


VARIANTS = {
    'semantic': ('A · Wirkungsfeld', 'Gruppen in getrennten Spalten.'),
    'staggered': ('B · Versetzte Gruppen', 'Gruppen höhenversetzt in getrennten Spalten.'),
}


def _variant_layout(graph, sizes, variant):
    """Two review options; leave the accepted/exported layout unchanged."""
    groups = {category: [] for category in ('sup', 'imp', 'gov')}
    for node in graph['nodes']:
        category = node.get('category', '')
        if category not in groups:
            return None
        groups[category].append(node['key'])
    if not all(groups.values()):
        return None
    ranks = _ranks(graph)
    groups['sup'].sort(key=lambda key: -ranks[key])
    names = ('sup', 'imp', 'gov') if variant == 'semantic' else ('sup', 'gov', 'imp')
    gap = 80
    heights = {category: sum(sizes[key][1] for key in keys) + gap*(len(keys)-1)
               for category, keys in groups.items()}
    height = max(heights.values()) + 112
    positions, columns = {}, {}
    left = 64
    for category in names:
        keys = groups[category]
        width = max(sizes[key][0] for key in keys)
        top = (height-heights[category])/2
        for key in keys:
            positions[key] = (left+width/2, top+sizes[key][1]/2)
            columns[key] = (left, left+width)
            top += sizes[key][1]+gap
        left += width+136
    return dict(width=left-136+64, height=height, positions=positions, columns=columns,
                chains=[[a, b] for a, b in graph['edges']], variant=variant)


def _rounded_route(points, radius=13):
    """A continuous orthogonal route with modest rounded corners."""
    points = [p for i, p in enumerate(points) if not i or p != points[i-1]]
    simplified = []
    for point in points:
        while len(simplified) >= 2 and (simplified[-2][0] == simplified[-1][0] == point[0]
                                       or simplified[-2][1] == simplified[-1][1] == point[1]):
            simplified.pop()
        simplified.append(point)
    curves = []
    current = simplified[0]
    for a, b, c in zip(simplified, simplified[1:], simplified[2:]):
        before = min(radius, (abs(b[0]-a[0])+abs(b[1]-a[1]))/2)
        after = min(radius, (abs(c[0]-b[0])+abs(c[1]-b[1]))/2)
        def toward(origin, target, distance):
            length = abs(target[0]-origin[0])+abs(target[1]-origin[1])
            return tuple(origin[j]+(target[j]-origin[j])*distance/length for j in (0, 1))
        entry, leave = toward(b, a, before), toward(b, c, after)
        curves.extend([(current, current, entry, entry), (entry, b, b, leave)])
        current = leave
    curves.append((current, current, simplified[-1], simplified[-1]))
    return curves


def _gutter_routes(drawing):
    """Route edges through the open gutters between explicitly placed containers."""
    boxes, columns = drawing['boxes'], drawing['columns']
    panels = sorted(drawing.get('lane_panels', []), key=lambda panel: panel['x'])
    gutter_centers = [(left['x']+left['width']+right['x'])/2
                      for left, right in zip(panels, panels[1:])]

    def lane(owner):
        center = sum(columns[owner])/2
        return next((i for i, panel in enumerate(panels)
                     if panel['x'] <= center <= panel['x']+panel['width']), None)

    roots = set(drawing['owners'].values())
    obstacles = [boxes[key] for key in roots]
    obstacles.extend((label['x'], label['y'], label['width'], label['height'])
                     for label in drawing.get('section_labels', []))
    lane_titles = [(p['x']+16, 18, len(p['label'])*11, 24) for p in panels]
    obstacles.extend(lane_titles)
    title_clearance = max((y+height+8 for _, y, _, height in lane_titles), default=0)
    reserved = []
    result = {}
    routing_order = drawing['chains']
    if drawing.get('section_labels'):
        # Route lower sources first so longer descents can nest around them.
        routing_order = sorted(routing_order, key=lambda chain: -boxes[chain[0]][1])
    for chain in routing_order:
        source, target = chain[0], chain[-1]
        a_owner, b_owner = (drawing['owners'][key] for key in (source, target))
        if a_owner == b_owner:
            continue
        a_lane, b_lane = lane(a_owner), lane(b_owner)
        cross_lane = a_lane is not None and b_lane is not None and a_lane != b_lane
        a, b = boxes[source], boxes[target]
        port_spec = drawing.get('edge_ports', {}).get((source, target), {})
        exit_side = drawing.get('edge_exits', {}).get((source, target))
        entry_side = drawing.get('edge_entries', {}).get((source, target))
        # A top-to-top connection between aligned cards uses the outer upper
        # track, leaving the nearer corridor for side arrivals.
        top_clearance = 24 if exit_side == entry_side == 'top' and a[1] == b[1] else 12
        leftward = columns[a_owner][0] >= columns[b_owner][0]
        target_right = columns[a_owner][0] > columns[b_owner][0] and target not in drawing['groups']
        start = (a[0]-1 if leftward else a[0]+a[2]+1, drawing['ports'][(source, target, 0)])
        end = (b[0]+b[2]+2 if target_right else b[0]-2, drawing['ports'][(source, target, -1)])
        first = (columns[a_owner][0]-20 if leftward else columns[a_owner][1]+20, start[1])
        if exit_side in ('top', 'bottom'):
            above = exit_side == 'top'
            start = (a[0]+a[2]*port_spec.get('exit_position', .5), a[1]-1 if above else a[1]+a[3]+1)
            root = boxes[a_owner]
            first = (start[0], root[1]-top_clearance if above else root[1]+root[3]+24)
            if above and exit_side == entry_side == 'top' and panels:
                first = (first[0], max(first[1], title_clearance))
        elif exit_side in ('left', 'right'):
            start = (a[0]-1 if exit_side == 'left' else a[0]+a[2]+1, start[1])
            first = (columns[a_owner][0]-20 if exit_side == 'left' else columns[a_owner][1]+20, start[1])
        if (drawing.get('section_labels') and target in drawing['groups'] and not leftward
                and entry_side not in ('top', 'bottom', 'right') and b[1]+8 < start[1] < b[1]+b[3]-8):
            # In realm sections a whole-project arrow can meet the frame at
            # the source height; it need not detour to the project's center.
            end = (end[0], start[1])
        last = (columns[b_owner][1]+20 if target_right else columns[b_owner][0]-20, end[1])
        if entry_side in ('top', 'bottom'):
            above = entry_side == 'top'
            end = (b[0]+b[2]*port_spec.get('entry_position', .5), b[1]-2 if above else b[1]+b[3]+2)
            root = boxes[b_owner]
            last = (end[0], root[1]-top_clearance if above else root[1]+root[3]+24)
            # A clear approach from below can turn at the source height,
            # avoiding an unnecessary detour through the inter-column gutter.
            if (not above and exit_side in ('left', 'right') and start[1] > last[1]
                    and not any(x-8 < last[0] < x+w+8 and y-8 < start[1]
                                and y+h+8 > last[1] for x, y, w, h in obstacles)
                    and not any(min(p[0], q[0])-8 < last[0] < max(p[0], q[0])+8
                                and min(p[1], q[1]) < start[1] and max(p[1], q[1]) > last[1]
                                for p, q in reserved)):
                last = (last[0], start[1])
            if above and exit_side == entry_side == 'top' and panels:
                last = (last[0], max(last[1], title_clearance))
        elif entry_side in ('left', 'right'):
            end = (b[0]-2 if entry_side == 'left' else b[0]+b[2]+2, end[1])
            last = (columns[b_owner][0]-20 if entry_side == 'left' else columns[b_owner][1]+20, end[1])
        xs = {first[0], last[0], 20, drawing['width']-20}
        preferred_gutters = gutter_centers
        if cross_lane:
            xs.update(gutter_centers)
            if drawing.get('section_labels'):
                # Opposite vertical directions use opposite sides of the wider
                # realm corridor; nested descents fan out toward the target.
                descending = end[1] > start[1]
                offset = 0 if descending else -14
                preferred_gutters = []
                for center, left_panel, right_panel in zip(gutter_centers, panels, panels[1:]):
                    lo = left_panel['x']+left_panel['width']+8
                    hi = right_panel['x']-8
                    candidates = [center+14*i for i in range(-int((hi-lo)/14)-1, int((hi-lo)/14)+2)
                                  if lo <= center+14*i <= hi]
                    candidates.sort(key=lambda x: (abs(x-(center+offset)), -x if descending else x))
                    free = [x for x in candidates if not any(
                        r[0] == s[0] and abs(x-r[0]) < 14
                        and min(max(first[1], last[1]), max(r[1], s[1])) >
                            max(min(first[1], last[1]), min(r[1], s[1]))
                        for r, s in reserved)]
                    preferred_gutters.append(free[0] if free else center+offset)
                xs.update(preferred_gutters)
        ys = {first[1], last[1], 20, drawing['height']-20}
        if entry_side not in ('top', 'bottom') and any(
                other_target == target and side == 'top'
                for (_, other_target), side in drawing.get('edge_entries', {}).items()):
            # Keep side arrivals on the inner upper track, visibly below an
            # existing top arrival while retaining clearance from the cards.
            ys.add(b[1]-10)
        for x, y, width, height in obstacles:
            xs.update((x-20, x-38, x+width+20, x+width+38))
            ys.update((y-20, y-38, y+height+20, y+height+38))
        for p, q in reserved:
            xs.update((p[0]-14, p[0]+14, q[0]-14, q[0]+14))
            ys.update((p[1]-14, p[1]+14, q[1]-14, q[1]+14))
        xs = sorted(x for x in xs if 8 <= x <= drawing['width']-8)
        ys = sorted(y for y in ys if 8 <= y <= drawing['height']-8)
        def clear(p, q):
            if cross_lane and p[0] == q[0] and any(
                    panel['x'] <= p[0] <= panel['x']+panel['width']
                    and max(p[1], q[1]) > panel['y']
                    and min(p[1], q[1]) < panel['y']+panel['height']
                    for panel in panels):
                return False
            for r, s in reserved:
                axis = 1 if p[0] == q[0] else 0
                other = 1-axis
                parallel = p[other] == q[other] and r[other] == s[other]
                separation = abs(p[other]-r[other])
                if parallel and (separation == 0 or
                                 (drawing.get('section_labels') and axis == 1 and separation < 14)):
                    overlap = min(max(p[axis], q[axis]), max(r[axis], s[axis]))-max(min(p[axis], q[axis]), min(r[axis], s[axis]))
                    if overlap > 0:
                        return False
            for x, y, width, height in obstacles:
                if p[0] == q[0]:
                    if x-8 < p[0] < x+width+8 and max(p[1], q[1]) > y-8 and min(p[1], q[1]) < y+height+8:
                        return False
                elif y-8 < p[1] < y+height+8 and max(p[0], q[0]) > x-8 and min(p[0], q[0]) < x+width+8:
                    return False
            return True
        initial = (xs.index(first[0]), ys.index(first[1]), 0)
        queue, distance, previous = [(0, initial)], {initial: 0}, {}
        finish = None
        while queue:
            cost, state = heappop(queue)
            if cost != distance.get(state):
                continue
            ix, iy, direction = state
            p = (xs[ix], ys[iy])
            if p == last:
                finish = state
                break
            for dx, dy, heading in ((1, 0, 1), (-1, 0, 1), (0, 1, 2), (0, -1, 2)):
                nx, ny = ix+dx, iy+dy
                if not (0 <= nx < len(xs) and 0 <= ny < len(ys)):
                    continue
                q = (xs[nx], ys[ny])
                if not clear(p, q):
                    continue
                new_cost = cost+abs(p[0]-q[0])+abs(p[1]-q[1])+(24 if direction and heading != direction else 0)
                if cross_lane and heading == 2:
                    # Prefer the middle of the lane gap; other tracks remain
                    # available when an earlier connection already occupies it.
                    weight = 10 if drawing.get('section_labels') else 100
                    new_cost += abs(p[1]-q[1])*min(abs(p[0]-x) for x in preferred_gutters)/weight
                next_state = (nx, ny, heading)
                if new_cost < distance.get(next_state, float('inf')):
                    distance[next_state] = new_cost
                    previous[next_state] = state
                    heappush(queue, (new_cost, next_state))
        if finish is None:
            raise ValueError('No available route between placed activities: ' + source + ' → ' + target)
        path = []
        while finish != initial:
            path.append((xs[finish[0]], ys[finish[1]]))
            finish = previous[finish]
        path = [first, *reversed(path)]
        compact = []
        for point in path:
            while len(compact) >= 2 and (compact[-2][0] == compact[-1][0] == point[0]
                                        or compact[-2][1] == compact[-1][1] == point[1]):
                compact.pop()
            compact.append(point)
        reserved.extend(zip(compact, compact[1:]))
        result[(source, target)] = _rounded_route([start, *path, end])
    return result


def _separate_route_tracks(chains, drawing, boxes):
    """Give module edges distinct tracks through shared project-level corridors."""
    shared = {}
    for index, chain in enumerate(chains):
        for key in chain[1:-1]:
            shared.setdefault(key, []).append(index)
    spacing, clearance = 12, 12
    for key, indices in shared.items():
        if len(indices) < 2:
            continue
        left, right = drawing['columns'][key]
        x, ideal = drawing['positions'][key]
        half = (len(indices)-1)*spacing/2
        enclosing = drawing.get('route_containers', {}).get(key, set())
        occupied = [(y-clearance, y+h+clearance)
                    for box_key, (bx, y, w, h) in boxes.items()
                    if box_key not in enclosing and bx < right and bx+w > left]
        occupied.extend((drawing['positions'][other][1]-spacing,
                         drawing['positions'][other][1]+spacing)
                        for chain in chains for other in chain[1:-1]
                        if other != key and drawing['columns'][other] == (left, right))
        candidates = [max(24+half, ideal), 24+half,
                      *(edge+offset for lo, hi in occupied
                        for edge, offset in ((lo, -half), (hi, half)))]
        free = [y for y in candidates if y-half >= 24 and all(
            y+half <= lo or y-half >= hi for lo, hi in occupied)]
        center = min(free, key=lambda y: (abs(y-ideal), y))
        indices.sort(key=lambda index: drawing['positions'][chains[index][-1]][1])
        for order, index in enumerate(indices):
            track = ('edge-route', index, key)
            y = center+(order-(len(indices)-1)/2)*spacing
            drawing['positions'][track] = (x, y)
            drawing['columns'][track] = (left, right)
            chains[index] = [track if point == key else point for point in chains[index]]
            drawing['height'] = max(drawing['height'], y+24)


def layout(graph, variant=None):
    """Place project containers as units; keep every module inside its parent."""
    by_key = {node['key']: node for node in graph['nodes']}
    children = {}
    for node in graph['nodes']:
        children.setdefault(node.get('parent', ''), []).append(node['key'])
    node_order = {key: index for index, key in enumerate(graph.get('node_order', []))}
    for siblings in children.values():
        siblings.sort(key=lambda key: node_order.get(key, len(node_order)))
    lines = {key: textwrap.wrap(node['label'], width=18) or [''] for key, node in by_key.items()}
    headers = {key: max(38, len(value)*20+18) for key, value in lines.items()}
    sizes = {}
    internal_edges = {}
    group_layouts = {}

    def child_unit(key, parent):
        while by_key[key].get('parent') != parent:
            key = by_key[key]['parent']
        return key

    def horizontal_group(key):
        """Reuse layered layout when boundary connections can reach its ports."""
        connections = internal_edges.get(key, [])
        if not connections:
            return None
        pairs = list(dict.fromkeys((child_unit(a, key), child_unit(b, key)) for a, b in connections))
        graph = dict(nodes=[by_key[c] for c in children[key]], edges=pairs)
        try:
            ranks = _ranks(graph)
        except ValueError:
            # Acyclic module edges can project to opposing container edges.
            return None
        for source, target in edges:
            a, b = key in ancestors(source), key in ancestors(target)
            if a and not b and ranks[child_unit(source, key)] != max(ranks.values()):
                return None
            if b and not a and ranks[child_unit(target, key)] != 0:
                return None
        slots = dict(sizes)
        for index, (a, b) in enumerate(pairs):
            count = sum((child_unit(s, key), child_unit(t, key)) == (a, b) for s, t in connections)
            for rank in range(ranks[a]+1, ranks[b]):
                slots[('route', index, rank)] = (CARD_WIDTH, 24+12*(count-1))
        return _flat_layout(graph, slots, column_gap=56)

    def measure(key):
        if key in children:
            child_sizes = [measure(child) for child in children[key]]
            local = horizontal_group(key)
            if local:
                group_layouts[key] = local
                sizes[key] = (local['width'], local['height']+headers[key])
                return sizes[key]
            # Keep internal routes beside the children, inside their common
            # container. Extra tracks must enlarge the frame, not cover cards.
            gutter = 30 + 16*len(internal_edges[key]) if key in internal_edges else 0
            sizes[key] = (max(w for w, _ in child_sizes) + 52 + gutter,
                          sum(h for _, h in child_sizes) + 18*(len(child_sizes)-1) + headers[key]+18)
        else:
            sizes[key] = (CARD_WIDTH, CARD_HEIGHT)
        return sizes[key]

    def owner(key):
        while by_key[key].get('parent'):
            key = by_key[key]['parent']
        return key

    def visual_leaves(key):
        return {leaf for child in children[key] for leaf in visual_leaves(child)} if key in children else {key}

    # Compact only when the visible container represents exactly the authored
    # semantic expansion. A perspective move must never hide effective edges.
    edges, meanings = [], []
    for source, target in graph['edges']:
        a, b = graph['expansions'][source], graph['expansions'][target]
        compact = visual_leaves(source) == set(a) and visual_leaves(target) == set(b)
        candidates = [(source, target)] if compact else [(x, y) for x in a for y in b]
        for edge in candidates:
            meaning = set((x, y) for x in a for y in b) if compact else {edge}
            edges.append(edge)
            meanings.append(meaning)
    selected = [(edge, meaning) for index, (edge, meaning) in enumerate(zip(edges, meanings))
                if not any(other > meaning or (j < index and other == meaning)
                           for j, other in enumerate(meanings))]
    edges = [edge for edge, _ in selected]

    def ancestors(key):
        result = []
        while by_key[key].get('parent'):
            key = by_key[key]['parent']
            result.append(key)
        return result

    for source, target in edges:
        common = next((key for key in ancestors(source) if key in ancestors(target)), None)
        if common:
            internal_edges.setdefault(common, []).append((source, target))

    roots = children.get('', [])
    for key in roots:
        measure(key)
    unit_edges = list(dict.fromkeys((owner(a), owner(b)) for a, b in edges if owner(a) != owner(b)))
    units = dict(nodes=[by_key[key] for key in roots], edges=unit_edges)
    # Opposing module edges can be acyclic even when their containers form a cycle.
    # Keep a deterministic forward layout, then route remaining edges explicitly.
    reachable = {key: set() for key in roots}
    for a, b in unit_edges:
        reachable[a].add(b)
    for pivot in roots:
        for key in roots:
            if pivot in reachable[key]:
                reachable[key].update(reachable[pivot])
    order = {key: i for i, key in enumerate(roots)}
    units['edges'] = [(a, b) for a, b in unit_edges if a not in reachable[b] or order[a] < order[b]]
    if variant is not None and variant not in VARIANTS:
        raise ValueError('Unknown graph variant: ' + str(variant))
    drawing = ((_variant_layout(units, sizes, variant) if variant else None)
               or (_column_layout(units, sizes, graph['columns'], graph.get('column_widths', ()),
                                  graph.get('sections', ()), graph.get('lanes', ()))
                   if graph.get('columns') and not variant else None)
               or _category_layout(units, sizes) or _flat_layout(units, sizes))
    routes = {edge: chain for edge, chain in zip(units['edges'], drawing['chains'])}
    boxes = {}
    internal_routes, route_owners = {}, {}
    route_containers = {}

    def place(key, x, y):
        width, height = sizes[key]
        drawing['positions'][key] = (x, y)
        boxes[key] = (x-width/2, y-height/2, width, height)
        top = y-height/2 + headers[key]
        if key in group_layouts:
            local = group_layouts[key]
            left = x-width/2
            def scoped(point):
                return point if isinstance(point, str) else ('inside', key, point)
            for point, (cx, cy) in local['positions'].items():
                identifier = scoped(point)
                drawing['positions'][identifier] = (left+cx, top+cy)
                lo, hi = local['columns'][point]
                drawing['columns'][identifier] = (left+lo, left+hi)
                if not isinstance(point, str):
                    route_containers[identifier] = set([key, *ancestors(key)])
            for child in children[key]:
                place(child, *drawing['positions'][child])
            paths = {(chain[0], chain[-1]): [scoped(p) for p in chain] for chain in local['chains']}
            for source, target in internal_edges[key]:
                units = (child_unit(source, key), child_unit(target, key))
                internal_routes[(source, target)] = paths[units]
                route_owners[(source, target)] = units
            return
        for child in children.get(key, []):
            gutter = 30 + 16*len(internal_edges[key]) if key in internal_edges else 0
            place(child, x-gutter/2, top + sizes[child][1]/2)
            top += sizes[child][1] + 18

    for key in roots:
        place(key, *drawing['positions'][key])
    alignments = graph.get('align_centers', []) if drawing.get('fixed_columns') else []
    edge_ports = graph.get('edge_ports', []) if drawing.get('fixed_columns') else []

    def move_root(root, new_y):
        x, _ = drawing['positions'][root]
        source_box = (boxes[root][0], new_y-sizes[root][1]/2, *sizes[root])
        sx, sy, sw, sh = source_box
        for key in roots:
            bx, by, bw, bh = boxes[key]
            if key != root and sx < bx+bw and sx+sw > bx and sy-16 < by+bh and sy+sh+16 > by:
                raise ValueError('Flow positioning would overlap another activity: ' + root)
        if sy < 48 or sy+sh > drawing['height']-24:
            raise ValueError('Flow positioning would leave the drawing: ' + root)
        place(root, x, new_y)

    for key, delta in (graph.get('offset_y', {}) if drawing.get('fixed_columns') else {}).items():
        if key not in roots:
            raise ValueError('Flow offset-y must reference an outer activity: ' + key)
        move_root(key, drawing['positions'][key][1]+delta)
    for source, target in alignments:
        if source not in boxes or target not in boxes or owner(source) == owner(target):
            raise ValueError('Flow alignment requires visible activities in distinct outer containers.')
        root = owner(source)
        move_root(root, drawing['positions'][root][1]
                  + drawing['positions'][target][1] - drawing['positions'][source][1])
    if any(drawing['positions'][a][1] != drawing['positions'][b][1] for a, b in alignments):
        raise ValueError('Flow center alignments conflict; order pairs from their anchor outward.')
    chains = []
    for source, target in edges:
        route = internal_routes.get((source, target), routes.get((owner(source), owner(target)), []))
        chains.append([source, *route[1:-1], target])
    drawing['route_containers'] = route_containers
    _separate_route_tracks(chains, drawing, boxes)
    back_routes = {}
    for chain in chains:
        source, target = owner(chain[0]), owner(chain[-1])
        if not drawing.get('variant') and source != target and drawing['columns'][source][0] > drawing['columns'][target][0]:
            back_routes[(chain[0], chain[-1])] = drawing['height'] + 24*len(back_routes)
    if back_routes:
        drawing['height'] += 24*len(back_routes)
    ports, port_sides = {}, {}
    for endpoint in (0, -1):
        connections = {}
        for chain in chains:
            same_column = drawing['columns'][owner(chain[0])] == drawing['columns'][owner(chain[-1])]
            backward = drawing.get('variant') and drawing['columns'][owner(chain[0])][0] > drawing['columns'][owner(chain[-1])][0]
            internal = owner(chain[0]) == owner(chain[-1]) and (chain[0], chain[-1]) not in internal_routes
            if (chain[0], chain[-1]) in internal_routes:
                same_column = backward = False
            side = 'right' if internal else 'left' if endpoint == -1 or same_column or backward else 'right'
            port_sides[(chain[0], chain[-1], endpoint)] = side
            connections.setdefault((chain[endpoint], side), []).append(chain)
        for (key, _), connected in connections.items():
            # Follow the adjacent routing waypoint, not the distant endpoint:
            # a skipped-rank edge can pass above a closer, higher destination.
            connected.sort(key=lambda chain: drawing['positions'][chain[1 if endpoint == 0 else -2]][1])
            x, y, width, height = boxes[key]
            center = y+height/2
            spacing = min(12, (height-24)/max(1, len(connected)-1))
            for index, chain in enumerate(connected):
                ports[(chain[0], chain[-1], endpoint)] = center + (index-(len(connected)-1)/2)*spacing
    if drawing.get('variant') or drawing.get('fixed_columns'):
        # A module can receive and send on its left side in these arrangements.
        # Allocate both directions together so a return edge never retraces an arrival.
        def opposite_height(item):
            chain, endpoint = item
            other = chain[-1 if endpoint == 0 else 0]
            port = next((p for p in edge_ports if (p['source'], p['target']) == (chain[0], chain[-1])), {})
            side = port.get('entry' if endpoint == 0 else 'exit')
            box = boxes[other]
            return box[1] if side == 'top' else box[1]+box[3] if side == 'bottom' else drawing['positions'][other][1]

        shared = {}
        for chain in chains:
            a, b = chain[0], chain[-1]
            source_left = drawing['columns'][owner(a)][0] >= drawing['columns'][owner(b)][0]
            target_right = drawing['columns'][owner(a)][0] > drawing['columns'][owner(b)][0] and b not in children
            if (a, b) in internal_routes:
                source_left, target_right = False, False
            elif owner(a) == owner(b):
                source_left, target_right = False, True
            port_sides[(a, b, 0)] = 'left' if source_left else 'right'
            port_sides[(a, b, -1)] = 'right' if target_right else 'left'
            authored_ports = next((p for p in edge_ports
                                   if (p['source'], p['target']) == (a, b)), {})
            for key, endpoint, side in ((a, 0, authored_ports.get('exit', 'left' if source_left else 'right')),
                                        (b, -1, authored_ports.get('entry', 'right' if target_right else 'left'))):
                if side in ('left', 'right'):
                    shared.setdefault((key, side), []).append((chain, endpoint))
        for (key, side), endpoints in shared.items():
            endpoints.sort(key=opposite_height)
            if (graph.get('sections') and side == 'left' and len(endpoints) > 1
                    and all(endpoint == -1 and drawing['positions'][chain[0]][1] < drawing['positions'][key][1]
                            for chain, endpoint in endpoints)):
                # Arrivals descending through a realm gutter nest: the nearer
                # source takes the upper port, the longer route the lower one.
                endpoints.reverse()
            x, y, width, height = boxes[key]
            spacing = min(12, (height-24)/max(1, len(endpoints)-1))
            for index, (chain, endpoint) in enumerate(endpoints):
                ports[(chain[0], chain[-1], endpoint)] = y+height/2+(index-(len(endpoints)-1)/2)*spacing
            aligned = {tuple(pair) for pair in alignments}
            centered = [item for item in endpoints if (item[0][0], item[0][-1]) in aligned
                        or (graph.get('sections') and drawing['positions'][item[0][0]][1]
                            == drawing['positions'][item[0][-1]][1])]
            if centered:
                for chain, endpoint in centered:
                    ports[(chain[0], chain[-1], endpoint)] = y+height/2
                others = [item for item in endpoints if item not in centered]
                for direction in (-1, 1):
                    side_items = [item for item in others if
                                  (opposite_height(item) < y+height/2)
                                  == (direction == -1)]
                    side_items.sort(key=lambda item: abs(opposite_height(item)-(y+height/2)))
                    step = min(12, (height-24)/2/max(1, len(side_items)))
                    for index, (chain, endpoint) in enumerate(side_items, 1):
                        ports[(chain[0], chain[-1], endpoint)] = y+height/2+direction*index*step
    drawing.update(boxes=boxes, lines=lines, headers=headers, chains=chains, groups=set(children)-{''},
                   owners={key: owner(key) for key in by_key}, route_owners=route_owners,
                   back_routes=back_routes, ports=ports,
                   edge_ports={(p['source'], p['target']): p for p in edge_ports},
                   edge_exits={(p['source'], p['target']): p['exit'] for p in edge_ports},
                   edge_entries={(p['source'], p['target']): p['entry'] for p in edge_ports if 'entry' in p})
    # Same-side connections nest like parentheses: longer spans use the outer
    # tracks and outer source/target ports. Rounded orthogonal routes retain a
    # visible gap instead of overlapping along a shared Bezier corridor.
    internal_tracks = {}
    for parent, connections in internal_edges.items():
        if parent in group_layouts:
            continue
        connections = sorted(connections, key=lambda edge: abs(
            drawing['positions'][edge[0]][1]-drawing['positions'][edge[1]][1]))
        right = max(boxes[child][0]+boxes[child][2] for child in children[parent])
        for index, edge in enumerate(connections):
            internal_tracks[edge] = right + 24 + 16*index
    internal_nodes = {key for edge in internal_tracks for key in edge}
    for key in internal_nodes:
        attached = [endpoint for endpoint, side in port_sides.items()
                    if side == 'right' and endpoint[0 if endpoint[2] == 0 else 1] == key]
        def port_order(endpoint):
            source, target, end = endpoint
            other_y = drawing['positions'][target if end == 0 else source][1]
            if (source, target) in internal_tracks:
                return (0 if other_y < drawing['positions'][key][1] else 2, -other_y)
            chain = next(c for c in chains if c[0] == source and c[-1] == target)
            return (1, drawing['positions'][chain[1 if end == 0 else -2]][1])
        attached.sort(key=port_order)
        x, y, width, height = boxes[key]
        spacing = min(12, (height-24)/max(1, len(attached)-1))
        for index, endpoint in enumerate(attached):
            ports[endpoint] = y+height/2+(index-(len(attached)-1)/2)*spacing
    drawing['internal_tracks'] = internal_tracks
    for port in edge_ports:
        for endpoint, key, side, position in (
                (0, port['source'], port['exit'], port.get('exit_position')),
                (-1, port['target'], port.get('entry', 'left'), port.get('entry_position'))):
            if position is not None and side in ('left', 'right'):
                box = boxes[key]
                ports[(port['source'], port['target'], endpoint)] = box[1]+box[3]*position
    if drawing.get('variant') or drawing.get('fixed_columns'):
        drawing['gutter_routes'] = _gutter_routes(drawing)
    return drawing


def _curves(chain, drawing):
    if (chain[0], chain[-1]) in drawing.get('gutter_routes', {}):
        return drawing['gutter_routes'][(chain[0], chain[-1])]
    positions = drawing['positions']
    points = [positions[key] for key in chain]
    source, target = chain[0], chain[-1]
    a_box, b_box = drawing['boxes'][source], drawing['boxes'][target]
    points[0] = (a_box[0]+a_box[2]+1, drawing['ports'][(source, target, 0)])
    points[-1] = (b_box[0]-2, drawing['ports'][(source, target, -1)])
    a_owner, b_owner = drawing['route_owners'].get((source, target),
                                                 (drawing['owners'][source], drawing['owners'][target]))
    if (source, target) in drawing.get('internal_tracks', {}):
        right = drawing['internal_tracks'][(source, target)]
        end = (b_box[0]+b_box[2]+2, points[-1][1])
        return _rounded_route([points[0], (right, points[0][1]), (right, end[1]), end])
    if (source, target) in drawing['back_routes']:
        bottom = drawing['back_routes'][(source, target)]
        right = drawing['columns'][a_owner][1]+16
        left = drawing['columns'][b_owner][0]-16
        route = [points[0], (right, points[0][1]), (right, bottom),
                 (left, bottom), (left, points[-1][1]), points[-1]]
        return [(a, a, b, b) for a, b in zip(route, route[1:])]
    if drawing['columns'][a_owner] == drawing['columns'][b_owner]:
        start = (a_box[0]-1, points[0][1])
        end = points[-1]
        gutter = drawing['columns'][a_owner][0]-32
        return [(start, (gutter, start[1]), (gutter, end[1]), end)]
    # Use the whole column's boundary: a narrower destination can sit above
    # a wider container, whose corner/title must not be cut by the curve.
    start = (max(drawing['columns'][a_owner][1], points[0][0]), points[0][1])
    end = (min(drawing['columns'][b_owner][0], points[-1][0]), points[-1][1])
    curves = [(points[0], points[0], start, start)] if points[0] != start else []
    a = start
    for key in chain[1:-1]:
        column_left, column_right = drawing['columns'][key]
        y = positions[key][1]
        b = (column_left, y)
        mid = (a[0]+b[0])/2
        curves.append((a, (mid, a[1]), (mid, b[1]), b))
        a = (column_right, y)
        curves.append((b, b, a, a))
    mid = (a[0]+end[0])/2
    curves.append((a, (mid, a[1]), (mid, end[1]), end))
    if end != points[-1]:
        curves.append((end, end, points[-1], points[-1]))
    return curves


def _node_order(graph, drawing):
    # Container fills go behind arrows; module cards stay in front.
    by_key = {node['key']: node for node in graph['nodes']}
    def depth(node):
        return 1 + depth(by_key[node['parent']]) if node['parent'] else 0
    return sorted(graph['nodes'], key=depth)


def _label_size(lines, group):
    """Fit wrapped labels inside uniform cards; containers retain header sizing."""
    if group:
        return 17, 20
    font = min(17, (CARD_WIDTH-24)/(max(map(len, lines))*.6),
               (CARD_HEIGHT-16)/(len(lines)*1.18))
    return font, font*1.18


def svg(graph, variant=None):
    drawing = layout(graph, variant)
    top = -44 if graph.get('title') else 0
    width = max(drawing['width'], len(graph.get('title', ''))*11+24)
    description = (CAPTION + '. ' + MODULE_EXPLANATION
                   if graph['edges'] else 'Ausgewählte Aktivitäten ohne hinterlegte Abhängigkeiten untereinander.')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {top} {width} {drawing["height"]-top}" '
             'role="img" aria-labelledby="graph-title graph-desc">',
             '<title id="graph-title">Activity Flow</title><desc id="graph-desc">' + description + '</desc>',
             f'<defs><marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 Z" fill="#{palette.HEX["namMuted"]}"/></marker></defs>',
             '<style>text{font-family:system-ui,-apple-system,sans-serif;font-size:17px;font-weight:600}a:hover rect,a:focus rect{stroke-width:2.5}a{outline:none}</style>',
             f'<rect y="{top}" width="{width}" height="{drawing["height"]-top}" fill="#{palette.HEX["namBg"]}"/>']
    if graph.get('title'):
        parts.append(f'<text x="12" y="-16" fill="#{palette.HEX["namInk"]}">' + escape(graph['title']) + '</text>')
    for panel in drawing.get('lane_panels', []):
        parts.append(f'<g data-flow-lane="{escape(panel["key"], quote=True)}"><rect x="{panel["x"]}" y="{panel["y"]}" '
                     f'width="{panel["width"]}" height="{panel["height"]}" rx="10" fill="#{panel["color"]}" '
                     f'fill-opacity="0.035" stroke="#{panel["color"]}" stroke-opacity="0.4"/>'
                     f'<text x="{panel["x"]+16}" y="36" fill="#{panel["color"]}">{escape(panel["label"])}</text></g>')
    for label in drawing.get('section_labels', []):
        parts.append(f'<text data-flow-section="true" x="{label["x"]}" y="{label["y"]+20}" '
                     f'fill="#{label["color"]}">{escape(label["label"])}</text>')

    def card(node, group):
        key = node['key']
        x, y, width, height = drawing['boxes'][key]
        border, fill = PALETTES[node['color']]
        parts.append('<a href="' + escape(activity_pdf(node), quote=True) + '" data-key="' +
                     escape(key, quote=True) + '"><title>' + escape(node['title'] + ' · ' + key) + '</title>')
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="7" '
                     f'fill="#{fill if group else palette.HEX["namPanel"]}" stroke="#{border}" stroke-width="1.5"/>')
        labels = drawing['lines'][key]
        font, leading = _label_size(labels, group)
        for index, line in enumerate(labels):
            text_y = y + 25 + index*20 if group else y+height/2 + (index-(len(labels)-1)/2)*leading + font*.35
            text_x = x+16 if group else x+width/2
            anchor = 'start' if group else 'middle'
            parts.append(f'<text x="{text_x}" y="{text_y}" style="font-size:{font}px" text-anchor="{anchor}" fill="#{node["color"]}">{escape(line)}</text>')
        parts.append('</a>')

    ordered = _node_order(graph, drawing)
    for node in ordered:
        if node['key'] in drawing['groups']:
            card(node, True)
    for chain in drawing['chains']:
        curves = _curves(chain, drawing)
        path = f'M {curves[0][0][0]} {curves[0][0][1]} ' + ' '.join(
            f'C {c[0]} {c[1]}, {d[0]} {d[1]}, {b[0]} {b[1]}' for a, c, d, b in curves)
        parts.append(f'<path d="{path}" fill="none" stroke="#{palette.HEX["namMuted"]}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#arrow)"/>')
    for node in ordered:
        if node['key'] not in drawing['groups']:
            card(node, False)
    result = ''.join(parts) + '</svg>'
    if variant:
        for identifier in ('graph-title', 'graph-desc', 'arrow'):
            result = result.replace('id="'+identifier+'"', 'id="'+identifier+'-'+variant+'"')
        result = result.replace('aria-labelledby="graph-title graph-desc"',
                                'aria-labelledby="graph-title-'+variant+' graph-desc-'+variant+'"')
        result = result.replace('url(#arrow)', 'url(#arrow-'+variant+')')
    return result


def tex(graph):
    drawing = layout(graph)
    lines = [r'\documentclass[tikz,border=0pt]{standalone}', r'\input{theme.tex}',
             r'\usetikzlibrary{arrows.meta}', r'\colorlet{graphInk}{namInk}',
             r'\colorlet{graphArrow}{namMuted}',
             r'\pagecolor{namBg}', r'\begin{document}',
             r'\begin{tikzpicture}[x=1pt,y=-1pt,font=\sffamily\fontsize{17}{20}\selectfont,text=graphInk]',
             r'\fill[namBg] (0,0) rectangle (' + str(drawing['width']) + ',' + str(drawing['height']) + ');']
    if graph.get('title'):
        lines.append(r'\node[anchor=south west] at (12,-12) {' + _tex(graph['title']) + '};')
    for panel in drawing.get('lane_panels', []):
        lines.append(r'\definecolor{laneAccent}{HTML}{' + panel['color'] + '}')
        x, y, w, h = (panel[k] for k in ('x', 'y', 'width', 'height'))
        lines.append(r'\draw[fill=laneAccent,fill opacity=0.035,draw=laneAccent,draw opacity=0.4,rounded corners=8pt] '
                     f'({x},{y}) rectangle ({x+w},{y+h});')
        lines.append(r'\node[anchor=base west,text=laneAccent,font=\sffamily\bfseries,inner sep=0pt] at '
                     f'({x+16},36)' + ' {' + _tex(panel['label']) + '};')
    for label in drawing.get('section_labels', []):
        lines.append(r'\definecolor{sectionAccent}{HTML}{' + label['color'] + '}')
        lines.append(r'\node[anchor=base west,text=sectionAccent,font=\sffamily\bfseries,inner sep=0pt] at '
                     f'({label["x"]},{label["y"]+20})' + ' {' + _tex(label['label']) + '};')

    def point(p):
        return '(' + str(p[0]) + ',' + str(p[1]) + ')'

    def card(node, group):
        key = node['key']
        x, y, width, height = drawing['boxes'][key]
        border, fill = PALETTES[node['color']]
        for name, value in [('nodeAccent', node['color']), ('nodeBorder', border), ('nodeFill', fill)]:
            lines.append(r'\definecolor{' + name + '}{HTML}{' + value + '}')
        lines.append(r'\draw[fill=' + ('nodeFill' if group else 'namPanel') +
                     r',draw=nodeBorder,rounded corners=6pt,line width=1.2pt] ' +
                     point((x, y)) + ' rectangle ' + point((x+width, y+height)) + ';')
        position = (x+16, y+drawing['headers'][key]/2) if group else (x+width/2, y+height/2)
        font, leading = _label_size(drawing['lines'][key], group)
        lines.append(r'\node[text=nodeAccent,align=' + ('left,anchor=west' if group else 'center') +
                     r',inner sep=0pt,font=\sffamily\bfseries\fontsize{' + str(font) + '}{' + str(leading) +
                     r'}\selectfont] at ' + point(position) + ' {' +
                     r'\\'.join(_tex(line) for line in drawing['lines'][key]) + '};')

    ordered = _node_order(graph, drawing)
    for node in ordered:
        if node['key'] in drawing['groups']:
            card(node, True)
    for chain in drawing['chains']:
        curves = _curves(chain, drawing)
        lines.append(r'\draw[graphArrow,line width=1.2pt,-{Stealth[length=5pt,width=4pt]}] ' +
                     point(curves[0][0]) + ' '.join(' .. controls ' + point(c) + ' and ' + point(d) +
                     ' .. ' + point(b) for a, c, d, b in curves) + ';')
    for node in ordered:
        if node['key'] not in drawing['groups']:
            card(node, False)
    return '\n'.join([*lines, r'\end{tikzpicture}', r'\end{document}', ''])


def render_html(graph, destination, *, selection=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    diagram = svg(dict(graph, title='')) if graph['nodes'] else '<p>Keine Aktivitäten in dieser Auswahl.</p>'
    explanation = ('<p>' + MODULE_EXPLANATION + ' Kästchen öffnen die Aktivität im Report.</p>' if graph['edges'] else
                   '<p>Zwischen diesen Aktivitäten sind keine Abhängigkeiten hinterlegt.</p>' if graph['nodes'] else '')
    exports = tuple(('Graph · ' + extension.upper(), 'views/dependency-graph/' + selections.filename(selection, 'graph.' + extension))
                    for extension in ('png', 'pdf', 'svg')) if graph['nodes'] else ()
    if graph['nodes']:
        (destination / selections.filename(selection, 'graph.svg')).write_text(svg(graph), encoding='utf-8')
    # Keep the graph comfortably legible on narrow windows through local scrolling.
    min_width = min(900, layout(graph)['width']) if graph['nodes'] else 0
    max_width = layout(graph)['width'] if graph['nodes'] else 0
    comparisons = ''
    if graph['nodes'] and not graph.get('columns') and layout(graph, 'semantic').get('variant'):
        comparisons = ('<section id="layoutvergleich" class="comparisons" aria-label="Layoutvergleich"><h2>Zwei Anordnungen</h2>'
                       '<p>Dieselben Vorhaben und Abhängigkeiten, anders angeordnet. '
                       'Pfeile zeigen weiterhin von der Grundlage zum darauf aufbauenden Vorhaben.</p>')
        for variant, (title, description) in VARIANTS.items():
            comparisons += ('<details class="comparison" open><summary>' + escape(title) + '</summary><p>'
                            + escape(description) + '</p><div class="graph" tabindex="0" role="region" aria-label="'
                            + escape(title, quote=True) + '">' + svg(graph, variant) + '</div></details>')
        comparisons += '</section>'
    html = ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            + navigation.head('graph') + '<style>'
            + palette.css(':root{color-scheme:dark}body{margin:0;background:@namBg;color:@namInk;font:16px/1.5 system-ui,sans-serif}'
            'main{max-width:1440px;margin:auto;padding:36px 24px}h1{font-size:2.4rem;margin:0}p{color:@namMuted}'
            'a{color:@namBrand;text-underline-offset:3px}'
            'a:focus-visible{outline:2px solid @namBrand;outline-offset:4px}.graph{overflow:auto;border:1px solid @namLine;border-radius:10px;padding:16px}'
            '.comparisons{margin-top:48px;padding-top:24px;border-top:1px solid @namLine}'
            '.comparisons h2{font-size:1.5rem;margin:0}.comparison{margin-top:28px}'
            '.comparison summary{cursor:pointer;font-size:1.15rem;font-weight:600;color:@namBrand}'
            '.comparison summary:focus-visible{outline:2px solid @namBrand;outline-offset:6px}')
            + f'.graph svg{{display:block;width:100%;min-width:{min_width}px;max-width:{max_width}px;height:auto}}'
            + navigation.STYLE + footer.STYLE + '</style></head><body class="yap-page">' + navigation.render('graph', theme='dark', exports=exports, selection=selection) +
            '<main><h1>' + escape(graph.get('title', 'Activity Flow')) + '</h1>'
            + ('<p>' + CAPTION + '</p>' if graph['edges'] else '')
            + '<div class="graph" tabindex="0" role="region" aria-label="Abhängigkeitsgraph">' + diagram + '</div>'
            + explanation
            + comparisons + '</main>' + footer.render() + '</body></html>')
    (destination / selections.filename(selection)).write_text(html, encoding='utf-8')
