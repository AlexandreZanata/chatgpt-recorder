// ChatGPT Image & Metadata Extractor — Popup Controller

document.addEventListener('DOMContentLoaded', () => {
  const autoImage = document.getElementById('autoImage');
  const autoMeta = document.getElementById('autoMeta');
  const prefix = document.getElementById('prefix');
  const subfolder = document.getElementById('subfolder');
  const saveBtn = document.getElementById('saveBtn');
  const statusMsg = document.getElementById('statusMsg');

  const api = typeof browser !== 'undefined' ? browser : chrome;

  if (api && api.storage && api.storage.local) {
    api.storage.local.get({
      autoDownloadImage: true,
      autoDownloadMetadata: true,
      filenamePrefix: 'chatgpt-img',
      subfolder: 'chatgpt-images'
    }).then((s) => {
      autoImage.checked = s.autoDownloadImage;
      autoMeta.checked = s.autoDownloadMetadata;
      prefix.value = s.filenamePrefix;
      subfolder.value = s.subfolder;
    });
  }

  saveBtn.addEventListener('click', () => {
    if (api && api.storage && api.storage.local) {
      api.storage.local.set({
        autoDownloadImage: autoImage.checked,
        autoDownloadMetadata: autoMeta.checked,
        filenamePrefix: prefix.value.trim() || 'chatgpt-img',
        subfolder: subfolder.value.trim() || 'chatgpt-images'
      }).then(() => {
        statusMsg.innerText = '✓ Settings saved!';
        setTimeout(() => { statusMsg.innerText = ''; }, 2000);
      });
    }
  });
});
