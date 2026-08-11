// Shared constants for ChatGPT Audio Capture Extension

export const EXTENSION_STATE = {
  IDLE: 'idle',
  RECORDING: 'recording',
  SAVED: 'saved',
  ERROR: 'error'
};

export const TTS_URL_PATTERNS = [
  '*://chatgpt.com/backend-api/synthesize*',
  '*://chatgpt.com/backend-api/voice/*',
  '*://chatgpt.com/backend-api/speech*',
  '*://*.oaiusercontent.com/*'
];

export const STORAGE_KEYS = {
  AUTO_DOWNLOAD: 'autoDownload',
  FILENAME_PREFIX: 'filenamePrefix',
  SUBFOLDER: 'subfolder',
  CAPTURE_HISTORY: 'captureHistory'
};

export const DEFAULTS = {
  AUTO_DOWNLOAD: true,
  FILENAME_PREFIX: 'chatgpt-tts',
  SUBFOLDER: '',
  MAX_HISTORY: 20
};
