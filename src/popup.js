// ChatGPT Audio Capture — Popup UI Logic (With Templates)

function renderHistory(items) {
  const container = document.getElementById('historyList');
  if (!container) return;
  if (!items || items.length === 0) {
    container.innerHTML = '<div class="history-item">No captures yet</div>';
    return;
  }
  container.innerHTML = items.map((i) => `
    <div class="history-item">
      <strong>${i.title || 'Untitled'}</strong><br/>
      <small>${i.filename}</small>
    </div>
  `).join('');
}

function updateStorage(data) {
  if (typeof browser !== 'undefined' && browser.storage) {
    browser.storage.local.set(data);
  }
}

function bindInputListener(id, eventType, key, isCheckbox) {
  const element = document.getElementById(id);
  if (!element) return;
  element.addEventListener(eventType, (event) => {
    const val = isCheckbox ? event.target.checked : event.target.value;
    updateStorage({ [key]: val });
  });
}

function bindClearButton() {
  const btn = document.getElementById('clearHistory');
  if (!btn) return;
  btn.addEventListener('click', () => {
    if (typeof browser !== 'undefined' && browser.storage) {
      browser.storage.local.set({ captureHistory: [] }).then(() => renderHistory([]));
    }
  });
}

function loadSettings() {
  if (typeof browser === 'undefined' || !browser.storage) return;
  browser.storage.local.get({
    autoDownload: true,
    filenamePrefix: 'chatgpt-tts',
    filenameTemplate: '{prefix}_{date}_{title}',
    subfolder: '',
    captureHistory: []
  }).then((s) => {
    const autoEl = document.getElementById('autoDownload');
    const prefixEl = document.getElementById('prefix');
    const tmplEl = document.getElementById('template');
    const subEl = document.getElementById('subfolder');
    if (autoEl) autoEl.checked = s.autoDownload;
    if (prefixEl) prefixEl.value = s.filenamePrefix;
    if (tmplEl) tmplEl.value = s.filenameTemplate;
    if (subEl) subEl.value = s.subfolder;
    renderHistory(s.captureHistory);
  });
}

function bindEvents() {
  bindInputListener('autoDownload', 'change', 'autoDownload', true);
  bindInputListener('prefix', 'input', 'filenamePrefix', false);
  bindInputListener('template', 'input', 'filenameTemplate', false);
  bindInputListener('subfolder', 'input', 'subfolder', false);
  bindClearButton();
}

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  bindEvents();
});
