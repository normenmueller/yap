"""The explorer preserves authored many-to-many relationships and safe content."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from yap import browser, goaltree


class GoalTreeTests(unittest.TestCase):
    def model(self):
        return dict(
            goals=[dict(key=key, id='goal-' + key, title=key, status='active',
                        activities=[dict(key='unassigned', anchor='')]) for key in ('one', 'two')],
            nodes=[dict(key='shared', id='act-shared', acronym='S', title='Shared',
                        versions=[dict(anchor='v1'), dict(anchor='v2')]),
                   dict(key='unassigned', id='act-unassigned', title='Not assigned')],
            key_results={key: [dict(key='result', title='Result', measure='Evidence',
                                    activities=['shared'])] for key in ('one', 'two')})

    def test_shared_activity_is_one_node_across_objectives_and_versions(self):
        model = self.model()
        original = deepcopy(model)
        data = goaltree.graph_data(model)
        self.assertEqual(model, original)
        self.assertEqual([node['id'] for node in data['nodes'] if node['kind'] == 'activity'], ['a:shared'])
        self.assertIn(['kr:one/result', 'a:shared'], data['edges'])
        self.assertIn(['kr:two/result', 'a:shared'], data['edges'])
        self.assertEqual(len(data['edges']), 4)
        self.assertNotIn('unassigned', json.dumps(data))
        self.assertEqual(next(node['title'] for node in data['nodes'] if node['kind'] == 'activity'), 'S – Shared')

    def test_empty_objectives_remain_visible_without_inferred_children(self):
        model = self.model()
        model['key_results'] = {}
        data = goaltree.graph_data(model)
        self.assertEqual(len(data['nodes']), 2)
        self.assertEqual(data['edges'], [])
        model['goals'] = []
        self.assertEqual(goaltree.graph_data(model), dict(nodes=[], edges=[]))

    def test_embedded_json_cannot_break_out_of_the_script_element(self):
        model = self.model()
        hostile = '</script><img src=x onerror=alert(1)> & "quoted"'
        model['goals'][0]['title'] = hostile
        html = goaltree.render(model)
        serialized = html.split('id="goal-explorer-data">', 1)[1].split('</script>', 1)[0]
        self.assertNotIn('<', serialized)
        self.assertEqual(json.loads(serialized)['nodes'][0]['title'], hostile)
        self.assertNotIn(hostile, html)

    def test_offline_exploration_keeps_shared_nodes_and_clear_geometry(self):
        model = self.model()
        model['goals'][0]['title'] = 'one: An objective with a longer title than its neighbor'
        model['goals'][1]['status'] = 'on hold'
        model['key_results']['one'][0]['title'] = 'A substantially longer result title ' * 12
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / 'graph.html'
            page.write_text('<!doctype html><html><head><meta charset="utf-8"><style>'
                            '*{box-sizing:border-box}body{margin:0;font:16px system-ui}'
                            '.test-panel{display:none}' + goaltree.STYLE + '</style></head><body>'
                            '<div class="test-panel">' + goaltree.render(model) + '</div></body></html>')
            with browser.page(page, directory) as connection:
                def js(expression):
                    result = connection.call('Runtime.evaluate', expression=expression,
                                             returnByValue=True, awaitPromise=True)
                    self.assertNotIn('exceptionDetails', result)
                    return result['result'].get('value')

                def frames():
                    js('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')

                def click(node):
                    js('document.querySelector(' + json.dumps('[data-node="' + node + '"] button') + ').click()')

                def counts():
                    return js('({nodes:[...document.querySelectorAll(".explorer-node:not([hidden])")].map(n=>n.dataset.node),'
                              'edges:document.querySelectorAll(".explorer-edge").length})')

                # The observer must initialize a component revealed after page load,
                # without knowing anything about its surrounding tab implementation.
                js('document.querySelector(".test-panel").style.display="block"')
                frames()
                self.assertEqual(counts(), dict(nodes=['o:one', 'o:two'], edges=0))
                js('document.querySelector("[data-node=\\"o:one\\"] h3").dispatchEvent(new MouseEvent("dblclick",{bubbles:true}))')
                click('o:two')
                click('kr:one/result')
                self.assertTrue(js('''(()=>{
                    const child=document.querySelector('[data-node="a:shared"]');
                    const parent=document.querySelector('[data-node="kr:one/result"]');
                    return child.offsetLeft === parent.offsetLeft;
                })()'''))
                click('kr:two/result')
                self.assertTrue(js('''(()=>{
                    const child=document.querySelector('[data-node="a:shared"]');
                    const parents=[...document.querySelectorAll('[data-kind=kr]')];
                    return Math.abs(child.offsetLeft - parents.reduce((sum,n)=>sum+n.offsetLeft,0)/parents.length)<1;
                })()'''))
                self.assertEqual(len(counts()['nodes']), 5)
                self.assertEqual(counts()['edges'], 4)
                self.assertEqual(counts()['nodes'].count('a:shared'), 1)
                self.assertTrue(js('document.querySelector("[data-node=\\"kr:one/result\\"] .explorer-description").textContent.includes("Objective: one")'))
                for width in (1200, 430, 320):
                    connection.call('Emulation.setDeviceMetricsOverride', width=width, height=1000,
                                    deviceScaleFactor=1, mobile=False)
                    frames()
                    self.assertTrue(js('document.documentElement.scrollWidth<=innerWidth'))
                    self.assertTrue(js('[...document.querySelectorAll(".explorer-node:not([hidden])")].every(n=>n.scrollHeight<=n.clientHeight && n.scrollWidth<=n.clientWidth)'))
                    self.assertTrue(js('''['objective','kr','activity'].every(kind=>{
                        const footers=[...document.querySelectorAll('.explorer-node:not([hidden])')]
                            .filter(n=>n.dataset.kind===kind)
                            .map(n=>n.querySelector('.explorer-node-footer').getBoundingClientRect().bottom);
                        return footers.length<2 || Math.max(...footers)-Math.min(...footers)<1;
                    })'''))
                    self.assertTrue(js('''(()=>{
                        const nodes=[...document.querySelectorAll('.explorer-node:not([hidden])')];
                        return [...document.querySelectorAll('.explorer-edge')].every(path=>{
                            const length=path.getTotalLength();
                            for(let i=1;i<100;i++){
                                const p=path.getPointAtLength(length*i/100);
                                if(nodes.some(n=>p.x>n.offsetLeft+1 && p.x<n.offsetLeft+n.offsetWidth-1 &&
                                    p.y>n.offsetTop+1 && p.y<n.offsetTop+n.offsetHeight-1)) return false;
                            }
                            return true;
                        });
                    })()'''))
                    before_zoom = counts()
                    js('document.querySelector("[data-action=zoom-fit]").click()')
                    frames()
                    self.assertTrue(js('''(()=>{
                        const v=document.querySelector('.explorer-viewport');
                        return v.scrollWidth<=v.clientWidth+1 && v.scrollHeight<=v.clientHeight+1;
                    })()'''))
                    self.assertEqual(counts(), before_zoom)
                    js('document.querySelector("[data-action=zoom-in]").click()')
                    self.assertEqual(js('document.querySelector("[data-action=zoom-fit]").getAttribute("aria-pressed")'), 'false')
                    js('document.querySelector("[data-action=zoom-reset]").click()')
                    self.assertEqual(js('document.querySelector(".explorer-stage").style.transform'), 'scale(1)')
                    self.assertEqual(counts(), before_zoom)
                # Keyboard zoom is scoped to the focused graph and preserves exploration.
                js('document.querySelector(".explorer-viewport").focus()')
                connection.call('Input.dispatchKeyEvent', type='keyDown', key='-', code='Minus', windowsVirtualKeyCode=189)
                self.assertNotEqual(js('document.querySelector(".explorer-stage").style.transform'), 'scale(1)')
                js('document.querySelector("[data-action=zoom-fit]").click()')
                click('kr:one/result')
                self.assertIn('a:shared', counts()['nodes'])
                self.assertEqual(counts()['edges'], 3)
                self.assertEqual(js('document.querySelector("[data-action=zoom-fit]").getAttribute("aria-pressed")'), 'true')
                click('o:two')
                self.assertNotIn('a:shared', counts()['nodes'])
                click('o:two')
                self.assertIn('a:shared', counts()['nodes'])
                js('document.querySelector("[data-node=\\"kr:two/result\\"] button").focus()')
                connection.call('Input.dispatchKeyEvent', type='keyDown', key='Enter', code='Enter', windowsVirtualKeyCode=13, text='\r')
                connection.call('Input.dispatchKeyEvent', type='keyUp', key='Enter', code='Enter', windowsVirtualKeyCode=13)
                self.assertNotIn('a:shared', counts()['nodes'])
                self.assertTrue(js('document.activeElement.matches(".explorer-toggle")'))
                connection.call('Input.dispatchKeyEvent', type='keyDown', key=' ', code='Space', windowsVirtualKeyCode=32)
                connection.call('Input.dispatchKeyEvent', type='keyUp', key=' ', code='Space', windowsVirtualKeyCode=32)
                self.assertIn('a:shared', counts()['nodes'])
                # A shared contribution remains visible through another selected
                # Objective; filtering preserves expansion for later restoration.
                js('document.querySelector("[data-status-filter][value=active]").click()')
                self.assertNotIn('o:one', counts()['nodes'])
                self.assertIn('a:shared', counts()['nodes'])
                js('document.querySelector("[data-status-filter][value=\\"on hold\\"]").click()')
                self.assertEqual(counts(), dict(nodes=[], edges=0))
                self.assertFalse(js('document.querySelector(".explorer-empty").hidden'))
                js('document.querySelector("[data-action=all-statuses]").click()')
                self.assertIn('o:one', counts()['nodes'])
                self.assertIn('a:shared', counts()['nodes'])
                js('document.querySelector("[data-action=collapse]").click()')
                self.assertEqual(counts(), dict(nodes=['o:one', 'o:two'], edges=0))
                self.assertTrue(js('document.querySelector("[data-action=collapse]").disabled'))
                # Browsers can restore checkbox values without change events.
                # Expanding a KR must use the visible filters, not an old copy.
                js('document.querySelector("[data-status-filter][value=\\"on hold\\"]").checked=false')
                click('o:one')
                self.assertEqual(counts(), dict(nodes=['o:one', 'kr:one/result'], edges=1))
                click('kr:one/result')
                self.assertEqual(counts(), dict(nodes=['o:one', 'kr:one/result', 'a:shared'], edges=2))


if __name__ == '__main__':
    unittest.main()
