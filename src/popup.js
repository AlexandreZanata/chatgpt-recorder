// ChatGPT Audio Capture — Popup UI Logic (With Export)

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

function triggerExport(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  if (typeof browser !== 'undefined' && browser.downloads) {
    browser.downloads.download({ url, filename, saveAs: true });
  }
}

function bindButtons() {
  const clearBtn = document.getElementById('clearHistory');
  const exportBtn = document.getElementById('exportSettings');

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (typeof browser !== 'undefined' && browser.storage) {
        browser.storage.local.set({ captureHistory: [] }).then(() => renderHistory([]));
      }
    });
  }
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      if (typeof browser !== 'undefined' && browser.storage) {
        browser.storage.local.get(null).then((s) => triggerExport(s, 'chatgpt-recorder-settings.json'));
      }
    });
  }
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
  bindButtons();
}

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  bindEvents();
});
