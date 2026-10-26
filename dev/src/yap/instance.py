"""Read ordinary instance data; loading never changes or provisions an instance."""
import json
from pathlib import Path, PurePosixPath
import re


def manifest(root=None):
    root = Path(root).resolve() if root is not None else Path.cwd()
    path = root / 'yap.json'
    if not path.is_file():
        return {}
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or value.get('schema') != 1:
        raise ValueError('yap.json: expected an object with schema 1.')
    if not isinstance(value.get('slug'), str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', value['slug']):
        raise ValueError('yap.json: slug must be a simple file name.')
    sources = value.get('sources', {})
    if not isinstance(sources, dict):
        raise ValueError('yap.json: sources must be a mapping.')
    if 'aspirations' in sources:
        selected = sources['aspirations']
        if (not isinstance(selected, str) or not selected.strip() or '\0' in selected
                or PurePosixPath(selected).is_absolute() or '..' in PurePosixPath(selected).parts):
            raise ValueError(f'yap.json: sources.aspirations must be a nonempty relative instance path: {selected!r}.')
    branding = value.get('branding', {})
    if not isinstance(branding, dict) or any(not isinstance(v, str) for key, v in branding.items() if key != 'footer_link'):
        raise ValueError('yap.json: branding values must be text except optional footer_link data.')
    for field in ('logo', 'favicon'):
        if field in branding:
            relative = PurePosixPath(branding[field])
            if relative.is_absolute() or '..' in relative.parts or not relative.parts:
                raise ValueError('yap.json: branding assets must be relative instance paths.')
            source = root / branding[field]
            if not source.resolve().is_relative_to(root) or not source.is_file():
                raise ValueError('yap.json: branding asset must exist within the instance: ' + str(source))
    prefix = value.get('publication_prefix', 'yap-')
    if not isinstance(prefix, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', prefix):
        raise ValueError('yap.json: publication_prefix must be an ASCII destination prefix.')
    return value


def entry():
    return manifest().get('slug', 'yap') + '.html'


def brand(field, default):
    return manifest().get('branding', {}).get(field, default)


def verify_application(value):
    """A declared revision selects exactly one clean application checkout."""
    import subprocess
    from .resources import APPLICATION
    pin = value.get('application')
    if pin is None:
        return
    if not isinstance(pin, dict) or not isinstance(pin.get('revision'), str) or not re.fullmatch(r'[0-9a-f]{40}', pin['revision']):
        raise ValueError('yap.json: application.revision must be an exact Git commit.')
    def git(*arguments):
        result = subprocess.run(['git', '-C', str(APPLICATION), *arguments], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('The selected application is not an available Git checkout.')
        return result.stdout.strip()
    if Path(git('rev-parse', '--show-toplevel')).resolve() != APPLICATION:
        raise ValueError('The selected application must have its own Git checkout.')
    if git('rev-parse', 'HEAD') != pin['revision']:
        raise ValueError('Application revision differs from the instance pin; select the pinned application explicitly.')
    if git('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Application checkout has changes; a pinned instance requires a clean application.')
