// Tests for Image Extractor Constants and Storage Keys
import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_SETTINGS,
  IMAGE_MIME_MAP,
  STORAGE_KEYS
} from '../image-metadata-extractor/src/shared/constants.js';

test('Image Extractor — Constants & Config Tests', async (t) => {
  await t.test('should define valid image MIME types', () => {
    assert.equal(IMAGE_MIME_MAP['image/png'], '.png');
    assert.equal(IMAGE_MIME_MAP['image/webp'], '.webp');
    assert.equal(IMAGE_MIME_MAP['image/jpeg'], '.jpg');
  });

  await t.test('should have default auto-download enabled for image and metadata', () => {
    assert.equal(DEFAULT_SETTINGS.autoDownloadImage, true);
    assert.equal(DEFAULT_SETTINGS.autoDownloadMetadata, true);
    assert.equal(DEFAULT_SETTINGS.subfolder, 'chatgpt-images');
  });

  await t.test('should define complete storage keys', () => {
    assert.equal(STORAGE_KEYS.AUTO_DOWNLOAD_IMAGE, 'autoDownloadImage');
    assert.equal(STORAGE_KEYS.AUTO_DOWNLOAD_METADATA, 'autoDownloadMetadata');
  });
});
