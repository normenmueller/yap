"""Capture the local HTML board using Chromium and standard-library CDP transport."""

import base64
from contextlib import contextmanager
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import signal
import socket
import struct
import subprocess
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import urlopen


class Connection:
    def __init__(self, url):
        address = urlsplit(url)
        self.socket = socket.create_connection((address.hostname, address.port), timeout=30)
        self.stream = self.socket.makefile('rb')
        self.serial = 0
        key = base64.b64encode(os.urandom(16)).decode()
        request = (f'GET {address.path} HTTP/1.1\r\nHost: {address.netloc}\r\n'
                   f'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n'
                   'Sec-WebSocket-Version: 13\r\n\r\n')
        self.socket.sendall(request.encode())
        status = self.stream.readline()
        headers = {}
        while True:
            line = self.stream.readline()
            if line in (b'\r\n', b''):
                break
            name, value = line.decode().split(':', 1)
            headers[name.lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        if b' 101 ' not in status or headers.get('sec-websocket-accept') != expected:
            self.close()
            raise RuntimeError('Could not establish the browser connection.')

    def close(self):
        self.stream.close()
        self.socket.close()

    def send(self, payload, opcode=1):
        mask = os.urandom(4)
        size = len(payload)
        header = bytes([0x80 | opcode])
        header += (bytes([0x80 | size]) if size < 126 else
                   bytes([0xfe])+struct.pack('!H', size) if size < 65536 else
                   bytes([0xff])+struct.pack('!Q', size))
        self.socket.sendall(header+mask+bytes(value ^ mask[index % 4] for index, value in enumerate(payload)))

    def receive(self):
        chunks = []
        while True:
            header = self.stream.read(2)
            if len(header) != 2:
                raise RuntimeError('The browser connection closed unexpectedly.')
            opcode, size = header[0] & 15, header[1] & 127
            if size == 126:
                size = struct.unpack('!H', self.stream.read(2))[0]
            elif size == 127:
                size = struct.unpack('!Q', self.stream.read(8))[0]
            mask = self.stream.read(4) if header[1] & 128 else None
            payload = self.stream.read(size)
            if mask:
                payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            if opcode == 8:
                raise RuntimeError('The browser closed the connection.')
            if opcode == 9:
                self.send(payload, 10)
                continue
            if opcode == 10:
                continue
            chunks.append(payload)
            if header[0] & 128:
                return json.loads(b''.join(chunks))

    def call(self, method, **params):
        self.serial += 1
        identifier = self.serial
        self.send(json.dumps(dict(id=identifier, method=method, params=params)).encode())
        while True:
            response = self.receive()
            if response.get('id') == identifier:
                if 'error' in response:
                    raise RuntimeError(f'Browser: {method}: {response["error"]}')
                return response.get('result', {})


@contextmanager
def page(source, directory):
    candidates = ['/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
                  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                  *(shutil.which(name) for name in ('chromium', 'chromium-browser', 'google-chrome'))]
    executable = next((path for path in candidates if path and Path(path).is_file()), None)
    if not executable:
        raise ValueError('Board layout and the Overview PDF require an installed Edge, Chrome, or Chromium browser.')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='browser-', dir=directory) as profile_directory:
        profile = Path(profile_directory).resolve()
        process = subprocess.Popen([executable, '--headless', '--disable-gpu', '--disable-background-networking',
                                    '--disable-component-update', '--no-first-run', '--no-default-browser-check',
                                    '--remote-debugging-port=0', '--user-data-dir='+str(profile), 'about:blank'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        connection = None
        try:
            port_file = profile / 'DevToolsActivePort'
            deadline = time.monotonic()+15
            while not port_file.exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Could not start the isolated browser for the board overview.')
                time.sleep(.05)
            port = int(port_file.read_text().splitlines()[0])
            with urlopen(f'http://127.0.0.1:{port}/json/list', timeout=10) as response:
                tabs = json.load(response)
            connection = Connection(next(tab['webSocketDebuggerUrl'] for tab in tabs if tab['type'] == 'page'))
            connection.call('Page.enable')
            connection.call('Emulation.setDeviceMetricsOverride', width=1720, height=1100, deviceScaleFactor=2, mobile=False)
            connection.call('Page.navigate', url=Path(source).resolve().as_uri())
            ready = connection.call('Runtime.evaluate', awaitPromise=True, expression='''(async()=>{
                if(document.readyState!=='complete') await new Promise(resolve=>addEventListener('load',resolve,{once:true}));
                await document.fonts.ready;
                await Promise.all([...document.images].map(image=>image.decode()));
                return true;
            })()''')
            if ready.get('exceptionDetails'):
                raise RuntimeError('Could not fully load the board view.')
            yield connection
        finally:
            if connection:
                connection.close()
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except ProcessLookupError:
                pass
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


def equalize_cards(connection, source):
    """Measure the narrowest board layout once; publish only static CSS dimensions."""
    connection.call('Emulation.setDeviceMetricsOverride', width=320, height=1100,
                    deviceScaleFactor=2, mobile=False)
    measured = connection.call('Runtime.evaluate', returnByValue=True, expression='''(()=>{
        const selectedView = document.querySelector('input[name="view"]:checked');
        const trackingView = document.querySelector('#tracking');
        if(trackingView) trackingView.checked=true;
        const disclosures = [...document.querySelectorAll('details')];
        const opened = disclosures.map(d=>d.open);
        disclosures.forEach(d=>d.open=true);
        document.querySelector('#board-card-dimensions')?.remove();
        const dimensions = [];
        for(const [scope, selector] of [['.board-sheet','.card'], ['.kr-board-sheet','.kr-activity']]) {
            const cards = [...document.querySelectorAll(scope+' '+selector)];
            if(!cards.length) continue;
            const sizes = cards.map(c=>getComputedStyle(c).gridTemplateRows.split(' ').map(Number.parseFloat));
            if(sizes.some(s=>s.length!==2 || s.some(n=>!Number.isFinite(n)))) throw Error('Invalid card grid');
            const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
            const names = ['title','caption'];
            const rules = names.map((name,i)=>'--card-'+name+'-height:'+
                (Math.ceil(Math.max(...sizes.map(s=>s[i]))*100/rem)/100)+'rem');
            dimensions.push(scope+'{'+rules.join(';')+'}');
        }
        disclosures.forEach((d,i)=>d.open=opened[i]);
        if(selectedView) selectedView.checked=true;
        const css=dimensions.join('');
        const style=document.createElement('style');
        style.id='board-card-dimensions';style.textContent=css;document.head.append(style);
        return css;
    })()''')
    if measured.get('exceptionDetails'):
        raise RuntimeError('Could not determine shared card dimensions.')
    css = measured['result']['value']
    source = Path(source)
    html = re.sub(r'<style id="board-card-dimensions">.*?</style>', '', source.read_text(), flags=re.S)
    source.write_text(html.replace('</head>', '<style id="board-card-dimensions">'+css+'</style></head>', 1))
    connection.call('Emulation.setDeviceMetricsOverride', width=1720, height=1100,
                    deviceScaleFactor=2, mobile=False)


def fit_cards(source):
    with page(source, Path(source).parent) as connection:
        equalize_cards(connection, source)


def screenshot(source, destination):
    destination = Path(destination)
    with page(source, destination.parent) as connection:
        size = connection.call('Page.getLayoutMetrics')['cssContentSize']
        shot = connection.call('Page.captureScreenshot', format='png', captureBeyondViewport=True,
                               clip=dict(x=0, y=0, width=size['width'], height=size['height'], scale=1))
        destination.write_bytes(base64.b64decode(shot['data']))
