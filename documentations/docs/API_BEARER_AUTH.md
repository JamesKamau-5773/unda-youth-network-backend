API Bearer Authentication
=========================

This document shows how to use the existing API login endpoint to obtain an
`access_token` (JWT) and use it for subsequent authenticated API requests.

1) Login (request JSON, receives `access_token` in JSON response)

Example (curl):

```bash
curl -X POST 'https://your-backend.example.com/api/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"username":"mica","password":"ABcd@123"}'
```

Response body (JSON):

```json
{
  "access_token": "<JWT_TOKEN>",
  "user": {"user_id":..., "username":"mica", ...}
}
```

2) Use `Authorization: Bearer` for subsequent requests

Axios example (recommended for XHR / SPA clients):

```javascript
// After receiving login response:
const token = response.data.access_token;

// Attach to subsequent requests
axios.get('/api/some/protected', {
  baseURL: 'https://unda-youth-network-backend.onrender.com',
  headers: {
    Authorization: `Bearer ${token}`
  }
}).then(resp => console.log(resp.data));
```

Notes:
- The API already supports Bearer JWT tokens. Using Bearer tokens avoids cross-site cookie
  SameSite/CSRF complexity for SPAs.
- The server also issues a `refresh_token` cookie for long-lived refresh flow; that cookie is
  HttpOnly and requires credentialed CORS if you want the browser to send it automatically.
- If you prefer session cookies, ensure the frontend uses `withCredentials: true` and your
  `CORS_ORIGINS` is set to the exact frontend origin (not `*`).

If you want, I can add a short frontend patch showing how to store the token (e.g., memory or
`localStorage`) and automatically attach it with an Axios interceptor.

Axios interceptor (automatic attach + 401 handler)
-----------------------------------------------

This pattern stores the token in memory or `localStorage` and automatically
attaches it to outgoing requests. It also shows a simple 401 handler to
optionally attempt a refresh or redirect to login.

```javascript
import axios from 'axios';

// Simple token storage (use memory in SPAs for better security)
let accessToken = null;
export function setAccessToken(token) { accessToken = token; }
export function clearAccessToken() { accessToken = null; }

// Create an axios instance for the API
const api = axios.create({
  baseURL: 'https://unda-youth-network-backend.onrender.com',
  headers: { 'Accept': 'application/json' }
});

// Request interceptor: attach Bearer token when present
api.interceptors.request.use(config => {
  if (accessToken) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// Response interceptor: handle 401 globally
api.interceptors.response.use(
  res => res,
  async err => {
    if (err.response && err.response.status === 401) {
      // Optional: attempt refresh flow (call /api/auth/refresh)
      // If you rely on the refresh_token cookie, ensure your frontend
      // uses `withCredentials: true` and CORS origin is exact.

      // Fallback: clear token and redirect to login
      clearAccessToken();
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;
```

Security notes:
- Prefer keeping tokens in memory; `localStorage` is persistent but exposed to XSS.
- Use `withCredentials: true` only if you intend to use the server-managed `refresh_token` cookie.

