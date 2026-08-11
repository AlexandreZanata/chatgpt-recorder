// ChatGPT Audio Capture — Background Service (Network & WebAudio Interceptor)

const LISTEN_URLS = [
  '*://chatgpt.com/*',
  '*://*.oaiusercontent.com/*',
  '*://*.openai.com/*'
];

const MIME_MAP = {
  'audio/mpeg': '.mp3',
  'audio/mp3': '.mp3',
  'audio/wav': '.wav',
  'audio/ogg': '.ogg',
  'audio/aac': '.aac',
  'audio/webm': '.webm'
};

const ICONS = {
  idle: 'icons/icon-idle.svg',
  recording: 'icons/icon-recording.svg',
  saved: 'icons/icon-saved.svg',
  error: 'icons/icon-error.svg'
};

let sessionCaptureCount = 0;

function isAudioCandidate(details) {
  const url = (details.url || '').toLowerCase();
  const type = details.type;
  if (type === 'media') return true;
  return url.includes('synthesize') || url.includes('speech') ||
         url.includes('voice') || url.includes('audio') ||
         url.includes('.mp3') || url.includes('.wav') || url.includes('.ogg');
}

function updateBadge() {
  if (typeof browser !== 'undefined' && browser.action) {
    browser.action.setBadgeText({ text: sessionCaptureCount > 0 ? String(sessionCaptureCount) : '' });
    browser.action.setBadgeBackgroundColor({ color: '#6366f1' });
  }
}

function updateIcon(state) {
  const iconPath = ICONS[state] || ICONS.idle;
  if (typeof browser !== 'undefined' && browser.action) {
    browser.action.setIcon({ path: iconPath });
  }
}

function formatFilename(tmpl, prefix, title, mimeType) {
  const now = new Date();
  const d = now.toISOString().split('T')[0];
  const t = now.toTimeString().split(' ')[0].replace(/:/g, '-');
  const ext = MIME_MAP[mimeType] || '.webm';
  const pattern = tmpl || '{prefix}_{date}_{title}';
  const name = pattern
    .replace(/\{prefix\}/g, prefix || 'chatgpt-tts')
    .replace(/\{date\}/g, d)
    .replace(/\{time\}/g, t)
    .replace(/\{title\}/g, title || 'audio');
  return `${name}${ext}`;
}

function triggerDownload(blob, title, mimeType) {
  if (typeof browser === 'undefined' || !browser.downloads) return;
  browser.storage.local.get({
    autoDownload: true,
    filenamePrefix: 'chatgpt-tts',
    filenameTemplate: '{prefix}_{date}_{title}',
    subfolder: ''
  }).then((s) => {
    if (!s.autoDownload) return;
    sessionCaptureCount += 1;
    updateBadge();
    updateIcon('saved');
    const name = formatFilename(s.filenameTemplate, s.filenamePrefix, title, mimeType);
    const path = s.subfolder ? `${s.subfolder.replace(/\/$/, '')}/${name}` : name;
    const url = URL.createObjectURL(blob);
    browser.downloads.download({ url, filename: path, saveAs: false });
    setTimeout(() => updateIcon('idle'), 3000);
  });
}

function processCapturedAudio(blob, tabId, mimeType) {
  if (typeof browser === 'undefined' || !browser.tabs || !tabId) {
    triggerDownload(blob, 'chatgpt-session', mimeType);
    return;
  }
  browser.tabs.sendMessage(tabId, { type: 'EXTRACT_TITLE' })
    .then((r) => triggerDownload(blob, r && r.title ? r.title : 'chatgpt-session', mimeType))
    .catch(() => triggerDownload(blob, 'chatgpt-session', mimeType));
}

function setupStreamFilter(details) {
  if (!isAudioCandidate(details)) return;
  if (typeof browser === 'undefined' || !browser.webRequest.filterResponseData) return;
  updateIcon('recording');
  const filter = browser.webRequest.filterResponseData(details.requestId);
  const chunks = [];

  filter.ondata = (e) => {
    chunks.push(e.data);
    filter.write(e.data);
  };

  filter.onstop = () => {
    filter.disconnect();
    if (chunks.length === 0) return;
    const blob = new Blob(chunks, { type: 'audio/mpeg' });
    processCapturedAudio(blob, details.tabId, 'audio/mpeg');
  };

  filter.onerror = () => {
    updateIcon('error');
    setTimeout(() => updateIcon('idle'), 3000);
  };
}

if (typeof browser !== 'undefined' && browser.webRequest) {
  browser.webRequest.onBeforeRequest.addListener(
    setupStreamFilter,
    { urls: LISTEN_URLS },
    ['blocking']
  );
}

if (typeof browser !== 'undefined' && browser.runtime) {
  browser.runtime.onMessage.addListener((message) => {
    if (message && message.type === 'FALLBACK_AUDIO_DATA' && message.dataUrl) {
      fetch(message.dataUrl)
        .then((res) => res.blob())
        .then((blob) => {
          triggerDownload(blob, message.title || 'chatgpt-session', blob.type || 'audio/webm');
        });
    }
  });
}
