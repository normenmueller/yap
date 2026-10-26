"""One instance-relative path contract for aspiration readers and builds."""

from dataclasses import dataclass
from pathlib import Path

from .instance import manifest


@dataclass(frozen=True)
class AspirationPaths:
    root: Path

    @property
    def goals(self):
        return self.root / 'goals.md'

    @property
    def objectives(self):
        return self.root / 'obj'


def resolve(root):
    """Validate the selected source before reading, discovery or cache reuse."""
    root = Path(root).resolve()
    paths = AspirationPaths(Path(manifest(root).get('sources', {}).get('aspirations', 'pfo/asp')))
    selected = root / paths.root
    portable = Path(paths.root.as_posix().casefold())
    for protected in ('.yap', '.git', 'pov', 'pfo/act', 'pfo/nts'):
        boundary = Path(protected)
        if portable.is_relative_to(boundary) or boundary.is_relative_to(portable):
            raise ValueError(f'{paths.root}: aspiration source overlaps {protected}.')
    current = root
    for component in paths.root.parts:
        current /= component
        if current.is_symlink():
            raise ValueError(f'{paths.root}: symlinks are not aspiration sources ({current.relative_to(root)}).')
    if not selected.resolve().is_relative_to(root):
        raise ValueError(f'{paths.root}: aspiration source must stay within the instance.')
    if not selected.is_dir():
        raise ValueError(f'{paths.root}: expected an existing aspiration source directory.')
    control = root / paths.goals
    if control.is_symlink() or not control.is_file():
        raise ValueError(f'{paths.goals}: expected a regular control file; symlinks are not allowed.')
    objectives = root / paths.objectives
    if objectives.is_symlink() or (objectives.exists() and not objectives.is_dir()):
        raise ValueError(f'{paths.objectives}: expected an objective directory; symlinks are not allowed.')
    return paths
