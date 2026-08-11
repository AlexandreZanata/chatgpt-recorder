// ChatGPT Audio Capture — Popup UI Logic (With Import/Export)

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

function handleImportFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const settings = JSON.parse(e.target.result);
      if (typeof browser !== 'undefined' && browser.storage) {
        browser.storage.local.set(settings).then(() => loadSettings());
      }
    } catch (err) {
      console.error('Invalid JSON settings file:', err);
    }
  };
  reader.readAsText(file);
}

function bindActionButtons() {
  const clearBtn = document.getElementById('clearHistory');
  const exportBtn = document.getElementById('exportSettings');
  const importBtn = document.getElementById('importSettings');
  const importFile = document.getElementById('importFile');

  if (clearBtn) clearBtn.addEventListener('click', () => updateStorage({ captureHistory: [] }));
  if (exportBtn) exportBtn.addEventListener('click', () => {
    browser?.storage?.local?.get(null).then((s) => triggerExport(s, 'chatgpt-recorder-settings.json'));
  });
  if (importBtn && importFile) {
    importBtn.addEventListener('click', () => importFile.click());
    importFile.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) handleImportFile(e.target.files[0]);
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
  bindActionButtons();
}

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  bindEvents();
});
