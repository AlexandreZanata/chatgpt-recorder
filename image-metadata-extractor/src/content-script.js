// ChatGPT Image & Metadata Extractor — Content Script

(function() {
  'use strict';

  let stageCounter = 0;
  let activeGenerationInterval = null;
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
    if (userMessages.length > 0) {
      return userMessages[userMessages.length - 1].innerText.trim();
    }
    return '';
  }

  function captureContainerStage(targetElement) {
    if (!targetElement) return;
    try {
      const canvas = targetElement.tagName === 'CANVAS' ? targetElement : targetElement.querySelector('canvas');
      if (canvas && canvas.width >= 64) {
        stageCounter += 1;
        api.runtime.sendMessage({
          type: 'INTERMEDIATE_FRAME_CAPTURED',
          data: {
            stageIndex: stageCounter,
            dataUrl: canvas.toDataURL('image/png'),
            pageTitle: getConversationTitle(),
            userPrompt: getLatestUserPrompt(),
            timestamp: new Date().toISOString()
          }
        }).catch(() => {});
      }
    } catch (_) {}
  }

  function startStageCapture() {
    if (activeGenerationInterval) return;
    stageCounter = 0;
    activeGenerationInterval = setInterval(() => {
      const candidates = document.querySelectorAll('canvas, [data-testid*="image"], .group\\/image');
      for (const el of candidates) captureContainerStage(el);
    }, 800);
  }

  function stopStageCapture() {
    if (activeGenerationInterval) {
      clearInterval(activeGenerationInterval);
      activeGenerationInterval = null;
    }
  }

  function handlePageMessage(evt) {
    if (!evt.data || evt.data.source !== 'CHATGPT_IMAGE_EXTRACTOR_INJECTOR') return;
    const { type, payload } = evt.data;
    if (type === 'CONVERSATION_STREAM_CHUNK') {
      startStageCapture();
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
    stopStageCapture();

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
