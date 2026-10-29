"""Valid public calls, checked statically and never executed."""

from datetime import date
from pathlib import Path

from yap.outputs import publish, validate_tree
from yap.source_values import canonical_date

root = Path('/synthetic-instance')
validated: Path = validate_tree(root, root / 'site')
publish(root / 'stage', validated, root=root)
deadline: date = canonical_date('2026-10-29', 'result: deadline')
