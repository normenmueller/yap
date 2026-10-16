"""Read the shared TeX palette for HTML, SVG and derived status colors."""

from pathlib import Path
import re


from .resources import TEMPLATES

SOURCE = TEMPLATES / 'tex/palette.tex'
HEX = {}
for line in SOURCE.read_text().splitlines():
    definition = re.fullmatch(r'\\definecolor\{(\w+)\}\{HTML\}\{([0-9A-F]{6})\}', line)
    alias = re.fullmatch(r'\\colorlet\{(\w+)\}\{(\w+)\}', line)
    if definition:
        HEX[definition[1]] = definition[2]
    elif alias:
        HEX[alias[1]] = HEX[alias[2]]

STATUS = {'ibx': 'namIcebox', 'wip': 'namWip',
          'on hold': 'namHold', 'released': 'namReleased'}


def css(template):
    """Expand @namToken references in static CSS without touching authored content."""
    return re.sub(r'@(nam\w+)', lambda match: '#' + HEX[match[1]].lower(), template)
