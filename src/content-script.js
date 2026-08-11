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
  const h1Element = document.querySelector('h1');
  const rawTitle = h1Element ? h1Element.textContent : document.title;
  return cleanTitle(rawTitle);
}

if (typeof browser !== 'undefined' && browser.runtime) {
  browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request && request.type === 'EXTRACT_TITLE') {
      sendResponse({ title: extractConversationTitle() });
    }
    return true;
  });
}
