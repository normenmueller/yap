"""Shared page signature and attribution for the offline HTML views."""

from html import escape

from . import palette, instance, product


STYLE = palette.css('''
body.yap-page{display:flex;flex-direction:column;min-height:100vh}
.yap-page>main{flex:1;width:100%;box-sizing:border-box}
.yap-footer{flex:none;box-sizing:border-box;width:100%;margin:0;padding:40px 24px 32px;text-align:center;color:@namMuted;font:400 .78rem/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.yap-footer .footer-signoff{color:@namBrand;white-space:nowrap}
.yap-footer .credit{margin:8px 0 0;font-size:.72rem}
.yap-footer a{color:@namBrand;text-underline-offset:3px}
.yap-footer a:hover{color:@namInk}
.yap-footer a:focus-visible{outline:2px solid @namBrand;outline-offset:4px}
@media print{.yap-footer{display:none}.yap-page{display:block!important;min-height:0!important}}
''')


def render(language='de', *, about_href='../../about.html'):
    description = ('Clarity about initiatives and impact.' if language == 'en'
                   else 'Klarheit über Vorhaben und Wirkung.')
    author = instance.brand('author', '')
    credit = escape(instance.brand('footer', 'Powered by yap'))
    if author.strip():
        byline = 'Portfolio by ' if language == 'en' else 'Portfolio von '
        credit = byline + escape(author) + (' · ' + credit if credit else '')
    return ('<footer class="yap-footer"><a class="footer-signoff" href="'
            + escape(about_href, quote=True) + '"><em>' + escape(product.SIGNATURE)
            + '</em></a> · ' + description + '<p class="credit">'
            + credit + '</p></footer>')
