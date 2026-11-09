// MAIN-world helpers. Capture is best-effort and never interrupts playback.
(function () {
  if (window.__chromeAudioHooks) return;
  let lastNetworkCapture = 0;

  function sendBlob(blob, network = false) {
    const mime = blob.type.split(';')[0].trim().toLowerCase();
    if (!mime.startsWith('audio/') || blob.size < 512) return;
    if (network) lastNetworkCapture = Date.now();
    const reader = new FileReader();
    reader.onloadend = () => window.postMessage({
      type: 'CHATGPT_AUDIO_CAPTURED_DATA', dataUrl: reader.result
    }, window.location.origin);
    reader.readAsDataURL(new Blob([blob], { type: mime }));
  }

  function recentlyCaptured(started = Date.now()) {
    return lastNetworkCapture > 0 && lastNetworkCapture >= started - 10000;
  }

  function recordStream(stream) {
    if (recentlyCaptured()) return null;
    const started = Date.now();
    const chunks = [];
    const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus' : 'audio/webm';
    const recorder = new MediaRecorder(stream, { mimeType: mime });
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size) chunks.push(event.data);
    };
    recorder.onstop = () => {
      if (chunks.length && !recentlyCaptured(started)) sendBlob(new Blob(chunks, { type: mime }));
    };
    recorder.start(500);
    return recorder;
  }

  function stopRecorder(recorder) {
    if (recorder && recorder.state === 'recording') recorder.stop();
  }

  window.__chromeAudioHooks = { sendBlob, recordStream, stopRecorder, recentlyCaptured };
})();
