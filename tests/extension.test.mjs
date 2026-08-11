import { describe, it } from 'node:test';
import assert from 'node:assert';
import { EXTENSION_STATE, TTS_URL_PATTERNS, MIME_EXTENSION_MAP } from '../src/shared/constants.js';

describe('ChatGPT Audio Capture — Task 09 MIME & Badge Tests', () => {
  it('should define valid extension states and MIME mappings', () => {
    assert.strictEqual(EXTENSION_STATE.IDLE, 'idle');
    assert.strictEqual(MIME_EXTENSION_MAP['audio/mpeg'], '.mp3');
    assert.strictEqual(MIME_EXTENSION_MAP['audio/wav'], '.wav');
    assert.strictEqual(MIME_EXTENSION_MAP['audio/ogg'], '.ogg');
  });

  it('should include target TTS URL patterns', () => {
    assert.ok(TTS_URL_PATTERNS.includes('*://chatgpt.com/backend-api/synthesize*'));
  });

  it('should resolve correct extension for MIME type', () => {
    const getExt = (mime) => MIME_EXTENSION_MAP[mime] || '.mp3';
    assert.strictEqual(getExt('audio/wav'), '.wav');
    assert.strictEqual(getExt('audio/mpeg'), '.mp3');
    assert.strictEqual(getExt('unknown/format'), '.mp3');
  });
});
