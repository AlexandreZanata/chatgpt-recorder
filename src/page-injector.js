// ChatGPT Audio Capture — Main World Page Injector (WebAudio & AudioElement Interceptor)

(function () {
  if (window.__chatgptAudioInjectorLoaded) return;
  window.__chatgptAudioInjectorLoaded = true;

  function sendAudioBlob(blob) {
    const reader = new FileReader();
    reader.onloadend = () => {
      window.postMessage({
        type: 'CHATGPT_AUDIO_CAPTURED_DATA',
        dataUrl: reader.result
      }, '*');
    };
    reader.readAsDataURL(blob);
  }

  function startStreamRecorder(stream) {
    const chunks = [];
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm';
    const recorder = new MediaRecorder(stream, { mimeType });

    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data);
    };

    recorder.onstop = () => {
      if (chunks.length > 0) {
        const blob = new Blob(chunks, { type: mimeType });
        sendAudioBlob(blob);
      }
    };

    recorder.start(1000);
    return recorder;
  }

  function hookAudioContext() {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;

    const origConnect = AudioNode.prototype.connect;
    AudioNode.prototype.connect = function (dest, out, inp) {
      if (dest === this.context.destination && !this.context.__recorded) {
        this.context.__recorded = true;
        try {
          const streamDest = this.context.createMediaStreamDestination();
          origConnect.call(this, streamDest, out, inp);
          const rec = startStreamRecorder(streamDest.stream);
          this.context.addEventListener('statechange', () => {
            if (this.context.state !== 'running' && rec.state === 'recording') {
              rec.stop();
            }
          });
        } catch {
          // ignore stream hook failure
        }
      }
      return origConnect.call(this, dest, out, inp);
    };
  }

  function monitorAudioElements() {
    document.addEventListener('play', (event) => {
      const el = event.target;
      if (el instanceof HTMLAudioElement && !el.dataset.captured) {
        el.dataset.captured = 'true';
        if (typeof el.captureStream === 'function') {
          const stream = el.captureStream();
          const rec = startStreamRecorder(stream);
          el.addEventListener('ended', () => rec.state === 'recording' && rec.stop(), { once: true });
        }
      }
    }, true);
  }

  hookAudioContext();
  monitorAudioElements();
})();
