// ChatGPT Audio Capture — Background Service Script (With History)

const TTS_PATTERNS = [
  '*://chatgpt.com/backend-api/synthesize*',
  '*://chatgpt.com/backend-api/voice/*',
  '*://chatgpt.com/backend-api/speech*',
  '*://*.oaiusercontent.com/*'
];

const ICONS = {
  idle: 'icons/icon-idle.svg',
  recording: 'icons/icon-recording.svg',
  saved: 'icons/icon-saved.svg',
  error: 'icons/icon-error.svg'
};

function updateIcon(state) {
  const iconPath = ICONS[state] || ICONS.idle;
  if (typeof browser !== 'undefined' && browser.action) {
    browser.action.setIcon({ path: iconPath });
  }
}

function buildPath(subfolder, prefix, title) {
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const safePrefix = prefix || 'chatgpt-tts';
  const safeTitle = title || 'audio';
  const name = `${safePrefix}_${ts}_${safeTitle}.mp3`;
  return subfolder ? `${subfolder.replace(/\/$/, '')}/${name}` : name;
}

function saveHistory(item) {
  if (typeof browser === 'undefined' || !browser.storage) return;
  browser.storage.local.get({ captureHistory: [] }).then((res) => {
    const list = [item, ...res.captureHistory].slice(0, 20);
    browser.storage.local.set({ captureHistory: list });
  });
}

function triggerDownload(blob, title) {
  if (typeof browser === 'undefined' || !browser.downloads) return;
  browser.storage.local.get({
    autoDownload: true,
    filenamePrefix: 'chatgpt-tts',
    subfolder: ''
  }).then((s) => {
    if (!s.autoDownload) return;
    updateIcon('saved');
    const path = buildPath(s.subfolder, s.filenamePrefix, title);
    const url = URL.createObjectURL(blob);
    browser.downloads.download({ url, filename: path, saveAs: false });
    saveHistory({ id: Date.now(), filename: path, title, timestamp: new Date().toISOString() });
    setTimeout(() => updateIcon('idle'), 3000);
  });
}

function processCapturedAudio(blob, tabId) {
  if (typeof browser === 'undefined' || !browser.tabs || !tabId) {
    triggerDownload(blob, 'chatgpt-session');
    return;
  }
  browser.tabs.sendMessage(tabId, { type: 'EXTRACT_TITLE' })
    .then((r) => triggerDownload(blob, r && r.title ? r.title : 'chatgpt-session'))
    .catch(() => triggerDownload(blob, 'chatgpt-session'));
}

function setupStreamFilter(details) {
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
    const blob = new Blob(chunks, { type: 'audio/mpeg' });
    processCapturedAudio(blob, details.tabId);
  };

  filter.onerror = () => {
    updateIcon('error');
    setTimeout(() => updateIcon('idle'), 3000);
  };
}

if (typeof browser !== 'undefined' && browser.webRequest) {
  browser.webRequest.onBeforeRequest.addListener(
    setupStreamFilter,
    { urls: TTS_PATTERNS },
    ['blocking']
  );
}
