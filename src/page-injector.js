// ChatGPT Audio Capture — Main World Page Injector (Strategy B Fallback)

(function () {
  if (window.__chatgptAudioInjectorLoaded) return;
  window.__chatgptAudioInjectorLoaded = true;

  function initMediaRecorder(stream) {
    const chunks = [];
    const recorder = new MediaRecorder(stream);

    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        chunks.push(e.data);
      }
    };

    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
      window.postMessage({ type: 'CHATGPT_AUDIO_FALLBACK_CAPTURED', blobUrl: URL.createObjectURL(blob) }, '*');
    };

    recorder.start();
    return recorder;
  }

  function monitorAudioElements() {
    document.addEventListener('play', (event) => {
      const element = event.target;
      if (element instanceof HTMLAudioElement && !element.dataset.captured) {
        element.dataset.captured = 'true';
        if (typeof element.captureStream === 'function') {
          const stream = element.captureStream();
          const recorder = initMediaRecorder(stream);
          element.addEventListener('ended', () => recorder.stop(), { once: true });
        }
      }
    }, true);
  }

  monitorAudioElements();
})();
