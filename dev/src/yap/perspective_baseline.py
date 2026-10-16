"""Read-only inventory of the live hierarchy before perspective migration."""

import json
from pathlib import Path
import re

from . import board, content, overview, performance_lanes


def inventory(root):
    model = content.load(root)
    lanes = board.lanes(model)
    selected = {}
    for node in model['nodes']:
        html = performance_lanes.render(model, [node['key']])
        selected[node['key']] = sorted(set(re.findall(r'data-activity="([^"]+)"', html)))
    return dict(
        purpose='Pre-migration acceptance snapshot; authored Markdown remains authoritative.',
        source_order=[dict(key=n['key'], path=n['path'], id=n['id'], parent=n['parent'], depth=n['depth'])
                      for n in model['nodes']],
        visible=[n['key'] for n in overview.activity_nodes(model)],
        board_columns=board.COLUMNS,
        board_lanes=lanes,
        dependencies=model['dgraph'],
        performance_selection=selected,
    )


if __name__ == '__main__':
    print(json.dumps(inventory(Path(__import__('sys').argv[1]).resolve()), ensure_ascii=False, indent=2))
