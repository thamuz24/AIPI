import httpClient from './httpClient';

export async function fetchAdminUsersApi() {
  const response = await httpClient.get('/api/admin/users');
  return response.data;
}

export async function fetchAdminBanLogsApi() {
  const response = await httpClient.get('/api/admin/users/ban-logs');
  return response.data;
}

export async function banUserApi(userId, payload) {
  const response = await httpClient.patch(`/api/admin/users/${userId}/ban`, payload);
  return response.data;
}
