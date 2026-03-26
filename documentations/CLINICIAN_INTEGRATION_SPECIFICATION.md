# Clinician Integration Specification
**Unda Mind Vibes (UMV) Prevention Program**  
**Version 1.0 | Date: March 16, 2026**

---

## Executive Summary

This specification defines the integration of professional clinicians into the Unda Youth Network platform. Clinicians serve as a specialized tier of verified professionals who provide specialized care (Trauma Therapy, Adolescent Counseling, Crisis Intervention) to youth referred by Prevention Advocates. This feature is **mandatory for regulatory compliance** and establishes a legal and operational framework for youth-clinician matching, emergency escalation, and confidential session management.

---

## Key Integration Principles

| Principle | Implementation |
|-----------|-----------------|
| **Regulatory Compliance** | All clinician data stored in secure, audit-logged database tables |
| **Isolation & Control** | Clinician = distinct user type requiring admin approval before platform access |
| **Legal Liability Protection** | Declaration acceptance logged with timestamp, IP, and admin verification chain |
| **Youth Safeguarding** | Emergency contact data immediately accessible; clinical notes encrypted separately |
| **Routing & Matching** | Specializations, languages, and service modes enable precise youth-clinician allocation |

---

## Architecture Overview

### Database Layer
- **New Tables**: `clinician_profiles`, `clinician_specializations`, `clinician_languages`, `clinician_audit_log`, `youth_clinician_referrals`, `clinical_sessions`
- **Storage**: PostgreSQL 16 with pgcrypto extension (for clinical session encryption)
- **Audit Trail**: Every action (registration, approval, suspension, license expiry) logged immutably

### Service Layer
- **ClinicianService**: Registration, verification, routing, license expiry checks
- **Scheduled Jobs** (Celery): Weekly license expiry audits; auto-suspension for expired credentials
- **RBAC**: `ROLE_CLINICIAN` isolated from existing Admin/Supervisor/Prevention Advocate roles

### Frontend Layer
- **Registration Portal**: Multi-step form (credentials → specializations → emergency contacts → declaration)
- **Admin Verification Dashboard**: Pending/approved/rejected clinicians with approval/rejection workflows
- **Clinician Dashboard** (Phase 2): View assigned youth, submit session summaries, manage specializations

---

## Critical Decisions

### 1. License Verification Workflow
**Decision**: Manual admin review (Phase 1) → Regulatory body API integration (Phase 3+)
- Clinician submits license_number + regulatory_body at registration
- Admin reviews via manual lookup (Kenya Medical Practitioners Board, Counseling Board, etc.)
- Admin approves/rejects with verification_notes
- If rejected, clinician receives email explaining why; can reapply
- **No automatic API calls in Phase 1** (avoids external dependencies; simpler MVP)

### 2. License Expiry Enforcement
**Decision**: Automatic account suspension on license expiry date
- Scheduled job (Celery) runs daily: checks `license_expiry_date` < TODAY()
- Expired clinician account auto-suspended (`account_suspended=true`)
- Email alert sent 30 days before expiry ("License expiring on [date]")
- Clinician cannot submit session notes or receive referrals while suspended
- Admin can manually unsuspend if clinician uploads renewed license

### 3. E-Signature & Declaration
**Decision**: Checkbox + timestamp + IP logging (audit trail, not legal docusign)
- Clinician checks "I declare..." box before registration submission
- System records: timestamp, clinician IP address, verified_by admin
- Digital equivalent of signature for audit purposes
- **Sufficient for liability protection & audit trail**
- If legal later requires DocuSign integration, it's a plugin, not a rewrite

### 4. Role Hierarchy & Multi-Role Support
**Decision**: Single role per clinician in Phase 1 (no multi-role)
- User.role = `ROLE_CLINICIAN` (isolated, clear permissions)
- Clinician cannot simultaneously be Admin/Supervisor
- If future need for "Supervisor Clinician", refactor to junction table then
- **Reduces RBAC complexity; security-first approach**

### 5. Clinician ↔ Prevention Advocate Relationship
**Decision**: Privacy-first matching; clinician sees only referred youth
- Prevention Advocate submits referral with reason
- Clinician notified of pending referral (accepts/declines)
- Once accepted, clinician can view youth profile + submit session notes
- Clinician **cannot freely browse all youth** (protects privacy)
- Admin can override/reassign if needed
- **Table**: `youth_clinician_referrals` tracks all interactions

### 6. Confidentiality & Data Encryption
**Decision**: Clinical session notes encrypted at rest; emergency contacts plaintext
- **Encrypted**: Session notes, session summaries, risk assessments (pgcrypto in PostgreSQL)
- **Plaintext**: Emergency contact name/phone (must be instantly accessible during crisis)
- **Separate table**: `clinical_sessions` NOT joined to ERP audit logs
- **Access control**: Only assigned clinician + authorized supervisors can decrypt
- **Audit log**: Every access to encrypted data recorded ("Who viewed what when")

### 7. Frontend Tech Stack
**Decision**: Flask templates (Jinja2) for MVP; React optional Phase 3+
- Consistent with existing admin panel (auth.py, admin.py using Flask)
- Faster development than React + API refactor
- Uses existing CSS framework (Tailwind + Unda design system)
- Can migrate to React SPA later if UX demands it
- **No breaking changes to current system**

### 8. Document Upload & Storage
**Decision**: Filesystem upload to `/static/uploads/clinician_documents/` with validation
- **Allowed**: PDF, JPG, PNG (license uploads, insurance certificates)
- **Max size**: 5MB per file
- **Retained**: Indefinitely (compliance/audit trail)
- **Virus scan**: Optional Phase 2 (add ClamAV later if required)
- **Cloud storage**: Optional Phase 3 (S3/GCS if scale demands)
- **Backup**: Included in existing database backup strategy

### 9. Testing & Validation Strategy
**Decision**: Mock regulatory body in development; real API in production
```
ENV=test  → Uses TEST_LICENSES dict (mock data)
ENV=prod  → Calls real regulatory body API (to be implemented)
```
- Unit tests for license expiry logic, role validation, emergency contact parsing
- Integration tests for referral workflow, session encryption/decryption
- Manual admin approval process tested before Phase 1 release
- **No external API dependency blocks MVP release**

### 10. Clinician Onboarding User Flow
**Decision**: Distinct from Prevention Advocate; requires manual admin approval
1. Clinician visits `/clinicians/register` (public route, no auth required)
2. Completes multi-step form (credentials, specializations, emergency contacts, declaration)
3. Submits → System creates User + ClinicianProfile with `verification_status='pending_verification'`
4. Admin dashboard shows pending clinician; admin reviews credentials
5. Admin clicks "Approve" → User.role = ROLE_CLINICIAN, verification_status = 'verified'
6. Clinician receives email: "Your account is approved. You can now log in."
7. Clinician logs in, completes profile setup, waits for referrals

---

## Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: MVP** | 2-3 weeks | Database schema, ClinicianService, registration form, admin verification dashboard |
| **Phase 2: Integration** | 1-2 weeks | Clinician dashboard, referral workflow, session logging (plaintext) |
| **Phase 3: Security** | 1 week | Encryption for session notes, access logging, license expiry automation |
| **Phase 4: Enhancement** | 2-3 weeks | Regulatory body API integration, document upload validation, advanced analytics |
| **Phase 5: React Migration** | Optional | Modern SPA for clinician dashboard (only if UX feedback demands) |

---

## Data Governance

### Privacy Commitments
- ✅ Clinician will NOT see other clinicians' data
- ✅ Clinician will NOT browse all youth; only referrals visible
- ✅ Clinical session notes NOT included in ERP audit logs
- ✅ Youth identifiers in clinical_sessions can be anonymized/encrypted (Phase 2)

### Compliance & Audit
- ✅ Every clinician action logged (registration, approval, suspension, license renewal)
- ✅ Admin approval chain preserved (who approved, when, why rejected)
- ✅ License expiry tracked; account auto-suspended if expired
- ✅ Declaration acceptance legally documented (timestamp + IP + admin verification)

### Security Posture
- ✅ Clinician role isolated (no multi-role complexity)
- ✅ Session notes encrypted; emergency contacts accessible
- ✅ Passwords follow existing Bcrypt + 8-char minimum policy
- ✅ Access to encrypted data requires session + role check + audit log

---

## Stakeholder Responsibilities

| Stakeholder | Responsibility |
|-------------|-----------------|
| **UNDA Admin** | Review & approve/reject clinician registrations; monitor license expiry |
| **UNDA Legal** | Review Declaration language; confirm audit trail meets liability requirements |
| **Prevention Advocates** | Submit referrals with clear reason; coordinate with clinician on youth care |
| **Clinicians** | Maintain current license; adhere to confidentiality; submit session notes |
| **Youth** | Consent to clinician assignment (via Prevention Advocate) |
| **DevOps** | Ensure daily backup of clinician_profiles table; monitor Celery jobs for license expiry |

---

## Success Metrics

- ✅ All clinicians have valid, unexpired licenses (100% compliance)
- ✅ Admin approval time < 48 hours (tracked in audit log)
- ✅ Youth-clinician matching accuracy > 90% (by specialization match)
- ✅ Zero unauthorized access to session notes (audited)
- ✅ Zero platform downtime due to clinician feature (robust error handling)

---

## Not In Scope (Phase 1)

- ❌ Regulatory body API integration (manual admin review sufficient)
- ❌ Digital signature with DocuSign (timestamp + IP adequate)
- ❌ Video session management/recording (can be added Phase 2)
- ❌ Clinician performance ratings by youth (feedback system, Phase 3)
- ❌ Advanced insurance verification (manual lookup sufficient)
- ❌ Multi-language support for declaration (English only, Phase 2)

---

## Sign-Off & Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Lead | ________________ | ________ | ________________ |
| Legal/Compliance | ________________ | ________ | ________________ |
| Tech Lead | ________________ | ________ | ________________ |
| DevOps | ________________ | ________ | ________________ |

---

**Document Status**: APPROVED FOR IMPLEMENTATION  
**Review Date**: Q2 2026  
**Version Control**: Maintained in `documentations/CLINICIAN_INTEGRATION_SPECIFICATION.md`
