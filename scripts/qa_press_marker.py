"""Test one-button pressure marking with temporary records and real canvas clicks."""
import hashlib
import json
import math
import tempfile
import threading
import urllib.request
from pathlib import Path
from run_presslens import ROOT, make_server


def main():
    from playwright.sync_api import sync_playwright, expect
    original = ROOT / '.presslens/annotations.jsonl'
    original_bytes = original.read_bytes()
    output = ROOT / '.presslens/qa'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='press-marker-', dir=output) as temporary:
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
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                expect(page.locator('#press-marker')).to_be_visible()
                assert page.locator('#annotation-form').count() == 0
                assert page.locator('#detailed-mode').count() == 0
                expect(page.locator('#marker-scope')).to_contain_text('counter-attacks, fast breaks and represses')
                page.locator('#marker-reviewer').fill('AUTOMATED MARKER CHECK — NOT A HUMAN LABEL')
                page.locator('#jump').fill('32')
                page.locator('#jump-form button').click()
                expect(page.locator('#frame-label')).to_contain_text('FRAME 32')
                page.locator('#marker-toggle').click()
                expect(page.locator('#marker-interval')).to_contain_text('Recording from frame 32')

                def click_player(pid):
                    frame = int(page.locator('#jump').input_value())
                    row = json.load(urllib.request.urlopen(base + f'/api/matches/1874553/frames?start={frame}&count=1'))['frames'][0]
                    target = next(v for v in row['players'] if v[0] == pid)
                    pitch_length, pitch_width = server.replay_store.load('1874553').info()['pitch']
                    scale = min(1080 / pitch_length, 700 / pitch_width)
                    left, top = (1200 - pitch_length * scale) / 2, (800 - pitch_width * scale) / 2
                    px = left + (target[1] + pitch_length / 2) * scale
                    py = top + (pitch_width / 2 - target[2]) * scale
                    box = page.locator('#pitch').bounding_box()
                    page.mouse.click(box['x'] + px / 1200 * box['width'], box['y'] + py / 800 * box['height'])

                click_player(50959)
                expect(page.locator('#marker-primary')).to_contain_text('S. Mauk')
                click_player(42513)
                click_player(797295)
                expect(page.locator('#marker-support')).to_contain_text('Z. Clough')
                expect(page.locator('#marker-support')).to_contain_text('L. Jovanovic')
                click_player(42513)
                expect(page.locator('#marker-support')).not_to_contain_text('Z. Clough')
                click_player(42513)
                click_player(51050)
                expect(page.locator('#marker-status')).to_contain_text('primary presser’s team')
                page.screenshot(path=str(output / 'press-marker-desktop.png'), full_page=True)
                page.locator('#play').click()
                page.wait_for_timeout(500)
                page.locator('#marker-toggle').click()
                expect(page.locator('#marker-count')).to_contain_text('1 saved press events')
                expect(page.locator('#play')).to_have_attribute('aria-label', 'Pause replay')
                record = server.focused_log.records()[0]
                event = record['press_event']
                assert event['start_frame'] == 32 and event['end_frame'] > 32
                assert event['primary_presser_id'] == 50959
                assert set(event['supporting_defender_ids']) == {42513, 797295}
                assert int(page.locator('#jump').input_value()) >= event['end_frame']
                assert record['question_key'] == 'press' and record['answer'] == 'yes'
                assert record['review_scope']['excluded_situations'] == ['counter_attack', 'fast_break', 'repress']
                assert record['review_scope']['excluded_handling'] == 'deferred_unreviewed'
                assert record['review_scope']['automatic_phase_filter'] is False
                assert 'funnel' not in server.focused_log.combined('1874553')['sequences'][0]['questions']
                page.locator('#play').click()
                page.reload()
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                expect(page.locator('#marker-count')).to_contain_text('1 saved press events')
                # Natural edit flow: cursor is beyond the saved end, without a seek
                # caused by Edit. Remove and re-add support using real pitch clicks.
                page.locator('#jump').fill('120')
                page.locator('#jump-form button').click()
                expect(page.locator('#frame-label')).to_contain_text('FRAME 120')
                page.get_by_role('button', name='Edit', exact=True).click()
                expect(page.locator('#marker-toggle')).to_have_text('Save changes')
                expect(page.locator('#frame-label')).to_contain_text('FRAME 120')
                click_player(797295)
                expect(page.locator('#marker-support')).not_to_contain_text('L. Jovanovic')
                click_player(797295)
                expect(page.locator('#marker-support')).to_contain_text('L. Jovanovic')
                expect(page.locator('#marker-status')).to_contain_text('outside the event interval')
                page.locator('#marker-toggle').click()
                expect(page.locator('#marker-status')).to_contain_text('Saved frames 32')
                expect(page.locator('#frame-label')).to_contain_text('FRAME 120')
                outside_edit = server.focused_log.latest()[0]
                assert outside_edit['press_event']['selection_frames_outside_revised_interval'] == {'797295': 120}
                assert outside_edit['sequence_id'] == record['sequence_id']
                assert outside_edit['event_id'] == record['event_id']
                assert outside_edit['press_event']['end_frame'] == event['end_frame']
                page.get_by_role('button', name='Edit', exact=True).click()
                page.locator('#marker-edit-start').fill('33')
                page.locator('#marker-edit-end').fill(str(event['end_frame'] + 2))
                page.locator('#jump').fill('33')
                page.locator('#jump-form button').click()
                expect(page.locator('#frame-label')).to_contain_text('FRAME 33')
                page.locator('#marker-replace-primary').click()
                click_player(42513)
                click_player(50959)
                page.locator('#play').click()
                page.locator('#marker-toggle').click()
                expect(page.locator('#marker-status')).to_contain_text('Saved frames 33–')
                expect(page.locator('#play')).to_have_attribute('aria-label', 'Pause replay')
                revised = server.focused_log.latest()[0]
                assert revised['event_id'] == record['event_id'] and revised['revision'] == 3
                assert revised['sequence_id'] != record['sequence_id']
                assert revised['press_event']['primary_presser_id'] == 42513
                assert set(revised['press_event']['supporting_defender_ids']) == {50959, 797295}
                assert len(server.focused_log.latest()) == 1
                page.get_by_role('button', name='Delete', exact=True).click()
                expect(page.locator('#marker-count')).to_contain_text('0 saved press events')
                expect(page.locator('#play')).to_have_attribute('aria-label', 'Pause replay')
                assert server.focused_log.latest() == []
                page.locator('#marker-undo-delete').click()
                expect(page.locator('#marker-count')).to_contain_text('1 saved press events')
                assert server.focused_log.latest()[0]['revision'] == 5
                page.reload()
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                expect(page.locator('#marker-count')).to_contain_text('1 saved press events')
                page.locator('#jump').fill('120')
                page.locator('#jump-form button').click()
                expect(page.locator('#frame-label')).to_contain_text('FRAME 120')
                page.locator('#marker-toggle').click()
                page.reload()
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                expect(page.locator('#marker-interval')).to_contain_text('Recording from frame 120')
                page.locator('#period2').click()
                expect(page.locator('#period2')).to_have_class('chip active')
                page.locator('#marker-toggle').click()
                expect(page.locator('#marker-status')).to_contain_text('starting half')
                page.locator('#marker-cancel').click()
                assert len(server.focused_log.records()) == 5
                expect(page.locator('#press-marker')).to_be_visible()
                page.set_viewport_size({'width': 390, 'height': 844})
                page.screenshot(path=str(output / 'press-marker-mobile.png'), full_page=True)
                assert page.locator('main').bounding_box()['width'] <= 390
                assert not errors, errors
                browser_version = browser.version
                browser.close()
            assert original.read_bytes() == original_bytes
            result = {'status': 'passed', 'software': server.replay_store.software, 'browser': browser_version,
                      'checks': ['same button captures start and end', 'real canvas click assigns primary',
                                 'other defenders toggle support', 'opponent rejected without stopping replay',
                                 'end autosaves with native bounds and clicked players', 'saving leaves full-half playback running',
                                 'record survives reload', 'edit bounds and clicked roles with stable event identity',
                                 'edit adds support from outside event with actual click frame and unchanged bounds/cursor',
                                 'delete hides event without labelling it negative', 'undo restore survives reload',
                                 'edit save and delete preserve playback', 'draft restored without moving replay cursor',
                                 'cross-half end rejected and cancel works', 'half selection retained', 'detailed tab and form removed',
                                 'scope exclusions recorded as deferred and not automatically filtered',
                                 'desktop/mobile without browser errors'],
                      'temporary_test_events': 1, 'human_annotation_file_unchanged': True,
                      'human_annotation_sha256': hashlib.sha256(original_bytes).hexdigest(), 'browser_errors': errors}
            (output / 'press-marker-browser-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            (ROOT / 'reports/press_marker_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result, indent=2))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    main()
