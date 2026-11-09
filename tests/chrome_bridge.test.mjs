import { it } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFile } from 'node:fs/promises';

// Contract: stale extension contexts request reload without uncaught page errors.
async function bridge(sendMessage, missingRuntime = false) {
  let listener;
  const notices = [];
  const page = { addEventListener(name, callback) { listener = callback; }, location: { reload() {} } };
  const document = {
    title: 'Test chat', querySelector() { return null; }, getElementById() { return null; },
    documentElement: { append(element) { notices.push(element); } },
    createElement() { return { style: {}, setAttribute() {}, append() {}, addEventListener() {} }; }
  };
  vm.runInNewContext(await readFile(new URL('../src/chrome/content-script.js', import.meta.url), 'utf8'), {
    window: page, document, chrome: { runtime: missingRuntime ? undefined : { id: 'extension', sendMessage } },
    console: { info() {}, warn() {} }
  });
  return { notices, deliver(origin = 'https://chatgpt.com') {
    listener({ source: page, origin, data: { type: 'CHATGPT_AUDIO_CAPTURED_DATA', dataUrl: 'data:audio/webm;base64,AAAA' } });
  } };
}

it('given invalidated runtime when old audio arrives then request reload once without throwing', async () => {
  const fixture = await bridge(() => { throw new Error('Extension context invalidated.'); });
  assert.doesNotThrow(() => fixture.deliver());
  assert.doesNotThrow(() => fixture.deliver());
  assert.equal(fixture.notices.length, 1);
});

it('given a disconnected worker then request reload instead of an unhandled rejection', async () => {
  const fixture = await bridge(() => Promise.reject(new Error('Could not establish connection.')));
  fixture.deliver();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(fixture.notices.length, 1);
});

it('given Chrome removed the old runtime then show the reload action without throwing', async () => {
  const fixture = await bridge(undefined, true);
  assert.doesNotThrow(() => fixture.deliver());
  assert.equal(fixture.notices.length, 1);
});

it('given an untrusted message then never relay it or display a reload notice', async () => {
  let calls = 0;
  const fixture = await bridge(() => { calls += 1; });
  fixture.deliver('https://other.example');
  assert.equal(calls, 0);
  assert.equal(fixture.notices.length, 0);
});
