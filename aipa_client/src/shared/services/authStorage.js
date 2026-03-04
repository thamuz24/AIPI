const AUTH_STORAGE_KEY = 'aipa_controll';
const LEGACY_AUTH_STORAGE_KEY = 'aipa_auth';

function parseAuth(raw) {
  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch (_error) {
    return null;
  }
}

export function getStoredAuth() {
  const currentRaw = localStorage.getItem(AUTH_STORAGE_KEY);
  const currentAuth = parseAuth(currentRaw);

  if (currentRaw && !currentAuth) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }

  if (currentAuth) return currentAuth;

  const legacyRaw = localStorage.getItem(LEGACY_AUTH_STORAGE_KEY);
  const legacyAuth = parseAuth(legacyRaw);

  if (legacyRaw && !legacyAuth) {
    localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY);
  }

  if (legacyAuth) {
    setStoredAuth(legacyAuth);
    localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY);
    return legacyAuth;
  }

  return null;
}

export function setStoredAuth(auth) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
}

export function clearStoredAuth() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
  localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY);
}
