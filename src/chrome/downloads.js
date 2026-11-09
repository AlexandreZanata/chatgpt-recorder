import { MIME_EXTENSION_MAP, DEFAULTS, interpolateTemplate } from '../shared/constants.js';

export function updateAction(api, method, value) {
  Promise.resolve().then(() => api.action[method](value)).catch(() => {});
}

export function captureError(error) {
  const reason = String(error?.message || 'Unknown error.')
    .replace(/data:[^\s]+/g, '[audio data]').slice(0, 240);
  return `Audio capture failed: ${reason}`;
}

export function audioMime(dataUrl) {
  if (typeof dataUrl !== 'string') return null;
  const match = /^data:(audio\/[a-z0-9.+-]+)(?:;codecs=[a-z0-9-]+)?;base64,([A-Za-z0-9+/]+={0,2})$/.exec(dataUrl);
  if (!match || !MIME_EXTENSION_MAP[match[1]] || match[2].length < 684) return null;
  return match[1];
}

export function trustedSender(sender, extensionId) {
  if (!sender || sender.id !== extensionId || !sender.tab || sender.frameId !== 0) return false;
  try {
    return new URL(sender.url).origin === 'https://chatgpt.com';
  } catch {
    return false;
  }
}

function safePart(value) {
  return String(value).replace(/[\\/:*?"<>|\x00-\x1f]/g, '-').replace(/^\.+/, '').slice(0, 120);
}

export function captureFilename(settings, title, mime) {
  const name = safePart(interpolateTemplate(settings.filenameTemplate, {
    prefix: settings.filenamePrefix, title
  })) || 'chatgpt-session';
  const folder = String(settings.subfolder || '').split(/[\\/]/)
    .map(safePart).filter(Boolean).join('/');
  return `${folder ? folder + '/' : ''}${name}${MIME_EXTENSION_MAP[mime]}`;
}

export async function downloadCapture(message, api) {
  const mime = audioMime(message.dataUrl);
  if (!mime) throw new Error('Invalid audio payload.');
  return downloadSource({ ...message, url: message.dataUrl }, mime, api);
}

export async function downloadRecording(recording, api) {
  const prefix = `blob:${api.runtime.getURL('')}`;
  if (!recording.url.startsWith(prefix) || recording.mime !== 'audio/webm') {
    throw new Error('Invalid recording source.');
  }
  return downloadSource(recording, recording.mime, api, true);
}

async function downloadSource(message, mime, api, manual = false) {
  const settings = await api.storage.local.get({
    autoDownload: true, filenamePrefix: DEFAULTS.FILENAME_PREFIX,
    filenameTemplate: DEFAULTS.FILENAME_TEMPLATE, subfolder: '', captureHistory: []
  });
  if (!manual && !settings.autoDownload) return { skipped: true };
  const title = safePart(message.title || 'chatgpt-session');
  const filename = captureFilename(settings, title, mime);
  updateAction(api, 'setIcon', { path: 'icons/icon-recording.png' });
  // The offscreen document owns recording Blob URLs until download completion.
  const downloadId = await api.downloads.download({ url: message.url, filename, saveAs: false });
  const session = await api.storage.session.get({ sessionCaptureCount: 0 });
  const count = session.sessionCaptureCount + 1;
  await api.storage.session.set({ sessionCaptureCount: count });
  const history = Array.isArray(settings.captureHistory) ? settings.captureHistory : [];
  await api.storage.local.set({ captureHistory: [
    { title, filename, downloadId, status: 'pending', capturedAt: new Date().toISOString() }, ...history
  ].slice(0, DEFAULTS.MAX_HISTORY) });
  updateAction(api, 'setBadgeText', { text: String(count) });
  updateAction(api, 'setBadgeBackgroundColor', { color: '#6366f1' });
  return { downloadId, filename };
}
