// Registered in MAIN at document_start, without script tags or inline eval.
(function () {
  if (window.__chromeAudioCaptureLoaded) return;
  window.__chromeAudioCaptureLoaded = true;
  const hooks = window.__chromeAudioHooks;
  const nativeFetch = window.fetch;

  function requestUrl(args) {
    const first = args[0];
    if (typeof first === 'string') return first;
    if (first instanceof window.Request) return first.url;
    return first?.url || '';
  }

  function isTtsUrl(url) {
    return /synthesize|backend-api\/(voice|speech)|tts|read-aloud/i.test(url);
  }

  function audioResponse(response, url) {
    if (!response.ok) return false;
    const mime = (response.headers.get('content-type') || '').toLowerCase();
    if (mime.startsWith('audio/')) return true;
    if (isTtsUrl(url) && (mime.startsWith('application/octet-stream') || mime === '')) return true;
    return false;
  }

  function sendNetworkBlob(blob, url) {
    if (blob.size < 512) return;
    if (blob.type.toLowerCase().startsWith('audio/')) {
      hooks.sendBlob(blob, true);
      return;
    }
    if (isTtsUrl(url)) hooks.sendBlob(new Blob([blob], { type: 'audio/webm' }), true);
  }

  window.fetch = async function (...args) {
    const url = requestUrl(args);
    const response = await nativeFetch.apply(this, args);
    if (audioResponse(response, url)) {
      try {
        response.clone().blob().then((blob) => sendNetworkBlob(blob, url)).catch(() => {});
      } catch {
        // Capture failure must never replace a successful playback response.
      }
    }
    return response;
  };

  function captureElement(element) {
    if (hooks.recentlyCaptured()) return;
    try {
      const source = element.currentSrc || element.src;
      if (source.startsWith('blob:')) {
        nativeFetch(source).then((response) => response.blob())
          .then((blob) => hooks.sendBlob(blob, true)).catch(() => {});
        return;
      }
      const recorder = hooks.recordStream(element.captureStream());
      const stop = () => hooks.stopRecorder(recorder);
      element.addEventListener('ended', stop, { once: true });
      element.addEventListener('pause', stop, { once: true });
    } catch {
      // Unsupported media streams do not affect the original audio element.
    }
  }

  const capturedElements = new WeakSet();
  document.addEventListener('play', (event) => {
    const element = event.target;
    if (!(element instanceof window.HTMLAudioElement) || capturedElements.has(element)) return;
    capturedElements.add(element);
    const release = () => capturedElements.delete(element);
    element.addEventListener('ended', release, { once: true });
    element.addEventListener('pause', release, { once: true });
    captureElement(element);
  }, true);

  function watchSource(node, entry) {
    if (!('onended' in node) || entry.sources.has(node)) return;
    entry.sources.add(node);
    clearTimeout(entry.idleTimer);
    node.addEventListener('ended', () => {
      entry.sources.delete(node);
      if (!entry.sources.size) {
        entry.idleTimer = setTimeout(() => hooks.stopRecorder(entry.recorder), 1000);
      }
    }, { once: true });
  }

  function isElementSource(node) {
    if (typeof window.MediaElementAudioSourceNode === 'function'
      && node instanceof window.MediaElementAudioSourceNode) return true;
    if (typeof window.HTMLMediaElement !== 'function') return false;
    return node?.mediaElement instanceof window.HTMLMediaElement;
  }

  function tapOutput(node, args, nativeConnect, contexts) {
    const destination = args[0];
    if (!(destination instanceof window.AudioDestinationNode)) return;
    if (isElementSource(node)) return;
    const context = destination.context;
    let entry = contexts.get(context);
    if (!entry || entry.recorder.state === 'inactive') {
      const sink = context.createMediaStreamDestination();
      const recorder = hooks.recordStream(sink.stream);
      if (!recorder) return;
      entry = { sink, recorder, sources: new Set(), idleTimer: null };
      contexts.set(context, entry);
      context.addEventListener('statechange', () => {
        if (context.state !== 'running') hooks.stopRecorder(recorder);
      });
    }
    const tapArgs = args.length > 1 ? [entry.sink, args[1]] : [entry.sink];
    nativeConnect.apply(node, tapArgs);
    watchSource(node, entry);
  }

  if (window.AudioNode && window.AudioDestinationNode) {
    const nativeConnect = window.AudioNode.prototype.connect;
    const contexts = new WeakMap();
    window.AudioNode.prototype.connect = function (...args) {
      // Preserve argument count, overloads, return value and native exceptions.
      const result = nativeConnect.apply(this, args);
      try {
        tapOutput(this, args, nativeConnect, contexts);
      } catch {
        // Only the optional recorder failed; the real connection already exists.
      }
      return result;
    };
  }
})();
