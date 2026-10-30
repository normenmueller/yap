"""Verify rejected boundary calls without ignores or unchecked assertions."""

from pathlib import Path
import re
import subprocess
import sys

fixture = Path('dev/tst/typecheck/negative.py')
result = subprocess.run([
    sys.executable, '-B', '-m', 'mypy', '--config-file', 'mypy.ini',
    '--no-incremental', '--no-error-summary', str(fixture),
], capture_output=True, text=True)
errors = re.findall(r'^dev/tst/typecheck/negative.py:\d+: error: .*\[([^\]]+)\]$',
                    result.stdout, re.M)
if result.returncode != 1 or sorted(errors) != ['arg-type'] * 5 + ['assignment']:
    print(result.stdout + result.stderr)
    raise SystemExit('The negative type fixture did not reject all six invalid calls.')
print('Type contracts: six invalid calls rejected; no type ignores or casts.')
