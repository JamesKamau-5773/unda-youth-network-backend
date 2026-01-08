# Unda Youth Network

A comprehensive web application for managing youth mental health engagement programs through a peer prevention advocate network. Built with Flask, PostgreSQL, and modern responsive design with **85-90% UNDA requirements coverage**.

## Overview

Unda Youth Network is a professional platform designed to support youth mental health initiatives by facilitating the management of peer prevention advocates who work directly with young people in their communities. The system provides role-based dashboards for administrators, supervisors, and prevention advocates to track engagement, monitor wellbeing, manage referrals, and ensure safeguarding compliance.

**Latest Update (v1.1.0 - January 2026)**: 
- Terminology updated: "Champion" → "Prevention Advocate"
- Email functionality added with Flask-Mail integration
- Comprehensive user manual and documentation
- Enhanced security and developer tools
- Full backwards compatibility maintained

## Features

### Multi-Role Dashboard System

#### Admin Dashboard
- **Prevention Advocate Status Overview**: Real-time tracking of Active, Inactive, and On Hold prevention advocates with color-coded metrics
- **Screening Completion Rate**: Average background check and assessment completion percentage
- **System-Wide Metrics**: Check-in rates, referral conversion, compliance scores, satisfaction ratings, and response times
- **Youth Reach Analytics**: Total youth reached across all prevention advocates with individual caseload tracking
- **Prevention Advocate Performance Monitoring**: View engagement metrics, attendance rates, and peer ratings per prevention advocate
- **Recruitment Analytics**: Monitor prevention advocates by recruitment source (Campus Edition, Mtaani, Referral, etc.)
- **Compliance Tracking**: Safeguarding consent monitoring with alert systems for missing documentation
- **Training Management**: Track certifications with trainer details, locations, and certificate numbers

#### Supervisor Dashboard
- **Prevention Advocate Management**: View and manage assigned prevention advocates with their codes, cohorts, and certification status
- **Performance Review**: Access detailed prevention advocate reports and engagement data
- **Safeguarding Notes**: Document and track safeguarding concerns
- **Referral Management**: Submit and monitor referrals to professional services
- **Quality Assessment**: Rate and provide feedback on prevention advocate performance

#### Prevention Advocate Dashboard
- **Report Submission**: Submit weekly reports including check-in rates, screenings, referrals, and quality scores
- **Wellbeing Tracking**: Document personal wellbeing and support needs
- **Historical Data**: View submission history with color-coded performance metrics
- **Alert System**: Receive notifications for pending reports and important updates

### Security & Authentication
- **Bcrypt Password Hashing**: Industry-standard password encryption with automatic salting
- **Flask-Login Integration**: Secure session management with httpOnly and SameSite cookies
- **Role-Based Access Control**: Three-tier permission system (Admin, Supervisor, Prevention Advocate)
- **Rate Limiting**: Redis-backed request throttling (10 requests/minute on login)
- **CSRF Protection**: Flask-WTF token-based form security on all POST requests
- **Password Strength Requirements**: Minimum 8 characters with uppercase, lowercase, numbers, and special characters
- **Account Lockout**: 7 failed login attempts trigger 30-minute account lockout
- **Security Headers**: Content Security Policy, X-Frame-Options, X-Content-Type-Options, HSTS
- **Environment-Based Configuration**: Secret keys and credentials stored in environment variables
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries

### Modern Professional Design
- **Medical/SaaS Aesthetic**: Clean, professional interface with Deep Navy and Trust Blue color scheme
- **Gradient Metric Cards**: Color-coded performance indicators (primary, success, info, warning, danger)
- **Professional Data Tables**: Organized tabular data with badges and status indicators
- **Interactive Forms**: Modern form design with validation and helpful hints
- **Alert Cards**: Contextualized notifications for compliance and safety monitoring

### Full Mobile Responsiveness
- **Adaptive Layouts**: Optimized for desktop (1920px+), tablet (1024px), mobile (768px), and small mobile (480px)
- **Touch-Friendly Interface**: Minimum 44-48px touch targets following Apple HIG guidelines
- **Horizontal Scrolling Tables**: Smooth touch scrolling for data tables on mobile
- **Responsive Navigation**: Sidebar converts to sticky horizontal navigation on mobile devices
- **Mobile-Optimized Forms**: 16px input font size to prevent iOS zoom
- **Progressive Enhancement**: Works across all modern browsers and devices

## Technology Stack

### Backend
- **Flask 2.3.3**: Lightweight Python web framework
- **SQLAlchemy**: SQL toolkit and ORM
- **PostgreSQL**: Robust relational database
- **Flask-Login**: User session management
- **Flask-Migrate**: Database migration handling
- **Flask-Limiter**: Rate limiting with Redis backend
- **Bcrypt**: Secure password hashing

### Frontend
- **Jinja2**: Server-side templating engine
- **Custom CSS**: 1300+ lines of professional styling
- **Inter Font Family**: Modern, readable typography
- **SVG Icons**: Scalable vector graphics for crisp visuals
- **Responsive Grid/Flexbox**: Modern CSS layout techniques

### Database Schema 
- **Users Table**: Authentication and role management with prevention advocate linkage
- **Prevention Advocates Table**: Comprehensive prevention advocate profiles with:
  - Personal data (full_name, date_of_birth, gender, phone, alternative phone, email)
  - Emergency contacts (name, relationship, phone)
  - Education & occupation (level, institution, course/field, year of study, workplace)
  - Enrollment tracking (application_status, screening_status, champion_status: Active/Inactive/On Hold)
  - Location (county, sub-county)
  - Cohort and recruitment source tracking
  - Consent documentation (personal and institutional)
- **TrainingRecord Table**: Training history with:
  - Training modules and dates
  - Certification status and refresher schedules
  - Trainer name, training location, certificate numbers
- **YouthSupport Table**: Operational and performance data with:
  - **Operational**: Assigned clusters, youth caseload, check-in frequency, engagement style
  - **Performance**: Attendance rates, UMV event participation, youth feedback scores, peer ratings
  - **Safeguarding**: Training completion, availability status, incident tracking, escalation flags
  - Weekly check-ins, screenings, documentation quality
  - Prevention Advocate wellbeing and supervisor notes
- **RefferalPathway Table**: Professional service referral tracking with outcomes
- **AccessAuditLog Table**: User activity logging for security and compliance

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Redis (for rate limiting)
- pip (Python package manager)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd unda
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database**
   ```bash
   # Create database
   createdb unda_db
   
   # Or using psql
   psql -U postgres
   CREATE DATABASE unda_db;
   \q
   ```

5. **Configure environment variables**
   Copy the example environment file and update with your values:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # Required: Generate a strong random secret key
   SECRET_KEY=your-secret-key-here-use-random-string
   
   # Required: Database connection string
   DATABASE_URL=postgresql://username:password@localhost/unda_db
   
   # Optional: Redis URL for rate limiting (defaults to localhost)
   REDIS_URL=redis://localhost:6379
   
   # Environment: development or production
   FLASK_ENV=development
   ```
   
   **Security Note**: Never commit `.env` to version control. Use strong random values for SECRET_KEY in production.

6. **Initialize the database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

7. **Seed the database with test data**
   ```bash
   python seed.py
   ```

8. **Run the application**
   ```bash
   # Development mode
   python app.py
   
   # Or using the run script
   chmod +x run.sh
   ./run.sh
   
   # Production mode
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

9. **Access the application**
   Open your browser and navigate to `http://127.0.0.1:5000`

## Test Credentials

After running `python seed.py`, the following test accounts are available:

### Administrator Account
- **Username**: `admin`
- **Password**: `Admin@123`
- **Access**: Full system access, user management, system-wide analytics with prevention advocate status tracking

### Supervisor Accounts
- **Username**: `supervisor1` | **Password**: `Super@123`
- **Username**: `supervisor2` | **Password**: `Super@123`
- **Access**: Prevention Advocate management, performance review, referrals, safeguarding notes

### Prevention Advocate Accounts
- **Prevention Advocate 1 (Alice Wanjiru)**: `alice` / `Alice@123`
  - Education: University of Nairobi, Psychology Year 3
  - Status: Active, 18 youth under support
  - Emergency Contact: Jane Wanjiru (Mother)
  
- **Prevention Advocate 2 (Brian Ochieng)**: `brian` / `Brian@123`
  - Education: Kisumu Technical College, Community Development Year 2
  - Status: Active, 12 youth under support
  - Emergency Contact: Peter Ochieng (Father)
  
- **Prevention Advocate 3 (Catherine Muthoni)**: `catherine` / `Cath@123`
  - Education: High School Graduate, Working at Nakuru Youth Center
  - Status: On Hold, 15 youth under support
  - Emergency Contact: Mary Muthoni (Sister)

**Note**: All passwords meet security requirements (8+ characters, uppercase, lowercase, numbers, special characters)

## Project Structure

```
unda/
├── app.py                      # Application factory and initialization
├── models.py                   # SQLAlchemy database models
├── extensions.py               # Flask extensions configuration
├── decorators.py               # Custom route decorators
├── email_utils.py              # Email utilities and configuration
├── seed.py                     # Database seeding script with comprehensive sample data
├── requirements.txt            # Python dependencies
├── run.sh                      # Application startup script
├── CHANGELOG.md                # Version history and changes
├── USER_MANUAL.md              # Comprehensive user guide
├── README.md                   # This file - project overview
├── IMPLEMENTATION_SUMMARY.md   # Phase 7 implementation details (33 new fields)
├── EMAIL_SETUP.md              # Email configuration guide
├── blueprints/                 # Flask blueprints
│   ├── __init__.py
│   ├── auth.py                 # Authentication routes
│   ├── admin.py                # Admin dashboard routes
│   ├── supervisor.py           # Supervisor dashboard routes
│   ├── champion.py             # Prevention Advocate dashboard routes
│   ├── events.py               # Event management
│   ├── blog.py                 # Blog content
│   ├── assessments.py          # Mental health assessments
│   ├── affirmations.py         # Daily affirmations
│   ├── mpesa.py                # M-Pesa payments
│   ├── seed_funding.py         # Funding applications
│   └── main.py                 # General routes
├── templates/                  # Jinja2 templates
│   ├── base.html               # Base template with navigation
│   ├── auth/                   # Authentication templates
│   │   ├── login.html
│   │   └── register.html
│   ├── admin/                  # Admin dashboard templates
│   │   └── dashboard.html
│   ├── supervisor/             # Supervisor templates
│   │   ├── dashboard.html
│   │   └── champion_details.html
│   └── prevention advocate/               # Prevention Advocate templates
│       └── dashboard.html
├── static/                     # Static assets
│   └── css/
│       └── dashboard.css       # Main stylesheet (1300+ lines)
├── tests/                      # Test suite
│   ├── test_admin_metrics.py
│   └── ...
├── migrations/                 # Database migrations
└── instance/                   # Instance-specific files
```

## API Endpoints

### Authentication
- `GET /auth/login` - Login page
- `POST /auth/login` - Process login
- `GET /auth/logout` - Logout user
- `GET /auth/register` - User registration (Admin only)
- `POST /auth/register` - Create new user

### Admin Routes
- `GET /admin/dashboard` - Admin analytics dashboard
- `GET /admin/settings` - System configuration

### Supervisor Routes
- `GET /supervisor/dashboard` - Supervisor overview
- `GET /supervisor/prevention advocate/<id>` - Prevention Advocate detail view
- `POST /supervisor/prevention advocate/<id>/safeguarding` - Add safeguarding note
- `POST /supervisor/prevention advocate/<id>/notes` - Add supervisor note
- `POST /supervisor/prevention advocate/<id>/quality` - Update quality score
- `POST /supervisor/prevention advocate/<id>/referral` - Create referral

### Prevention Advocate Routes
- `GET /prevention advocate/dashboard` - Prevention Advocate dashboard
- `POST /prevention advocate/submit-report` - Submit weekly report

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_admin_metrics.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html
```

### Database Migrations
```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Revert last migration
flask db downgrade

# View migration history
flask db history

# Current migration: ca78f27269e6 (33 new fields: emergency contacts, education, status tracking, performance metrics)
```

### Code Style
The project follows PEP 8 style guidelines for Python code and uses:
- **SQLAlchemy ORM**: For database interactions
- **Blueprint Pattern**: For modular route organization
- **Jinja2 Templates**: For server-side rendering
- **Custom CSS**: No external CSS frameworks

## Configuration

### Environment Variables
- `SECRET_KEY`: Flask secret key for session encryption
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string for rate limiting
- `FLASK_ENV`: Environment (development/production)
- `FLASK_DEBUG`: Debug mode (0/1)

### Database Configuration
The application uses PostgreSQL with the following key settings:
- **Connection Pool**: SQLAlchemy default pooling
- **Track Modifications**: Disabled for performance
- **Migrations**: Flask-Migrate for version control

### Security Configuration
- **Rate Limiting**: 100 requests per minute per IP (configurable)
- **Password Hashing**: Bcrypt with automatic salt generation
- **Session Security**: HTTP-only cookies, secure in production
- **CSRF Protection**: Enabled for all forms

## Deployment

### Production Checklist
1. Set `FLASK_ENV=production`
2. Set strong `SECRET_KEY`
3. Use production-grade WSGI server (gunicorn, uWSGI)
4. Configure PostgreSQL connection pooling
5. Set up Redis for rate limiting
6. Enable HTTPS with SSL certificates
7. Configure firewall rules
8. Set up backup schedule for database
9. Configure logging and monitoring
10. Set up reverse proxy (nginx, Apache)

### Example Production Deployment
```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - app:app

# With nginx reverse proxy
# Configure nginx to proxy to localhost:5000
```

## Contributing

Contributions are welcome! Please follow these guidelines:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software developed for the Unda Youth Network organization.

## Support

For issues, questions, or feature requests, please contact the development team or open an issue in the repository.

## Implementation Highlights

### Phase 7: Comprehensive UNDA Requirements (December 2025)
**Status**: Complete (85-90% requirements coverage)

**Database Extensions**:
- 33 new fields across 3 core models
- Prevention Advocate model: +12 fields (emergency contacts, education, enrollment status)
- TrainingRecord model: +3 fields (trainer details, location, certificates)
- YouthSupport model: +18 fields (operational, performance, safeguarding)

**New Features**:
- Prevention Advocate lifecycle status tracking (Active/Inactive/On Hold)
- Screening completion rate metrics
- Total youth reached aggregation
- Enhanced operational analytics (clusters, caseload, engagement styles)
- Performance metrics (attendance rates, event participation, peer ratings)
- Safeguarding compliance flags (training completed, incidents, escalations)
- Comprehensive seed data with realistic examples

**Migration**: `ca78f27269e6_add_comprehensive_champion_data_fields_`

For detailed implementation information, see `IMPLEMENTATION_SUMMARY.md`.

## Key Metrics & Statistics

- **Database Fields**: 80+ comprehensive data points per prevention advocate
- **Requirements Coverage**: 85-90% of UNDA specification
- **Test Coverage**: 21 passing tests
- **Code Quality**: PEP 8 compliant, modular blueprint architecture
- **Responsive Design**: 4 breakpoints (1920px, 1024px, 768px, 480px)
- **CSS**: 1362 lines of custom professional styling
- **Performance**: Optimized SQLAlchemy queries with proper indexing

## Acknowledgments

- **Flask Community**: For the excellent web framework
- **Inter Font**: By Rasmus Andersson
- **PostgreSQL**: For robust database management
- **UNDA Youth Network**: For detailed requirements specification and domain expertise
- **Youth Mental Health Organizations**: For insights on peer prevention advocate program management

---

**Version**: 1.1.0  
**Last Updated**: December 18, 2025  
**Phase**: 7 - Comprehensive Requirements Implementation  
**Migration**: ca78f27269e6  
**Requirements Coverage**: 85-90%  
**Maintained By**: Development Team
