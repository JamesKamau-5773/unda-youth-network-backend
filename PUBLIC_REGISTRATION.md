# Public Registration & Champion Application System

This document describes the public member registration and champion application workflow.

## Overview

The system allows:
1. Public users to register as members (requires admin approval)
2. Registered members to apply to become champions (requires admin approval)
3. Admins to review and approve/reject both registrations and applications

## Database Models

### MemberRegistration
Tracks pending member registration requests.

**Fields:**
- `registration_id`: Primary key
- `full_name`: Full name of applicant
- `email`: Email address
- `phone_number`: Phone number (254XXXXXXXXX format)
- `username`: Desired username
- `password_hash`: Hashed password
- `date_of_birth`: Date of birth (optional)
- `gender`: Gender (optional)
- `county_sub_county`: Location (optional)
- `status`: Pending, Approved, or Rejected
- `submitted_at`: Submission timestamp
- `reviewed_at`: Review timestamp
- `reviewed_by`: Admin user_id who reviewed
- `rejection_reason`: Reason if rejected
- `created_user_id`: Created User ID if approved

### ChampionApplication
Tracks champion applications from registered members.

**Fields:**
- `application_id`: Primary key
- `user_id`: Foreign key to User
- `full_name`: Full name
- `email`: Email address
- `phone_number`: Phone number
- `gender`: Gender (required)
- `date_of_birth`: Date of birth (required, age 15-35)
- `county_sub_county`: Location
- `emergency_contact_name`: Emergency contact
- `emergency_contact_relationship`: Relationship
- `emergency_contact_phone`: Emergency phone
- `current_education_level`: Education level
- `education_institution_name`: Institution
- `motivation`: Why they want to be a champion
- `skills_interests`: Skills and interests
- `status`: Pending, Approved, or Rejected
- `submitted_at`: Submission timestamp
- `reviewed_at`: Review timestamp
- `reviewed_by`: Admin user_id who reviewed
- `rejection_reason`: Reason if rejected
- `created_champion_id`: Created Champion ID if approved

## API Endpoints

### 1. Public Member Registration

**POST** `/api/auth/register`

Register as a new member (no authentication required).

**Request Body:**
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone_number": "254712345678",
  "username": "johndoe",
  "password": "SecurePass123!",
  "date_of_birth": "2000-01-15",
  "gender": "Male",
  "county_sub_county": "Nairobi, Westlands"
}
```

**Required Fields:**
- `full_name`
- `email` (valid email format)
- `phone_number` (254XXXXXXXXX or 07XXXXXXXX)
- `username` (unique)
- `password` (must meet strength requirements)

**Response (201):**
```json
{
  "message": "Registration submitted successfully. Your account will be reviewed by an administrator.",
  "registration_id": 1,
  "status": "Pending"
}
```

**Validation:**
- Email must be valid format
- Phone must be Kenya format (254XXXXXXXXX or 07XXXXXXXX)
- Password must meet strength requirements
- Username must be unique
- Email must not already exist in Champion records

### 2. Apply to Become Champion

**POST** `/api/champion/apply`

Submit champion application (requires login).

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone_number": "254712345678",
  "alternative_phone_number": "254787654321",
  "gender": "Male",
  "date_of_birth": "2000-01-15",
  "county_sub_county": "Nairobi, Westlands",
  "emergency_contact_name": "Jane Doe",
  "emergency_contact_relationship": "Mother",
  "emergency_contact_phone": "254722222222",
  "current_education_level": "University",
  "education_institution_name": "University of Nairobi",
  "course_field_of_study": "Computer Science",
  "year_of_study": "3rd Year",
  "motivation": "I want to make a difference in my community...",
  "skills_interests": "Leadership, mentoring, technology"
}
```

**Required Fields:**
- `full_name`
- `email` (valid format)
- `phone_number` (Kenya format)
- `gender`
- `date_of_birth` (age must be 15-35)

**Response (201):**
```json
{
  "message": "Champion application submitted successfully. An administrator will review your application.",
  "application_id": 1,
  "status": "Pending"
}
```

**Validation:**
- User must not already have a champion profile
- User must not have a pending application
- Age must be between 15 and 35 years
- Email and phone must be valid formats

### 3. Get My Applications

**GET** `/api/my-applications`

Get current user's champion applications (requires login).

**Response (200):**
```json
{
  "applications": [
    {
      "application_id": 1,
      "full_name": "John Doe",
      "status": "Pending",
      "submitted_at": "2026-01-02T10:30:00",
      "reviewed_at": null,
      "rejection_reason": null
    }
  ]
}
```

## Admin Endpoints

### 4. Get Member Registrations

**GET** `/api/admin/registrations?status=Pending`

Get member registrations (admin only).

**Query Parameters:**
- `status`: Filter by status (Pending, Approved, Rejected) - default: Pending

**Response (200):**
```json
{
  "registrations": [
    {
      "registration_id": 1,
      "full_name": "John Doe",
      "email": "john@example.com",
      "phone_number": "254712345678",
      "username": "johndoe",
      "date_of_birth": "2000-01-15",
      "gender": "Male",
      "county_sub_county": "Nairobi, Westlands",
      "status": "Pending",
      "submitted_at": "2026-01-02T10:00:00",
      "reviewed_at": null,
      "rejection_reason": null
    }
  ]
}
```

### 5. Approve Member Registration

**POST** `/api/admin/registrations/<registration_id>/approve`

Approve a member registration (admin only).

**Response (200):**
```json
{
  "message": "Registration approved successfully",
  "user_id": 123,
  "username": "johndoe"
}
```

### 6. Reject Member Registration

**POST** `/api/admin/registrations/<registration_id>/reject`

Reject a member registration (admin only).

**Request Body:**
```json
{
  "reason": "Incomplete information provided"
}
```

**Response (200):**
```json
{
  "message": "Registration rejected",
  "reason": "Incomplete information provided"
}
```

### 7. Get Champion Applications

**GET** `/api/admin/champion-applications?status=Pending`

Get champion applications (admin only).

**Query Parameters:**
- `status`: Filter by status (Pending, Approved, Rejected) - default: Pending

**Response (200):**
```json
{
  "applications": [
    {
      "application_id": 1,
      "user_id": 123,
      "full_name": "John Doe",
      "email": "john@example.com",
      "phone_number": "254712345678",
      "gender": "Male",
      "date_of_birth": "2000-01-15",
      "county_sub_county": "Nairobi, Westlands",
      "current_education_level": "University",
      "education_institution_name": "University of Nairobi",
      "motivation": "I want to make a difference...",
      "skills_interests": "Leadership, mentoring",
      "status": "Pending",
      "submitted_at": "2026-01-02T11:00:00",
      "reviewed_at": null,
      "rejection_reason": null
    }
  ]
}
```

### 8. Approve Champion Application

**POST** `/api/admin/champion-applications/<application_id>/approve`

Approve a champion application (admin only).

**Request Body:**
```json
{
  "assigned_champion_code": "UMV-2026-001"
}
```

**Required:**
- `assigned_champion_code`: Unique champion code

**Response (200):**
```json
{
  "message": "Champion application approved successfully",
  "champion_id": 456,
  "champion_code": "UMV-2026-001"
}
```

**Actions Performed:**
- Creates Champion profile with all application details
- Links Champion to User account
- Updates application status to Approved
- Sets champion status to Active
- Sets application_status to Recruited

### 9. Reject Champion Application

**POST** `/api/admin/champion-applications/<application_id>/reject`

Reject a champion application (admin only).

**Request Body:**
```json
{
  "reason": "Does not meet age requirements"
}
```

**Response (200):**
```json
{
  "message": "Champion application rejected",
  "reason": "Does not meet age requirements"
}
```

## Workflow

### Member Registration Workflow

1. **User Submits Registration**
   - POST `/api/auth/register`
   - Status: Pending
   - User receives confirmation message

2. **Admin Reviews Registration**
   - GET `/api/admin/registrations?status=Pending`
   - Admin sees all pending registrations

3. **Admin Approves/Rejects**
   - **Approve**: POST `/api/admin/registrations/<id>/approve`
     - Creates User account with role "Champion"
     - User can now log in
   - **Reject**: POST `/api/admin/registrations/<id>/reject`
     - Registration marked as rejected
     - Rejection reason stored

### Champion Application Workflow

1. **Member Logs In**
   - Uses approved credentials

2. **Member Submits Application**
   - POST `/api/champion/apply`
   - Status: Pending
   - Member receives confirmation

3. **Admin Reviews Applications**
   - GET `/api/admin/champion-applications?status=Pending`
   - Admin sees all pending applications with full details

4. **Admin Approves/Rejects**
   - **Approve**: POST `/api/admin/champion-applications/<id>/approve`
     - Creates Champion profile
     - Links to User account
     - Assigns champion code
     - User becomes a Champion
   - **Reject**: POST `/api/admin/champion-applications/<id>/reject`
     - Application marked as rejected
     - Rejection reason stored
     - User remains a regular member

## Validation Rules

### Email Validation
- Must match pattern: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`

### Phone Validation
- Kenya format: `254XXXXXXXXX` (12 digits starting with 254)
- Alternative: `07XXXXXXXX` or `01XXXXXXXX` (10 digits)

### Password Strength
- Validated by `password_validator.validate_password_strength()`
- Must meet application security requirements

### Age Requirements (Champion Application)
- Minimum age: 15 years
- Maximum age: 35 years
- Calculated from date_of_birth

## Error Responses

**400 Bad Request:**
```json
{
  "error": "Missing required field: email"
}
```

**400 Validation Error:**
```json
{
  "error": "Invalid email format"
}
```

**400 Duplicate:**
```json
{
  "error": "Username already exists"
}
```

**401 Unauthorized:**
```json
{
  "error": "Authentication required"
}
```

**403 Forbidden:**
```json
{
  "error": "Admin access required"
}
```

**404 Not Found:**
```json
{
  "error": "Not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Error message"
}
```

## Testing

### Test Member Registration
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "email": "test@example.com",
    "phone_number": "254712345678",
    "username": "testuser",
    "password": "SecurePass123!",
    "gender": "Male",
    "date_of_birth": "2000-01-15"
  }'
```

### Test Champion Application
```bash
curl -X POST http://localhost:5000/api/champion/apply \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "full_name": "Test Champion",
    "email": "champion@example.com",
    "phone_number": "254787654321",
    "gender": "Female",
    "date_of_birth": "1998-05-20",
    "motivation": "I want to help my community"
  }'
```

## Production Deployment

1. **Apply Migration**
   ```bash
   flask db upgrade
   ```

2. **Update CORS Settings**
   - Ensure frontend URL is in CORS_ORIGINS

3. **Notify Admins**
   - Set up email notifications for new registrations (future enhancement)
   - Create admin dashboard for review workflow

4. **Monitor**
   - Track registration success rates
   - Monitor approval times
   - Review rejection reasons for patterns

## Future Enhancements

- Email notifications to admins on new registrations
- Email notifications to users on approval/rejection
- Bulk approval functionality
- Advanced filtering and search for admin review
- Document upload for champion applications
- SMS notifications using M-Pesa integration
- Application deadline management
- Waitlist functionality
