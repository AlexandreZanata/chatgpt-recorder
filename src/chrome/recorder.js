// The offscreen document owns media and Blob URLs across service-worker restarts.
let recording = null;
const urls = new Set();

async function startRecording(message) {
  if (recording) throw new Error('A recording is already active.');
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { mandatory: { chromeMediaSource: 'tab', chromeMediaSourceId: message.streamId } },
    video: false
  });
  try {
    const output = new AudioContext();
    output.createMediaStreamSource(stream).connect(output.destination);
    await output.resume();
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '');
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    const entry = { recorder, stream, output, chunks: [], ...message };
    recording = entry;
    recorder.ondataavailable = (event) => {
      if (event.data.size) entry.chunks.push(event.data);
    };
    recorder.onstop = () => finishRecording(entry);
    recorder.onerror = () => stopRecording();
    stream.getTracks().forEach((track) => track.addEventListener('ended', stopRecording));
    recorder.start(1000);
    return { state: 'recording' };
  } catch (error) {
    stream.getTracks().forEach((track) => track.stop());
    recording = null;
    throw error;
  }
}

async function finishRecording(entry) {
  entry.stream.getTracks().forEach((track) => track.stop());
  await entry.output.close();
  const blob = new Blob(entry.chunks, { type: 'audio/webm' });
  entry.chunks = [];
  const url = URL.createObjectURL(blob);
  urls.add(url);
  recording = null;
  await chrome.runtime.sendMessage({
    type: 'RECORDER_FINISHED', target: 'worker', sessionId: entry.sessionId,
    url, size: blob.size, mime: 'audio/webm'
  });
}

function stopRecording() {
  if (recording && recording.recorder.state === 'recording') recording.recorder.stop();
  return { state: 'saving' };
}

function releaseUrl(url) {
  if (urls.delete(url)) URL.revokeObjectURL(url);
  return { released: true };
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (sender.id !== chrome.runtime.id || message.target !== 'recorder') return false;
  let operation;
  switch (message.type) {
    case 'RECORDER_STREAM': operation = startRecording(message); break;
    case 'RECORDER_STOP_STREAM': operation = stopRecording(); break;
    case 'RECORDER_RELEASE': operation = releaseUrl(message.url); break;
    default: return false;
  }
  Promise.resolve(operation).then(respond).catch((error) => respond({ error: error.message }));
  return true;
});
