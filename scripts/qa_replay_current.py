"""Replay regression for marker-only UI; no writes to real annotation files."""
import hashlib
import json
import re
import tempfile
import threading
from pathlib import Path
from run_presslens import ROOT, make_server


def main():
    from playwright.sync_api import sync_playwright, expect
    output = ROOT / '.presslens/qa'
    output.mkdir(parents=True, exist_ok=True)
    original = ROOT / '.presslens/annotations.jsonl'
    before = original.read_bytes()
    with tempfile.TemporaryDirectory(prefix='replay-qa-', dir=output) as temporary:
        log = Path(temporary) / 'annotations.jsonl'
        log.write_bytes(before)
        server = make_server(port=0, log_path=log)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        errors = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
                page = browser.new_page(viewport={'width': 1550, 'height': 1000})
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
                page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
                page.goto(base)
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                assert page.locator('#match option').count() == 20
                assert page.locator('#detailed-mode').count() == page.locator('#annotation-form').count() == 0
                page.locator('#jump').fill('8958')
                page.locator('#jump-form button').click()
                expect(page.locator('#frame-label')).to_contain_text('8,958')
                page.locator('#provider').check()
                expect(page.locator('#provider-context')).to_contain_text('Tracking/event carrier disagreement')
                page.locator('#jump').fill('6732')
                page.locator('#jump-form button').click()
                expect(page.locator('#context-frame')).to_contain_text('6732')
                expect(page.locator('#provider-context')).to_contain_text('Event/phase team disagreement')
                page.locator('#provider').uncheck()
                page.locator('#next').click()
                expect(page.locator('#frame-label')).to_contain_text('6,733')
                page.locator('#pitch').focus()
                page.keyboard.press('ArrowLeft')
                expect(page.locator('#frame-label')).to_contain_text('6,732')
                page.locator('#speed').select_option('2')
                page.locator('#play').click()
                page.wait_for_timeout(300)
                page.locator('#play').click()
                assert int(page.locator('#jump').input_value()) > 6732
                page.locator('#period2').click()
                expect(page.locator('#period2')).to_have_class(re.compile(r'.*active.*'))
                page.locator('#extrapolated').uncheck()
                page.locator('#extrapolated').check()
                with page.expect_download() as download:
                    page.locator('#export').click()
                exported = json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
                assert exported['revisions'] == [json.loads(line) for line in before.decode('utf-8').splitlines() if line.strip()]
                assert exported['press_event_revisions'] == []
                page.screenshot(path=str(output / 'review-desktop.png'), full_page=True)
                assert not errors, errors
                browser.close()
            assert original.read_bytes() == before
            result = {'status': 'passed', 'software': server.replay_store.software,
                      'checks': ['20 match catalogue', 'carrier and phase conflicts', 'native frame and keyboard steps',
                                 'full-half playback and speed', 'half selection', 'extrapolation display toggle',
                                 'detailed tab/form removed', 'legacy history preserved in download', 'no browser errors'],
                      'human_annotation_sha256': hashlib.sha256(before).hexdigest(), 'browser_errors': errors}
            (output / 'browser-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            (ROOT / 'reports/replay_current_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result, indent=2))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    main()
