# Seed Funding Application System

## Overview
The Seed Funding Application System allows students and members to apply for funding for their projects under the Campus Edition workstream. Admins can review, approve, reject, and track disbursements through the admin dashboard.

## Architecture

### Database Model: `SeedFundingApplication`
Located in `models.py`, this model stores all seed funding application data including:

- **Applicant Information**: Name, email, phone, institution, student ID
- **Project Details**: Title, description, category, beneficiaries, expected impact, timeline
- **Budget**: Total requested amount, detailed breakdown, other funding sources
- **Team**: Team members and size
- **Status Tracking**: Pending → Under Review → Approved/Rejected → Funded
- **Approval Details**: Approved amount, conditions, admin notes
- **Disbursement**: Date, method (M-Pesa, Bank Transfer, etc.), reference number

### API Endpoints (`/api/seed-funding/`)

#### User-Facing Routes
- **POST `/api/seed-funding/apply`** - Submit a new application (requires login)
- **GET `/api/seed-funding/my-applications`** - View user's own applications
- **GET `/api/seed-funding/applications/<id>`** - View specific application details

#### Admin-Only Routes
- **GET `/api/seed-funding/applications`** - List all applications with filters
- **POST `/api/seed-funding/applications/<id>/update-status`** - Update application status
- **GET `/api/seed-funding/statistics`** - Get funding statistics

### Admin Dashboard Routes (`/admin/seed-funding/`)

- **GET `/admin/seed-funding`** - List all applications with status filters
- **GET `/admin/seed-funding/<id>`** - View detailed application
- **POST `/admin/seed-funding/<id>/approve`** - Approve application with amount
- **POST `/admin/seed-funding/<id>/reject`** - Reject application with reason
- **POST `/admin/seed-funding/<id>/mark-funded`** - Mark as funded with disbursement details
- **POST `/admin/seed-funding/<id>/update-review-status`** - Move to "Under Review"

## Frontend Integration

### Submitting an Application

Your React frontend should POST to `/api/seed-funding/apply` with this payload:

```json
{
  "applicant_name": "John Doe",
  "email": "john@university.edu",
  "phone_number": "254712345678",
  "institution_name": "University of Nairobi",
  "student_id_number": "A001/2024",
  "project_title": "Mental Health Awareness Campaign",
  "project_description": "Detailed description of the project...",
  "project_category": "Mental Health Awareness",
  "target_beneficiaries": "200 university students",
  "expected_impact": "Improved mental health awareness...",
  "total_budget_requested": 50000.00,
  "budget_breakdown": [
    {
      "item": "Posters and Flyers",
      "amount": 15000.00
    },
    {
      "item": "Venue Rental",
      "amount": 20000.00
    },
    {
      "item": "Refreshments",
      "amount": 15000.00
    }
  ],
  "project_start_date": "2026-02-01",
  "project_end_date": "2026-03-15",
  "implementation_timeline": "Week 1-2: Planning\nWeek 3-4: Execution\nWeek 5: Evaluation",
  "team_members": [
    {
      "name": "Jane Smith",
      "role": "Project Coordinator"
    },
    {
      "name": "Bob Johnson",
      "role": "Logistics"
    }
  ],
  "team_size": 5,
  "proposal_document_url": "https://...",
  "budget_document_url": "https://..."
}
```

### Response Format

The API returns both **snake_case** and **camelCase** field names for compatibility:

```json
{
  "application": {
    "id": 1,
    "application_id": 1,
    "projectTitle": "Mental Health Awareness Campaign",
    "project_title": "Mental Health Awareness Campaign",
    "totalBudgetRequested": 50000.00,
    "total_budget_requested": 50000.00,
    "status": "Pending",
    "submittedAt": "2026-01-03T10:30:00",
    "submitted_at": "2026-01-03T10:30:00"
  }
}
```

### Checking Application Status

GET `/api/seed-funding/my-applications` returns all applications for the logged-in user:

```json
{
  "applications": [
    {
      "id": 1,
      "projectTitle": "Mental Health Awareness Campaign",
      "status": "Approved",
      "approvedAmount": 45000.00,
      "submittedAt": "2026-01-03T10:30:00",
      "reviewedAt": "2026-01-05T14:20:00"
    }
  ]
}
```

## Admin Workflow

### 1. Review Applications
- Navigate to **Admin Dashboard → Workstreams → Seed Funding** ()
- View statistics: Total applications, pending, approved, total amount
- Filter by status: All, Pending, Under Review, Approved, Funded, Rejected

### 2. Review Application Details
- Click "View Details" on any application
- Review project description, budget breakdown, team information
- View supporting documents if provided

### 3. Take Action

#### Option A: Move to Under Review
- Click "Mark Under Review" button
- Indicates application is being actively reviewed

#### Option B: Approve Application
- Click "Approve Application" button
- Enter approved amount (can be less than requested)
- Add approval conditions (optional)
- Add admin notes (internal, not visible to applicant)
- Submit approval

#### Option C: Reject Application
- Click "Reject Application" button
- Provide rejection reason (visible to applicant)
- Add admin notes (optional)
- Submit rejection

#### Option D: Mark as Funded (after approval)
- Only available for Approved applications
- Click "Mark as Funded" button
- Enter disbursement date
- Select disbursement method (M-Pesa, Bank Transfer, Cheque, Cash)
- Enter reference number (transaction ID)
- Submit

## Status Flow

```
Pending
   ↓
Under Review (optional)
   ↓
Approved ← → Rejected
   ↓
Funded
```

## Database Migration

The system was deployed with migration:
```
7893d12e324d_add_seed_funding_applications_model.py
```

## Files Created/Modified

### New Files
- `blueprints/seed_funding.py` - API blueprint
- `templates/admin/seed_funding_list.html` - List view
- `templates/admin/seed_funding_detail.html` - Detail view

### Modified Files
- `models.py` - Added `SeedFundingApplication` model with `to_dict()` method
- `blueprints/admin.py` - Added admin routes and updated workstreams
- `app.py` - Registered `seed_funding_bp` blueprint
- `migrations/versions/7893d12e324d_*.py` - Database migration

## Security

- All admin routes require `@admin_required` decorator
- User routes require `@login_required` decorator
- Users can only view their own applications (unless admin)
- CSRF protection exempted for API routes
- SQL injection prevented via SQLAlchemy ORM

## Testing the System

### Via API (cURL)
```bash
# Submit application
curl -X POST http://localhost:5000/api/seed-funding/apply \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "applicant_name": "Test User",
    "email": "test@example.com",
    "phone_number": "254712345678",
    "project_title": "Test Project",
    "project_description": "Testing the system",
    "total_budget_requested": 10000.00
  }'

# Get my applications
curl http://localhost:5000/api/seed-funding/my-applications \
  -H "Authorization: Bearer <token>"
```

### Via Admin Dashboard
1. Login as admin
2. Go to `/admin/workstreams`
3. Click "Seed Funding" card
4. View applications and test approve/reject workflows

## Notes

- Frontend integration requires authentication token
- Budget breakdown is stored as JSON array
- Team members stored as JSON array
- All monetary values in Kenyan Shillings (KES)
- Dates formatted as ISO 8601 strings in API responses
