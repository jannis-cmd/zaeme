"""Main private preview: ElevenLabs Agents, with the classic gateway as fallback."""
import argparse
import json
import sys
from io import BytesIO
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gateway import Gateway, MAX_BODY_BYTES
from agents_service import session, settle


class AgentsGateway(Gateway):
    bundle = None

    def send_head(self):
        path = urlsplit(self.path).path
        if path in ('/', '/index.html', '/voice-agent.js'):
            if path == '/voice-agent.js':
                body = self.bundle.read_bytes()
                content_type = 'text/javascript; charset=utf-8'
            else:
                html = (Path(self.directory) / 'index.html').read_text()
                html = html.replace('</body>', '<script defer src="voice-agent.js?v=1"></script></body>')
                body = html.encode()
                content_type = 'text/html; charset=utf-8'
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            return BytesIO(body)
        return super().send_head()

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ('/api/agents/session', '/api/agents/settle'):
            return super().do_POST()
        # Private preview only: this is not an authenticated public token broker.
        # Reject cross-site browser requests as well.
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            return self.send_json(403, {'error': 'Nicht erlaubt.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY_BYTES:
                raise ValueError('Ungültige Anfrage.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Ungültige Anfrage.')
            result = session(data, transport=self.headers.get('X-Zaeme-Voice-Transport', 'webrtc')) if path.endswith('/session') else settle(data)
            self.send_json(200, result)
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {'error': 'Ungültige Anfrage.'})
        except (RuntimeError, OSError, KeyError):
            self.send_json(503, {'error': 'Der Gesprächsdienst ist gerade nicht verfügbar.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', default=str(ROOT))
    parser.add_argument('--bundle', default=str(ROOT / 'dist' / 'voice-agent.js'))
    parser.add_argument('--port', type=int, default=4185)
    parser.add_argument('--backend', choices=('agents', 'classic'), default='agents')
    args = parser.parse_args()
    AgentsGateway.bundle = Path(args.bundle)
    if args.backend == 'agents' and not AgentsGateway.bundle.is_file():
        parser.error('Build the browser SDK first: npm ci && npm run build')
    gateway = AgentsGateway if args.backend == 'agents' else Gateway
    def handler(*a, **kw):
        return gateway(*a, directory=args.directory, **kw)
    print('Zäme ' + args.backend + ' preview on 127.0.0.1:' + str(args.port), flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), handler).serve_forever()
