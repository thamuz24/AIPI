import httpClient from './httpClient';

export async function fetchMeApi() {
  const response = await httpClient.get('/api/user/me');
  return response.data;
}

export async function updateProfileApi(payload) {
  const response = await httpClient.put('/api/user/profile', payload);
  return response.data;
}
