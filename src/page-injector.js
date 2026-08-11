// ChatGPT Audio Capture — Main World Page Injector (WebAudio & HTMLAudioElement)

(function () {
  if (window.__chatgptAudioInjectorLoaded) return;
  window.__chatgptAudioInjectorLoaded = true;

  console.log('[AudioCapture injector] loaded');

  function sendAudioBlob(blob) {
    const reader = new FileReader();
    reader.onloadend = () => {
      console.log('[AudioCapture injector] sending blob', blob.size, 'bytes via postMessage');
      window.postMessage({ type: 'CHATGPT_AUDIO_CAPTURED_DATA', dataUrl: reader.result }, '*');
    };
    reader.readAsDataURL(blob);
  }

  function startStreamRecorder(stream, label) {
    const chunks = [];
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm';
    const recorder = new MediaRecorder(stream, { mimeType });

    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data);
    };

    recorder.onstop = () => {
      console.log('[AudioCapture injector] recorder stopped, chunks:', chunks.length, 'label:', label);
      if (chunks.length > 0) {
        sendAudioBlob(new Blob(chunks, { type: mimeType }));
      }
    };

    recorder.onerror = (e) => console.warn('[AudioCapture injector] recorder error:', e);
    recorder.start(500);
    console.log('[AudioCapture injector] recorder started, label:', label);
    return recorder;
  }

  // ── Hook AudioContext ────────────────────────────────────────────────────────
  // ChatGPT decodes audio via Web Audio API (AudioBufferSourceNode → destination)
  // We tap the stream at createMediaStreamDestination and record it.
  function hookAudioContext() {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) {
      console.warn('[AudioCapture injector] AudioContext not available');
      return;
    }

    const origConnect = AudioNode.prototype.connect;
    AudioNode.prototype.connect = function (dest, outChannel, inChannel) {
      // Only intercept connections going to the final audio output
      if (dest instanceof AudioDestinationNode && !dest.context.__acRecorder) {
        dest.context.__acRecorder = true;
        try {
          const streamDest = dest.context.createMediaStreamDestination();
          // Record the stream
          const rec = startStreamRecorder(streamDest.stream, 'AudioContext');
          // Stop recording when context closes or suspends
          const stopOnIdle = () => {
            if (dest.context.state !== 'running' && rec.state === 'recording') {
              rec.stop();
            }
          };
          dest.context.addEventListener('statechange', stopOnIdle);
          // Also stop after 60s silence guard
          setTimeout(() => {
            if (rec.state === 'recording') rec.stop();
          }, 60000);
          // Connect this node to BOTH the real destination AND our recorder
          origConnect.call(this, streamDest, outChannel, inChannel);
        } catch (err) {
          console.warn('[AudioCapture injector] AudioContext hook error:', err);
        }
      }
      // Always connect to original destination so user hears audio
      return origConnect.call(this, dest, outChannel, inChannel);
    };

    console.log('[AudioCapture injector] AudioContext hooked');
  }

  function captureAudioElementSource(el) {
    if (typeof el.captureStream === 'function') {
      try {
        const stream = el.captureStream();
        const rec = startStreamRecorder(stream, 'HTMLAudioElement');
        const stop = () => { if (rec.state === 'recording') rec.stop(); };
        el.addEventListener('ended', stop, { once: true });
        el.addEventListener('pause', stop, { once: true });
        return;
      } catch (err) {
        console.warn('[AudioCapture injector] captureStream failed:', err);
      }
    }

    const src = el.src || el.currentSrc;
    if (src && (src.startsWith('blob:') || src.startsWith('https://'))) {
      fetch(src)
        .then((r) => r.blob())
        .then((blob) => {
          console.log('[AudioCapture injector] fetched audio element src, size:', blob.size);
          sendAudioBlob(blob);
        })
        .catch((err) => console.warn('[AudioCapture injector] fetch src failed:', err));
    }
  }

  // ── Hook HTMLAudioElement ────────────────────────────────────────────────────
  // Some ChatGPT voices use a plain <audio> element
  function hookAudioElements() {
    document.addEventListener('play', (event) => {
      const el = event.target;
      if (!(el instanceof HTMLAudioElement) || el.__acCaptured) return;
      el.__acCaptured = true;
      console.log('[AudioCapture injector] <audio> play detected src:', el.src || el.currentSrc);
      captureAudioElementSource(el);
    }, true);

    console.log('[AudioCapture injector] HTMLAudioElement hooked');
  }

  // ── Hook fetch to intercept audio responses ──────────────────────────────────
  // If webRequest filter misses the request, we catch it here in page context
  function hookFetch() {
    const origFetch = window.fetch;
    window.fetch = async function (...args) {
      const response = await origFetch.apply(this, args);
      const ct = response.headers.get('content-type') || '';
      const url = typeof args[0] === 'string' ? args[0] : (args[0].url || '');

      if (ct.startsWith('audio/') || url.includes('synthesize') ||
          url.includes('/voice') || url.includes('/speech')) {
        console.log('[AudioCapture injector] fetch intercepted audio:', url, ct);
        // Clone so original consumer still gets the response
        const clone = response.clone();
        clone.blob().then((blob) => {
          if (blob.size > 512) sendAudioBlob(blob);
        }).catch(() => {});
      }
      return response;
    };
    console.log('[AudioCapture injector] fetch hooked');
  }

  hookAudioContext();
  hookAudioElements();
  hookFetch();
})();
