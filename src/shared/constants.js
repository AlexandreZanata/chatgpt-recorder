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

export const MIME_EXTENSION_MAP = {
  'audio/mpeg': '.mp3',
  'audio/mp3': '.mp3',
  'audio/wav': '.wav',
  'audio/ogg': '.ogg',
  'audio/aac': '.aac',
  'audio/webm': '.webm'
};

export const STORAGE_KEYS = {
  AUTO_DOWNLOAD: 'autoDownload',
  FILENAME_PREFIX: 'filenamePrefix',
  FILENAME_TEMPLATE: 'filenameTemplate',
  SUBFOLDER: 'subfolder',
  CAPTURE_HISTORY: 'captureHistory'
};

export const DEFAULTS = {
  AUTO_DOWNLOAD: true,
  FILENAME_PREFIX: 'chatgpt-tts',
  FILENAME_TEMPLATE: '{prefix}_{date}_{title}',
  SUBFOLDER: '',
  MAX_HISTORY: 20
};

export function interpolateTemplate(template, vars) {
  const now = new Date();
  const dateStr = now.toISOString().split('T')[0];
  const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '-');
  const fmt = template || DEFAULTS.FILENAME_TEMPLATE;
  return fmt
    .replace(/\{prefix\}/g, vars.prefix || DEFAULTS.FILENAME_PREFIX)
    .replace(/\{date\}/g, dateStr)
    .replace(/\{time\}/g, timeStr)
    .replace(/\{title\}/g, vars.title || 'audio');
}
