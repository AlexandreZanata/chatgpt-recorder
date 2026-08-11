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

export const MESSAGE_TYPES = {
  STATE_CHANGE: 'STATE_CHANGE',
  AUDIO_CAPTURED: 'AUDIO_CAPTURED',
  EXTRACT_TITLE: 'EXTRACT_TITLE',
  TITLE_RESPONSE: 'TITLE_RESPONSE'
};
