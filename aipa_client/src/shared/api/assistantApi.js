import { API_BASE_URL, AIPA_CONTROLL_URL } from '../config';

const CHAT_ENDPOINT = `${AIPA_CONTROLL_URL}/api/chat`;
const TRAIN_ENDPOINT = `${AIPA_CONTROLL_URL}/api/train`;
const COMPUTER_CONTROL_SAVE_ENDPOINT = `${AIPA_CONTROLL_URL}/api/computer-control/save`;
const COMPUTER_CONTROL_RULES_ENDPOINT = `${AIPA_CONTROLL_URL}/api/computer-control/rules`;
const COMPUTER_CONTROL_GRID_ENDPOINT = `${AIPA_CONTROLL_URL}/api/computer-control/grid`;
const COMPUTER_CONTROL_OVERLAY_STATUS_ENDPOINT = `${AIPA_CONTROLL_URL}/api/computer-control/overlay/status`;
const COMPUTER_CONTROL_OVERLAY_SHOW_ENDPOINT = `${AIPA_CONTROLL_URL}/api/computer-control/overlay/show`;
const COMPUTER_CONTROL_OVERLAY_HIDE_ENDPOINT = `${AIPA_CONTROLL_URL}/api/computer-control/overlay/hide`;
const CORE_BASE_URL = String(API_BASE_URL || '').replace(/\/$/, '');
// Route face extraction through aipa_core to avoid CORS issues and to support remote clients.
const FACE_EXTRACT_ENDPOINT = `${CORE_BASE_URL}/api/face/extract`;
const HEALTH_ENDPOINT = `${AIPA_CONTROLL_URL}/health`;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const extractErrorMessage = (payload) => {
  if (!payload) return '';
  if (typeof payload === 'string') {
    const value = payload.trim();
    return value === '[object Object]' ? '' : value;
  }

  if (Array.isArray(payload)) {
    for (const item of payload) {
      const message = extractErrorMessage(item);
      if (message) return message;
    }
    return '';
  }

  if (typeof payload === 'object') {
    for (const key of ['message', 'detail', 'error', 'title', 'description', 'defaultMessage']) {
      const message = extractErrorMessage(payload?.[key]);
      if (message) return message;
    }

    if (typeof payload?.field === 'string' && typeof payload?.defaultMessage === 'string') {
      return `${payload.field}: ${payload.defaultMessage}`.trim();
    }

    for (const value of Object.values(payload)) {
      const message = extractErrorMessage(value);
      if (message) return message;
    }
  }

  return '';
};

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
    const message = extractErrorMessage(data) || 'Kh\u00f4ng th\u1ec3 k\u1ebft n\u1ed1i d\u1ecbch v\u1ee5 AI.';
    throw new Error(message);
  }

  return data;
}

async function requestGetJson(url, timeoutMs = 20000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response;
  try {
    response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data?.detail || data?.message || 'Không thể lấy dữ liệu hướng dẫn.';
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

export async function saveComputerControlRuleApi(payload) {
  return requestJson(COMPUTER_CONTROL_SAVE_ENDPOINT, payload, 25000);
}

export async function fetchComputerControlRulesApi() {
  return requestGetJson(COMPUTER_CONTROL_RULES_ENDPOINT, 20000);
}

export async function fetchComputerControlGridApi() {
  return requestGetJson(COMPUTER_CONTROL_GRID_ENDPOINT, 20000);
}

export async function fetchComputerControlOverlayStatusApi() {
  return requestGetJson(COMPUTER_CONTROL_OVERLAY_STATUS_ENDPOINT, 15000);
}

export async function showComputerControlOverlayApi(payload = {}) {
  return requestJson(COMPUTER_CONTROL_OVERLAY_SHOW_ENDPOINT, payload, 20000);
}

export async function hideComputerControlOverlayApi() {
  return requestJson(COMPUTER_CONTROL_OVERLAY_HIDE_ENDPOINT, {}, 15000);
}

export async function extractFaceEmbeddingApi(payload) {
  return requestJson(FACE_EXTRACT_ENDPOINT, payload, 25000);
}

