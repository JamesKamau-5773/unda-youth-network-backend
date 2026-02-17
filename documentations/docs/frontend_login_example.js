// Minimal frontend example demonstrating login using the `api` axios instance
// that automatically attaches a Bearer token (see API_BEARER_AUTH.md).

import api, { setAccessToken } from './api_instance';

async function login(username, password) {
  try {
    const resp = await api.post('/auth/login', { username, password });
    const token = resp.data && resp.data.access_token;
    if (token) {
      setAccessToken(token);
      // Now you can call protected endpoints via `api`
      return resp.data.user;
    }
    throw new Error('No access token in login response');
  } catch (err) {
    // Handle and surface sanitized errors per UI policy
    if (err.response) {
      const status = err.response.status;
      if (status === 400 || status === 401) throw new Error('Incorrect username or password.');
      if (status === 403) throw new Error('Account access restricted.');
    }
    throw new Error('Unable to connect to server. Please try again later.');
  }
}

export default login;
