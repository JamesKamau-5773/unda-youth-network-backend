# Changelog

All notable changes to the UNDA Youth Network project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-01-08

### Added
- **Email Functionality**
  - Email utilities for user communication
  - Email verification field to User model
  - Email configuration examples and documentation (EMAIL_SETUP.md)
  - Flask-Mail integration for sending emails
  
- **Developer Tools**
  - Hidden developer routes for system inspection and debugging
  - Developer dashboard with system metrics and analytics
  - Secure access via secret key authentication
  - Routes for viewing build info, file structure, and registered routes

- **Documentation**
  - Comprehensive USER_MANUAL.md covering all platform features
  - Complete user guide for Prevention Advocates, Supervisors, and Admins
  - Step-by-step instructions for all major features
  - FAQs and troubleshooting section

### Changed
- **Terminology Update** (Breaking Change)
  - Changed "Champion" role to "Prevention Advocate" throughout the system
  - Updated all documentation files to reflect new terminology
  - Added backwards compatibility in code (Champion → Prevention Advocate mapping)
  - Updated UI templates with new role terminology

- **Enhanced Blueprints**
  - Improved admin blueprint with additional features
  - Enhanced auth blueprint for better user management
  - Updated supervisor blueprint with new capabilities
  
- **Database Migrations**
  - New migration for email field in User model
  - Updated models with email verification support

### Fixed
- Redirect loop prevention in authentication flow
- Security enhancements in session management
- CSRF protection improvements

---

## [1.0.0] - 2025-12 (Previous Release)

### Added
- Initial release of UNDA Youth Network platform
- Multi-role dashboard system (Admin, Supervisor, Champion/Prevention Advocate)
- Mental health assessment features (PHQ-9, GAD-7, PHQ-2, GAD-2)
- Daily affirmations system
- Event management and participation tracking
- Seed funding application workflow
- Blog and podcast content management
- M-Pesa payment integration
- Symbolic items (badges, certificates) tracking
- Comprehensive security implementation
- Privacy-first data handling
- Role-based access control (RBAC)
- Rate limiting with Redis
- Account lockout protection
- Password strength requirements
- CSRF protection
- Security headers
- Database encryption for sensitive fields
- Safeguarding and compliance tracking
- Performance metrics and analytics
- Mobile-responsive design
- PostgreSQL database with SQLAlchemy ORM
- Flask-Login authentication
- Flask-Migrate for database migrations

---

## Terminology Migration Guide

**Important:** As of version 1.1.0, the role previously known as "Champion" is now "Prevention Advocate."

### For Developers:
- All code references use "Prevention Advocate"
- Database role field accepts both "Champion" and "Prevention Advocate"
- Legacy "Champion" role automatically mapped to "Prevention Advocate" in models.py
- Update any frontend code to use new terminology

### For Users:
- Existing Champion accounts now display as "Prevention Advocate"
- All functionality remains the same
- No action required from users

### For Administrators:
- Use "Prevention Advocate" when creating new accounts
- Existing data automatically migrated
- All documentation updated to reflect new terminology

---

## Security Notes

### Version 1.1.0
- Developer routes added with secret key protection
- Returns 404 on invalid access to hide route existence
- Sensitive environment variables automatically masked in responses
- Email functionality added with secure credential storage

---

## Deployment Notes

### Version 1.1.0
**Required Environment Variables:**
- `MAIL_SERVER` - Email server hostname
- `MAIL_PORT` - Email server port
- `MAIL_USE_TLS` - Enable TLS (True/False)
- `MAIL_USERNAME` - Email account username
- `MAIL_PASSWORD` - Email account password
- `MAIL_DEFAULT_SENDER` - Default sender email address
- `DEV_SECRET_KEY` - Secret key for developer routes (optional, development only)

**Database Migrations:**
Run `flask db upgrade` to apply email field migration.

---

## Contributors

- Development Team: UNDA Youth Network
- Documentation: Comprehensive guides and user manuals

---

## Support

For questions or issues:
- Review documentation in `/docs` folder
- Check USER_MANUAL.md for complete user guide
- Contact system administrator

---

**Legend:**
- `Added` - New features
- `Changed` - Changes to existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Security improvements
