import axios from 'axios';
import { API_BASE_URL } from '../config/env';
import { clearStoredAuth, getStoredAuth, setStoredAuth } from '../services/authStorage';

const httpClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

const refreshClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

let refreshPromise = null;

function mergeAuthSession(currentAuth, refreshResponse) {
  return {
    accessToken: refreshResponse?.accessToken || '',
    tokenType: refreshResponse?.tokenType || currentAuth?.tokenType || 'Bearer',
    role: refreshResponse?.role || currentAuth?.role || '',
    refreshToken: refreshResponse?.refreshToken || currentAuth?.refreshToken || '',
    message: refreshResponse?.message || '',
  };
}

async function refreshAccessToken() {
  const currentAuth = getStoredAuth();
  const refreshToken = currentAuth?.refreshToken;

  if (!refreshToken) {
    throw new Error('Không tìm thấy refresh token.');
  }

  const response = await refreshClient.post('/api/auth/refresh', { refreshToken });
  const nextAuth = mergeAuthSession(currentAuth, response.data);

  if (!nextAuth.accessToken || !nextAuth.refreshToken) {
    throw new Error('Phản hồi làm mới token không hợp lệ.');
  }

  setStoredAuth(nextAuth);
  return nextAuth;
}

httpClient.interceptors.request.use((config) => {
  const auth = getStoredAuth();
  if (auth?.accessToken) {
    config.headers.Authorization = `${auth.tokenType || 'Bearer'} ${auth.accessToken}`;
  }
  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const originalRequest = error?.config;
    const requestUrl = originalRequest?.url || '';

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      originalRequest.skipAuthRefresh ||
      requestUrl.includes('/api/auth/login') ||
      requestUrl.includes('/api/auth/login-face') ||
      requestUrl.includes('/api/auth/register') ||
      requestUrl.includes('/api/auth/refresh')
    ) {
      return Promise.reject(error);
    }

    const storedAuth = getStoredAuth();
    if (!storedAuth?.refreshToken) {
      clearStoredAuth();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }

      const newAuth = await refreshPromise;
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `${newAuth.tokenType || 'Bearer'} ${newAuth.accessToken}`;
      return httpClient(originalRequest);
    } catch (refreshError) {
      clearStoredAuth();
      return Promise.reject(refreshError);
    }
  }
);

export default httpClient;
