# Unda Youth Network

A professional web application for managing youth mental health engagement programs through a peer champion network. Built with Flask, PostgreSQL, and modern responsive design.

## Overview

Unda Youth Network is a comprehensive platform designed to support youth mental health initiatives by facilitating the management of peer champions who work directly with young people in their communities. The system provides role-based dashboards for administrators, supervisors, and champions to track engagement, monitor wellbeing, manage referrals, and ensure safeguarding compliance.

## Features

### Multi-Role Dashboard System

#### Admin Dashboard
- **System-Wide Metrics**: Track check-in rates, conversion metrics, compliance scores, satisfaction ratings, and response times
- **Champion Performance Monitoring**: View youth reach statistics and engagement metrics per champion
- **Recruitment Analytics**: Monitor active champions, pending certifications, and cohort performance
- **Compliance Tracking**: Safeguarding consent monitoring with alert systems
- **Training Management**: Track and schedule training refreshers for champions

#### Supervisor Dashboard
- **Champion Management**: View and manage assigned champions with their codes, cohorts, and certification status
- **Performance Review**: Access detailed champion reports and engagement data
- **Safeguarding Notes**: Document and track safeguarding concerns
- **Referral Management**: Submit and monitor referrals to professional services
- **Quality Assessment**: Rate and provide feedback on champion performance

#### Champion Dashboard
- **Report Submission**: Submit weekly reports including check-in rates, screenings, referrals, and quality scores
- **Wellbeing Tracking**: Document personal wellbeing and support needs
- **Historical Data**: View submission history with color-coded performance metrics
- **Alert System**: Receive notifications for pending reports and important updates

### Security & Authentication
- **Bcrypt Password Hashing**: Industry-standard password encryption
- **Flask-Login Integration**: Secure session management
- **Role-Based Access Control**: Three-tier permission system (Admin, Supervisor, Champion)
- **Rate Limiting**: Redis-backed request throttling to prevent abuse
- **CSRF Protection**: Built-in form security

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
- **Users Table**: Authentication and role management
- **Champions Table**: Champion profiles and metadata
- **Youth Table**: Young people data and engagement tracking
- **Champion Reports Table**: Weekly performance submissions
- **Safeguarding Notes**: Documentation of concerns and interventions
- **Referrals Table**: Professional service referral tracking

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
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=postgresql://username:password@localhost/unda_db
   REDIS_URL=redis://localhost:6379
   ```

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

### Administrator Account
- **Username**: `admin`
- **Password**: `admin123`
- **Access**: Full system access, user management, analytics

### Supervisor Account
- **Username**: `supervisor1`
- **Password**: `super123`
- **Access**: Champion management, performance review, referrals

### Champion Account
- **Username**: `alice`
- **Password**: `alice123`
- **Access**: Report submission, personal dashboard

## Project Structure

```
unda/
├── app.py                      # Application factory and initialization
├── models.py                   # SQLAlchemy database models
├── extensions.py               # Flask extensions configuration
├── decorators.py               # Custom route decorators
├── seed.py                     # Database seeding script
├── requirements.txt            # Python dependencies
├── run.sh                      # Application startup script
├── blueprints/                 # Flask blueprints
│   ├── __init__.py
│   ├── auth.py                 # Authentication routes
│   ├── admin.py                # Admin dashboard routes
│   ├── supervisor.py           # Supervisor dashboard routes
│   ├── champion.py             # Champion dashboard routes
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
│   └── champion/               # Champion templates
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
- `GET /supervisor/champion/<id>` - Champion detail view
- `POST /supervisor/champion/<id>/safeguarding` - Add safeguarding note
- `POST /supervisor/champion/<id>/notes` - Add supervisor note
- `POST /supervisor/champion/<id>/quality` - Update quality score
- `POST /supervisor/champion/<id>/referral` - Create referral

### Champion Routes
- `GET /champion/dashboard` - Champion dashboard
- `POST /champion/submit-report` - Submit weekly report

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

## Acknowledgments

- **Flask Community**: For the excellent web framework
- **Inter Font**: By Rasmus Andersson
- **PostgreSQL**: For robust database management
- **Youth Mental Health Organizations**: For domain expertise and requirements

---

**Version**: 1.0.0  
**Last Updated**: December 2025  
**Maintained By**: Development Team
