import { it } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

// Contract: preserve WebAudio playback, recording only when network capture is absent.
async function playbackPage() {
  const recorders = [];
  const messages = [];
  const connections = [];
  let finished;
  const captured = new Promise((resolve) => { finished = resolve; });
  class Node extends EventTarget {
    connect(...args) { connections.push(args); return args[0]; }
  }
  class Destination extends Node {}
  class Recorder {
    static isTypeSupported() { return true; }
    constructor() { this.state = 'inactive'; recorders.push(this); }
    start() { this.state = 'recording'; }
    stop() {
      this.state = 'inactive';
      this.ondataavailable({ data: new Blob([Buffer.alloc(1024)], { type: 'audio/webm' }) });
      this.onstop();
    }
  }
  class Reader {
    async readAsDataURL(blob) {
      this.result = `data:${blob.type};base64,${Buffer.from(await blob.arrayBuffer()).toString('base64')}`;
      this.onloadend();
    }
  }
  const events = {};
  class AudioElement extends EventTarget {
    src = 'https://chatgpt.com/audio';
    captureStream() { return {}; }
  }
  const page = { AudioNode: Node, AudioDestinationNode: Destination, HTMLAudioElement: AudioElement,
    location: { origin: 'https://chatgpt.com' },
    fetch: async () => new Response(Buffer.alloc(1024), { headers: { 'content-type': 'audio/webm' } }),
    postMessage(message) { messages.push(message); finished(message); }
  };
  const context = vm.createContext({ window: page, Blob, URL, FileReader: Reader,
    MediaRecorder: Recorder, setTimeout, clearTimeout, Date, console,
    document: { addEventListener(name, handler) { events[name] = handler; } }
  });
  for (const name of ['audio-hooks', 'page-injector']) {
    vm.runInContext(await readFile(new URL(`../src/chrome/${name}.js`, import.meta.url), 'utf8'), context);
  }
  const audioContext = new EventTarget();
  audioContext.state = 'running';
  audioContext.createMediaStreamDestination = () => ({ stream: {} });
  const destination = new Destination();
  destination.context = audioContext;
  return { page, recorders, messages, captured, connections, destination, audioContext,
    node: new Node(), element: new AudioElement(), events };
}

it('given WebAudio output then preserve native connect arguments and return value', async () => {
  const fixture = await playbackPage();
  assert.equal(fixture.node.connect(fixture.destination), fixture.destination);
  assert.equal(fixture.connections[0].length, 1);
  assert.equal(fixture.connections[0][0], fixture.destination);
  assert.equal(fixture.recorders[0].state, 'recording');
});

it('given WebAudio with no captured fetch then context suspend saves the fallback', async () => {
  const fixture = await playbackPage();
  fixture.node.connect(fixture.destination);
  fixture.audioContext.state = 'suspended';
  fixture.audioContext.dispatchEvent(new Event('statechange'));
  assert.match((await fixture.captured).dataUrl, /^data:audio\/webm;base64,/);
});

it('given media element fallback then pause saves audio without stopping native playback', async () => {
  const fixture = await playbackPage();
  fixture.events.play({ target: fixture.element });
  assert.equal(fixture.recorders[0].state, 'recording');
  fixture.element.dispatchEvent(new Event('pause'));
  assert.match((await fixture.captured).dataUrl, /^data:audio\/webm;base64,/);
});

it('given captured network audio then avoid duplicate WebAudio recording for that playback', async () => {
  const fixture = await playbackPage();
  await fixture.page.fetch('https://chatgpt.com/backend-api/synthesize');
  await fixture.captured;
  fixture.node.connect(fixture.destination);
  assert.equal(fixture.recorders.length, 0);
  assert.equal(fixture.connections[0][0], fixture.destination);
});

it('given captured network audio then avoid downloading its blob again from the audio element', async () => {
  const fixture = await playbackPage();
  await fixture.page.fetch('https://chatgpt.com/backend-api/synthesize');
  await fixture.captured;
  fixture.element.src = 'blob:https://chatgpt.com/example';
  fixture.events.play({ target: fixture.element });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(fixture.messages.length, 1);
  assert.equal(fixture.recorders.length, 0);
});
