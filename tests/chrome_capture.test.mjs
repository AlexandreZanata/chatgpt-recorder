import { it } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFile } from 'node:fs/promises';
import { audioMime, captureFilename, downloadCapture, trustedSender, captureError } from '../src/chrome/downloads.js';

const payload = `data:audio/webm;base64,${Buffer.alloc(1024, 7).toString('base64')}`;

// Contract: report the actual failure without falsely blaming Downloads settings.
it('given a capture failure then report its reason without exposing embedded audio data', () => {
  assert.equal(captureError(new Error('Invalid audio payload.')), 'Audio capture failed: Invalid audio payload.');
  assert.equal(captureError(new Error('Invalid filename')), 'Audio capture failed: Invalid filename');
  assert.ok(!captureError(new Error(`Bad URL ${payload}`)).includes(payload));
});

function fakeChrome(overrides = {}) {
  const local = { ...overrides };
  const session = {};
  const downloads = [];
  const badge = [];
  const storage = (state) => ({
    async get(defaults) { return { ...defaults, ...state }; },
    async set(values) { Object.assign(state, values); }
  });
  return {
    local, session, downloads, badge,
    storage: { local: storage(local), session: storage(session) },
    downloadsApi: { async download(details) { downloads.push(details); return downloads.length; } },
    action: {
      async setIcon() {}, async setBadgeBackgroundColor() {},
      async setBadgeText(value) { badge.push(value.text); }
    }
  };
}

function apiFor(fake) { return { ...fake, downloads: fake.downloadsApi }; }

// Contract: Chrome preserves captured response bytes and filename settings.
it('given audio when saved then download original bytes and update history and session badge', async () => {
  const fake = fakeChrome({ filenameTemplate: '{prefix}_{title}', filenamePrefix: 'story', subfolder: 'audio' });
  await downloadCapture({ dataUrl: payload, title: 'my-chat' }, apiFor(fake));
  assert.deepEqual(fake.downloads[0], { url: payload, filename: 'audio/story_my-chat.webm', saveAs: false });
  assert.equal(fake.local.captureHistory[0].filename, 'audio/story_my-chat.webm');
  assert.equal(fake.session.sessionCaptureCount, 1);
  assert.deepEqual(fake.badge, ['1']);
  await downloadCapture({ dataUrl: payload, title: 'next-chat' }, apiFor(fake));
  assert.equal(fake.session.sessionCaptureCount, 2);
  assert.equal(fake.local.captureHistory.length, 2);
});

it('given disabled auto-download then no download history or badge changes', async () => {
  const fake = fakeChrome({ autoDownload: false });
  assert.deepEqual(await downloadCapture({ dataUrl: payload }, apiFor(fake)), { skipped: true });
  assert.equal(fake.downloads.length, 0);
  assert.equal(fake.local.captureHistory, undefined);
  assert.equal(fake.badge.length, 0);
});

// Contract: cosmetic action updates must never block saving valid audio.
it('given a stalled icon update then still initiate the audio download', async () => {
  const fake = fakeChrome();
  fake.action.setIcon = () => new Promise(() => {});
  let timer;
  try {
    await Promise.race([
      downloadCapture({ dataUrl: payload }, apiFor(fake)),
      new Promise((resolve, reject) => { timer = setTimeout(() => reject(new Error('Icon blocked audio save')), 250); })
    ]);
  } finally {
    clearTimeout(timer);
  }
  assert.equal(fake.downloads.length, 1);
});

it('given invalid or non-audio payload then reject instead of downloading an error body', async () => {
  const fake = fakeChrome();
  assert.equal(audioMime('data:application/json;base64,e30='), null);
  assert.equal(audioMime('https://example.com/recording.webm'), null);
  assert.equal(audioMime('data:audio/webm;base64,AAAA'), null);
  await assert.rejects(downloadCapture({ dataUrl: 'javascript:alert(1)' }, apiFor(fake)));
  assert.equal(fake.downloads.length, 0);
});

it('given an untrusted origin frame or extension then deny capture', () => {
  const sender = { id: 'extension-id', tab: { id: 1 }, frameId: 0, url: 'https://chatgpt.com/c/example' };
  assert.equal(trustedSender(sender, 'extension-id'), true);
  assert.equal(trustedSender({ ...sender, frameId: 1 }, 'extension-id'), false);
  assert.equal(trustedSender({ ...sender, id: 'other' }, 'extension-id'), false);
  assert.equal(trustedSender({ ...sender, url: 'https://chatgpt.com.evil.example/' }, 'extension-id'), false);
});

it('given unsafe filename settings then stay inside the Downloads directory', () => {
  const filename = captureFilename({ filenameTemplate: '../{title}', subfolder: '../../nested' }, 'test', 'audio/webm');
  assert.equal(filename, 'nested/-test.webm');
});

async function pageWithResponse(response) {
  const messages = [];
  let finish;
  const captured = new Promise((resolve) => { finish = resolve; });
  class Reader {
    async readAsDataURL(blob) {
      this.result = `data:${blob.type};base64,${Buffer.from(await blob.arrayBuffer()).toString('base64')}`;
      this.onloadend();
    }
  }
  const page = {
    fetch: async () => response, location: { origin: 'https://chatgpt.com' },
    postMessage(message) { messages.push(message); finish(message); }
  };
  const context = vm.createContext({ window: page, document: { addEventListener() {} },
    FileReader: Reader, Blob, URL, console, setTimeout, clearTimeout, Date });
  for (const name of ['audio-hooks', 'page-injector']) {
    vm.runInContext(await readFile(new URL(`../src/chrome/${name}.js`, import.meta.url), 'utf8'), context);
  }
  return { page, messages, captured };
}

it('given successful fetch audio then clone original bytes without consuming playback response', async () => {
  const bytes = Buffer.alloc(1024, 7);
  const response = new Response(bytes, { headers: { 'content-type': 'audio/webm' } });
  const { page, captured } = await pageWithResponse(response);
  const returned = await page.fetch('https://chatgpt.com/backend-api/synthesize');
  assert.equal(returned, response);
  assert.deepEqual(Buffer.from(await returned.arrayBuffer()), bytes);
  const message = await captured;
  assert.equal(message.dataUrl, payload);
});

it('given HTTP 500 then return original response and never capture its JSON as audio', async () => {
  const response = new Response('{"detail":"Internal Server Error"}', {
    status: 500, headers: { 'content-type': 'application/json' }
  });
  const { page, messages } = await pageWithResponse(response);
  assert.equal(await page.fetch('https://chatgpt.com/backend-api/synthesize'), response);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(messages.length, 0);
  assert.equal(response.bodyUsed, false);
});
