````markdown
# Frontend Integration Guide
## UMV Backend API - Local Development Setup

---

## Quick Start

### 1. Backend is Ready
The backend API is already configured for local development with:
- OK CORS enabled for `localhost` origins
- OK All privacy-first endpoints operational
- OK Session/cookie authentication working
- OK Health check endpoints available

### 2. Backend URL
```
http://localhost:5000
```

### 3. Test Backend Connectivity
```bash
# Test 1: Health check (no auth required)
curl http://localhost:5000/api/health

# Test 2: API status (no auth required)
curl http://localhost:5000/api/status

# Test 3: CORS test
curl -H "Origin: http://localhost:3000" http://localhost:5000/api/cors-test
```

Expected response from `/api/health`:
```json
{
  "status": "ok",
  "timestamp": "2026-01-14T10:30:00.000000",
  "service": "UMV Backend API",
  "version": "2.0.0-privacy-first",
  "database": "healthy"
}
```

---

## Authentication Flow

### Frontend Configuration
```javascript
// Configure axios or fetch with credentials
const api = axios.create({
  baseURL: 'http://localhost:5000',
  withCredentials: true, // CRITICAL: Enable cookies/sessions
  headers: {
    'Content-Type': 'application/json'
  }
});
```

### Login Flow
```javascript
// Step 1: Login (creates session cookie)
const login = async (username, password) => {
  const response = await api.post('/auth/login', {
    username,
    password
  });
  
  // Session cookie automatically set by backend
  // No need to manually store tokens
  return response.data;
};

// Step 2: Get current user info
const getCurrentUser = async () => {
  const response = await api.get('/api/me');
  return response.data.user;
  // Returns: { user_id, username, role, champion_id }
};

// Step 3: Logout
const logout = async () => {
  await api.post('/auth/logout');
};
```

---

## Members Portal API Endpoints

### 1. Prevention Advocate Registration (Public - No Auth)
```javascript
const registerChampion = async (formData) => {
  const response = await api.post('/api/prevention advocates/register', {
    first_name: formData.firstName,
    last_name: formData.lastName,
    date_of_birth: formData.dob, // YYYY-MM-DD
    gender: formData.gender,
    location: formData.location,
    phone: formData.phone,
    email: formData.email,
    emergency_contact_name: formData.emergencyName,
    emergency_contact_phone: formData.emergencyPhone,
    consent_given: true
  });
  
  // CRITICAL: Save champion_code!
  const { champion_code } = response.data;
  // Display to user: "Save this code: UMV-2026-000001"
  
  return response.data;
};
```

**Response:**
```json
{
  "success": true,
  "message": "Prevention Advocate registered successfully",
  "champion_code": "UMV-2026-000001",
  "warning": "Please save this code. You will need it for assessments."
}
```

... (content preserved) ...

````