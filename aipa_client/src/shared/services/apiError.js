import axios from 'axios';

function extractMessageFromPayload(payload) {
  if (!payload) return '';

  if (typeof payload === 'string') {
    const value = payload.trim();
    return value === '[object Object]' ? '' : value;
  }

  if (Array.isArray(payload)) {
    for (const item of payload) {
      const message = extractMessageFromPayload(item);
      if (message) return message;
    }
    return '';
  }

  if (typeof payload === 'object') {
    for (const key of ['message', 'detail', 'error', 'title', 'description', 'defaultMessage']) {
      const message = extractMessageFromPayload(payload?.[key]);
      if (message) return message;
    }

    if (typeof payload?.field === 'string' && typeof payload?.defaultMessage === 'string') {
      return `${payload.field}: ${payload.defaultMessage}`.trim();
    }

    for (const value of Object.values(payload)) {
      const message = extractMessageFromPayload(value);
      if (message) return message;
    }
  }

  return '';
}

export function getApiErrorMessage(error, fallbackMessage = 'Có lỗi xảy ra. Vui lòng thử lại.') {
  if (!error) return fallbackMessage;

  if (axios.isAxiosError(error)) {
    const responseMessage = extractMessageFromPayload(error.response?.data);
    if (responseMessage) {
      return responseMessage;
    }

    if (error.response?.status === 401) {
      return 'Thông tin đăng nhập không hợp lệ.';
    }

    if (error.code === 'ECONNABORTED') {
      return 'Yêu cầu hết thời gian. Vui lòng thử lại.';
    }

    return 'Không thể kết nối đến aipa_core. Hãy kiểm tra backend và biến REACT_APP_API_BASE_URL.';
  }

  const rawMessage = String(error?.message || '');
  const lowerMessage = rawMessage.toLowerCase();
  if (
    lowerMessage.includes('failed to fetch') ||
    lowerMessage.includes('networkerror') ||
    lowerMessage.includes('network request failed') ||
    lowerMessage.includes('load failed') ||
    lowerMessage.includes('timed out')
  ) {
    return 'KhĂ´ng thá»ƒ káº¿t ná»‘i backend. HĂ£y kiá»ƒm tra aipa_core (:8080) vĂ  aipa_controll (:8001).';
  }

  if (error instanceof Error && error.message) {
    if (error.message === '[object Object]') {
      const objectMessage = extractMessageFromPayload(error);
      if (objectMessage && objectMessage !== '[object Object]') {
        return objectMessage;
      }
    }
    return error.message;
  }

  const payloadMessage = extractMessageFromPayload(error);
  if (payloadMessage) {
    return payloadMessage;
  }

  return fallbackMessage;
}
