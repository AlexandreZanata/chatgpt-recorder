// ChatGPT Image & Metadata Extractor — Page Context Injector
(function() {
  'use strict';

  function postMsg(type, payload) {
    if (!payload) return;
    try {
      window.postMessage({ source: 'CHATGPT_IMAGE_EXTRACTOR_INJECTOR', type, payload }, '*');
    } catch (_) {}
  }

  function parseSSEStream(text) {
    const lines = text.split('\n');
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const jsonStr = line.slice(6).trim();
      if (!jsonStr || jsonStr === '[DONE]') continue;
      try {
        const data = JSON.parse(jsonStr);
        const msg = data.message || {};
        const parts = msg.content?.parts || [];
        postMsg('CONVERSATION_STREAM_CHUNK', {
          conversationId: data.conversation_id,
          messageId: msg.id,
          model: msg.metadata?.model_slug,
          parts,
          metadata: msg.metadata,
          timestamp: new Date().toISOString()
        });
      } catch (_) {}
    }
  }

  function hookFetch() {
    const origFetch = window.fetch;
    window.fetch = async function(...args) {
      const res = await origFetch.apply(this, args);
      try {
        const url = (typeof args[0] === 'string' ? args[0] : args[0]?.url) || '';
        if (url.includes('/backend-api/') || url.includes('/lat/r')) {
          const clone = res.clone();
          const reader = clone.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          const readChunk = async () => {
            const { done, value } = await reader.read();
            if (done) return;
            buffer += decoder.decode(value, { stream: true });
            parseSSEStream(buffer);
            await readChunk();
          };
          readChunk().catch(() => {});
        }
      } catch (_) {}
      return res;
    };
  }

  function hookWebSocket() {
    const OrigWS = window.WebSocket;
    window.WebSocket = function(...args) {
      const ws = new OrigWS(...args);
      ws.addEventListener('message', (e) => {
        if (typeof e.data === 'string') parseSSEStream(e.data);
      });
      return ws;
    };
  }

  hookFetch();
  hookWebSocket();
  console.log('[ImageExtractor] Page injector active for stream and metadata extraction.');
})();
