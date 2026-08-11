import { describe, it } from 'node:test';
import assert from 'node:assert';
import { EXTENSION_STATE, TTS_URL_PATTERNS } from '../src/shared/constants.js';

describe('ChatGPT Audio Capture — Extension Core Tests', () => {
  it('should define valid extension states', () => {
    assert.strictEqual(EXTENSION_STATE.IDLE, 'idle');
    assert.strictEqual(EXTENSION_STATE.RECORDING, 'recording');
    assert.strictEqual(EXTENSION_STATE.SAVED, 'saved');
  });

  it('should include target TTS URL patterns for network interception', () => {
    assert.ok(TTS_URL_PATTERNS.includes('*://chatgpt.com/backend-api/synthesize*'));
    assert.ok(TTS_URL_PATTERNS.includes('*://*.oaiusercontent.com/*'));
  });

  it('should format clean file names', () => {
    const rawTitle = '  My Awesome ChatGPT Audio!  ';
    const cleanTitle = rawTitle
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .slice(0, 35);
    assert.strictEqual(cleanTitle, 'my-awesome-chatgpt-audio');
  });
});
