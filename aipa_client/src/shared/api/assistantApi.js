import { AIPA_CONTROLL_URL } from '../config';

const CHAT_ENDPOINT = `${AIPA_CONTROLL_URL}/api/chat`;
const TRAIN_ENDPOINT = `${AIPA_CONTROLL_URL}/api/train`;
const FACE_EXTRACT_ENDPOINT = `${AIPA_CONTROLL_URL}/api/face/extract`;

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
    const message = data?.detail || data?.message || 'Không thể kết nối dịch vụ AI.';
    throw new Error(message);
  }

  return data;
}

export async function chatWithAssistantApi(payload) {
  return requestJson(CHAT_ENDPOINT, payload, 30000);
}

export async function trainAssistantApi(payload) {
  return requestJson(TRAIN_ENDPOINT, payload, 20000);
}

export async function extractFaceEmbeddingApi(payload) {
  return requestJson(FACE_EXTRACT_ENDPOINT, payload, 25000);
}
