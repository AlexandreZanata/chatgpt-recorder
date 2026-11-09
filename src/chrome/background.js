import { downloadCapture, trustedSender, updateAction, captureError } from './downloads.js';
import { recordingCommand, downloadChanged, suppressAutomatic } from './recording-controller.js';

// Serialize storage updates from simultaneous captures while the worker lives.
let captureQueue = Promise.resolve();
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.target === 'worker' && message.type?.startsWith('RECORDER_')) {
    captureQueue = captureQueue.then(() => recordingCommand(message, sender, chrome))
      .then(sendResponse).catch((error) => sendResponse({ state: 'error', error: error.message }));
    return true;
  }
  if (!message || message.type !== 'FALLBACK_AUDIO_DATA') return false;
  if (!trustedSender(sender, chrome.runtime.id)) return false;
  captureQueue = captureQueue.then(async () => {
    if (await suppressAutomatic(sender, chrome)) return { skipped: true };
    return downloadCapture(message, chrome);
  })
    .then(sendResponse).catch((error) => {
      updateAction(chrome, 'setIcon', { path: 'icons/icon-error.png' });
      sendResponse({ error: captureError(error) });
    });
  return true;
});

chrome.downloads.onChanged.addListener((delta) => {
  captureQueue = captureQueue.then(() => downloadChanged(delta, chrome)).catch(() => {});
});
