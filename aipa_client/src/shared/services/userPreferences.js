const SETTINGS_STORAGE_PREFIX = 'aipa_user_settings_v1';
const PROMPT_HISTORY_STORAGE_PREFIX = 'aipa_prompt_history_v1';
const MAX_PROMPT_HISTORY_ITEMS = 120;

const DEFAULT_USER_SETTINGS = Object.freeze({
  twoFactorEnabled: true,
  privacySetting: 'Private',
  shareDataForTraining: false,
  faceVerificationEnabled: true,
  voiceChatEnabled: true,
});

function isStorageAvailable() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function normalizeUserKey(username) {
  const value = String(username || '').trim().toLowerCase();
  return value || 'guest';
}

function getStorageKey(prefix, username) {
  return `${prefix}:${normalizeUserKey(username)}`;
}

function safeParseJson(raw, fallback) {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch (_error) {
    return fallback;
  }
}

function normalizeBoolean(value, fallback) {
  if (typeof value === 'boolean') return value;
  return fallback;
}

function normalizePrivacySetting(value) {
  if (value === 'Private' || value === 'Semi-Private' || value === 'Public') {
    return value;
  }
  return DEFAULT_USER_SETTINGS.privacySetting;
}

function normalizePromptType(value) {
  return value === 'voice' ? 'voice' : 'text';
}

function normalizePromptStatus(value) {
  return value === 'Failed' ? 'Failed' : 'Completed';
}

function normalizePromptHistoryItem(item, index) {
  if (!item || typeof item !== 'object') {
    return null;
  }

  const content = String(item.content || '').trim();
  if (!content) {
    return null;
  }

  const createdAt = item.createdAt || new Date().toISOString();
  const tokensNumber = Number(item.tokens);

  return {
    id: String(item.id || `${Date.now()}-${index}`),
    type: normalizePromptType(item.type),
    content,
    createdAt,
    status: normalizePromptStatus(item.status),
    tokens: Number.isFinite(tokensNumber) && tokensNumber >= 0 ? Math.round(tokensNumber) : 0,
  };
}

export function getUserSettings(username) {
  if (!isStorageAvailable()) {
    return { ...DEFAULT_USER_SETTINGS };
  }

  const key = getStorageKey(SETTINGS_STORAGE_PREFIX, username);
  const raw = window.localStorage.getItem(key);
  const parsed = safeParseJson(raw, {});

  return {
    twoFactorEnabled: normalizeBoolean(parsed?.twoFactorEnabled, DEFAULT_USER_SETTINGS.twoFactorEnabled),
    privacySetting: normalizePrivacySetting(parsed?.privacySetting),
    shareDataForTraining: normalizeBoolean(parsed?.shareDataForTraining, DEFAULT_USER_SETTINGS.shareDataForTraining),
    faceVerificationEnabled: normalizeBoolean(parsed?.faceVerificationEnabled, DEFAULT_USER_SETTINGS.faceVerificationEnabled),
    voiceChatEnabled: normalizeBoolean(parsed?.voiceChatEnabled, DEFAULT_USER_SETTINGS.voiceChatEnabled),
  };
}

export function saveUserSettings(username, nextSettings) {
  const merged = {
    ...DEFAULT_USER_SETTINGS,
    ...(nextSettings || {}),
  };

  const normalized = {
    twoFactorEnabled: normalizeBoolean(merged.twoFactorEnabled, DEFAULT_USER_SETTINGS.twoFactorEnabled),
    privacySetting: normalizePrivacySetting(merged.privacySetting),
    shareDataForTraining: normalizeBoolean(merged.shareDataForTraining, DEFAULT_USER_SETTINGS.shareDataForTraining),
    faceVerificationEnabled: normalizeBoolean(merged.faceVerificationEnabled, DEFAULT_USER_SETTINGS.faceVerificationEnabled),
    voiceChatEnabled: normalizeBoolean(merged.voiceChatEnabled, DEFAULT_USER_SETTINGS.voiceChatEnabled),
  };

  if (isStorageAvailable()) {
    const key = getStorageKey(SETTINGS_STORAGE_PREFIX, username);
    window.localStorage.setItem(key, JSON.stringify(normalized));
  }

  return normalized;
}

export function patchUserSettings(username, patch) {
  const current = getUserSettings(username);
  return saveUserSettings(username, { ...current, ...(patch || {}) });
}

export function getPromptHistory(username) {
  if (!isStorageAvailable()) {
    return [];
  }

  const key = getStorageKey(PROMPT_HISTORY_STORAGE_PREFIX, username);
  const raw = window.localStorage.getItem(key);
  const parsed = safeParseJson(raw, []);

  if (!Array.isArray(parsed)) {
    return [];
  }

  return parsed
    .map((item, index) => normalizePromptHistoryItem(item, index))
    .filter(Boolean)
    .slice(0, MAX_PROMPT_HISTORY_ITEMS);
}

export function appendPromptHistory(username, item) {
  const normalized = normalizePromptHistoryItem(item, 0);
  if (!normalized) {
    return getPromptHistory(username);
  }

  const current = getPromptHistory(username);
  const next = [normalized, ...current].slice(0, MAX_PROMPT_HISTORY_ITEMS);

  if (isStorageAvailable()) {
    const key = getStorageKey(PROMPT_HISTORY_STORAGE_PREFIX, username);
    window.localStorage.setItem(key, JSON.stringify(next));
  }

  return next;
}

export function clearPromptHistory(username) {
  if (!isStorageAvailable()) {
    return;
  }
  const key = getStorageKey(PROMPT_HISTORY_STORAGE_PREFIX, username);
  window.localStorage.removeItem(key);
}
