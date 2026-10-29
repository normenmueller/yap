"""Misuses that the checked public boundary must reject before execution."""

from pathlib import Path

from yap.outputs import publish, validate_tree
from yap.source_values import canonical_date

validate_tree('instance', Path('site'))
publish(Path('stage'), Path('site'), root='instance')
canonical_date('2026-10-29', 42)
deadline: str = canonical_date('2026-10-29', 'result: deadline')
