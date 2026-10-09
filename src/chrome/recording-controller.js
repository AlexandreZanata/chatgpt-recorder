import { downloadRecording, updateAction } from './downloads.js';

const busy = new Set(['starting', 'recording', 'saving']);
const recorderPath = 'src/chrome/recorder.html';

export async function recordingState(api) {
  return (await api.storage.session.get({ completeRecording: {} })).completeRecording;
}

async function update(api, state) {
  await api.storage.session.set({ completeRecording: state });
  return state;
}

function senderIs(sender, path, api) {
  return sender.id === api.runtime.id && sender.url === api.runtime.getURL(path);
}

async function recorderCommand(api, message) {
  const result = await api.runtime.sendMessage({ ...message, target: 'recorder' });
  if (!result || result.error) throw new Error(result?.error || 'Recorder did not respond.');
  return result;
}

async function start(api) {
  const previous = await recordingState(api);
  if (busy.has(previous.state) || previous.url) throw new Error('Save the current recording first.');
  const [tab] = await api.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url || new URL(tab.url).origin !== 'https://chatgpt.com') {
    throw new Error('Open this popup on the ChatGPT tab you want to record.');
  }
  const entry = { state: 'starting', tabId: tab.id, sessionId: crypto.randomUUID(), title: tab.title };
  await update(api, entry);
  try {
    if (!await api.offscreen.hasDocument()) {
      await api.offscreen.createDocument({ url: recorderPath, reasons: ['USER_MEDIA', 'BLOBS'],
        justification: 'Record complete ChatGPT tab audio and retain it until it is saved.' });
    }
    const streamId = await api.tabCapture.getMediaStreamId({ targetTabId: tab.id });
    await recorderCommand(api, { type: 'RECORDER_STREAM', streamId, sessionId: entry.sessionId });
    updateAction(api, 'setBadgeText', { text: 'REC' });
    updateAction(api, 'setIcon', { path: 'icons/icon-recording.png' });
    return update(api, { ...entry, state: 'recording' });
  } catch (error) {
    await api.offscreen.closeDocument().catch(() => {});
    return update(api, { state: 'error', error: error.message });
  }
}

async function save(api, entry) {
  try {
    const result = await downloadRecording(entry, api);
    return update(api, { ...entry, ...result, state: 'saving', error: '' });
  } catch (error) {
    return update(api, { ...entry, state: 'error', error: error.message });
  }
}

async function finish(api, message) {
  const entry = await recordingState(api);
  if (entry.sessionId !== message.sessionId || !busy.has(entry.state)) return {};
  if (!Number.isFinite(message.size) || message.size < 512) {
    await recorderCommand(api, { type: 'RECORDER_RELEASE', url: message.url });
    await api.offscreen.closeDocument();
    return update(api, { state: 'error', error: 'No audio was recorded. Start before Read aloud.' });
  }
  return save(api, { ...entry, url: message.url, mime: message.mime, size: message.size });
}

export async function recordingCommand(message, sender, api) {
  if (message.type === 'RECORDER_FINISHED') {
    if (!senderIs(sender, recorderPath, api)) return {};
    return finish(api, message);
  }
  if (!senderIs(sender, 'popup.html', api)) return {};
  if (message.type === 'RECORDER_START') return start(api);
  const entry = await recordingState(api);
  if (message.type === 'RECORDER_STOP' && entry.state === 'recording') {
    const result = await update(api, { ...entry, state: 'saving' });
    await recorderCommand(api, { type: 'RECORDER_STOP_STREAM' });
    return result;
  }
  if (message.type === 'RECORDER_RETRY' && entry.state === 'error' && entry.url) return save(api, entry);
  return entry;
}

export async function downloadChanged(delta, api) {
  if (!delta.state) return;
  const status = delta.state.current;
  const { captureHistory = [] } = await api.storage.local.get('captureHistory');
  await api.storage.local.set({ captureHistory: captureHistory.map((item) =>
    item.downloadId === delta.id ? { ...item, status, error: delta.error?.current } : item) });
  const entry = await recordingState(api);
  if (entry.downloadId !== delta.id) return;
  if (status === 'interrupted') {
    await update(api, { ...entry, state: 'error', error: delta.error?.current || 'Download interrupted.' });
  }
  if (status === 'complete') {
    await recorderCommand(api, { type: 'RECORDER_RELEASE', url: entry.url });
    await api.offscreen.closeDocument();
    await update(api, { state: 'saved', filename: entry.filename, downloadId: entry.downloadId });
    updateAction(api, 'setIcon', { path: 'icons/icon-saved.png' });
    const session = await api.storage.session.get({ sessionCaptureCount: 0 });
    updateAction(api, 'setBadgeText', { text: String(session.sessionCaptureCount) });
  }
}

export async function suppressAutomatic(sender, api) {
  const entry = await recordingState(api);
  if (!entry || sender?.tab?.id !== entry.tabId) return false;
  return busy.has(entry.state) || Boolean(entry.url);
}
