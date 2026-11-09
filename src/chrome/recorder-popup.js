const section = document.createElement('section');
section.className = 'card';
section.innerHTML = `
  <strong>Complete audio recording</strong>
  <p>Start here before Read aloud. Wait until the voice finishes, then stop and save.
  Records this tab's sound only. No microphone. Pauses remain in the file.</p>
  <button class="action-btn" id="recordComplete">Record complete tab audio</button>
  <button class="action-btn" id="saveComplete" disabled>Stop and save recording</button>
  <button class="action-btn" id="retryComplete" hidden>Retry saving recording</button>
  <p id="recordState" role="status" aria-live="polite">Ready.</p>`;
document.querySelector('.header').after(section);
const start = section.querySelector('#recordComplete');
const stop = section.querySelector('#saveComplete');
const retry = section.querySelector('#retryComplete');
const status = section.querySelector('#recordState');
const active = new Set(['starting', 'recording', 'saving']);

function render(result) {
  const state = result.state || 'idle';
  start.disabled = active.has(state) || Boolean(result.url);
  stop.disabled = state !== 'recording';
  retry.hidden = state !== 'error' || !result.url;
  const labels = {
    idle: 'Ready.', starting: 'Starting recording…',
    recording: 'Recording — play Read aloud, then stop and save.',
    saving: 'Saving complete recording…', saved: 'Saved complete recording.',
    error: result.error || 'Recording failed. Please try again.'
  };
  status.textContent = labels[state];
}

async function command(type) {
  start.disabled = true;
  stop.disabled = true;
  retry.disabled = true;
  try {
    const result = await chrome.runtime.sendMessage({ type, target: 'worker' });
    render(result || {});
  } catch (error) {
    render({ state: 'error', error: error.message });
  } finally {
    retry.disabled = false;
  }
}

start.onclick = () => command('RECORDER_START');
stop.onclick = () => command('RECORDER_STOP');
retry.onclick = () => command('RECORDER_RETRY');
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'session' && changes.completeRecording) render(changes.completeRecording.newValue || {});
});
command('RECORDER_STATUS');
