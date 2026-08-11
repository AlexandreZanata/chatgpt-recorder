// ChatGPT Audio Capture — Background Service (Strategy A)

const TTS_URL_PATTERNS = [
  '*://chatgpt.com/backend-api/synthesize*',
  '*://chatgpt.com/backend-api/voice/*',
  '*://chatgpt.com/backend-api/speech*',
  '*://*.oaiusercontent.com/*'
];

const ICONS = {
  idle: 'icons/icon-idle.svg',
  recording: 'icons/icon-recording.svg',
  saved: 'icons/icon-saved.svg'
};

function updateIcon(state) {
  const iconPath = ICONS[state] || ICONS.idle;
  if (typeof browser !== 'undefined' && browser.action) {
    browser.action.setIcon({ path: iconPath });
  }
}

function generateFilename(title) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const safeTitle = title || 'audio';
  return `chatgpt-tts_${timestamp}_${safeTitle}.mp3`;
}

function triggerDownload(blob, title) {
  if (typeof browser === 'undefined' || !browser.downloads) return;
  updateIcon('saved');
  const filename = generateFilename(title);
  const blobUrl = URL.createObjectURL(blob);
  browser.downloads.download({
    url: blobUrl,
    filename: filename,
    saveAs: false
  });
  setTimeout(() => updateIcon('idle'), 3000);
}

function processCapturedAudio(blob, tabId) {
  if (typeof browser === 'undefined' || !browser.tabs || !tabId) {
    triggerDownload(blob, 'chatgpt-session');
    return;
  }
  browser.tabs.sendMessage(tabId, { type: 'EXTRACT_TITLE' })
    .then((response) => {
      const title = response && response.title ? response.title : 'chatgpt-session';
      triggerDownload(blob, title);
    })
    .catch(() => {
      triggerDownload(blob, 'chatgpt-session');
    });
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
    updateIcon('idle');
  };
}

if (typeof browser !== 'undefined' && browser.webRequest) {
  browser.webRequest.onBeforeRequest.addListener(
    setupStreamFilter,
    { urls: TTS_URL_PATTERNS },
    ['blocking']
  );
}
