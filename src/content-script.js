// ChatGPT Audio Capture — Content Script Bridge & Injector

function cleanTitle(rawTitle) {
  if (!rawTitle) return 'chatgpt-session';
  return rawTitle
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .slice(0, 35);
}

function extractConversationTitle() {
  const h1Element = document.querySelector('h1');
  const rawTitle = h1Element ? h1Element.textContent : document.title;
  return cleanTitle(rawTitle);
}

function injectMainWorldScript() {
  if (document.getElementById('chatgpt-recorder-injector')) return;
  const script = document.createElement('script');
  script.id = 'chatgpt-recorder-injector';
  script.src = browser.runtime.getURL('src/page-injector.js');
  (document.head || document.documentElement).appendChild(script);
}

window.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'CHATGPT_AUDIO_CAPTURED_DATA') {
    const title = extractConversationTitle();
    browser.runtime.sendMessage({
      type: 'FALLBACK_AUDIO_DATA',
      dataUrl: event.data.dataUrl,
      title: title
    });
  }
});

if (typeof browser !== 'undefined' && browser.runtime) {
  browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request && request.type === 'EXTRACT_TITLE') {
      sendResponse({ title: extractConversationTitle() });
    }
    return true;
  });
}

injectMainWorldScript();
