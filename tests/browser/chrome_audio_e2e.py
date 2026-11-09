"""BR-01/02: real Chromium saves both audio passages, including a streaming gap."""

import json
import os
import subprocess
import tempfile
from array import array
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / '.local/tmp/chrome-audio/e2e'
PASSAGE_SECONDS = int(os.environ.get('CHROME_AUDIO_PASSAGE_SECONDS', '2'))


def browser_path():
    configured = os.environ.get('CHROME_AUDIO_BROWSER')
    return configured or '/usr/bin/google-chrome'


def audible_frequency(window):
    if sum(value * value for value in window) / len(window) < 250000:
        return None
    # Normalize crossings to audible samples when a window straddles silence.
    audible = [index for index, value in enumerate(window) if abs(value) > 1000]
    if not audible:
        return None
    window = window[audible[0]:audible[-1] + 1]
    crossings = sum((a < 0) != (b < 0) for a, b in zip(window, window[1:]))
    return crossings * 8000 / (2 * len(window))


def validate_audio(path):
    result = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le',
                             '-ac', '1', '-ar', '8000', 'pipe:1'], check=True, capture_output=True)
    samples = array('h', result.stdout)
    tone_seconds = {440: 0, 880: 0}
    positions = {440: [], 880: []}
    for offset in range(0, len(samples) - 800, 800):
        frequency = audible_frequency(samples[offset:offset + 800])
        if frequency is None:
            continue
        for tone in tone_seconds:
            if abs(frequency - tone) < 25:
                tone_seconds[tone] += 0.1
                positions[tone].append(offset / 8000)
    assert len(samples) / 8000 >= PASSAGE_SECONDS * 2 + 1.8, 'Recording was truncated.'
    assert all(seconds >= PASSAGE_SECONDS - 0.2 for seconds in tone_seconds.values()), 'Both complete passages must be audible.'
    assert min(positions[880]) - max(positions[440]) >= 1.6, 'The streaming gap must remain in one recording.'
    return {'durationSeconds': len(samples) / 8000, 'audibleToneSeconds': tone_seconds}


def run():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright, tempfile.TemporaryDirectory() as profile:
        context = playwright.chromium.launch_persistent_context(
            profile, executable_path=browser_path(), headless=True,
            chromium_sandbox=True, ignore_default_args=['--disable-extensions', '--mute-audio'],
            args=['--enable-unsafe-extension-debugging'], accept_downloads=True)
        page = context.pages[0]
        browser_session = context.browser.new_browser_cdp_session()
        extension_id = browser_session.send('Extensions.loadUnpacked', {
            'path': str(ROOT / 'dist/chrome')})['id']
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('https://chatgpt.com/**', lambda route: route.fulfill(
            content_type='text/html', body=(ROOT / 'tests/browser/audio_fixture.html').read_text()))
        page.goto(f'https://chatgpt.com/c/controlled-audio-test?passage={PASSAGE_SECONDS}')
        worker = context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker')
        context.new_cdp_session(page).send('Browser.setDownloadBehavior', {
            'behavior': 'allow', 'downloadPath': str(OUTPUT), 'eventsEnabled': True})
        targets = browser_session.send('Target.getTargets', {'filter': [{'type': 'tab'}]})['targetInfos']
        target_id = next(item['targetId'] for item in targets if item['url'] == page.url)
        browser_session.send('Extensions.triggerAction', {'id': extension_id, 'targetId': target_id})
        popup = context.new_page()
        popup.goto(f'chrome-extension://{extension_id}/popup.html')
        page.bring_to_front()
        popup.get_by_role('button', name='Record complete tab audio', exact=True).click()
        popup.wait_for_function("document.querySelector('#recordState').textContent !== 'Ready.'")
        popup.get_by_text('Recording — play Read aloud, then stop and save.', exact=True).wait_for()
        popup.close()
        page.get_by_role('button', name='Read aloud', exact=True).click()
        print(f'Recording two {PASSAGE_SECONDS}-second passages with a 1.8-second streaming gap.', flush=True)
        page.wait_for_function("document.querySelector('#state').textContent === 'Finished'",
                               timeout=(PASSAGE_SECONDS * 2 + 15) * 1000)
        popup = context.new_page()
        popup.goto(f'chrome-extension://{extension_id}/popup.html')
        popup.get_by_role('button', name='Stop and save recording', exact=True).click()
        popup.get_by_text('Saved complete recording.', exact=True).wait_for(timeout=15000)
        downloads = worker.evaluate("chrome.downloads.search({})")
        assert len(downloads) == 1, 'One complete recording must be downloaded.'
        assert downloads[0]['state'] == 'complete', 'Download must complete.'
        audio = validate_audio(downloads[0]['filename'])
        report = {'browser': context.browser.version, 'pageErrors': errors,
                  'audio': audio, 'downloads': [{key: item.get(key) for key in
                                 ('id', 'state', 'filename', 'fileSize', 'error')}
                                for item in downloads]}
        (OUTPUT / 'report.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2), flush=True)
        page.screenshot(path=str(OUTPUT / 'fixture.png'))
        worker.evaluate('setTimeout(() => chrome.runtime.reload(), 0)')
        page.wait_for_timeout(500)
        page.evaluate('''window.postMessage({type: 'CHATGPT_AUDIO_CAPTURED_DATA',
            dataUrl: 'data:audio/webm;base64,AAAA'}, location.origin)''')
        page.get_by_role('button', name='Reload ChatGPT', exact=True).wait_for(timeout=5000)
        assert not errors, f'Unexpected page errors: {errors}'
        print('Extension reload recovery: no uncaught page error; reload action displayed.', flush=True)
        context.close()


if __name__ == '__main__':
    run()
