// ChatGPT Image & Metadata Extractor — Page Context Injector
(function() {
  'use strict';

  const EVENT_NAME = '__CHATGPT_IMAGE_METADATA_EVENT__';

  function dispatchMetadata(payload) {
    if (!payload) return;
    try {
      const event = new CustomEvent(EVENT_NAME, { detail: JSON.stringify(payload) });
      window.dispatchEvent(event);
    } catch (e) {
      console.warn('[ImageExtractor] dispatch error:', e);
    }
  }

  function extractFromParts(parts, conversationId, messageId) {
    if (!Array.isArray(parts)) return;
    for (const part of parts) {
      if (!part) continue;
      const isImg = part.content_type === 'image_asset_pointer' ||
                    part.content_type === 'multimodal_text' ||
                    (typeof part === 'string' && part.includes('image_asset_pointer'));
      if (isImg) {
        dispatchMetadata({
          source: 'sse_stream_part',
          conversationId,
          messageId,
          timestamp: new Date().toISOString(),
          part
        });
      }
    }
  }

  function parseConversationSSEChunk(text) {
    const lines = text.split('\n');
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const jsonStr = line.slice(6).trim();
      if (jsonStr === '[DONE]') continue;
      try {
        const data = JSON.parse(jsonStr);
        const msg = data.message || {};
        const parts = msg.content && msg.content.parts;
        if (parts) {
          extractFromParts(parts, data.conversation_id, msg.id);
        }
        if (msg.metadata && msg.metadata.dalle) {
          dispatchMetadata({
            source: 'dalle_metadata',
            conversationId: data.conversation_id,
            messageId: msg.id,
            timestamp: new Date().toISOString(),
            dalle: msg.metadata.dalle
          });
        }
      } catch (_) {
        // partial chunk JSON, ignore
      }
    }
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
  console.log('[ImageExtractor] Page injector active for image metadata capture.');
})();
