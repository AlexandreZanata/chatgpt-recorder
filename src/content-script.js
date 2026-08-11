// ChatGPT Audio Capture — Content Script Bridge

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
  const h1 = document.querySelector('h1');
  return cleanTitle(h1 ? h1.textContent : document.title);
}

// Inject page-injector into MAIN world via <script> with the extension's
// content-script CSP bypass. Firefox content scripts bypass page CSP when
// injecting extension resources via runtime.getURL.
function injectMainWorldScript() {
  if (window.__chatgptAudioInjectorLoaded) return;
  const url = browser.runtime.getURL('src/page-injector.js');

  // Method 1: classic <script src> — works if page CSP allows extension URLs
  const s = document.createElement('script');
  s.src = url;
  s.onload = () => s.remove();
  s.onerror = () => {
    // Method 2: fetch the script text and inject inline
    fetch(url)
      .then((r) => r.text())
      .then((code) => {
        const inline = document.createElement('script');
        inline.textContent = code;
        (document.head || document.documentElement).appendChild(inline);
        inline.remove();
      })
      .catch((e) => console.warn('[AudioCapture CS] inject failed:', e));
  };
  (document.head || document.documentElement).appendChild(s);
}

// Bridge: forward page → background messages
window.addEventListener('message', (event) => {
  if (!event.data || event.data.type !== 'CHATGPT_AUDIO_CAPTURED_DATA') return;
  browser.runtime.sendMessage({
    type: 'FALLBACK_AUDIO_DATA',
    dataUrl: event.data.dataUrl,
    title: extractConversationTitle()
  });
});

// Bridge: answer title requests from background
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request && request.type === 'EXTRACT_TITLE') {
    sendResponse({ title: extractConversationTitle() });
  }
  return true;
});

injectMainWorldScript();
