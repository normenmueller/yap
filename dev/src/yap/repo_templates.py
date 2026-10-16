"""Render portable repository starters without Git, portfolio or destination writes."""

from copy import deepcopy
import html
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit


from .resources import TEMPLATES as APPLICATION_TEMPLATES

TEMPLATES = APPLICATION_TEMPLATES / 'repo'
PROFILES = ('general', 'db-gitlab')
LANGUAGES = ('de', 'en')
DEFAULTS = {
    'copyright_holder': 'Project contributors',
    'copyright_year': 2026,
    'copyright_url': '',
    'ai4x_footer': True,
    'db_metadata': {
        'version': 'v3',
        'license': 'LicenseRef-DBISL',
        'contacts': [],
        'confidentiality': 'internal',
        'reference-ids': ['none'],
        'protected-branches': ['trunk'],
        'usage-scenario': ['other'],
        'custom': {'integrity': 'normal', 'availability': 'normal', 'confidentiality': 'normal'},
    },
}
INPUTS = {'title', 'languages', 'primary_language', 'purpose', 'maintainer',
          'copyright_holder', 'copyright_year', 'copyright_url', 'ai4x_footer',
          'db_metadata', 'db_confirmed', 'license_text'}
TOKEN = re.compile(r'\{\{([a-z_-]+)\}\}')


def defaults():
    """Return independent generic suggestions; these do not confirm DB metadata."""
    return deepcopy(DEFAULTS)


def resolved_inputs(inputs):
    """Expose effective values after render validation, without confirming metadata."""
    result = deepcopy(inputs)
    for key in ('copyright_holder', 'copyright_year', 'ai4x_footer'):
        result.setdefault(key, DEFAULTS[key])
    result.setdefault('copyright_url', DEFAULTS['copyright_url']
                      if result['copyright_holder'].strip() == DEFAULTS['copyright_holder'] else '')
    for field in ('purpose', 'maintainer'):
        values = result.setdefault(field, {})
        if isinstance(values, dict):
            for language in result['languages']:
                values.setdefault(language, 'Noch offen.' if language == 'de' else 'Open.')
    return result


def _text(value, name, *, multiline=False):
    if (not isinstance(value, str) or not value.strip()
            or any(ord(char) < 32 and not (multiline and char == '\n') for char in value)
            or '\x7f' in value):
        raise ValueError(f'{name}: expected nonempty {"text" if multiline else "single-line text"}.')
    return value.strip()


def _markdown(value):
    # Inputs are authored plain text, never executable HTML or Markdown fragments.
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', html.escape(value, quote=False))


def _replace(data, values, name):
    def replacement(match):
        if match[1] not in values:
            raise ValueError(f'{name}: unresolved placeholder {match[0]}.')
        return values[match[1]]
    source = data.decode('utf-8')
    literal = TOKEN.sub('', source)
    if '{{' in literal or '}}' in literal:
        raise ValueError(f'{name}: unresolved placeholder.')
    return TOKEN.sub(replacement, source).encode('utf-8')


def _template_path(relative):
    for parent in TEMPLATES.parents:
        if parent.is_symlink():
            raise ValueError(f'Template symlinks are not allowed: {parent.name}.')
    path = TEMPLATES
    for part in ('', *Path(relative).parts):
        path = path / part
        if path.is_symlink():
            raise ValueError(f'Template symlinks are not allowed: {relative}.')
    return path


def _read_file(path):
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode) or mode & 0o111:
        raise ValueError(f'Template must be a nonexecutable regular file: {path.name}.')
    return path.read_bytes()


def _files(directory):
    """Read literal template files, rejecting links, metadata and active hooks."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f'Invalid template directory: {directory.name}.')
    result = {}
    for current, directories, files in os.walk(directory, followlinks=False):
        for name in sorted([*directories, *files]):
            path = Path(current) / name
            relative = path.relative_to(directory)
            if (path.is_symlink() or any(part.casefold() in {'.git', 'hooks'} for part in relative.parts)
                    or '\\' in name or ':' in name or any(ord(char) < 32 for char in name)):
                raise ValueError(f'Unsafe template path: {relative}.')
            mode = path.stat().st_mode
            if stat.S_ISDIR(mode):
                continue
            result[relative.as_posix()] = _read_file(path)
    return result


def _metadata(value):
    expected = DEFAULTS['db_metadata']
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('db_metadata: supply the complete displayed metadata set.')
    if value['version'] != 'v3' or value['license'] != 'LicenseRef-DBISL':
        raise ValueError('db_metadata: only version v3 and LicenseRef-DBISL are supported.')
    result = {'version': 'v3', 'license': 'LicenseRef-DBISL'}
    for key in ('contacts', 'reference-ids', 'protected-branches', 'usage-scenario'):
        entries = value[key]
        if not isinstance(entries, list) or not entries:
            raise ValueError(f'db_metadata.{key}: expected a nonempty list of strings.')
        result[key] = [_text(item, f'db_metadata.{key}') for item in entries]
    result['confidentiality'] = _text(value['confidentiality'], 'db_metadata.confidentiality')
    custom = value['custom']
    if not isinstance(custom, dict) or set(custom) != set(expected['custom']):
        raise ValueError('db_metadata.custom: integrity, availability and confidentiality are required.')
    result['custom'] = {key: _text(custom[key], f'db_metadata.custom.{key}') for key in expected['custom']}
    return result


def render_template(profile, inputs):
    """Return deterministic relative POSIX paths mapped to bytes; never write files.

    Required: title, languages (de/en list), primary_language. Optional purpose
    and maintainer map selected languages to plain text; missing values remain
    explicitly open. Copyright/footer suggestions come from defaults(). A custom
    holder without copyright_url gets no inherited personal profile link.
    General accepts optional verbatim license_text. DB requires the complete
    db_metadata object and db_confirmed=True; neither is inferred from defaults.
    """
    if profile not in PROFILES:
        raise ValueError('profile: choose general or db-gitlab.')
    if not isinstance(inputs, dict) or set(inputs) - INPUTS:
        raise ValueError('Template inputs contain unsupported keys or are not an object.')
    title = _text(inputs.get('title'), 'title')
    languages = inputs.get('languages')
    if (not isinstance(languages, list) or not languages
            or any(language not in LANGUAGES for language in languages)
            or len(set(languages)) != len(languages)):
        raise ValueError('languages: choose ["de"], ["en"] or both without duplicates.')
    primary = inputs.get('primary_language')
    if primary not in languages:
        raise ValueError('primary_language: explicitly select one of the documentation languages.')
    _text(inputs.get('copyright_holder', DEFAULTS['copyright_holder']), 'copyright_holder')
    inputs = resolved_inputs(inputs)
    localized = {}
    for field in ('purpose', 'maintainer'):
        values = inputs.get(field, {})
        if not isinstance(values, dict) or set(values) - set(languages):
            raise ValueError(f'{field}: expected an object keyed by selected documentation languages.')
        localized[field] = {language: _text(value, f'{field}.{language}', multiline=True)
                            for language, value in values.items()}
    holder = _text(inputs['copyright_holder'], 'copyright_holder')
    year = inputs['copyright_year']
    if type(year) is not int or not 1 <= year <= 9999:
        raise ValueError('copyright_year: expected an explicit integer between 1 and 9999.')
    url = inputs['copyright_url']
    if not isinstance(url, str):
        raise ValueError('copyright_url: expected an HTTPS/HTTP URL or an empty string.')
    if url:
        parsed = urlsplit(url)
        if (parsed.scheme not in {'https', 'http'} or not parsed.netloc or parsed.username is not None
                or any(char.isspace() or ord(char) < 32 or char in '<>\\"' for char in url)):
            raise ValueError('copyright_url: expected an HTTPS/HTTP URL without credentials or whitespace.')
    footer = inputs['ai4x_footer']
    if type(footer) is not bool:
        raise ValueError('ai4x_footer: expected true or false.')
    license_text = inputs.get('license_text')
    metadata = None
    if profile == 'db-gitlab':
        if 'license_text' in inputs:
            raise ValueError('DB LICENSE cannot be replaced by license_text.')
        if inputs.get('db_confirmed') is not True:
            raise ValueError('Confirm the complete DB metadata for this repository with db_confirmed: true.')
        metadata = _metadata(inputs.get('db_metadata'))
    else:
        if 'db_metadata' in inputs or 'db_confirmed' in inputs:
            raise ValueError('DB metadata and confirmation require the db-gitlab profile.')
        if 'license_text' in inputs:
            _text(license_text, 'license_text', multiline=True)

    # The durable trees have no executable hooks or expression language.
    base = _files(_template_path('base'))
    required = {'README.de.md', 'README.en.md', 'doc/README.de.md', 'doc/README.en.md',
                '.ai4x/BEHAVIOR.md', '.ai4x/CONTEXT.md', '.ai4x/STATE.md',
                'AGENTS.md', '.gitattributes', '.gitignore'}
    if required - set(base):
        raise ValueError('Incomplete base template: missing ' + ', '.join(sorted(required - set(base))))
    result = {name: data for name, data in base.items()
              if name not in {'README.de.md', 'README.en.md', 'doc/README.de.md', 'doc/README.en.md'}}
    footer_text = _read_file(_template_path('ai4x-footer.html')).decode('utf-8') if footer else ''
    copyright_holder = _markdown(holder)
    if url:
        # Angle-delimited destinations allow literal parentheses without breaking links.
        copyright_holder = f'[{copyright_holder}](<{url}>)'
    filenames = {language: 'README.md' if language == primary else f'README.{language}.md'
                 for language in languages}
    for language in languages:
        filename = filenames[language]
        if filename in result or f'doc/{filename}' in result:
            raise ValueError(f'Template output collision: {filename}.')
        other = next((item for item in languages if item != language), None)
        alternate = (f'[{"English" if other == "en" else "Deutsch"}]({filenames[other]})\n' if other else '')
        licensed = metadata is not None or license_text is not None
        values = {
            'title': _markdown(title),
            'purpose': _markdown(localized['purpose'][language]),
            'maintainer': _markdown(localized['maintainer'][language]),
            'alternate_link': alternate,
            'readme': filename,
            'db_structure': (('`LICENSE` enthält die DB-Lizenz; `scm-info.yaml` enthält bestätigte Repository-Metadaten.\n'
                              if language == 'de' else '`LICENSE` contains the DB license; `scm-info.yaml` contains confirmed repository metadata.\n')
                             if metadata is not None else ''),
            'license_notice': (('Siehe [LICENSE](./LICENSE).' if language == 'de' else 'See [LICENSE](./LICENSE).')
                               if licensed else ('Noch nicht festgelegt.' if language == 'de' else 'Not selected yet.')),
            'copyright': f'© {year} {copyright_holder}',
            'footer': footer_text,
        }
        result[filename] = _replace(base[f'README.{language}.md'], values, filename)
        result[f'doc/{filename}'] = _replace(base[f'doc/README.{language}.md'], values, f'doc/{filename}')
    context = {'title': _markdown(title), 'languages': ', '.join(language for language in LANGUAGES if language in languages),
               'primary_language': primary,
               'db_authority': ('LICENSE owns the selected license text; scm-info.yaml owns confirmed DB repository metadata.\n'
                                if metadata is not None else ('LICENSE owns the explicitly supplied license text.\n' if license_text else ''))}
    for name in ('.ai4x/BEHAVIOR.md', '.ai4x/CONTEXT.md', '.ai4x/STATE.md', 'AGENTS.md'):
        result[name] = _replace(result[name], context, name)
    if metadata is not None:
        db = _files(_template_path('gitlab/db'))
        if set(db) != {'LICENSE', 'scm-info.yaml'}:
            raise ValueError('DB template must contain exactly LICENSE and scm-info.yaml.')
        result['LICENSE'] = db['LICENSE']
        values = {key: json.dumps(value, ensure_ascii=False) for key, value in metadata.items() if key != 'custom'}
        values.update({key: json.dumps(metadata['custom'][key], ensure_ascii=False)
                       for key in ('integrity', 'availability')})
        values['custom_confidentiality'] = json.dumps(metadata['custom']['confidentiality'], ensure_ascii=False)
        result['scm-info.yaml'] = _replace(db['scm-info.yaml'], values, 'scm-info.yaml')
    elif license_text is not None:
        result['LICENSE'] = license_text.encode('utf-8')
    if 'LICENSE' in result:
        result['.gitattributes'] += b'LICENSE -text\n'
    return dict(sorted(result.items()))
