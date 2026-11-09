// Isolated-world bridge. The MAIN-world hooks never receive extension APIs.
function conversationTitle() {
  const heading = document.querySelector('h1');
  const raw = heading ? heading.textContent : document.title;
  return (raw || 'chatgpt-session').trim().toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').slice(0, 35);
}

let reloadShown = false;
function requestReload() {
  if (reloadShown) return;
  reloadShown = true;
  console.info('[AudioCapture] Extension updated. Reload this ChatGPT tab to reconnect.');
  const notice = document.createElement('div');
  notice.setAttribute('role', 'alert');
  notice.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:2147483647;padding:16px;background:#fff;color:#111;border:1px solid #777;border-radius:8px;max-width:320px';
  notice.textContent = 'Audio capture needs this ChatGPT tab to be reloaded after the extension update. ';
  const button = document.createElement('button');
  button.textContent = 'Reload ChatGPT';
  button.addEventListener('click', () => window.location.reload());
  notice.append(button);
  document.documentElement?.append(notice);
}

function captureFailed(error) {
  const message = String(error?.message || error || 'Audio capture failed.');
  if (/context invalidated|establish connection|receiving end|message port closed/i.test(message)) {
    requestReload();
    return;
  }
  console.warn('[AudioCapture]', message.slice(0, 240));
}

function relayAudio(dataUrl) {
  try {
    if (!chrome.runtime?.id) return requestReload();
    chrome.runtime.sendMessage({
      type: 'FALLBACK_AUDIO_DATA', dataUrl, title: conversationTitle()
    }).then((result) => {
      if (result?.error) captureFailed(result.error);
    }).catch(captureFailed);
  } catch (error) {
    captureFailed(error);
  }
}

window.addEventListener('message', (event) => {
  if (event.source !== window || event.origin !== 'https://chatgpt.com') return;
  const data = event.data;
  if (!data || data.type !== 'CHATGPT_AUDIO_CAPTURED_DATA') return;
  if (typeof data.dataUrl !== 'string' || !data.dataUrl.startsWith('data:audio/')) return;
  relayAudio(data.dataUrl);
});
