# Frontend Integration Guide
## UMV Backend API - Local Development Setup

---

## Quick Start

### 1. Backend is Ready ✅
The backend API is already configured for local development with:
- ✅ CORS enabled for `localhost` origins
- ✅ All privacy-first endpoints operational
- ✅ Session/cookie authentication working
- ✅ Health check endpoints available

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

### 2. Verify Prevention Advocate Code (Public - No Auth)
```javascript
const verifyChampionCode = async (code) => {
  const response = await api.post('/api/prevention advocates/verify-code', {
    champion_code: code
  });
  
  return response.data.valid; // true/false
};
```

### 3. Submit Mental Health Assessment (Requires Prevention Advocate Auth)
```javascript
const submitAssessment = async (assessmentData) => {
  const response = await api.post('/api/assessments/submit', {
    champion_code: assessmentData.championCode,
    assessment_type: 'PHQ-9', // or 'GAD-7'
    raw_score: assessmentData.totalScore, // 0-27 for PHQ-9, 0-21 for GAD-7
    notes: assessmentData.notes // optional
  });
  
  return response.data;
};
```

**Request Example:**
```json
{
  "champion_code": "UMV-2026-000001",
  "assessment_type": "PHQ-9",
  "raw_score": 18,
  "notes": "Follow-up needed"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Assessment submitted successfully",
  "assessment": {
    "assessment_id": 123,
    "champion_code": "UMV-2026-000001",
    "assessment_type": "PHQ-9",
    "risk_category": "Orange",
    "score_range": "15-19",
    "date_taken": "2026-01-14",
    "auto_flag": true,
    "auto_referral": true
  }
}
```

**Risk Categories:**
- 🟢 **Green** (0-4): Minimal depression/anxiety
- 🔵 **Blue** (5-9): Mild symptoms
- 🟣 **Purple** (10-14): Moderate symptoms
- 🟠 **Orange** (15-19): Moderately severe (PHQ-9 only, auto-referral)
- 🔴 **Red** (20-27 PHQ-9 / 15-21 GAD-7): Severe (auto-referral)

### 4. View My Submissions (Prevention Advocate)
```javascript
const getMySubmissions = async () => {
  const response = await api.get('/api/assessments/my-submissions');
  return response.data.assessments;
};
```

**Response:**
```json
{
  "success": true,
  "assessments": [
    {
      "assessment_id": 123,
      "champion_code": "UMV-2026-000001",
      "assessment_type": "PHQ-9",
      "risk_category": "Orange",
      "score_range": "15-19",
      "date_taken": "2026-01-14T10:30:00",
      "notes": "Follow-up needed"
    }
  ]
}
```

### 5. Assessment Dashboard (Supervisor/Admin)
```javascript
const getDashboard = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.startDate) params.append('start_date', filters.startDate);
  if (filters.endDate) params.append('end_date', filters.endDate);
  if (filters.riskCategory) params.append('risk_category', filters.riskCategory);
  
  const response = await api.get(`/api/assessments/dashboard?${params}`);
  return response.data;
};
```

**Response:**
```json
{
  "success": true,
  "statistics": {
    "total_assessments": 150,
    "by_type": {
      "PHQ-9": 80,
      "GAD-7": 70
    },
    "by_risk_category": {
      "Green": 45,
      "Blue": 50,
      "Purple": 30,
      "Orange": 15,
      "Red": 10
    },
    "auto_referrals": 25,
    "unique_champions": 120
  }
}
```

---

## Error Handling

### Standard Error Response
```json
{
  "success": false,
  "error": "Error message here"
}
```

### Common Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad request (validation error)
- `401`: Unauthorized (not logged in)
- `403`: Forbidden (wrong role)
- `404`: Not found
- `500`: Server error

### Example Error Handler
```javascript
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    
    const message = error.response?.data?.error || 'An error occurred';
    console.error('API Error:', message);
    
    return Promise.reject(error);
  }
);
```

---

## Role-Based Access Control

### Roles & Permissions
| Endpoint | Admin | Supervisor | Prevention Advocate | Public |
|----------|-------|------------|---------------------|--------|
| `/api/prevention advocates/register` | ✅ | ✅ | ✅ | ✅ |
| `/api/prevention advocates/verify-code` | ✅ | ✅ | ✅ | ✅ |
| `/api/assessments/submit` | ✅ | ✅ | ✅ | ❌ |
| `/api/assessments/my-submissions` | ✅ | ✅ | ✅ | ❌ |
| `/api/assessments/dashboard` | ✅ | ✅ | ❌ | ❌ |
| `/api/me` | ✅ | ✅ | ✅ | ❌ |

### Check User Role
```javascript
const user = await getCurrentUser();

if (user.role === 'Prevention Advocate') {
  // Show assessment submission form
} else if (user.role === 'Supervisor') {
  // Show dashboard
} else if (user.role === 'Admin') {
  // Show full admin panel
}
```

---

## Privacy Compliance

### What Frontend Should NOT Display
- ❌ Raw assessment scores (PHQ-9/GAD-7 numbers)
- ❌ Prevention Advocate personal information alongside assessment results
- ❌ Individual assessment details to supervisors (only aggregated stats)

### What Frontend SHOULD Display
- ✅ Risk categories (Green/Blue/Purple/Orange/Red) as colors
- ✅ Prevention Advocate codes (UMV-YYYY-NNNNNN)
- ✅ Auto-referral flags
- ✅ Aggregated statistics (counts, percentages)
- ✅ Score ranges (0-4, 5-9, etc.) instead of exact scores

### Privacy-First UI Examples
```javascript
// Good: Display risk category as color
const getRiskColor = (category) => {
  const colors = {
    'Green': '#22c55e',
    'Blue': '#3b82f6',
    'Purple': '#a855f7',
    'Orange': '#f97316',
    'Red': '#ef4444'
  };
  return colors[category];
};

// Good: Show score range, not exact score
<div className="assessment-card">
  <span className="risk-badge" style={{ backgroundColor: getRiskColor(assessment.risk_category) }}>
    {assessment.risk_category}
  </span>
  <span className="score-range">{assessment.score_range}</span>
  {assessment.auto_referral && <span className="referral-flag">Auto-Referral</span>}
</div>

// Bad: Don't do this
<div>Raw Score: {assessment.total_score}</div> // ❌ Backend won't return this anyway
```

---

## Testing Checklist

### Before Integration
- [ ] Backend running: `http://localhost:5000`
- [ ] Health check passes: `curl http://localhost:5000/api/health`
- [ ] CORS test passes: `curl -H "Origin: http://localhost:3000" http://localhost:5000/api/cors-test`

### During Integration
- [ ] Login sets session cookie (check browser DevTools → Application → Cookies)
- [ ] `withCredentials: true` set in axios/fetch
- [ ] Prevention Advocate registration returns `champion_code`
- [ ] Assessment submission returns risk category (not raw score)
- [ ] Logout clears session

### Privacy Validation
- [ ] No raw scores visible in UI
- [ ] No prevention advocate names visible alongside assessments
- [ ] Only aggregated data shown to supervisors
- [ ] Auto-referral flags displayed for Orange/Red

---

## Local Development Commands

### Start Backend
```bash
cd /home/james/projects/unda
./run.sh
# Or manually:
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

### Test Endpoints
```bash
# Health check
curl http://localhost:5000/api/health

# API status
curl http://localhost:5000/api/status | jq

# Login (creates session)
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"username":"admin","password":"yourpassword"}'

# Get current user (using session)
curl http://localhost:5000/api/me \
  -b cookies.txt

# Submit assessment (using session)
curl -X POST http://localhost:5000/api/assessments/submit \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "champion_code": "UMV-2026-000001",
    "assessment_type": "PHQ-9",
    "raw_score": 12
  }'
```

---

## Need Help?

### Common Issues

**Issue: CORS errors**
- Solution: Ensure `withCredentials: true` in frontend config
- Verify origin is `localhost` (CORS auto-allows localhost)

**Issue: 401 Unauthorized**
- Solution: Check session cookie is being sent
- Login first, then make authenticated requests

**Issue: Prevention Advocate code not found**
- Solution: Verify code format: `UMV-YYYY-NNNNNN`
- Use `/api/prevention advocates/verify-code` to check validity

**Issue: Role permission denied**
- Solution: Check user role with `/api/me`
- Ensure user has correct role for endpoint

### Documentation References
- API Endpoints: [PRIVACY_FIRST_IMPLEMENTATION.md](PRIVACY_FIRST_IMPLEMENTATION.md)
- Deployment Status: [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md)
- Security: [SECURITY_IMPLEMENTATION.md](SECURITY_IMPLEMENTATION.md)

---

## Ready to Connect! 🚀

Your backend is **fully operational** and ready for frontend integration. All endpoints are privacy-compliant and tested.

**Next Steps:**
1. Configure your frontend API client (axios/fetch) with `withCredentials: true`
2. Test health check: `http://localhost:5000/api/health`
3. Implement login flow
4. Start with prevention advocate registration
5. Add assessment submission form
