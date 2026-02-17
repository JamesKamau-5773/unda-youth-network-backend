# Frontend credentialed requests (cookies)

This document shows how to call the backend endpoints that rely on the server-managed `refresh_token` cookie.

Backend requirements

- Prefer setting `SESSION_COOKIE_DOMAIN` explicitly in production (recommended). Example: `SESSION_COOKIE_DOMAIN=.undayouth.org`.
- Optionally set `FRONTEND_ORIGIN=https://undayouth.org` (or add the origin to `CORS_ORIGINS`) to enable CORS for that origin. Do NOT rely on the app to auto-derive the cookie domain from `FRONTEND_ORIGIN`.
- Ensure your deployment uses `flask` with the updated `app.py` so CORS `supports_credentials` is enabled for that origin.

Fetch example (login)

```js
fetch('https://unda-youth-network-backend.onrender.com/api/auth/login', {
  method: 'POST',
  credentials: 'include', // <-- must include to receive/save HttpOnly cookie
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
})
.then(r => r.json())
.then(data => console.log('access token', data.access_token));
```

Fetch example (refresh)

```js
fetch('https://unda-youth-network-backend.onrender.com/api/auth/refresh', {
  method: 'POST',
  credentials: 'include', // <-- must include to send HttpOnly cookie
  headers: { 'Content-Type': 'application/json' }
})
.then(r => r.json())
.then(data => console.log('new access token', data.access_token));
```

Axios example

```js
axios.post('/api/auth/login', { username, password }, { withCredentials: true })
.then(resp => console.log(resp.data));

axios.post('/api/auth/refresh', null, { withCredentials: true })
.then(resp => console.log(resp.data));
```

Notes

- Cookies issued by the server are `HttpOnly` and `Secure` with `SameSite=None` — they will only be stored and sent by the browser when `credentials: 'include'` / `withCredentials: true` is used and the page is served over HTTPS.
- Verify in browser devtools Network tab that the `Set-Cookie` header is present on the login response and that subsequent requests include a `Cookie` header.

Troubleshooting

- If you see `Missing refresh token` from `/api/auth/refresh`, the cookie wasn't sent — check the `Set-Cookie` on login and use the examples above.
- If using a wildcard `CORS_ORIGINS='*'` the server will not enable credentialed responses. Set `FRONTEND_ORIGIN` or `CORS_ORIGINS` to an explicit origin instead.
