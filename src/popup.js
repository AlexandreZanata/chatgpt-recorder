// ChatGPT Audio Capture — Popup UI Logic

function loadSettings() {
  if (typeof browser === 'undefined' || !browser.storage) return;
  browser.storage.local.get({ autoDownload: true, filenamePrefix: 'chatgpt-tts' })
    .then((settings) => {
      const autoEl = document.getElementById('autoDownload');
      const prefixEl = document.getElementById('prefix');
      if (autoEl) autoEl.checked = settings.autoDownload;
      if (prefixEl) prefixEl.value = settings.filenamePrefix;
    });
}

function bindEvents() {
  const autoEl = document.getElementById('autoDownload');
  const prefixEl = document.getElementById('prefix');

  if (autoEl) {
    autoEl.addEventListener('change', (e) => {
      if (typeof browser !== 'undefined' && browser.storage) {
        browser.storage.local.set({ autoDownload: e.target.checked });
      }
    });
  }

  if (prefixEl) {
    prefixEl.addEventListener('input', (e) => {
      if (typeof browser !== 'undefined' && browser.storage) {
        browser.storage.local.set({ filenamePrefix: e.target.value });
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  bindEvents();
});
