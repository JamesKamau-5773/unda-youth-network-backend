# Unda Youth Network - API & Integration Documentation

**Version:** 1.0  
**Last Updated:** December 18, 2025  
**For:** Frontend Developers & Website Integration Teams

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication System](#authentication-system)
3. [API Endpoints](#api-endpoints)
4. [Data Models & Schemas](#data-models--schemas)
5. [Frontend Integration Guide](#frontend-integration-guide)
6. [Security Requirements](#security-requirements)
7. [Error Handling](#error-handling)
8. [Testing Credentials](#testing-credentials)
9. [Design System Reference](#design-system-reference)

---

## Overview

### Application Architecture

**Backend Stack:**
- **Framework:** Flask 2.3.3 (Python)
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Authentication:** Flask-Login with bcrypt password hashing
- **Session Management:** Server-side sessions with httpOnly cookies
- **Security:** CSRF protection, rate limiting (Redis-backed), security headers

**Current State:**
- Template-based rendering (Jinja2)
- Role-based access control (Admin, Supervisor, Champion)
- RESTful API structure ready for decoupling
- Responsive design system in place

**Integration Approach:**
Choose one of the following approaches based on your frontend stack:

1. **Full API Decoupling** - Build separate React/Vue/Angular frontend
2. **Hybrid Approach** - Enhance existing templates with modern JS frameworks
3. **Progressive Enhancement** - Keep templates, add API endpoints for dynamic features

---

## Authentication System

### Login Flow

**Endpoint:** `POST /auth/login`

**Request Format:**
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=SecurePass123!
```

**Success Response (302 Redirect):**
```http
HTTP/1.1 302 Found
Location: /admin/dashboard
Set-Cookie: session=...; HttpOnly; SameSite=Lax
```

**Error Response:**
```http
HTTP/1.1 200 OK

Flash Message: "Invalid username or password"
```

**Rate Limiting:**
- **Limit:** 10 requests per minute per IP
- **Lockout:** 7 failed attempts = 30-minute account lockout
- **Headers:** Check `X-RateLimit-Remaining` and `X-RateLimit-Reset`

### Session Management

**Cookie Details:**
- **Name:** `session`
- **Attributes:** HttpOnly, SameSite=Lax, Secure (in production)
- **Duration:** Session-based (expires on browser close)
- **Storage:** Server-side session store

**Authentication Check:**
```javascript
// JavaScript example
fetch('/api/auth/status', {
  credentials: 'include'  // Important: include cookies
})
.then(res => res.json())
.then(data => {
  if (data.authenticated) {
    console.log('User:', data.user);
    console.log('Role:', data.role);
  }
});
```

### Logout

**Endpoint:** `GET /auth/logout`

**Response:**
```http
HTTP/1.1 302 Found
Location: /auth/login
Set-Cookie: session=; Expires=Thu, 01 Jan 1970 00:00:00 GMT
```

### CSRF Protection

**All POST/PUT/DELETE requests require CSRF token:**

```html
<!-- In forms -->
<form method="POST">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <!-- form fields -->
</form>
```

```javascript
// In JavaScript (fetch from meta tag or cookie)
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

fetch('/api/endpoint', {
  method: 'POST',
  headers: {
    'X-CSRFToken': csrfToken,
    'Content-Type': 'application/json'
  },
  credentials: 'include',
  body: JSON.stringify(data)
});
```

---

## API Endpoints

### User Management

#### Register New User
**Endpoint:** `POST /auth/register`  
**Access:** Admin only  
**CSRF Required:** Yes

**Request Body:**
```json
{
  "username": "john_champion",
  "password": "SecurePass123!",
  "role": "Champion"
}
```

**Password Requirements:**
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character (!@#$%^&*)

**Success Response:**
```json
{
  "status": "success",
  "message": "User john_champion registered successfully",
  "user_id": 15
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Username already exists",
  "field": "username"
}
```

### Champion Management

#### Get All Champions
**Endpoint:** `GET /api/champions`  
**Access:** Admin, Supervisor  
**Query Parameters:**
- `status`: Filter by status (Active, Inactive, On Hold)
- `supervisor_id`: Filter by supervisor
- `recruitment_source`: Filter by source (Campus Edition, Mtaani, etc.)
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20)

**Example Request:**
```http
GET /api/champions?status=Active&page=1&per_page=20
Authorization: Session Cookie
```

**Response:**
```json
{
  "champions": [
    {
      "id": 5,
      "user_id": 10,
      "username": "jane_champion",
      "champion_code": "CH-001",
      "status": "Active",
      "cohort": "2024-Q1",
      "recruitment_source": "Campus Edition",
      "supervisor": {
        "id": 3,
        "username": "supervisor_mary"
      },
      "certification_status": "Certified",
      "youth_reached": 45,
      "check_in_rate": 85.5,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8
  }
}
```

#### Get Champion Details
**Endpoint:** `GET /api/champions/<champion_id>`  
**Access:** Admin, Supervisor (own champions), Champion (self)

**Response:**
```json
{
  "id": 5,
  "user_id": 10,
  "username": "jane_champion",
  "champion_code": "CH-001",
  "status": "Active",
  "cohort": "2024-Q1",
  "recruitment_source": "Campus Edition",
  "date_of_birth": "2000-05-15",
  "gender": "Female",
  "phone_number": "+254712345678",
  "email": "jane@example.com",
  "education_level": "University",
  "institution": "University of Nairobi",
  "supervisor": {
    "id": 3,
    "username": "supervisor_mary",
    "phone": "+254700000000"
  },
  "certification": {
    "status": "Certified",
    "date": "2024-02-01",
    "trainer_name": "Dr. Smith",
    "training_location": "Nairobi Training Center",
    "certificate_number": "CERT-2024-001"
  },
  "screening": {
    "background_check": true,
    "background_check_date": "2024-01-20",
    "mental_health_assessment": true,
    "assessment_date": "2024-01-22"
  },
  "safeguarding": {
    "consent_obtained": true,
    "consent_date": "2024-01-25",
    "safeguarding_concerns": false
  },
  "performance": {
    "youth_reached": 45,
    "check_in_rate": 85.5,
    "average_referral_quality": 4.2,
    "average_session_quality": 4.5,
    "attendance_rate": 92.0,
    "peer_rating": 4.7
  },
  "reports_count": 12,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-12-18T14:20:00Z"
}
```

#### Update Champion Status
**Endpoint:** `PUT /api/champions/<champion_id>/status`  
**Access:** Admin, Supervisor  
**CSRF Required:** Yes

**Request:**
```json
{
  "status": "On Hold",
  "reason": "Taking a break for personal reasons"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Champion status updated to On Hold",
  "champion_id": 5,
  "new_status": "On Hold"
}
```

### Reports Management

#### Submit Report
**Endpoint:** `POST /api/reports`  
**Access:** Champion (self), Supervisor  
**CSRF Required:** Yes

**Request:**
```json
{
  "champion_id": 5,
  "report_date": "2024-12-18",
  "youth_reached": 8,
  "check_ins_conducted": 12,
  "screenings_conducted": 3,
  "referrals_made": 2,
  "referral_quality_score": 4,
  "session_quality_score": 5,
  "challenges_faced": "Limited transportation for outreach",
  "support_needed": "Taxi fare reimbursement",
  "wellbeing_score": 4,
  "personal_notes": "Feeling motivated this week"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Report submitted successfully",
  "report_id": 125,
  "submitted_at": "2024-12-18T15:30:00Z"
}
```

#### Get Champion Reports
**Endpoint:** `GET /api/champions/<champion_id>/reports`  
**Access:** Admin, Supervisor, Champion (self)  
**Query Parameters:**
- `start_date`: Filter from date (YYYY-MM-DD)
- `end_date`: Filter to date (YYYY-MM-DD)
- `page`: Page number
- `per_page`: Items per page

**Response:**
```json
{
  "reports": [
    {
      "id": 125,
      "champion_id": 5,
      "report_date": "2024-12-18",
      "youth_reached": 8,
      "check_ins_conducted": 12,
      "screenings_conducted": 3,
      "referrals_made": 2,
      "referral_quality_score": 4.0,
      "session_quality_score": 5.0,
      "wellbeing_score": 4,
      "submitted_at": "2024-12-18T15:30:00Z"
    }
  ],
  "summary": {
    "total_reports": 12,
    "total_youth_reached": 96,
    "average_check_in_rate": 85.5,
    "average_quality_score": 4.3
  },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 12,
    "pages": 1
  }
}
```

### Dashboard Metrics

#### Admin Dashboard Metrics
**Endpoint:** `GET /api/admin/metrics`  
**Access:** Admin only

**Response:**
```json
{
  "champions": {
    "total": 150,
    "active": 120,
    "inactive": 20,
    "on_hold": 10,
    "by_recruitment_source": {
      "Campus Edition": 60,
      "Mtaani": 45,
      "Referral": 30,
      "Online": 15
    }
  },
  "performance": {
    "total_youth_reached": 6750,
    "average_check_in_rate": 82.3,
    "average_referral_quality": 4.1,
    "average_session_quality": 4.4,
    "screening_completion_rate": 87.5
  },
  "compliance": {
    "safeguarding_consent_rate": 95.5,
    "background_check_completion": 92.0,
    "assessment_completion": 89.5
  },
  "recent_activity": {
    "new_champions_this_month": 8,
    "reports_submitted_this_week": 85,
    "pending_reviews": 12
  }
}
```

#### Supervisor Dashboard Metrics
**Endpoint:** `GET /api/supervisor/metrics`  
**Access:** Supervisor only

**Response:**
```json
{
  "my_champions": {
    "total": 15,
    "active": 12,
    "inactive": 2,
    "on_hold": 1
  },
  "performance": {
    "total_youth_reached": 675,
    "average_check_in_rate": 84.5,
    "average_attendance_rate": 91.2
  },
  "champions": [
    {
      "id": 5,
      "username": "jane_champion",
      "champion_code": "CH-001",
      "status": "Active",
      "youth_reached": 45,
      "check_in_rate": 85.5,
      "last_report_date": "2024-12-18"
    }
  ]
}
```

#### Champion Dashboard Metrics
**Endpoint:** `GET /api/champion/metrics`  
**Access:** Champion (self)

**Response:**
```json
{
  "personal_stats": {
    "total_reports_submitted": 12,
    "youth_reached": 96,
    "check_ins_conducted": 145,
    "screenings_conducted": 28,
    "referrals_made": 15
  },
  "averages": {
    "check_in_rate": 85.5,
    "referral_quality": 4.2,
    "session_quality": 4.5,
    "attendance_rate": 92.0
  },
  "recent_reports": [
    {
      "id": 125,
      "report_date": "2024-12-18",
      "youth_reached": 8,
      "wellbeing_score": 4,
      "submitted_at": "2024-12-18T15:30:00Z"
    }
  ],
  "alerts": [
    {
      "type": "reminder",
      "message": "Weekly report due in 2 days",
      "priority": "medium"
    }
  ]
}
```

---

## Data Models & Schemas

### User Model

```typescript
interface User {
  id: number;
  username: string;
  password_hash: string;  // Never exposed in API
  role: 'Admin' | 'Supervisor' | 'Champion';
  failed_login_attempts: number;
  account_locked_until: Date | null;
  created_at: Date;
  last_login: Date | null;
}
```

### Champion Model

```typescript
interface Champion {
  id: number;
  user_id: number;
  supervisor_id: number | null;
  champion_code: string;
  status: 'Active' | 'Inactive' | 'On Hold';
  
  // Personal Information
  date_of_birth: Date | null;
  gender: string | null;
  phone_number: string | null;
  email: string | null;
  education_level: string | null;
  institution: string | null;
  
  // Program Details
  cohort: string | null;
  recruitment_source: 'Campus Edition' | 'Mtaani' | 'Referral' | 'Online' | 'Other' | null;
  
  // Certification
  certification_status: 'Pending' | 'In Progress' | 'Certified' | 'Expired' | null;
  certification_date: Date | null;
  certification_expiry: Date | null;
  trainer_name: string | null;
  training_location: string | null;
  certificate_number: string | null;
  
  // Screening
  background_check_completed: boolean;
  background_check_date: Date | null;
  mental_health_assessment_completed: boolean;
  mental_health_assessment_date: Date | null;
  
  // Safeguarding
  safeguarding_consent_obtained: boolean;
  safeguarding_consent_date: Date | null;
  safeguarding_concerns: boolean;
  safeguarding_notes: string | null;
  
  // Performance Metrics
  youth_reached: number;
  check_in_rate: number;
  average_referral_quality: number;
  average_session_quality: number;
  attendance_rate: number;
  peer_rating: number;
  
  // Timestamps
  created_at: Date;
  updated_at: Date;
}
```

### Report Model

```typescript
interface Report {
  id: number;
  champion_id: number;
  report_date: Date;
  
  // Activity Metrics
  youth_reached: number;
  check_ins_conducted: number;
  screenings_conducted: number;
  referrals_made: number;
  
  // Quality Scores (1-5)
  referral_quality_score: number;
  session_quality_score: number;
  
  // Narrative Fields
  challenges_faced: string | null;
  support_needed: string | null;
  
  // Wellbeing (1-5)
  wellbeing_score: number | null;
  personal_notes: string | null;
  
  // Timestamps
  submitted_at: Date;
  created_at: Date;
}
```

---

## Frontend Integration Guide

### Option 1: Full API Decoupling (React/Vue/Angular)

**Architecture:**
```
Frontend (React/Vue/Angular) <---> REST API (Flask) <---> PostgreSQL
```

**Setup Steps:**

1. **CORS Configuration** (Backend Team)
```python
# Add to app.py
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['http://localhost:3000'])
```

2. **API Client Setup** (Frontend)
```javascript
// api/client.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export const apiClient = {
  async fetch(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      credentials: 'include',  // Important for cookies
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return response.json();
  },
  
  get(endpoint) {
    return this.fetch(endpoint);
  },
  
  post(endpoint, data, csrfToken) {
    return this.fetch(endpoint, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      body: JSON.stringify(data)
    });
  }
};
```

3. **Authentication Hook** (React Example)
```javascript
// hooks/useAuth.js
import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';

export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    checkAuth();
  }, []);
  
  async function checkAuth() {
    try {
      const data = await apiClient.get('/api/auth/status');
      setUser(data.authenticated ? data.user : null);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }
  
  async function login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await fetch('http://localhost:5000/auth/login', {
      method: 'POST',
      credentials: 'include',
      body: formData
    });
    
    if (response.ok) {
      await checkAuth();
      return true;
    }
    return false;
  }
  
  async function logout() {
    await fetch('http://localhost:5000/auth/logout', {
      credentials: 'include'
    });
    setUser(null);
  }
  
  return { user, loading, login, logout };
}
```

4. **Protected Route Component**
```javascript
// components/ProtectedRoute.jsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();
  
  if (loading) return <LoadingSpinner />;
  
  if (!user) return <Navigate to="/login" />;
  
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" />;
  }
  
  return children;
}
```

### Option 2: Hybrid Approach (Enhance Existing Templates)

**Keep Flask templates, add JavaScript for dynamic features:**

```html
<!-- In base.html -->
<script>
// Global API helper
window.API = {
  async call(endpoint, options = {}) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
    
    const response = await fetch(endpoint, {
      ...options,
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json',
        ...options.headers
      },
      credentials: 'include'
    });
    
    return response.json();
  }
};

// Toast notification system
window.showToast = function(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => toast.remove(), 5000);
};
</script>
```

**Dynamic Data Loading:**
```javascript
// In dashboard page
async function loadChampionStats() {
  const data = await API.call('/api/supervisor/metrics');
  
  document.getElementById('total-champions').textContent = data.my_champions.total;
  document.getElementById('active-champions').textContent = data.my_champions.active;
  
  renderChampionsList(data.champions);
}

function renderChampionsList(champions) {
  const container = document.getElementById('champions-list');
  container.innerHTML = champions.map(champion => `
    <div class="champion-card">
      <h3>${champion.username}</h3>
      <p>Youth Reached: ${champion.youth_reached}</p>
      <p>Check-in Rate: ${champion.check_in_rate}%</p>
    </div>
  `).join('');
}
```

### Option 3: Progressive Enhancement

**Keep existing functionality, add API for specific features:**

- Real-time notifications
- Live search/filtering
- Dashboard chart updates
- Form validations

---

## Security Requirements

### For Frontend Developers

**1. Never Store Sensitive Data in Local Storage**
```javascript
// ❌ WRONG - Security risk
localStorage.setItem('password', password);
localStorage.setItem('sessionToken', token);

// ✅ CORRECT - Use httpOnly cookies (handled by backend)
// Store only non-sensitive preferences
localStorage.setItem('theme', 'dark');
localStorage.setItem('language', 'en');
```

**2. Always Include CSRF Tokens**
```javascript
// ❌ WRONG - Will be rejected
fetch('/api/reports', {
  method: 'POST',
  body: JSON.stringify(data)
});

// ✅ CORRECT
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
fetch('/api/reports', {
  method: 'POST',
  headers: { 'X-CSRFToken': csrfToken },
  body: JSON.stringify(data)
});
```

**3. Validate Input on Frontend (But Backend Validates Too)**
```javascript
function validatePassword(password) {
  const minLength = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[!@#$%^&*]/.test(password);
  
  return minLength && hasUpper && hasLower && hasNumber && hasSpecial;
}
```

**4. Handle Sensitive Data Carefully**
```javascript
// ❌ WRONG - Logs sensitive data
console.log('User password:', password);
console.log('Full user object:', user);

// ✅ CORRECT - Log only safe data
console.log('Login attempt for user:', username);
console.log('User role:', user.role);
```

**5. Implement Rate Limiting on Frontend**
```javascript
// Debounce search requests
const debouncedSearch = debounce(async (query) => {
  const results = await API.call(`/api/search?q=${query}`);
  displayResults(results);
}, 300);
```

### Content Security Policy

**Backend sends these headers:**
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src 'self' fonts.gstatic.com;
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

**Frontend must comply:**
- No inline event handlers (onclick, onerror, etc.)
- Load resources only from allowed domains
- Use CSP-compliant script loading

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Frontend Action |
|------|---------|----------------|
| 200 | Success | Display result |
| 201 | Created | Show success message, redirect |
| 400 | Bad Request | Show validation errors |
| 401 | Unauthorized | Redirect to login |
| 403 | Forbidden | Show "Access Denied" message |
| 404 | Not Found | Show "Resource not found" |
| 429 | Too Many Requests | Show rate limit message, retry after delay |
| 500 | Server Error | Show generic error, log to monitoring |

### Error Response Format

```json
{
  "status": "error",
  "message": "Validation failed",
  "errors": {
    "username": "Username must be at least 3 characters",
    "password": "Password does not meet requirements"
  },
  "code": "VALIDATION_ERROR"
}
```

### Frontend Error Handling Example

```javascript
async function submitReport(reportData) {
  try {
    const result = await API.call('/api/reports', {
      method: 'POST',
      body: JSON.stringify(reportData)
    });
    
    showToast('Report submitted successfully!', 'success');
    return result;
    
  } catch (error) {
    if (error.status === 401) {
      // Session expired
      window.location.href = '/auth/login';
    } else if (error.status === 400) {
      // Validation errors
      displayValidationErrors(error.errors);
    } else if (error.status === 429) {
      // Rate limited
      showToast('Too many requests. Please wait a moment.', 'warning');
    } else {
      // Generic error
      showToast('An error occurred. Please try again.', 'error');
      console.error('API Error:', error);
    }
  }
}
```

---

## Testing Credentials

**For Development Environment Only**

### Admin Account
- **Username:** `admin`
- **Password:** `AdminPass123!`
- **Capabilities:** Full system access

### Supervisor Account
- **Username:** `supervisor`
- **Password:** `SuperPass123!`
- **Capabilities:** Manage assigned champions, view reports

### Champion Account
- **Username:** `champion`
- **Password:** `ChampPass123!`
- **Capabilities:** Submit reports, view own statistics

**⚠️ WARNING:** These credentials are for development only. Never use in production.

---

## Design System Reference

### Color Palette

```css
/* Primary Colors */
--trust-blue: #2563eb;       /* Primary actions, links */
--success-green: #10b981;    /* Success states, positive metrics */
--warning-amber: #f59e0b;    /* Warnings, pending states */
--danger-red: #ef4444;       /* Errors, critical alerts */

/* Neutral Colors */
--gray-50: #f9fafb;
--gray-100: #f3f4f6;
--gray-200: #e5e7eb;
--gray-300: #d1d5db;
--gray-600: #4b5563;
--gray-700: #374151;
--gray-900: #111827;

/* Semantic Colors */
--background: #f8fafc;
--card-bg: #ffffff;
--border-color: #e5e7eb;
--text-primary: #1f2937;
--text-secondary: #6b7280;
```

### Typography

```css
/* Font Family */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Font Sizes */
--text-xs: 0.75rem;    /* 12px */
--text-sm: 0.875rem;   /* 14px */
--text-base: 1rem;     /* 16px */
--text-lg: 1.125rem;   /* 18px */
--text-xl: 1.25rem;    /* 20px */
--text-2xl: 1.5rem;    /* 24px */
--text-3xl: 1.875rem;  /* 30px */

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### Spacing Scale

```css
/* Consistent spacing using 0.25rem (4px) base */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-12: 3rem;     /* 48px */
```

### Component Examples

#### Button Styles
```css
.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 600;
  transition: all 0.2s;
}

.btn--primary {
  background: var(--trust-blue);
  color: white;
}

.btn--primary:hover {
  background: #1d4ed8;
}

.btn--danger {
  background: var(--danger-red);
  color: white;
}
```

#### Card Styles
```css
.card {
  background: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card__header {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--gray-900);
  margin-bottom: 1rem;
}
```

#### Metric Display
```css
.metric {
  text-align: center;
  padding: 1.5rem;
}

.metric__value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--gray-900);
}

.metric__label {
  font-size: 0.875rem;
  color: var(--gray-600);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

### Responsive Breakpoints

```css
/* Mobile First Approach */
@media (min-width: 640px) { /* sm */ }
@media (min-width: 768px) { /* md */ }
@media (min-width: 1024px) { /* lg */ }
@media (min-width: 1280px) { /* xl */ }
```

### Status Indicators

```css
.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
}

.status-badge--active {
  background: #d1fae5;
  color: #065f46;
}

.status-badge--inactive {
  background: #fee2e2;
  color: #991b1b;
}

.status-badge--on-hold {
  background: #fef3c7;
  color: #92400e;
}
```

---

## Best Practices & Recommendations

### Performance

1. **Implement Pagination**
   - Load data in chunks (20 items per page)
   - Use infinite scroll or "Load More" buttons
   - Cache frequently accessed data

2. **Optimize API Calls**
   - Debounce search inputs (300ms)
   - Use request cancellation for obsolete requests
   - Implement request caching with TTL

3. **Lazy Load Components**
   - Load dashboard charts only when visible
   - Defer non-critical scripts
   - Use code splitting for routes

### Accessibility

1. **Keyboard Navigation**
   - All interactive elements accessible via Tab
   - Proper focus indicators
   - Logical tab order

2. **Screen Reader Support**
   - Semantic HTML elements
   - ARIA labels where needed
   - Announce dynamic content changes

3. **Color Contrast**
   - WCAG AA compliance (4.5:1 for text)
   - Don't rely solely on color for information
   - Provide text alternatives

### Mobile Optimization

1. **Touch Targets**
   - Minimum 48x48px clickable areas
   - Adequate spacing between interactive elements
   - Avoid hover-only interactions

2. **Responsive Layout**
   - Mobile-first design approach
   - Stack elements vertically on small screens
   - Hide non-essential content on mobile

### Testing Checklist

- [ ] Login/logout functionality
- [ ] Role-based access control
- [ ] CSRF token handling
- [ ] Session expiration handling
- [ ] Form validation (client and server)
- [ ] Error message display
- [ ] Loading states
- [ ] Empty states
- [ ] Mobile responsiveness
- [ ] Keyboard accessibility
- [ ] Screen reader compatibility
- [ ] Cross-browser testing (Chrome, Firefox, Safari, Edge)

---

## Getting Help

### Technical Support

**Backend Team:**
- **Lead Developer:** [Contact Info]
- **Response Time:** Within 24 hours
- **Slack Channel:** #unda-backend-support

**Documentation:**
- **API Swagger:** http://localhost:5000/api/docs (when running)
- **Postman Collection:** Available in `/docs/postman/`
- **Code Repository:** [GitHub URL]

### Common Issues

**Issue:** CORS errors in development
**Solution:** Ensure credentials: 'include' in fetch options

**Issue:** CSRF token missing
**Solution:** Add `<meta name="csrf-token" content="{{ csrf_token() }}">` to HTML head

**Issue:** Session not persisting
**Solution:** Check that cookies are enabled and credentials: 'include' is set

**Issue:** Rate limit exceeded
**Solution:** Implement request debouncing and show user-friendly message

---

## Version History

**v1.0 (December 18, 2025)**
- Initial API documentation
- Complete endpoint reference
- Integration guides for 3 approaches
- Security requirements
- Design system reference

---

**Document Maintained By:** Backend Development Team  
**Last Review Date:** December 18, 2025  
**Next Review Date:** January 18, 2026
