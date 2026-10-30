"""Homepage disclosure and layout contracts survive branding and offline use."""
from pathlib import Path
import json
import os
import tempfile
import time
import unittest

from yap import browser, home


class HomeTests(unittest.TestCase):
    def test_mission_owned_layout_and_native_definition_with_and_without_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / 'site/example.html'
            for title in ('yap.', 'Example portfolio.'):
                branding = {'title': title, 'tagline': 'An explicitly selected activity portfolio'}
                if title != 'yap.':
                    branding['assistant_credit'] = 'https://example.org/' + 'long-fragment-' * 15
                (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example',
                                                       'branding': branding}))
                previous = Path.cwd()
                try:
                    os.chdir(root)
                    home.render(root / 'site')
                finally:
                    os.chdir(previous)
                with browser.page(page, root) as connection:
                    def js(expression):
                        result = connection.call('Runtime.evaluate', expression=expression,
                                                 returnByValue=True, awaitPromise=True)
                        self.assertNotIn('exceptionDetails', result)
                        return result['result'].get('value')

                    def frames(enabled):
                        if enabled:
                            js('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
                        else:
                            connection.call('Page.getLayoutMetrics')

                    for enabled in (True, False):
                        connection.call('Emulation.setScriptExecutionDisabled', value=not enabled)
                        connection.call('Page.navigate', url=page.as_uri())
                        for _ in range(150):
                            if js('document.readyState==="complete" && document.querySelector(".home-content")'
                                  '?.classList.contains("home-enhanced")===' + json.dumps(enabled)):
                                break
                            time.sleep(.02)
                        else:
                            self.fail('Homepage did not load in the selected script mode.')
                        for width in (1200, 320, 1200):
                            with self.subTest(title=title, scripts=enabled, width=width):
                                connection.call('Emulation.setDeviceMetricsOverride', width=width,
                                                height=1000, deviceScaleFactor=1, mobile=False)
                                frames(enabled)
                                geometry = js('''(()=>{
                                    const rect=s=>document.querySelector(s).getBoundingClientRect();
                                    const box=rect('.home-content'),lead=rect('.lead'),input=rect('textarea');
                                    return {center:(box.left+box.right)/2,edge:input.right-lead.right,
                                            overflow:document.documentElement.scrollWidth>innerWidth,
                                            top:input.top};})()''')
                                self.assertAlmostEqual(geometry['center'], width / 2, delta=1)
                                self.assertAlmostEqual(geometry['edge'], 0, delta=1)
                                self.assertFalse(geometry['overflow'])
                                js('document.querySelector("textarea").value="Keep this draft";'
                                   'document.querySelector(".yapic-explanation summary").focus()')
                                connection.call('Input.dispatchKeyEvent', type='keyDown', key='Enter',
                                                code='Enter', windowsVirtualKeyCode=13, text='\r')
                                connection.call('Input.dispatchKeyEvent', type='keyUp', key='Enter',
                                                code='Enter', windowsVirtualKeyCode=13)
                                frames(enabled)
                                self.assertTrue(js('document.querySelector(".yapic-explanation").open'))
                                if enabled:
                                    self.assertAlmostEqual(js('document.querySelector("textarea")'
                                        '.getBoundingClientRect().top'), geometry['top'], delta=1)
                                    js('document.querySelector("textarea").focus()')
                                    self.assertFalse(js('document.querySelector(".yapic-explanation").open'))
                                else:
                                    self.assertTrue(js('document.querySelector("textarea").getBoundingClientRect().top'
                                        '>=document.querySelector(".definition-bubble").getBoundingClientRect().bottom'))
                                    js('document.querySelector(".yapic-explanation summary").click()')
                                self.assertEqual(js('document.querySelector("textarea").value'), 'Keep this draft')
                                self.assertTrue(js('document.querySelector(".request-box button").disabled'))
                                self.assertEqual(js('document.querySelector("textarea").labels.length'), 1)
