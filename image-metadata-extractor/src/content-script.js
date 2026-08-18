// ChatGPT Image & Metadata Extractor — Content Script

(function() {
  'use strict';

  let stageCounter = 0;
  let activeGenerationInterval = null;
  const capturedFinalUrls = new Set();
  const capturedFrameHashes = new Set();
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

  function sendFrameData(dataUrl) {
    if (!dataUrl || dataUrl.length < 500) return;
    const hash = dataUrl.slice(0, 100);
    if (capturedFrameHashes.has(hash)) return;
    capturedFrameHashes.add(hash);
    stageCounter += 1;
    api.runtime.sendMessage({
      type: 'INTERMEDIATE_FRAME_CAPTURED',
      data: {
        stageIndex: stageCounter,
        dataUrl,
        pageTitle: getConversationTitle(),
        userPrompt: getLatestUserPrompt(),
        timestamp: new Date().toISOString()
      }
    }).catch(() => {});
  }

  function captureImgNode(img) {
    try {
      const cvs = document.createElement('canvas');
      cvs.width = img.naturalWidth || img.width || 512;
      cvs.height = img.naturalHeight || img.height || 512;
      const ctx = cvs.getContext('2d');
      ctx.drawImage(img, 0, 0);
      sendFrameData(cvs.toDataURL('image/png'));
    } catch (_) {}
  }

  function captureElementToDataUrl(el) {
    if (!el) return;
    if (el.tagName === 'CANVAS' && el.width >= 32) {
      try { sendFrameData(el.toDataURL('image/png')); } catch (_) {}
      return;
    }
    if (el.tagName === 'IMG' && el.src) {
      captureImgNode(el);
    }
  }

  function startStageCapture() {
    if (activeGenerationInterval) return;
    activeGenerationInterval = setInterval(() => {
      const els = document.querySelectorAll('canvas, img[src*="blob:"], img[src*="data:"], img[src*="oaiusercontent"], .group\\/image img, [data-testid*="image"] img');
      for (const el of els) captureElementToDataUrl(el);
    }, 400);
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
    captureElementToDataUrl(img);
    if (capturedFinalUrls.has(src)) return;
    capturedFinalUrls.add(src);
    setTimeout(stopStageCapture, 2000);

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
