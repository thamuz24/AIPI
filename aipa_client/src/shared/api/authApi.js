import httpClient from './httpClient';

export async function loginApi(payload) {
  const response = await httpClient.post('/api/auth/login', payload);
  return response.data;
}

export async function loginByFaceApi(payload) {
  const response = await httpClient.post('/api/auth/login-face', payload);
  return response.data;
}

export async function registerApi(payload) {
  const response = await httpClient.post('/api/auth/register', payload);
  return response.data;
}

export async function refreshTokenApi(payload) {
  const response = await httpClient.post('/api/auth/refresh', payload, { skipAuthRefresh: true });
  return response.data;
}
