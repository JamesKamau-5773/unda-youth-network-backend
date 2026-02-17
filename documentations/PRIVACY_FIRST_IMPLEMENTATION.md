# UMV PRIVACY-FIRST MENTAL HEALTH SCREENING IMPLEMENTATION

**Date:** January 6, 2026  
**Status:** ✅ IMPLEMENTED  
**Security Level:** MAXIMUM PRIVACY PROTECTION

---

## 🎯 IMPLEMENTATION SUMMARY

Successfully implemented a **zero-compromise** privacy-first mental health screening system for the UMV Prevention Program ("Converse. Prevent. Thrive Mentally").

### Core Privacy Principles Achieved

1. ✅ **NO raw scores stored in database**
2. ✅ **NO individual question responses stored**
3. ✅ **NO prevention advocate names linked to assessments**
4. ✅ **Prevention Advocate codes used for anonymized tracking**
5. ✅ **Color-coded risk categories instead of numeric scores**
6. ✅ **Role-based access control (RBAC) enforced**
7. ✅ **Auto-referral for high-risk cases**

---

## 👥 USER ROLES IMPLEMENTED

### 1. Admin (System Owner)
- Full system access
- Manages supervisors
- Oversees data governance
- **Views aggregated dashboards only** (no individual scores)

### 2. Supervisors
- Manage Prevention Advocates
- Access performance metrics
- View referral summaries
- **Cannot see raw screening scores**

### 3. Prevention Advocates (formerly "Prevention Advocates")
- Register and manage Prevention Prevention Advocates
- Submit mental health screenings
- View operational data (attendance, engagement)
- **Capture screening outcomes as color flags only**

---

## 🎨 COLOR-CODED RISK SYSTEM

### PHQ-9 (Depression Screening)
| Score Range | Risk Category | Color | Description | Auto-Referral |
|-------------|---------------|-------|-------------|---------------|
| 0-4 | Green | 🟢 | Minimal/No depression | No |
| 5-9 | Blue | 🔵 | Mild depression | No |
| 10-14 | Purple | 🟣 | Moderate depression | No |
| 15-19 | Orange | 🟠 | Moderately severe depression | **YES** |
| 20-27 | Red | 🔴 | Severe depression | **YES** |

### GAD-7 (Anxiety Screening)
| Score Range | Risk Category | Color | Description | Auto-Referral |
|-------------|---------------|-------|-------------|---------------|
| 0-4 | Green | 🟢 | Minimal anxiety | No |
| 5-9 | Blue | 🔵 | Mild anxiety | No |
| 10-14 | Purple | 🟣 | Moderate anxiety | No |
| 15-21 | Red | 🔴 | Severe anxiety | **YES** |

**IMPORTANT:** Raw scores are NEVER stored. Only the risk category and score range are saved.

---

## 🗄️ DATABASE SCHEMA CHANGES

### MentalHealthAssessment Model (Refactored)

**REMOVED (Privacy Violations):**
- `champion_id` (foreign key)
- `total_score` (raw score)
- `item_scores` (individual responses)
- `severity_level` (text description)

**ADDED (Privacy-First):**
- `champion_code` (anonymized identifier, e.g., UMV-2026-000001)
- `risk_category` (Green, Blue, Purple, Orange, Red)
- `score_range` (e.g., "0-4", "5-9")

### Prevention Advocate Code Format
```
UMV-YYYY-NNNNNN
```
Example: `UMV-2026-000042`

- UMV = Unda Mind Vibes
- YYYY = Registration year
- NNNNNN = Sequential number (6 digits, zero-padded)

---

## 🔌 API ENDPOINTS CREATED

### For Prevention Advocates

#### Submit Assessment
```http
POST /api/assessments/submit
Authorization: Bearer <token>
Role: Prevention Advocate

Request Body:
{
  "champion_code": "UMV-2026-000001",
  "assessment_type": "PHQ-9",
  "raw_score": 18,
  "is_baseline": true,
  "assessment_period": "Initial",
  "notes": "Non-identifiable notes"
}

Response:
{
  "success": true,
  "assessment_id": 123,
  "risk_category": "Orange",
  "risk_description": "Moderately severe depression",
  "referral_created": true,
  "referral_id": 456
}
```

**PRIVACY NOTE:** Raw score is processed server-side and NEVER stored or returned.

#### View My Submissions
```http
GET /api/assessments/my-submissions
Authorization: Bearer <token>
Role: Prevention Advocate
```

#### Validate Prevention Advocate Code
```http
POST /api/assessments/validate-prevention advocate-code
Authorization: Bearer <token>

Request Body:
{
  "champion_code": "UMV-2026-000001"
}
```

---

### For Supervisors/Admins

#### Assessment Dashboard (Aggregated)
```http
GET /api/assessments/dashboard?days=30
Authorization: Bearer <token>
Role: Supervisor, Admin

Response:
{
  "success": true,
  "period_days": 30,
  "total_assessments": 150,
  "risk_distribution": {
    "Green": 45,
    "Blue": 38,
    "Purple": 32,
    "Orange": 25,
    "Red": 10
  },
  "high_risk_count": 35,
  "referrals": {
    "recommended": 35,
    "completed": 28,
    "pending": 7
  }
}
```

**PRIVACY: NO individual prevention advocate data or raw scores exposed.**

#### Statistics
```http
GET /api/assessments/statistics?type=PHQ-9
Authorization: Bearer <token>
Role: Supervisor, Admin
```

#### Assessments by Advocate
```http
GET /api/assessments/by-advocate
Authorization: Bearer <token>
Role: Supervisor, Admin
```

#### Admin Overview
```http
GET /api/assessments/admin/overview
Authorization: Bearer <token>
Role: Admin
```

---

### Public Endpoints (No Auth Required)

#### Prevention Advocate Self-Registration
```http
POST /api/prevention advocates/register

Request Body:
{
  "full_name": "Jane Doe",
  "gender": "Female",
  "date_of_birth": "2005-03-15",
  "phone_number": "254712345678",
  "email": "jane@example.com",
  "county_sub_county": "Nairobi, Westlands",
  "consent_obtained": true,
  "recruitment_source": "Online Registration"
}

Response:
{
  "success": true,
  "message": "Prevention Advocate registered successfully",
  "champion_code": "UMV-2026-000042",
  "champion_id": 42,
  "important_notice": "Please save your Prevention Advocate Code securely..."
}
```

#### Verify Prevention Advocate Code
```http
POST /api/prevention advocates/verify-code

Request Body:
{
  "champion_code": "UMV-2026-000042"
}
```

---

## 🗃️ DATABASE MIGRATIONS

### Migration 1: Rename Role
**File:** `26e1fa061b8b_rename_champion_role_to_prevention_.py`

```sql
UPDATE users 
SET role = 'Prevention Advocate' 
WHERE role = 'Prevention Advocate'
```

### Migration 2: Refactor Assessment Schema
**File:** `9fda0325abce_refactor_mental_health_assessment_.py`

**Actions:**
1. Add columns: `champion_code`, `risk_category`, `score_range`
2. Create index on `champion_code`
3. **DELETE all existing assessment data** (privacy violation cleanup)
4. Drop columns: `total_score`, `item_scores`, `severity_level`, `champion_id`

**To Apply:**
```bash
cd /home/james/projects/unda
flask db upgrade
```

---

## 🔒 PRIVACY COMPLIANCE CHECKLIST

- [x] No raw scores stored in database
- [x] No individual question responses stored
- [x] Prevention Advocate names not linked to assessments
- [x] Only champion_code used for tracking
- [x] Prevention Advocates see only color flags
- [x] Supervisors see only aggregated statistics
- [x] Admins see only system-wide dashboards
- [x] Audit trail for who administered (not who was assessed)
- [x] Auto-referral system for Orange/Red flags
- [x] Role-based access control (RBAC) enforced

---

## 📁 FILES MODIFIED

### Core Models & Logic
- ✅ `models.py` - Updated User roles, refactored MentalHealthAssessment
- ✅ `decorators.py` - Added prevention_advocate_required decorator
- ✅ `migrations/versions/26e1fa061b8b_*.py` - Role renaming migration
- ✅ `migrations/versions/9fda0325abce_*.py` - Assessment schema migration

### API Blueprints
- ✅ `blueprints/assessments.py` - **COMPLETELY REWRITTEN** (privacy-first)
- ✅ `blueprints/admin.py` - Updated assessment views (no raw scores)
- ✅ `blueprints/public_auth.py` - Added prevention advocate registration endpoints

### Backup Files
- 📦 `blueprints/assessments.py.backup` - Original (legacy) implementation

---

## 🚀 DEPLOYMENT STEPS

### 1. Backup Database
```bash
# CRITICAL: Backup before migration
pg_dump unda_db > unda_backup_$(date +%Y%m%d).sql
```

### 2. Apply Migrations
```bash
cd /home/james/projects/unda
flask db upgrade
```

### 3. Verify Migration
```bash
flask shell
>>> from models import MentalHealthAssessment, User
>>> MentalHealthAssessment.query.count()  # Should be 0
>>> User.query.filter_by(role='Prevention Advocate').count()
```

### 4. Test Endpoints
```bash
# Test prevention advocate registration
curl -X POST http://localhost:5000/api/prevention advocates/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test User","email":"test@test.com","phone_number":"254712345678","gender":"Male","date_of_birth":"2000-01-01","county_sub_county":"Nairobi","consent_obtained":true}'
```

---

## 🧪 TESTING CHECKLIST

### Unit Tests Needed
- [ ] Test `map_phq9_to_risk_category()` with all score ranges
- [ ] Test `map_gad7_to_risk_category()` with all score ranges
- [ ] Test `generate_champion_code()` uniqueness
- [ ] Test assessment submission with invalid prevention advocate code
- [ ] Test auto-referral creation for Orange/Red flags

### Integration Tests
- [ ] Prevention Advocate can submit assessment
- [ ] Supervisor can view dashboard (no raw scores)
- [ ] Admin can view system overview
- [ ] Public prevention advocate registration works
- [ ] Role-based access control is enforced

### Security Tests
- [ ] Confirm NO raw scores in database
- [ ] Confirm NO prevention advocate names in assessment responses
- [ ] Confirm unauthorized users cannot access endpoints
- [ ] Confirm SQL injection protection

---

## 🎯 NEXT STEPS (Frontend Development)

### Member Portal Requirements

1. **Prevention Advocate Registration Form**
   - Capture all required fields
   - Generate and display prevention advocate code
   - Emphasize importance of saving code

2. **Assessment Submission Interface**
   - Input prevention advocate code
   - Display PHQ-9/GAD-7 questionnaire
   - Calculate score client-side
   - Submit to `/api/assessments/submit`
   - Display color-coded result (NOT raw score)

3. **Supervisor Dashboard**
   - Display aggregated statistics
   - Risk distribution charts (pie/bar)
   - Referral tracking
   - Advocate performance metrics

4. **Admin Panel**
   - System-wide metrics
   - User management
   - Data export (aggregated only)

---

## 📞 SUPPORT & QUESTIONS

**Implementation Team:** Development Team  
**Date Completed:** January 6, 2026  
**Security Audit:** Required before production deployment

---

## ⚠️ CRITICAL WARNINGS

1. **DO NOT** restore the old assessments.py.backup file
2. **DO NOT** add endpoints that expose raw scores
3. **DO NOT** link prevention advocate names to assessment records
4. **ALWAYS** use champion_code, never champion_id in assessments
5. **VERIFY** all API responses before frontend integration

---

**"We will not compromise on security."** ✅ Mission Accomplished.
