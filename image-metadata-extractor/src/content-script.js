// ChatGPT Image & Metadata Extractor — Content Script

(function() {
  'use strict';

  const EVENT_NAME = '__CHATGPT_IMAGE_METADATA_EVENT__';

  function injectScript() {
    try {
      const script = document.createElement('script');
      const api = typeof browser !== 'undefined' ? browser : chrome;
      script.src = api.runtime.getURL('src/page-injector.js');
      (document.head || document.documentElement).appendChild(script);
      script.onload = () => script.remove();
    } catch (e) {
      console.warn('[ImageExtractor] Script injection failed:', e);
    }
  }

  function getConversationTitle() {
    const titleEl = document.querySelector('title');
    const title = titleEl ? titleEl.innerText : 'chatgpt-image';
    return title.replace(/ChatGPT\s*[-–—|]?\s*/gi, '').trim() || 'chatgpt-image';
  }

  function setupMetadataListener() {
    window.addEventListener(EVENT_NAME, (evt) => {
      if (!evt.detail) return;
      try {
        const payload = JSON.parse(evt.detail);
        payload.pageTitle = getConversationTitle();
        payload.url = window.location.href;
        const api = typeof browser !== 'undefined' ? browser : chrome;
        api.runtime.sendMessage({
          type: 'IMAGE_METADATA_CAPTURED',
          data: payload
        }).catch(() => {});
      } catch (err) {
        console.warn('[ImageExtractor] Parse event error:', err);
      }
    });
  }

  function processImage(img) {
    const src = img.src || img.getAttribute('src') || '';
    if (!src.includes('oaiusercontent.com') && !src.includes('dalle')) return;
    const alt = img.alt || img.getAttribute('alt') || '';
    const api = typeof browser !== 'undefined' ? browser : chrome;
    api.runtime.sendMessage({
      type: 'IMAGE_DOM_DISCOVERED',
      data: {
        src,
        alt,
        pageTitle: getConversationTitle(),
        timestamp: new Date().toISOString()
      }
    }).catch(() => {});
  }

  function handleAddedNode(node) {
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    if (node.tagName === 'IMG') {
      processImage(node);
      return;
    }
    const imgs = node.querySelectorAll('img');
    for (const img of imgs) {
      processImage(img);
    }
  }

  function observeDOMImages() {
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          handleAddedNode(node);
        }
      }
    });

    observer.observe(document.body || document.documentElement, {
      childList: true,
      subtree: true
    });
  }

  if (typeof browser !== 'undefined' && browser.runtime) {
    browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
      if (msg && msg.type === 'EXTRACT_PAGE_INFO') {
        sendResponse({ title: getConversationTitle(), url: window.location.href });
      }
    });
  }

  injectScript();
  setupMetadataListener();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observeDOMImages);
  } else {
    observeDOMImages();
  }
})();
