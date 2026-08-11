// ChatGPT Audio Capture — Background Service

// Wide net: all chatgpt.com traffic; audio confirmed by Content-Type in response headers
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

// requestId → mime type, set by onHeadersReceived before filter.onstop fires
const pendingAudio = new Map();

function isAudioMime(value) {
  if (!value) return false;
  const base = value.split(';')[0].trim().toLowerCase();
  return base in MIME_MAP;
}

function getMimeBase(value) {
  return value.split(';')[0].trim().toLowerCase();
}

function updateBadge() {
  if (typeof browser !== 'undefined' && browser.action) {
    browser.action.setBadgeText({
      text: sessionCaptureCount > 0 ? String(sessionCaptureCount) : ''
    });
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
  const ext = MIME_MAP[mimeType] || '.mp3';
  const pattern = tmpl || '{prefix}_{date}_{title}';
  return pattern
    .replace(/\{prefix\}/g, prefix || 'chatgpt-tts')
    .replace(/\{date\}/g, d)
    .replace(/\{time\}/g, t)
    .replace(/\{title\}/g, title || 'audio') + ext;
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
    browser.downloads.download({
      url: URL.createObjectURL(blob),
      filename: path,
      saveAs: false
    });
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

// ── Strategy A: filterResponseData (stream copy) ─────────────────────────────
// onBeforeRequest attaches a filter to EVERY request.
// onHeadersReceived marks requests whose Content-Type is audio.
// filter.onstop only saves blobs for marked requests.
// Order guaranteed by Firefox: onBeforeRequest → onHeadersReceived → body data → onstop

function attachFilter(details) {
  if (typeof browser === 'undefined' || !browser.webRequest.filterResponseData) return;

  const filter = browser.webRequest.filterResponseData(details.requestId);
  const chunks = [];

  filter.ondata = (e) => {
    chunks.push(e.data);
    filter.write(e.data);
  };

  filter.onstop = () => {
    filter.disconnect();
    const entry = pendingAudio.get(details.requestId);
    pendingAudio.delete(details.requestId);

    if (!entry) return; // not audio — discard silently
    if (chunks.length === 0) return;

    const blob = new Blob(chunks, { type: entry.mime });
    if (blob.size < 512) {
      console.log('[AudioCapture] blob too small, skipping:', blob.size);
      return;
    }

    console.log('[AudioCapture] saving', blob.size, 'bytes mime:', entry.mime, 'url:', details.url);
    updateIcon('recording');
    processCapturedAudio(blob, details.tabId, entry.mime);
  };

  filter.onerror = () => {
    pendingAudio.delete(details.requestId);
    updateIcon('error');
    setTimeout(() => updateIcon('idle'), 3000);
  };
}

function markAudioHeaders(details) {
  const ct = (details.responseHeaders || []).find(
    (h) => h.name.toLowerCase() === 'content-type'
  );
  const mime = ct ? ct.value : '(none)';

  // Log every response so we can spot the audio one
  console.log('[AudioCapture] response:', details.type, mime, details.url.slice(0, 120));

  if (!ct || !isAudioMime(ct.value)) return;
  const mimeBase = getMimeBase(ct.value);
  console.log('[AudioCapture] ✓ AUDIO FOUND:', details.url, mimeBase);
  pendingAudio.set(details.requestId, { mime: mimeBase });
}

if (typeof browser !== 'undefined' && browser.webRequest) {
  browser.webRequest.onBeforeRequest.addListener(
    attachFilter,
    { urls: LISTEN_URLS },
    ['blocking']
  );

  browser.webRequest.onHeadersReceived.addListener(
    markAudioHeaders,
    { urls: LISTEN_URLS },
    ['responseHeaders']
  );
}

// ── Strategy B: page-injector fallback (WebAudio / HTMLAudioElement) ─────────
if (typeof browser !== 'undefined' && browser.runtime) {
  browser.runtime.onMessage.addListener((message) => {
    if (message && message.type === 'FALLBACK_AUDIO_DATA' && message.dataUrl) {
      console.log('[AudioCapture] fallback audio received from page-injector');
      fetch(message.dataUrl)
        .then((res) => res.blob())
        .then((blob) => {
          triggerDownload(
            blob,
            message.title || 'chatgpt-session',
            blob.type || 'audio/webm'
          );
        });
    }
  });
}
