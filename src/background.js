// ChatGPT Audio Capture — Background Service (Strategy A & Pipeline)

const TTS_URL_PATTERNS = [
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

function buildFilename(prefix, title) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const safePrefix = prefix || 'chatgpt-tts';
  const safeTitle = title || 'audio';
  return `${safePrefix}_${timestamp}_${safeTitle}.mp3`;
}

function triggerDownload(blob, title) {
  if (typeof browser === 'undefined' || !browser.downloads) return;
  browser.storage.local.get({ autoDownload: true, filenamePrefix: 'chatgpt-tts' })
    .then((settings) => {
      if (!settings.autoDownload) return;
      updateIcon('saved');
      const filename = buildFilename(settings.filenamePrefix, title);
      const blobUrl = URL.createObjectURL(blob);
      browser.downloads.download({ url: blobUrl, filename: filename, saveAs: false });
      setTimeout(() => updateIcon('idle'), 3000);
    });
}

function processCapturedAudio(blob, tabId) {
  if (typeof browser === 'undefined' || !browser.tabs || !tabId) {
    triggerDownload(blob, 'chatgpt-session');
    return;
  }
  browser.tabs.sendMessage(tabId, { type: 'EXTRACT_TITLE' })
    .then((res) => triggerDownload(blob, res && res.title ? res.title : 'chatgpt-session'))
    .catch(() => triggerDownload(blob, 'chatgpt-session'));
}

function setupStreamFilter(details) {
  if (typeof browser === 'undefined' || !browser.webRequest.filterResponseData) return;
  updateIcon('recording');
  const filter = browser.webRequest.filterResponseData(details.requestId);
  const chunks = [];

  filter.ondata = (event) => {
    chunks.push(event.data);
    filter.write(event.data);
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
    { urls: TTS_URL_PATTERNS },
    ['blocking']
  );
}
