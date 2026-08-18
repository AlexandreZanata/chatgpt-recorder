// ChatGPT Image & Metadata Extractor — Content Script

(function() {
  'use strict';

  const capturedFinalUrls = new Set();
  const api = typeof browser !== 'undefined' ? browser : chrome;

  function injectScript() {
    try {
      const script = document.createElement('script');
      script.src = api.runtime.getURL('src/page-injector.js');
      (document.head || document.documentElement).appendChild(script);
      script.onload = () => script.remove();
    } catch (_) {}
  }

  function getConversationTitle() {
    const titleEl = document.querySelector('title');
    const title = titleEl ? titleEl.innerText : 'chatgpt-image';
    return title.replace(/ChatGPT\s*[-–—|]?\s*/gi, '').trim() || 'chatgpt-image';
  }

  function getLatestUserPrompt() {
    const userMessages = document.querySelectorAll('[data-message-author-role="user"]');
    return userMessages.length > 0 ? userMessages[userMessages.length - 1].innerText.trim() : '';
  }

  function handlePageMessage(evt) {
    if (!evt.data || evt.data.source !== 'CHATGPT_IMAGE_EXTRACTOR_INJECTOR') return;
    const { type, payload } = evt.data;
    if (type === 'CONVERSATION_STREAM_CHUNK') {
      payload.pageTitle = getConversationTitle();
      payload.userPrompt = getLatestUserPrompt();
      api.runtime.sendMessage({ type: 'STREAM_METADATA_CHUNK', data: payload }).catch(() => {});
    }
  }

  function processFinalImage(img) {
    const src = img.src || img.getAttribute('src') || '';
    if (!src.includes('oaiusercontent.com') && !src.includes('estuary') && !src.includes('dalle')) return;
    if (capturedFinalUrls.has(src)) return;
    capturedFinalUrls.add(src);

    api.runtime.sendMessage({
      type: 'IMAGE_DOM_DISCOVERED',
      data: {
        src,
        alt: img.alt || img.getAttribute('alt') || '',
        pageTitle: getConversationTitle(),
        userPrompt: getLatestUserPrompt(),
        timestamp: new Date().toISOString()
      }
    }).catch(() => {});
  }

  function observeDOM() {
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (node.nodeType !== Node.ELEMENT_NODE) continue;
          if (node.tagName === 'IMG') processFinalImage(node);
          const imgs = node.querySelectorAll ? node.querySelectorAll('img') : [];
          for (const img of imgs) processFinalImage(img);
        }
      }
    });
    observer.observe(document.body || document.documentElement, { childList: true, subtree: true });
  }

  injectScript();
  window.addEventListener('message', handlePageMessage);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observeDOM);
  } else {
    observeDOM();
  }
})();
