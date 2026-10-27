"""Browser regression of protocol 2 against a temporary copy of annotation 1.

Never writes to the human annotation log. New temporary revisions are labelled
AUTOMATED UI CHECK and establish software behaviour only.
"""
import hashlib
import json
import tempfile
import threading
from pathlib import Path

from run_presslens import ROOT, make_server


def main():
    from playwright.sync_api import sync_playwright, expect
    original = ROOT / '.presslens/annotations.jsonl'
    original_bytes = original.read_bytes()
    rows = [json.loads(line) for line in original_bytes.decode('utf-8').splitlines() if line.strip()]
    legacy = next(r for r in rows if r['annotation_id'] == '8f5f12b0-1075-4f96-96b9-74ac608538a5' and r['revision'] == 1)
    output = ROOT / '.presslens/qa'
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with tempfile.TemporaryDirectory(prefix='protocol2-', dir=output) as temporary:
        log = Path(temporary) / 'annotations.jsonl'
        log.write_text(json.dumps(legacy) + '\n', encoding='utf-8')
        server = make_server(port=0, log_path=log)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
                page = browser.new_page(viewport={'width': 1550, 'height': 1000})
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
                page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
                page.goto(base)
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                page.locator('#history').click()
                expect(page.locator('#saved-list')).to_contain_text('legacy: non funnel pressure')
                page.locator('#saved-list button').click()
                expect(page.locator('#frame-label')).to_contain_text('FRAME 32')
                expect(page.locator('#legacy-panel')).to_be_visible()
                expect(page.locator('#legacy-summary')).to_contain_text('non funnel pressure')
                expect(page.locator('#press-assessment')).to_have_value('not_assessed')
                expect(page.locator('#funnel-assessment')).to_have_value('not_assessed')
                expect(page.locator('#press-uncertainty')).to_have_value('not_assessed')
                expect(page.locator('#blocked')).to_have_value('unknown')
                page.locator('#legacy-panel summary').click()
                page.locator('#copy-legacy-notes').click()
                expect(page.locator('#quality-notes')).to_have_value(legacy['observation']['notes'])
                page.locator('#observation-tab').click()
                page.locator('#reviewer').fill('AUTOMATED UI CHECK — NOT A HUMAN TACTICAL LABEL')
                page.locator('#rationale').fill('Software verification of independent judgements and source visibility; no tactical claim.')
                page.locator('#context-start').fill('29')
                page.locator('#press-assessment').select_option('present')
                page.locator('#press-uncertainty').select_option('low')
                page.locator('#funnel-assessment').select_option('no_funnel')
                page.locator('#funnel-observability').select_option('limited')
                page.locator('#funnel-rationale').fill('Automated validation probe; not a football conclusion.')
                page.locator('#funnel-uncertainty').select_option('high')
                page.locator('#save').click()
                expect(page.locator('#save-status')).to_contain_text('adequate route visibility')
                assert len(server.review_log.records()) == 1
                expected_error = [e for e in errors if 'server responded with a status of 400' in e]
                assert len(expected_error) == 1, errors
                errors.remove(expected_error[0])  # Deliberate rejected no-funnel/limited-visibility probe.
                page.locator('#funnel-assessment').select_option('unassessable')
                page.locator('#nominated-carrier').select_option('51050')
                page.locator('#primary-uncertainty').select_option('low')
                page.locator('#role-42513-function').select_option('cover_receiver')
                page.locator('#role-42513-target').select_option('50994')
                page.locator('#role-42513-uncertainty').select_option('high')
                page.locator('#role-797295-function').select_option('cover_route')
                page.locator('#role-797295-description').fill('Automated role-entry test only; route not established.')
                page.locator('#role-797295-uncertainty').select_option('high')
                expect(page.locator('#actor-quality')).to_contain_text('C. Brown')
                expect(page.locator('#actor-quality')).to_contain_text('extrapolated')
                page.get_by_text('Stage bookmarks', exact=True).click()
                for field, value in [('cue-frame', 29), ('onset-frame', 32), ('reception-frame', 42), ('action-frame', 60)]:
                    page.locator('#' + field).fill(str(value))
                page.locator('#cue').select_option('backward_pass')
                page.locator('#cue-uncertainty').select_option('medium')
                page.locator('#blocked').select_option('forward')
                expect(page.locator('#direction-guide')).to_contain_text('attacking-left = upper pitch (+y)')
                page.get_by_text('Replay exposure disclosure', exact=True).click()
                page.locator('#future-viewed').select_option('yes')
                page.locator('#reviewed-through').fill('102')
                page.locator('#save').click()
                expect(page.locator('#save-status')).to_contain_text('Observation saved locally. Revision 2')
                second = server.review_log.latest()[0]
                assert second['schema_version'] == '2.0'
                assert second['observation']['press_uncertainty'] == 'low'
                assert second['observation']['funnel_uncertainty'] == 'high'
                assert second['observation']['stages']['cue_frame'] == 29
                assert second['actor_visibility']['actors']['50994']['extrapolated'] == 30
                assert second['replay_review']['future_replay_exposed']
                assert not second['provenance']['outcomes_revealed_in_session']
                page.locator('#outcome-tab').click()
                page.locator('#followup-through').fill('102')
                page.locator('#followup-future').select_option('yes')
                page.locator('#save-quality').click()
                expect(page.locator('#save-status')).to_contain_text('Data-quality review saved locally. Revision 3')
                third = server.review_log.latest()[0]
                assert third['observation'] == second['observation']
                assert third['quality_review']['notes'] == legacy['observation']['notes']
                assert third['outcome'] is None
                page.reload()
                expect(page.locator('#frame-label')).to_contain_text('FRAME 10')
                page.locator('#history').click()
                expect(page.locator('#saved-list')).to_contain_text('quality reviewed')
                page.locator('#saved-list button').click()
                expect(page.locator('#annotation-state')).to_contain_text('revision 3')
                expect(page.locator('#press-assessment')).to_have_value('present')
                expect(page.locator('#funnel-assessment')).to_have_value('unassessable')
                expect(page.locator('#role-42513-target')).to_have_value('50994')
                page.get_by_text('Replay exposure disclosure', exact=True).click()
                page.locator('#future-viewed').select_option('no')
                page.locator('#reviewed-through').fill('')
                page.locator('#save').click()
                expect(page.locator('#save-status')).to_contain_text('Revision 4')
                assert server.review_log.latest()[0]['replay_review']['future_replay_exposed']
                assert server.review_log.records()[0] == legacy
                page.locator('.annotation').screenshot(path=str(output / 'protocol2-annotation-desktop.png'))
                page.set_viewport_size({'width': 390, 'height': 844})
                page.screenshot(path=str(output / 'protocol2-mobile.png'), full_page=True)
                assert page.locator('main').bounding_box()['width'] <= 390
                assert not errors, errors
                browser_version = browser.version
                browser.close()
            assert original.read_bytes() == original_bytes, 'The human annotation log changed during QA; investigate concurrent writes.'
            result = {'status': 'passed', 'software': server.replay_store.software, 'browser': browser_version,
                      'checks': ['legacy label visible without automatic conversion', 'no-funnel/limited-visibility rejection',
                                 'independent press/funnel uncertainty', 'pre-interval cue stage', 'named receiver/support function',
                                 'actor-specific extrapolation visibility', 'attacking-relative direction guide',
                                 'raw-replay exposure despite unopened provider-outcome panel', 'separate quality revision',
                                 'reload of schema 2 roles and judgements', 'sticky future exposure across revision',
                                 'desktop/mobile rendering without browser errors'],
                      'human_annotation_file_unchanged': True,
                      'human_annotation_sha256': hashlib.sha256(original_bytes).hexdigest(),
                      'temporary_revisions_only': True, 'browser_errors': errors}
            (output / 'refinements-browser-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            (ROOT / 'reports/annotation_refinements_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result, indent=2))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    main()
