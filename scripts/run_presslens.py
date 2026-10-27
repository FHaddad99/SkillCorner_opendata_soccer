"""Launch the local PressLens review workspace: python scripts/run_presslens.py."""
import argparse
import json
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from presslens.replay import ReplayStore, clean_json
from presslens.review import ReviewLog
from presslens.focused import FocusedLog, SequenceBank, build_queue, question_key
from presslens.candidates import CandidateReviews, candidates, source_diagnostics


def make_server(root=ROOT, port=8765, log_path=None):
    store = ReplayStore(root)
    reviews = ReviewLog(log_path or Path(root) / '.presslens/annotations.jsonl')
    focused = FocusedLog(reviews.path.parent / 'pass_reviews.jsonl')
    bank = SequenceBank(reviews.path.parent / 'review_sequences.jsonl')
    candidate_reviews = CandidateReviews(reviews.path.parent / 'candidate_reviews.jsonl')
    sessions, session_lock = {}, threading.RLock()
    assets = ROOT / 'viewer'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def safe_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def send(self, status, value, content_type='application/json; charset=utf-8'):
            raw = json.dumps(clean_json(value), ensure_ascii=False, allow_nan=False).encode() if content_type.startswith('application/json') else value
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(raw)

        def session(self):
            token = self.headers.get('X-Review-Session')
            with session_lock:
                if token not in sessions:
                    raise ValueError('Review session expired. Reload the page.')
                return sessions[token]

        def do_GET(self):
            try:
                if not self.safe_host():
                    return self.send(403, {'error': 'Localhost access only'})
                url = urlparse(self.path)
                parts = url.path.strip('/').split('/')
                query = parse_qs(url.query)
                if url.path in ('/', '/app.js', '/press_marker.js', '/candidates.js', '/style.css'):
                    name = {'/': 'index.html', '/app.js': 'app.js', '/press_marker.js': 'press_marker.js', '/candidates.js': 'candidates.js', '/style.css': 'style.css'}[url.path]
                    mime = 'text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
                    return self.send(200, (assets / name).read_bytes(), mime + '; charset=utf-8')
                if url.path == '/api/session':
                    token = secrets.token_urlsafe(32)
                    with session_lock:
                        sessions[token] = {'outcomes_revealed': set(), 'provider_revealed': set(), 'history_revealed': set()}
                    return self.send(200, {'session': token})
                if url.path == '/api/matches':
                    return self.send(200, store.catalogue())
                if url.path == '/api/candidates':
                    session = self.session()
                    match = store.load(query.get('match', [''])[0])
                    session['provider_revealed'].add(match.mid)
                    pool = query.get('pool', ['pressure'])[0]
                    cases = candidates(match, pool, focused)
                    manual = candidates(match, 'manual', focused)
                    base = cases if pool == 'pressure' else candidates(match, 'pressure', focused)
                    comparison = [{'candidate_id': m['candidate_id'], 'start_frame': m['start_frame'], 'end_frame': m['end_frame'],
                                   'overlapping_candidates': [c['candidate_id'] for c in base if c['period'] == m['period'] and c['start_frame'] <= m['end_frame'] and c['end_frame'] >= m['start_frame']]}
                                  for m in manual]
                    diagnostics = source_diagnostics(match, pool == 'expanded', cases if pool == 'expanded' else base)
                    return self.send(200, {'cases': cases, 'reviews': candidate_reviews.latest(match.mid, query.get('reviewer', [''])[0]),
                                          'manual_comparison': comparison, 'policy': match.candidate_policy,
                                          'source_diagnostics': diagnostics,
                                          'scope': match.review_scope,
                                          'note': 'Provider proposals, not confirmed pressure. Overlap with saved examples is not a recall estimate.'})
                if url.path == '/api/pass-queue':
                    self.session()
                    match = store.load(query.get('match', [''])[0])
                    return self.send(200, {'cases': build_queue(match, reviews, query.get('pool', ['marked_intervals'])[0], bank),
                                          'note': 'Review windows, not detected positives. All provider possession starts are eligible; no later outcomes used.'})
                if url.path == '/api/pass-reviews':
                    self.session()
                    mid = query.get('match', [''])[0]
                    if mid not in store.ids:
                        raise ValueError('Choose a known match')
                    q = question_key(query.get('pass', ['press'])[0], query.get('cue_type', [None])[0])
                    reviewer = query.get('reviewer', [''])[0].strip()
                    if not reviewer:
                        raise ValueError('Enter your reviewer name')
                    rows = focused.latest(mid, q, reviewer)
                    return self.send(200, {'reviews': [{**r, 'event_id': focused.event_id(r)} if r.get('press_event') else r for r in rows]})
                if url.path == '/api/pass-combined':
                    session = self.session()
                    mid = query.get('match', [''])[0]
                    if mid not in store.ids:
                        raise ValueError('Choose a known match')
                    session.setdefault('pass_results_revealed', set()).add(mid)
                    return self.send(200, focused.combined(mid))
                if len(parts) >= 3 and parts[:2] == ['api', 'matches']:
                    match = store.load(parts[2])
                    if len(parts) == 3:
                        return self.send(200, match.info())
                    if len(parts) == 4 and parts[3] == 'frames':
                        return self.send(200, match.window(int(query.get('start', ['0'])[0]), int(query.get('count', ['100'])[0])))
                    if len(parts) == 4 and parts[3] == 'context':
                        self.session()['provider_revealed'].add(match.mid)
                        return self.send(200, match.context(match.raw(int(query.get('frame', ['0'])[0]))))
                if url.path == '/api/annotations':
                    session = self.session()
                    mid = query.get('match', [None])[0]
                    if mid not in store.ids:
                        raise ValueError('Choose a known match')
                    session['history_revealed'].add(mid)
                    return self.send(200, {'annotations': reviews.latest(mid)})
                if url.path == '/api/export':
                    self.session()['history_revealed'].update(store.ids)
                    return self.send(200, {'schema_version': '3.0', 'scope': 'local human annotations; records retain original schema and review scope',
                                           'revisions': reviews.records(), 'press_event_revisions': focused.records(),
                                           'candidate_review_revisions': candidate_reviews.records(),
                                           'review_intervals': bank.records()})
                self.send(404, {'error': 'Route not found'})
            except (ValueError, TypeError, KeyError) as exc:
                self.send(400, {'error': str(exc)})
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass  # The user navigated away before the local response completed.
            except OSError:
                self.send(500, {'error': 'Local file could not be read. Check the data and annotation directories.'})

        def do_POST(self):
            try:
                if not self.safe_host() or self.headers.get('Origin') != f'http://{self.headers.get("Host")}':
                    return self.send(403, {'error': 'Same-origin local review requests only'})
                session = self.session()
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 65536:
                    raise ValueError('Request size must be between 1 and 65,536 bytes')
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError('Request body must be an object')
                match = store.load(str(payload.get('match_id')))
                if self.path == '/api/annotations':
                    return self.send(200, reviews.save(payload, match, session))
                if self.path == '/api/pass-reviews':
                    return self.send(200, focused.save(payload, match, reviews, session, bank))
                if self.path == '/api/pass-intervals':
                    return self.send(200, bank.add(match, payload.get('start_frame'), payload.get('end_frame')))
                if self.path == '/api/press-events':
                    return self.send(200, focused.save_press_event(payload, match, bank, session))
                if self.path == '/api/press-event-state':
                    return self.send(200, focused.set_deleted(payload, match))
                if self.path == '/api/candidate-reviews':
                    session['provider_revealed'].add(match.mid)
                    return self.send(200, candidate_reviews.save(payload, match, focused, session))
                if self.path == '/api/reveal-outcomes':
                    start, end = int(payload['start_frame']), int(payload['end_frame'])
                    if start > end or end - start > 3000:
                        raise ValueError('Outcome window must be ordered and at most 300 seconds')
                    first, last = match.raw(start), match.raw(end)
                    if first['period'] not in (1, 2) or first['period'] != last['period']:
                        raise ValueError('Outcome review must stay within a single period')
                    session['outcomes_revealed'].add(match.mid)
                    keys = ('event_id', 'frame_start', 'frame_end', 'player_id', 'end_type', 'pass_outcome', 'game_interruption_after')
                    rows = [{k: e.get(k) for k in keys} for e in match.possessions if int(e['period']) == first['period'] and start <= int(e['frame_end']) <= end]
                    return self.send(200, {'outcomes': rows, 'evidence_type': 'provider retrospective labels', 'exposure_recorded': True})
                self.send(404, {'error': 'Route not found'})
            except (ValueError, TypeError, KeyError) as exc:
                self.send(400, {'error': str(exc)})
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass
            except OSError:
                self.send(500, {'error': 'Local review could not be saved. Check filesystem access.'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.replay_store, server.review_log, server.focused_log = store, reviews, focused
    server.candidate_reviews = candidate_reviews
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    try:
        server = make_server(port=args.port)
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc))
    print(f'PressLens local review: http://127.0.0.1:{server.server_port}', flush=True)
    print('Raw files stay local. Press Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
