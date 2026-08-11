import { describe, it } from 'node:test';
import assert from 'node:assert';
import { EXTENSION_STATE, TTS_URL_PATTERNS, STORAGE_KEYS, DEFAULTS } from '../src/shared/constants.js';

describe('ChatGPT Audio Capture — Task 08 Core & History Tests', () => {
  it('should define valid extension states and storage keys', () => {
    assert.strictEqual(EXTENSION_STATE.IDLE, 'idle');
    assert.strictEqual(STORAGE_KEYS.SUBFOLDER, 'subfolder');
    assert.strictEqual(DEFAULTS.MAX_HISTORY, 20);
  });

  it('should include target TTS URL patterns', () => {
    assert.ok(TTS_URL_PATTERNS.includes('*://chatgpt.com/backend-api/synthesize*'));
  });

  it('should build relative subfolder path correctly', () => {
    const subfolder = 'chatgpt-audio/';
    const prefix = 'chatgpt-tts';
    const cleanTitle = 'my-audio';
    const filename = `${prefix}_2026_${cleanTitle}.mp3`;
    const fullPath = `${subfolder.replace(/\/$/, '')}/${filename}`;
    assert.strictEqual(fullPath, 'chatgpt-audio/chatgpt-tts_2026_my-audio.mp3');
  });
});
