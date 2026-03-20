import { API_BASE_URL, AIPA_CONTROLL_URL } from '../config';

const CHAT_ENDPOINT = `${AIPA_CONTROLL_URL}/api/chat`;
const TRAIN_ENDPOINT = `${AIPA_CONTROLL_URL}/api/train`;
const CORE_BASE_URL = String(API_BASE_URL || '').replace(/\/$/, '');
// Route face extraction through aipa_core to avoid CORS issues and to support remote clients.
const FACE_EXTRACT_ENDPOINT = `${CORE_BASE_URL}/api/face/extract`;
const HEALTH_ENDPOINT = `${AIPA_CONTROLL_URL}/health`;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const looksLikeNetworkError = (error) => {
  if (!error) return false;
  if (error.name === 'AbortError') return true;
  if (error instanceof TypeError) return true;
  const message = String(error.message || '').toLowerCase();
  return (
    message.includes('failed to fetch') ||
    message.includes('networkerror') ||
    message.includes('network request failed') ||
    message.includes('load failed') ||
    message.includes('timed out')
  );
};

async function isControllServiceReady() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 3500);
  try {
    const response = await fetch(HEALTH_ENDPOINT, {
      method: 'GET',
      signal: controller.signal,
    });
    return response.ok;
  } catch (_error) {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

async function requestJson(url, payload, timeoutMs = 30000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = data?.detail || data?.message || 'Kh\u00f4ng th\u1ec3 k\u1ebft n\u1ed1i d\u1ecbch v\u1ee5 AI.';
    throw new Error(message);
  }

  return data;
}

export async function chatWithAssistantApi(payload) {
  const maxAttempts = 7;
  let lastError;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await requestJson(CHAT_ENDPOINT, payload, 30000);
    } catch (error) {
      lastError = error;
      const shouldRetry = looksLikeNetworkError(error) && attempt < maxAttempts;
      if (!shouldRetry) {
        throw error;
      }

      const ready = await isControllServiceReady();
      if (!ready) {
        await sleep(Math.min(2000 * attempt, 5000));
      } else {
        await sleep(500);
      }
    }
  }

  throw lastError || new Error('Khong the ket noi dich vu AI.');
}

export async function trainAssistantApi(payload) {
  return requestJson(TRAIN_ENDPOINT, payload, 20000);
}

export async function extractFaceEmbeddingApi(payload) {
  return requestJson(FACE_EXTRACT_ENDPOINT, payload, 25000);
}

