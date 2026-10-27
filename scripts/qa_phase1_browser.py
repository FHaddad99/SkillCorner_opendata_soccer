"""Optional browser QA using an installed Playwright and Chrome; no downloads.

All automated annotations go to a temporary log, never the user's review log.
Screenshots/results stay in ignored .presslens/qa. This is UI verification,
not tactical annotation or detector validation.
"""
import json
import re
import sys
import tempfile
import threading
from pathlib import Path

from run_presslens import ROOT, make_server


def main():
    from playwright.sync_api import sync_playwright, expect
    output = ROOT / '.presslens/qa'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='qa-review-', dir=output) as temporary:
        server = make_server(port=0, log_path=Path(temporary) / 'annotations.jsonl')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        errors = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
                page = browser.new_page(viewport={'width': 1600, 'height': 1050}, device_scale_factor=1)
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
                page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
                page.goto(base)
                expect(page.locator('#match-status')).to_contain_text('native 10 Hz')
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                assert page.locator('#match option').count() == 20
                assert not page.locator('#provider').is_checked()
                page.locator('#jump').fill('8958')
                page.locator('#jump-form button').click()
                expect(page.locator('#frame-label')).to_contain_text('8,958')
                page.locator('#provider').check()
                expect(page.locator('#provider-context')).to_contain_text('Tracking/event carrier disagreement')
                assert 'B. Halloran' in page.locator('#provider-context').inner_text()
                assert 'B. Vriends' in page.locator('#carrier').inner_text()
                page.screenshot(path=str(output / 'carrier-conflict-desktop.png'), full_page=True)
                page.locator('#jump').fill('6732')
                page.locator('#jump-form button').click()
                expect(page.locator('#context-frame')).to_contain_text('6732')
                expect(page.locator('#provider-context')).to_contain_text('Event/phase team disagreement')
                page.locator('#provider').uncheck()
                page.locator('#play').click()
                page.wait_for_timeout(650)
                page.locator('#play').click()
                progressed = int(page.locator('#jump').input_value())
                assert progressed > 6732
                page.locator('#jump').fill('6732')
                page.locator('#jump-form button').click()
                expect(page.locator('#frame-label')).to_contain_text('6,732')
                page.locator('#detailed-mode').click()
                page.locator('#new').click()
                page.locator('#reviewer').fill('AUTOMATED UI CHECK — NOT A HUMAN TACTICAL LABEL')
                page.locator('#rationale').fill('Software verification only: save, reload and revision handling. No tactical claim.')
                page.locator('#bookmark').click()
                page.locator('#save').click()
                expect(page.locator('#save-status')).to_contain_text('Observation saved locally')
                page.locator('#outcome-tab').click()
                page.locator('#reveal').click()
                expect(page.locator('#outcome-results')).to_contain_text('exposure recorded')
                page.locator('#save-outcome').click()
                expect(page.locator('#save-status')).to_contain_text('Outcome review saved locally')
                page.reload()
                expect(page.locator('#match-status')).to_contain_text('native 10 Hz')
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                page.locator('#history').click()
                expect(page.locator('#saved-list')).to_contain_text('AUTOMATED UI CHECK')
                page.locator('#saved-list button').click()
                expect(page.locator('#annotation-state')).to_contain_text('revision 2')
                expect(page.locator('#frame-label')).to_contain_text('6,732')
                page.locator('#next').click()
                expect(page.locator('#frame-label')).to_contain_text('6,733')
                page.locator('#period2').click()
                expect(page.locator('#period2')).to_have_class(re.compile(r'.*active.*'))
                page.screenshot(path=str(output / 'review-desktop.png'), full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.screenshot(path=str(output / 'review-mobile.png'), full_page=True)
                assert page.locator('body').bounding_box()['width'] <= 390
                records = server.review_log.records()
                assert len(records) == 2 and records[1]['revision'] == 2
                assert records[1]['provenance']['outcomes_revealed_in_session']
                assert records[0]['start_context']['frame'] == 6732
                assert not errors, errors
                browser.close()
            result = {'status': 'passed', 'fixture': '1874553', 'matches_available': 20,
                      'checks': ['initial observation mode', 'carrier conflict at frame 8958', 'phase conflict at frame 6732',
                                 'native playback', 'frame step', 'period switch', 'observation save', 'separate outcome review',
                                 'revision 2 after reload', 'mobile layout without horizontal overflow', 'no browser errors'],
                      'annotations': 'temporary automated software checks, removed after test; no human labels created',
                      'browser_errors': errors}
            (output / 'browser-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result, indent=2))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    main()
