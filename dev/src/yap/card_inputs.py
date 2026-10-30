"""Checked, illustrative display inputs for the two existing collection cards.

These authored examples are neither saved yapic definitions nor measured growth.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Need:
    paragraphs: tuple[str, ...]
    sender: str = ''
    recipient: str = ''


@dataclass(frozen=True)
class Card:
    need: Need | None = None
    growth_label: str = ''


@dataclass(frozen=True)
class Cards:
    activity: Card = Card()
    performance: Card = Card()


def _mapping(value: object, path: str, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f'{path}: expected an object.')
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str) or key not in fields:
            raise ValueError(f'{path}: unknown field {key!r}.')
        result[key] = item
    return result


def _text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{path}: expected nonempty text.')
    return value


def _card(value: object, path: str) -> Card:
    fields = _mapping(value, path, {'need', 'growth_label'})
    need = None
    if 'need' in fields:
        need_path = path + '.need'
        source = _mapping(fields['need'], need_path, {'paragraphs', 'sender', 'recipient'})
        paragraphs = source.get('paragraphs')
        if not isinstance(paragraphs, list) or not paragraphs:
            raise ValueError(f'{need_path}.paragraphs: expected a nonempty array of text paragraphs.')
        need = Need(tuple(_text(item, need_path + '.paragraphs') for item in paragraphs),
                    _text(source['sender'], need_path + '.sender') if 'sender' in source else '',
                    _text(source['recipient'], need_path + '.recipient') if 'recipient' in source else '')
    growth = _text(fields['growth_label'], path + '.growth_label') if 'growth_label' in fields else ''
    return Card(need, growth)


def decode(value: object) -> Cards:
    """Validate JSON at its boundary and own immutable copies of authored values."""
    path = 'yap.json: illustrative_cards'
    fields = _mapping(value, path, {'activity', 'performance'})
    return Cards(_card(fields.get('activity', {}), path + '.activity'),
                 _card(fields.get('performance', {}), path + '.performance'))
