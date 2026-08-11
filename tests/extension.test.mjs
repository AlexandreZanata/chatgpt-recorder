import { describe, it } from 'node:test';
import assert from 'node:assert';
import { EXTENSION_STATE, interpolateTemplate, STORAGE_KEYS, DEFAULTS } from '../src/shared/constants.js';

describe('ChatGPT Audio Capture — Task 12 Template Engine Tests', () => {
  it('should define template constants and storage keys', () => {
    assert.strictEqual(EXTENSION_STATE.IDLE, 'idle');
    assert.strictEqual(STORAGE_KEYS.FILENAME_TEMPLATE, 'filenameTemplate');
    assert.strictEqual(DEFAULTS.FILENAME_TEMPLATE, '{prefix}_{date}_{title}');
  });

  it('should interpolate template placeholders correctly', () => {
    const tmpl = '{prefix}_{title}';
    const vars = { prefix: 'test-prefix', title: 'sample-audio' };
    const res = interpolateTemplate(tmpl, vars);
    assert.strictEqual(res, 'test-prefix_sample-audio');
  });
});
