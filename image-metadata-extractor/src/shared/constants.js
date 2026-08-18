// ChatGPT Image & Metadata Extractor — Shared Constants

export const LISTEN_URLS = [
  '*://chatgpt.com/*',
  '*://*.oaiusercontent.com/*',
  '*://*.openai.com/*'
];

export const IMAGE_MIME_MAP = {
  'image/png': '.png',
  'image/webp': '.webp',
  'image/jpeg': '.jpg',
  'image/jpg': '.jpg',
  'image/gif': '.gif'
};

export const STORAGE_KEYS = {
  AUTO_DOWNLOAD_IMAGE: 'autoDownloadImage',
  AUTO_DOWNLOAD_METADATA: 'autoDownloadMetadata',
  FILENAME_PREFIX: 'filenamePrefix',
  FILENAME_TEMPLATE: 'filenameTemplate',
  SUBFOLDER: 'subfolder'
};

export const DEFAULT_SETTINGS = {
  autoDownloadImage: true,
  autoDownloadMetadata: true,
  filenamePrefix: 'chatgpt-img',
  filenameTemplate: '{prefix}_{date}_{time}_{title}',
  subfolder: 'chatgpt-images'
};

export const EVENT_NAME = '__CHATGPT_IMAGE_METADATA_EVENT__';

export const ICONS = {
  idle: 'icons/icon-idle.svg',
  recording: 'icons/icon-recording.svg',
  saved: 'icons/icon-saved.svg',
  error: 'icons/icon-error.svg'
};
