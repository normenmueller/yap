"""Minimal application credit and optional instance-supplied plain text."""

from html import escape

from . import palette, instance


STYLE = palette.css('''
body.yap-page{display:flex;flex-direction:column;min-height:100vh}
.yap-page>main{flex:1;width:100%;box-sizing:border-box}
.yap-footer{flex:none;box-sizing:border-box;width:100%;margin:0;padding:40px 24px 32px;text-align:center;color:@namMuted;font:400 .78rem/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.yap-footer .footer-signoff{color:@namBrand;white-space:nowrap}
.yap-footer a{color:@namBrand;text-underline-offset:3px}
.yap-footer a:hover{color:@namInk}
.yap-footer a:focus-visible{outline:2px solid @namBrand;outline-offset:4px}
@media print{.yap-footer{display:none}.yap-page{display:block!important;min-height:0!important}}
''')


def render(language='de', *, about_href='../../about.html'):
    """Keep the product name unchanged in both interface languages."""
    credit = instance.brand('footer', '')
    prefix = escape(credit) + ' · ' if credit.strip() else ''
    return ('<footer class="yap-footer">' + prefix
            + '<a class="footer-signoff" href="' + escape(about_href, quote=True)
            + '">Focused with yap</a></footer>')
