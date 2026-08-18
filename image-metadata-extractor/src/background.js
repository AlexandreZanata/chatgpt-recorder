// ChatGPT Image & Metadata Extractor — Background Service

const LISTEN_URLS = [
  '*://chatgpt.com/*',
  '*://*.oaiusercontent.com/*',
  '*://*.openai.com/*'
];

const IMAGE_MIME_MAP = {
  'image/png': '.png',
  'image/webp': '.webp',
  'image/jpeg': '.jpg',
  'image/jpg': '.jpg'
};

const ICONS = {
  idle: 'icons/icon-idle.svg',
  recording: 'icons/icon-recording.svg',
  saved: 'icons/icon-saved.svg',
  error: 'icons/icon-error.svg'
};

let sessionImageCount = 0;
const pendingImages = new Map();
let currentContext = {};

function sanitize(str) {
  return (str || 'image').toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/-+/g, '-').slice(0, 50);
}

function updateBadge() {
  if (typeof browser !== 'undefined' && browser.action) {
    browser.action.setBadgeText({ text: sessionImageCount > 0 ? String(sessionImageCount) : '' });
    browser.action.setBadgeBackgroundColor({ color: '#10b981' });
  }
}

function updateIcon(state) {
  if (typeof browser !== 'undefined' && browser.action) {
    browser.action.setIcon({ path: ICONS[state] || ICONS.idle });
  }
}

function formatBaseName(tmpl, prefix, title) {
  const now = new Date();
  const d = now.toISOString().split('T')[0];
  const t = now.toTimeString().split(' ')[0].replace(/:/g, '-');
  const cleanTitle = sanitize(title);
  const pattern = tmpl || '{prefix}_{date}_{time}_{title}';
  return pattern
    .replace(/\{prefix\}/g, prefix || 'chatgpt-img')
    .replace(/\{date\}/g, d)
    .replace(/\{time\}/g, t)
    .replace(/\{title\}/g, cleanTitle);
}

function downloadFile(url, filename) {
  if (typeof browser === 'undefined' || !browser.downloads) return;
  browser.downloads.download({ url, filename, saveAs: false }).catch((err) => {
    console.warn('[ImageExtractor] downloadFile error:', err);
  });
}

function triggerDownloads(imageBlob, metadataObj, title, mimeType) {
  if (typeof browser === 'undefined' || !browser.downloads) return;
  browser.storage.local.get({
    autoDownloadImage: true,
    autoDownloadMetadata: true,
    filenamePrefix: 'chatgpt-img',
    filenameTemplate: '{prefix}_{date}_{time}_{title}',
    subfolder: 'chatgpt-images'
  }).then((s) => {
    sessionImageCount += 1;
    updateBadge();
    updateIcon('saved');
    const base = formatBaseName(s.filenameTemplate, s.filenamePrefix, title);
    const ext = IMAGE_MIME_MAP[mimeType] || '.png';
    const folder = s.subfolder ? `${s.subfolder.replace(/\/$/, '')}/` : '';

    if (s.autoDownloadImage && imageBlob) {
      downloadFile(URL.createObjectURL(imageBlob), `${folder}${base}${ext}`);
    }

    if (s.autoDownloadMetadata && metadataObj) {
      const fullMeta = Object.assign({}, currentContext, metadataObj, {
        savedAt: new Date().toISOString(),
        finalImageFilename: `${base}${ext}`
      });
      const metaBlob = new Blob([JSON.stringify(fullMeta, null, 2)], { type: 'application/json' });
      downloadFile(URL.createObjectURL(metaBlob), `${folder}${base}_metadata.json`);
    }
    setTimeout(() => updateIcon('idle'), 3000);
  });
}

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
    const entry = pendingImages.get(details.requestId);
    pendingImages.delete(details.requestId);
    if (!entry || chunks.length === 0) return;

    const blob = new Blob(chunks, { type: entry.mime });
    if (blob.size < 1024) return;

    updateIcon('recording');
    const meta = {
      extractedUrl: details.url,
      timestamp: new Date().toISOString(),
      mimeType: entry.mime,
      sizeBytes: blob.size,
      userPrompt: currentContext.userPrompt || '',
      pageTitle: currentContext.pageTitle || 'chatgpt-image'
    };
    triggerDownloads(blob, meta, meta.pageTitle, entry.mime);
  };

  filter.onerror = () => {
    pendingImages.delete(details.requestId);
    updateIcon('error');
    setTimeout(() => updateIcon('idle'), 3000);
  };
}

function markHeaders(details) {
  const ct = (details.responseHeaders || []).find((h) => h.name.toLowerCase() === 'content-type');
  if (!ct) return;
  const mime = ct.value.split(';')[0].trim().toLowerCase();
  if (mime in IMAGE_MIME_MAP) {
    pendingImages.set(details.requestId, { mime });
  }
}

if (typeof browser !== 'undefined' && browser.webRequest) {
  browser.webRequest.onBeforeRequest.addListener(attachFilter, { urls: LISTEN_URLS }, ['blocking']);
  browser.webRequest.onHeadersReceived.addListener(markHeaders, { urls: LISTEN_URLS }, ['responseHeaders']);
}

if (typeof browser !== 'undefined' && browser.runtime) {
  browser.runtime.onMessage.addListener((msg) => {
    if (!msg) return;
    if (msg.type === 'STREAM_METADATA_CHUNK' || msg.type === 'IMAGE_DOM_DISCOVERED') {
      currentContext = Object.assign({}, currentContext, msg.data, {
        updatedAt: new Date().toISOString()
      });
    }
  });
}
