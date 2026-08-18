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
let latestMetadata = null;

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
  browser.downloads.download({ url, filename, saveAs: false });
}

function triggerImageAndMetadataDownload(imageBlob, metadataObj, title, mimeType) {
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
      const metaBlob = new Blob([JSON.stringify(metadataObj, null, 2)], { type: 'application/json' });
      downloadFile(URL.createObjectURL(metaBlob), `${folder}${base}_metadata.json`);
    }
    setTimeout(() => updateIcon('idle'), 3000);
  });
}

function handleFrameDownload(frameData) {
  if (typeof browser === 'undefined' || !browser.downloads) return;
  browser.storage.local.get({
    autoDownloadFrames: true,
    filenamePrefix: 'chatgpt-img',
    subfolder: 'chatgpt-images'
  }).then((s) => {
    if (!s.autoDownloadFrames || !frameData.dataUrl) return;
    const folder = s.subfolder ? `${s.subfolder.replace(/\/$/, '')}/stages/` : 'stages/';
    const base = formatBaseName('{prefix}_{date}_{time}_{title}', s.filenamePrefix, frameData.pageTitle || 'stage');
    downloadFile(frameData.dataUrl, `${folder}${base}_frame_${frameData.frameIndex}.png`);
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
    const meta = latestMetadata || {
      extractedUrl: details.url,
      timestamp: new Date().toISOString(),
      mimeType: entry.mime,
      sizeBytes: blob.size
    };
    triggerImageAndMetadataDownload(blob, meta, meta.pageTitle || 'chatgpt-image', entry.mime);
  };

  filter.onerror = () => {
    pendingImages.delete(details.requestId);
    updateIcon('error');
    setTimeout(() => updateIcon('idle'), 3000);
  };
}

function markImageHeaders(details) {
  const ct = (details.responseHeaders || []).find((h) => h.name.toLowerCase() === 'content-type');
  if (!ct) return;
  const mime = ct.value.split(';')[0].trim().toLowerCase();
  if (mime in IMAGE_MIME_MAP) {
    pendingImages.set(details.requestId, { mime });
  }
}

if (typeof browser !== 'undefined' && browser.webRequest) {
  browser.webRequest.onBeforeRequest.addListener(attachFilter, { urls: LISTEN_URLS }, ['blocking']);
  browser.webRequest.onHeadersReceived.addListener(markImageHeaders, { urls: LISTEN_URLS }, ['responseHeaders']);
}

if (typeof browser !== 'undefined' && browser.runtime) {
  browser.runtime.onMessage.addListener((msg) => {
    if (!msg) return;
    if (msg.type === 'INTERMEDIATE_FRAME_CAPTURED' && msg.data) {
      handleFrameDownload(msg.data);
    } else if (msg.type === 'IMAGE_METADATA_CAPTURED' || msg.type === 'IMAGE_DOM_DISCOVERED') {
      latestMetadata = Object.assign({}, latestMetadata || {}, msg.data, {
        updatedAt: new Date().toISOString()
      });
    }
  });
}
