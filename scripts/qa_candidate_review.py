"""Browser/API regression for pressure proposals; all writes use temporary logs."""
import hashlib
import json
import tempfile
import threading
from pathlib import Path
from run_presslens import ROOT, make_server


def main():
    from playwright.sync_api import sync_playwright, expect
    output = ROOT / '.presslens/qa'
    output.mkdir(parents=True, exist_ok=True)
    paths = [ROOT / '.presslens' / name for name in ('annotations.jsonl', 'pass_reviews.jsonl', 'review_sequences.jsonl', 'candidate_reviews.jsonl')]
    original = {p: p.read_bytes() if p.exists() else None for p in paths}
    with tempfile.TemporaryDirectory(prefix='candidate-qa-', dir=output) as temporary:
        server = make_server(port=0, log_path=Path(temporary) / 'annotations.jsonl')
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
                expect(page.locator('#candidate-status')).to_contain_text('Queue ready')
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                page.locator('#marker-reviewer').fill('AUTOMATED CANDIDATE QA - NOT A HUMAN LABEL')
                page.locator('#marker-reviewer').press('Tab')
                expect(page.locator('#candidate-status')).to_contain_text('Queue ready')
                assert page.locator('#candidate-select option').count() > 1
                first_id = page.locator('#candidate-select').input_value()
                start = int(page.locator('#candidate-start').input_value())
                end = int(page.locator('#candidate-end').input_value())
                page.locator('#candidate-go').click()
                expect(page.locator('#jump')).to_have_value(str(max(10, start-30)))
                page.locator('#play').click()
                page.locator('input[name="candidate-decision"][value="yes"]').check()
                page.locator('#candidate-save').click()
                expect(page.locator('#candidate-status')).to_contain_text('Saved yes')
                expect(page.locator('#play')).to_have_attribute('aria-label', 'Pause replay')
                row = server.candidate_reviews.latest()[0]
                assert row['funnel'] == 'yes' and row['case']['start_frame'] == start
                assert row['provenance']['outcome_filtered'] is False
                assert server.focused_log.records() == []
                page.locator('#play').click()
                page.reload()
                expect(page.locator('#candidate-status')).to_contain_text('Queue ready')
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                assert page.locator('#candidate-select').input_value() == first_id
                expect(page.locator('input[name="candidate-decision"][value="yes"]')).to_be_checked()
                # Bound edits append a review revision without moving the replay.
                page.locator('#candidate-end').fill(str(end+1))
                page.locator('input[name="candidate-decision"][value="uncertain"]').check()
                page.locator('#candidate-save').click()
                expect(page.locator('#candidate-status')).to_contain_text('revision 2')
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                revised = server.candidate_reviews.latest()[0]
                assert revised['original_case']['end_frame'] == end
                assert revised['case']['end_frame'] == end+1
                assert revised['case']['sequence_id'] != row['case']['sequence_id']
                # A stale write through the real API must leave both revisions intact.
                payload = {'match_id': '1874553', 'reviewer': row['reviewer'], 'candidate_id': first_id,
                           'pool': 'pressure', 'start_frame': start, 'end_frame': end, 'decision': 'no', 'base_revision': 1}
                stale = page.evaluate('''async payload => {const r=await fetch('/api/candidate-reviews', {method:'POST',headers:{'Content-Type':'application/json','X-Review-Session':state.session},body:JSON.stringify(payload)});return {status:r.status,body:await r.json()};}''', payload)
                assert stale['status'] == 400 and 'another tab' in stale['body']['error']
                # Expected HTTP 400 is checked above; only unexpected console errors matter.
                errors = [e for e in errors if '400 (Bad Request)' not in e]
                page.locator('input[name="candidate-decision"][value="out_of_scope"]').check()
                expect(page.locator('#candidate-scope-field')).to_be_visible()
                page.locator('#candidate-scope').select_option('repress')
                page.locator('#candidate-save').click()
                expect(page.locator('#candidate-status')).to_contain_text('Saved out of scope')
                assert server.candidate_reviews.latest()[0]['funnel'] == 'not_assessed'
                assert server.candidate_reviews.latest()[0]['scope_reason'] == 'repress'
                page.locator('#candidate-filter').select_option('deferred')
                assert page.locator('#candidate-select option').count() == 1
                page.locator('#candidate-filter').select_option('unreviewed')
                assert first_id not in page.locator('#candidate-select option').evaluate_all('(els)=>els.map(e=>e.value)')
                current = page.locator('#candidate-select').input_value()
                page.locator('input[name="candidate-decision"][value="no"]').check()
                page.locator('#candidate-save-next').click()
                expect(page.locator('#candidate-status')).to_contain_text('Showing build-up')
                assert page.locator('#candidate-select').input_value() != current
                assert any(r['funnel'] == 'no' for r in server.candidate_reviews.latest())
                # A normal save under Unreviewed must not silently switch the
                # selected episode while replay still shows the previous one.
                pinned = page.locator('#candidate-select').input_value()
                cursor = page.locator('#jump').input_value()
                page.locator('input[name="candidate-decision"][value="uncertain"]').check()
                page.locator('#candidate-save').click()
                expect(page.locator('#candidate-status')).to_contain_text('Saved uncertain')
                assert page.locator('#candidate-select').input_value() == pinned
                expect(page.locator('#jump')).to_have_value(cursor)
                expect(page.locator('#candidate-count')).to_contain_text('kept selected')
                # Expanded and outside-candidate pools are available without auto seeking.
                cursor = page.locator('#jump').input_value()
                page.locator('#candidate-filter').select_option('all')
                for pool in ('expanded', 'audit', 'manual'):
                    page.locator('#candidate-pool').select_option(pool)
                    expect(page.locator('#candidate-status')).to_contain_text('Queue ready')
                    expect(page.locator('#jump')).to_have_value(cursor)
                    if pool != 'manual':
                        assert page.locator('#candidate-select option').count() > 0
                # Export includes review history with all decisions and original bounds.
                exported = page.evaluate('async()=>await api("/api/export")')
                assert len(exported['candidate_review_revisions']) == 5
                assert exported['press_event_revisions'] == []
                page.locator('#candidate-pool').select_option('pressure')
                expect(page.locator('#candidate-status')).to_contain_text('Queue ready')
                page.locator('#candidate-next').click()
                expect(page.locator('#candidate-status')).to_contain_text('Showing build-up')
                page.screenshot(path=str(output / 'candidate-review-desktop.png'), full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.locator('main').bounding_box()['width'] <= 390
                page.screenshot(path=str(output / 'candidate-review-mobile.png'), full_page=True)
                assert not errors, errors
                browser.close()
            assert all((p.read_bytes() if p.exists() else None) == before for p, before in original.items())
            result = {'status': 'passed', 'software': server.replay_store.software,
                      'checks': ['provider queue loaded without moving replay', 'explicit context navigation',
                                 'yes review saves while full-half playback continues', 'review survives reload',
                                 'bounds edits retain source bounds and change sequence identity', 'stale API revision rejected',
                                 'repress deferred without funnel negative', 'review filters and save-next navigation',
                                 'ordinary save keeps the episode selected when its decision leaves the current filter',
                                 'expanded/manual/noncandidate pools', 'complete review history export',
                                 'desktop/mobile without browser errors'],
                      'human_files_unchanged': True, 'browser_errors': errors,
                      'original_human_file_sha256': {p.name: hashlib.sha256(b).hexdigest() if b else None for p, b in original.items()}}
            (output / 'candidate-browser-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            (ROOT / 'reports/candidate_review_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result, indent=2))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    main()
