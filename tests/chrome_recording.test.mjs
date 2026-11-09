import { it } from 'node:test';
import assert from 'node:assert/strict';
import { recordingCommand, recordingState, downloadChanged, suppressAutomatic } from '../src/chrome/recording-controller.js';
import { downloadRecording } from '../src/chrome/downloads.js';

// Contract: docs/CHROME-EXTENSION.md complete-tab recording and completion/retry.
const root = 'chrome-extension://test-extension/';
const popup = { id: 'test-extension', url: `${root}popup.html` };
const recorder = { id: 'test-extension', url: `${root}src/chrome/recorder.html` };

function fakeApi() {
  const local = { autoDownload: false };
  const session = {};
  const calls = [];
  const store = (state) => ({
    async get(keys) { return typeof keys === 'string' ? { [keys]: state[keys] } : { ...keys, ...state }; },
    async set(values) { Object.assign(state, values); }
  });
  const api = {
    local, session, calls, storage: { local: store(local), session: store(session) },
    runtime: {
      id: 'test-extension', getURL: (path) => `${root}${path}`,
      async sendMessage(message) { calls.push(message); return { state: 'recording' }; }
    },
    tabs: { async query() { return [{ id: 4, url: 'https://chatgpt.com/c/test', title: 'Test chat' }]; } },
    offscreen: { async hasDocument() { return false; }, async createDocument() {}, async closeDocument() {} },
    tabCapture: { async getMediaStreamId() { return 'native-stream'; } },
    action: { async setBadgeText() {}, async setBadgeBackgroundColor() {}, async setIcon() {} },
    downloads: { async download(details) { calls.push(details); return 12; } }
  };
  return api;
}

async function recorded(api) {
  const entry = await recordingCommand({ type: 'RECORDER_START' }, popup, api);
  return { type: 'RECORDER_FINISHED', sessionId: entry.sessionId,
    url: `blob:${root}recording`, mime: 'audio/webm', size: 1024 };
}

it('given a page or another extension then recording commands cannot request tab capture', async () => {
  const api = fakeApi();
  for (const sender of [{ id: 'other', url: popup.url },
    { id: popup.id, url: 'https://chatgpt.com/', tab: { id: 4 } }]) {
    assert.deepEqual(await recordingCommand({ type: 'RECORDER_START' }, sender, api), {});
  }
  assert.deepEqual(api.session, {});
  assert.equal(api.calls.length, 0);
});

it('given manual recording then suppress only that tab and reject a second start', async () => {
  const api = fakeApi();
  await recorded(api);
  assert.equal(await suppressAutomatic({ tab: { id: 4 } }, api), true);
  assert.equal(await suppressAutomatic({ tab: { id: 5 } }, api), false);
  await assert.rejects(recordingCommand({ type: 'RECORDER_START' }, popup, api), /Save the current/);
});

it('given auto-download disabled then explicit manual save still starts a pending download', async () => {
  const api = fakeApi();
  const message = await recorded(api);
  const result = await recordingCommand(message, recorder, api);
  assert.equal(result.state, 'saving');
  assert.equal(result.downloadId, 12);
  assert.equal(api.local.captureHistory[0].status, 'pending');
  assert.equal(api.calls.find((call) => call.url).url, message.url);
});

it('given interrupted recording download then retain the original Blob for retry after worker restart', async () => {
  const api = fakeApi();
  const message = await recorded(api);
  await recordingCommand(message, recorder, api);
  await downloadChanged({ id: 12, state: { current: 'interrupted' }, error: { current: 'FILE_NO_SPACE' } }, api);
  assert.equal((await recordingState(api)).state, 'error');
  assert.equal((await recordingState(api)).url, message.url);
  const retried = await recordingCommand({ type: 'RECORDER_RETRY' }, popup, api);
  assert.equal(retried.state, 'saving');
  assert.equal(api.calls.filter((call) => call.url === message.url).length, 2);
});

it('given completed recording download then release the Blob and report saved', async () => {
  const api = fakeApi();
  const message = await recorded(api);
  await recordingCommand(message, recorder, api);
  await downloadChanged({ id: 12, state: { current: 'complete' } }, api);
  assert.equal((await recordingState(api)).state, 'saved');
  assert.equal((await recordingState(api)).url, undefined);
  assert.equal(api.local.captureHistory[0].status, 'complete');
  assert.equal(api.calls.at(-1).type, 'RECORDER_RELEASE');
});

it('given a page-supplied Blob or forged completion then never download it as a recording', async () => {
  const api = fakeApi();
  await assert.rejects(downloadRecording({ url: 'blob:https://chatgpt.com/forged', mime: 'audio/webm' }, api));
  const message = await recorded(api);
  assert.deepEqual(await recordingCommand(message, popup, api), {});
  assert.equal(api.calls.filter((call) => call.url).length, 0);
});
