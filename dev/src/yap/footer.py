"""Minimal application credit and optional instance-supplied plain text."""

from html import escape
from urllib.parse import urlsplit

from . import palette, instance


STYLE = palette.css('''
body.yap-page{display:flex;flex-direction:column;min-height:100vh}
.yap-page>main{flex:1;width:100%;box-sizing:border-box}
.yap-footer{flex:none;box-sizing:border-box;width:100%;margin:0;padding:40px 24px 32px;text-align:center;color:@namMuted;font:400 .78rem/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.yap-footer .footer-signoff{color:@namBrand;white-space:nowrap}
.yap-footer a{color:@namBrand;text-underline-offset:3px}
.yap-footer a:hover{color:@namInk}
.yap-footer a:focus-visible{outline:2px solid @namBrand;outline-offset:4px}
.footer-product{position:relative;display:inline-block}.footer-gloss{position:absolute;z-index:20;bottom:calc(100% + 8px);right:0;width:max-content;max-width:calc(100vw - 48px);padding:6px 10px;border:1px solid @namLine;border-radius:7px;background:@namPanel;color:@namInk;font-size:.75rem;line-height:1.6;visibility:hidden;pointer-events:none;white-space:normal}.footer-product:hover .footer-gloss,.footer-product:focus-within .footer-gloss{visibility:visible}
@media print{.yap-footer{display:none}.yap-page{display:block!important;min-height:0!important}}
''')


def _credit(text, link):
    """A malformed or ambiguous optional link leaves the credit as plain text."""
    plain = escape(text)
    if not isinstance(link, dict) or set(link) != {'text', 'url'}:
        return plain
    label, url = link['text'], link['url']
    if (not isinstance(label, str) or not label or label.strip() != label
            or text.find(label) < 0 or text.find(label) != text.rfind(label)
            or not isinstance(url, str) or not url
            or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in url)):
        return plain
    try:
        address = urlsplit(url)
        if (address.scheme not in ('http', 'https') or not address.hostname
                or address.username is not None or address.password is not None):
            return plain
        address.port  # Reject malformed ports without making network requests.
    except ValueError:
        return plain
    before, _, after = text.partition(label)
    return (escape(before) + '<a href="' + escape(url, quote=True) + '">'
            + escape(label) + '</a>' + escape(after))


def render(language='de', *, about_href='../../about.html', homepage=False):
    """Keep the product name unchanged in both interface languages."""
    credit = instance.brand('footer', '')
    separator = ' ' if homepage and credit.rstrip().endswith('.') else ' · '
    prefix = _credit(credit, instance.brand('footer_link', None)) + separator if credit.strip() else ''
    signoff = ('<a class="footer-signoff" href="' + escape(about_href, quote=True) + '"'
               + (' aria-describedby="footer-gloss"' if homepage else '') + '>yap</a>')
    if homepage:
        signoff = ('<span class="footer-product">' + signoff
                   + '<span class="footer-gloss" id="footer-gloss" role="tooltip">to yap ≈ quasseln</span></span>.')
    return '<footer class="yap-footer">' + prefix + 'Focused with ' + signoff + '</footer>'
