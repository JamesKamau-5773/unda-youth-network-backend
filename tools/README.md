# Tools

This folder contains small utilities to help the frontend and local testing.

## frontend_helpers.js

- Location: `tools/frontend_helpers.js`
- Exports:
  - `normalizePhone(phone)` — normalize Kenyan phone numbers to +254 format when possible.
  - `formatDateYYYYMMDD(value)` — format Date or date-string to `YYYY-MM-DD`.
  - `registerMember(payload, baseUrl)` — example `fetch` call to `POST /api/auth/register`.
  - `registerChampion(payload, baseUrl)` — example `fetch` call to `POST /api/champions/register`.
  - `applyChampionLegacy(payload, baseUrl)` — wrapper for legacy `/api/champion/apply`.
  - `isValidPhoneForChampion(phone)` and `isValidDateYYYYMMDD(value)` — simple client validators.

Copy the functions into your frontend `apiService.js` or import when bundling. `baseUrl` defaults to `''` (same origin).

## Run local smoke tests

1. Start the app locally (SQLite example):

```bash
export DATABASE_URL=sqlite:///dev_local.db
pip install -r requirements.txt
# Start the app (project may use run.sh or flask run)
bash run.sh
```

2. Member registration smoke test (curl):

```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"full_name":"Test User","phone_number":"0712345678","username":"testuser1","password":"P@ssw0rd1"}' \
  http://127.0.0.1:5000/api/auth/register | jq
```

3. Champion self-registration smoke test (curl):

```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"full_name":"Champ One","phone_number":"0712345678","gender":"Female","date_of_birth":"2000-01-01","county_sub_county":"Nairobi","consent_obtained":true}' \
  http://127.0.0.1:5000/api/champions/register | jq
```

4. Poll registration status:

```bash
curl -s http://127.0.0.1:5000/api/auth/registration/<registration_id> | jq
```

Replace `127.0.0.1:5000` with your app host if different.

If you want, I can attempt to run the curl tests here — I would need the app started in this environment.
