// ChatGPT Image & Metadata Extractor — Page Context Injector
(function() {
  'use strict';

  const EVENT_NAME = '__CHATGPT_IMAGE_METADATA_EVENT__';
  const FRAME_EVENT = '__CHATGPT_IMAGE_FRAME_EVENT__';
  let frameSequence = 0;

  function dispatch(name, payload) {
    if (!payload) return;
    try {
      window.dispatchEvent(new CustomEvent(name, { detail: JSON.stringify(payload) }));
    } catch (e) {
      console.warn('[ImageExtractor] dispatch error:', e);
    }
  }

  function handleImagePart(part, conversationId, messageId) {
    if (!part) return;
    const isImg = part.content_type === 'image_asset_pointer' ||
                  part.content_type === 'multimodal_text' ||
                  (typeof part === 'string' && part.includes('image_asset_pointer'));
    if (isImg) {
      dispatch(EVENT_NAME, {
        source: 'sse_stream_part',
        conversationId,
        messageId,
        timestamp: new Date().toISOString(),
        part
      });
    }
  }

  function parseLineData(jsonStr, conversationId) {
    try {
      const data = JSON.parse(jsonStr);
      const msg = data.message || {};
      const parts = msg.content && msg.content.parts;
      if (Array.isArray(parts)) {
        for (const p of parts) handleImagePart(p, data.conversation_id, msg.id);
      }
      if (msg.metadata && msg.metadata.dalle) {
        dispatch(EVENT_NAME, {
          source: 'dalle_metadata',
          conversationId: data.conversation_id,
          messageId: msg.id,
          timestamp: new Date().toISOString(),
          dalle: msg.metadata.dalle
        });
      }
    } catch (_) {}
  }

  function parseConversationSSEChunk(text) {
    const lines = text.split('\n');
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const jsonStr = line.slice(6).trim();
      if (jsonStr === '[DONE]') continue;
      parseLineData(jsonStr);
    }
  }

  function monitorCanvasAndVideoFrames() {
    setInterval(() => {
      const canvases = document.querySelectorAll('canvas');
      for (const c of canvases) {
        if (c.width < 64 || c.height < 64) continue;
        try {
          const dataUrl = c.toDataURL('image/png');
          frameSequence += 1;
          dispatch(FRAME_EVENT, {
            type: 'canvas_frame',
            frameIndex: frameSequence,
            timestamp: new Date().toISOString(),
            dataUrl
          });
        } catch (_) {}
      }
    }, 1200);
  }

  function hookFetch() {
    const origFetch = window.fetch;
    window.fetch = async function(...args) {
      const res = await origFetch.apply(this, args);
      try {
        const url = (typeof args[0] === 'string' ? args[0] : args[0]?.url) || '';
        if (url.includes('/backend-api/conversation') || url.includes('/lat/r')) {
          const clone = res.clone();
          const reader = clone.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          const readChunk = async () => {
            const { done, value } = await reader.read();
            if (done) return;
            buffer += decoder.decode(value, { stream: true });
            parseConversationSSEChunk(buffer);
            await readChunk();
          };
          readChunk().catch(() => {});
        }
      } catch (err) {
        console.warn('[ImageExtractor] hookFetch error:', err);
      }
      return res;
    };
  }

  hookFetch();
  monitorCanvasAndVideoFrames();
  console.log('[ImageExtractor] Page injector active with frame extraction.');
})();
