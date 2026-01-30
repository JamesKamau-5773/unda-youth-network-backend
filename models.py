from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date, timezone
from bcrypt import hashpw, gensalt, checkpw


db = SQLAlchemy()

#Helper function for password hashing
def hash_password(password):
  """Return a bcrypt hash (utf-8 string) for the given password."""
  return hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')

#Helper function to check password
def check_password(password, hashed_password):
  """Return True if password matches the stored bcrypt hashed password."""
  return checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


class User(db.Model, UserMixin):
  __tablename__ = 'users'
  
  # Valid roles constant - UMV Prevention Program roles
  VALID_ROLES = ['Admin', 'Supervisor', 'Prevention Advocate']
  
  # Role constants to prevent typos and inconsistencies
  ROLE_ADMIN = 'Admin'
  ROLE_SUPERVISOR = 'Supervisor'
  ROLE_PREVENTION_ADVOCATE = 'Prevention Advocate'
  
  user_id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(100), unique=True, nullable=False)
  password_hash = db.Column(db.String(255), nullable=False)
  role = db.Column(db.String(50), nullable=False, default='Prevention Advocate')
  email = db.Column(db.String(100), unique=True, nullable=True)  # Email for password recovery and notifications

  champion_id = db.Column(
    db.Integer,
    db.ForeignKey(
      'champions.champion_id',
      ondelete='SET NULL',
      use_alter=True,
      name='fk_users_champion_id'
    )
  )

  supervised_champion_ids = db.Column(db.JSON)
  
  # Account lockout fields
  failed_login_attempts = db.Column(db.Integer, default=0)
  account_locked = db.Column(db.Boolean, default=False)
  locked_until = db.Column(db.DateTime)
  # Invite token for admin-created accounts (one-time set-password link)
  invite_token = db.Column(db.String(255), unique=True, nullable=True)
  invite_token_expires = db.Column(db.DateTime, nullable=True)
  # Store a small list of frequently visited admin pages for quick access (kept to max 3)
  frequent_pages = db.Column(db.JSON, nullable=True)

  #Implement UserMixin required methord
  def get_id(self):
    return str(self.user_id)
  
  def set_password(self, password):
    self.password_hash = hash_password(password)

  def check_password(self, password):
    return check_password(password, self.password_hash)
  
  def set_role(self, role):
    """Set role with automatic capitalization and validation."""
    if role:
      # Handle legacy 'Champion' role mapping to 'Prevention Advocate'
      if role.capitalize() == 'Champion':
        self.role = self.ROLE_PREVENTION_ADVOCATE
      elif role.title() in self.VALID_ROLES:  # Use title() for multi-word roles
        self.role = role.title()
      else:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {', '.join(self.VALID_ROLES)}")
    else:
      self.role = self.ROLE_PREVENTION_ADVOCATE  # Default
  
  def validate_role(self):
    """Validate and normalize the current role."""
    if self.role:
      # Handle legacy 'Champion' role
      if self.role.capitalize() == 'Champion':
        self.role = self.ROLE_PREVENTION_ADVOCATE
      elif self.role.title() in self.VALID_ROLES:
        self.role = self.role.title()
      elif self.role not in self.VALID_ROLES:
        raise ValueError(f"Invalid role '{self.role}'. Must be one of: {', '.join(self.VALID_ROLES)}")
    else:
      self.role = self.ROLE_PREVENTION_ADVOCATE
  
  def is_role(self, role_name):
    """Case-insensitive role check. Accepts both 'Champion' and 'Prevention Advocate' for advocates."""
    if not self.role:
      return False
    role_lower = self.role.lower()
    check_lower = role_name.lower()
    
    # Handle legacy Champion role
    if check_lower == 'champion' and role_lower == 'prevention advocate':
      return True
    if check_lower == 'prevention advocate' and role_lower == 'champion':
      return True
    
    return role_lower == check_lower
  
  def is_locked(self):
    """Check if account is currently locked."""
    if self.account_locked and self.locked_until:
      # Ensure comparison works if locked_until is naive (treat as UTC)
      locked_until = self.locked_until
      if locked_until.tzinfo is None:
        from datetime import timezone as _tz
        locked_until = locked_until.replace(tzinfo=_tz.utc)
      if datetime.now(timezone.utc) < locked_until:
        return True
      else:
        # Lock expired, reset
        self.account_locked = False
        self.failed_login_attempts = 0
        self.locked_until = None
        db.session.commit()
        return False
    return False
  
  def record_failed_login(self):
    """Record failed login attempt and lock account if threshold reached."""
    from datetime import timedelta
    self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
    if self.failed_login_attempts >= 7:
      self.account_locked = True
      self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.session.commit()
  
  def reset_failed_logins(self):
    """Reset failed login counter after successful login."""
    self.failed_login_attempts = 0
    self.account_locked = False
    self.locked_until = None
    db.session.commit()

  def set_invite(self, token, expires_at):
    """Set invite token and expiry for this user."""
    self.invite_token = token
    self.invite_token_expires = expires_at
    db.session.commit()

  def clear_invite(self):
    """Clear invite token after it's used or expired."""
    self.invite_token = None
    self.invite_token_expires = None
    db.session.commit()

  def touch_frequent_page(self, page_id: str, name: str, endpoint: str):
    """Record a visit to an admin page for quick-access personalization.

    Keeps at most 3 entries ordered by most-recently-seen. Each entry is a dict:
      { 'id': page_id, 'name': name, 'endpoint': endpoint, 'count': N, 'last_seen': iso8601 }
    This method is idempotent and safe to call on every GET to an admin page.
    """
    try:
      pages = (self.frequent_pages or [])[:]
    except Exception:
      pages = []

    now_iso = datetime.now(timezone.utc).isoformat()

    # Find existing entry
    existing = None
    for p in pages:
      if p.get('id') == page_id or p.get('endpoint') == endpoint:
        existing = p
        break

    if existing:
      existing['count'] = (existing.get('count') or 0) + 1
      existing['last_seen'] = now_iso
    else:
      pages.append({'id': page_id, 'name': name, 'endpoint': endpoint, 'count': 1, 'last_seen': now_iso})

    # Sort by last_seen desc and keep only top 3
    pages = sorted(pages, key=lambda x: x.get('last_seen', ''), reverse=True)[:3]

    self.frequent_pages = pages
    try:
      db.session.add(self)
      db.session.commit()
    except Exception:
      db.session.rollback()


class RefreshToken(db.Model):
  """Store hashed refresh tokens for rotation and revocation.

  Storing the hash allows revocation without keeping raw tokens in the DB.
  """
  __tablename__ = 'refresh_tokens'
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
  token_hash = db.Column(db.String(128), nullable=False, unique=True)
  jti = db.Column(db.String(100), nullable=True, index=True)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  expires_at = db.Column(db.DateTime)
  revoked = db.Column(db.Boolean, default=False)

  user = db.relationship('User', backref='refresh_tokens')
  
class Champion(db.Model):
  __tablename__ = 'champions'
  champion_id = db.Column(db.Integer, primary_key=True)
  # Link to user account (one-to-one)
  user_id = db.Column(
    db.Integer,
    db.ForeignKey(
      'users.user_id',
      ondelete='SET NULL',
      use_alter=True,
      name='fk_champions_user_id'
    )
  )
  
  #Link back to user account (explicit foreign_keys to avoid ambiguity)
  user = db.relationship('User', backref='champion_profile', uselist=False, foreign_keys=[user_id])

  #Supervisor link for assignment
  supervisor_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))  

  #Personal & Contact information
  full_name = db.Column(db.String(255), nullable=False)
  gender = db.Column(db.String(20), nullable=False)
  date_of_birth = db.Column(db.Date)
  phone_number = db.Column(db.String(20), unique=True, nullable=False)
  alternative_phone_number = db.Column(db.String(20))
  email = db.Column(db.String(100), unique=True, nullable=True)
  county_sub_county = db.Column(db.String(100))
  assigned_champion_code = db.Column(db.String(20), unique=True, nullable=False)
  
  # Emergency Contacts
  emergency_contact_name = db.Column(db.String(255))
  emergency_contact_relationship = db.Column(db.String(100))
  emergency_contact_phone = db.Column(db.String(20))

  # EDUCATION & OCCUPATION
  current_education_level = db.Column(db.String(100))  # High School, TVET, College, University, Graduate
  education_institution_name = db.Column(db.String(255))
  course_field_of_study = db.Column(db.String(255))
  year_of_study = db.Column(db.String(50))
  workplace_organization = db.Column(db.String(255))  # If out of school

  #UMV PROGRAM ENROLLMENT DATA
  date_of_application = db.Column(db.Date)
  recruitment_source = db.Column(db.String(100))  # Campus Edition, Mtaani, Referral, Social Media
  application_status = db.Column(db.String(50), default='Pending')  # Pending, Shortlisted, Recruited, Dropped
  screening_status = db.Column(db.String(100))  # Initial Assessment Completed / Missing
  assigned_cohort = db.Column(db.String(100))
  champion_status = db.Column(db.String(50), default='Active')  # Active, Inactive, On Hold

  # CONSENT & LEGAL COMPLIANCE
  consent_obtained = db.Column(db.Boolean, default=False)
  consent_date = db.Column(db.Date)
  consent_document_link = db.Column(db.String(500))  # URL/path to signed consent form
  legal_guardian_name = db.Column(db.String(255))  # if applicable for minors or institutional consent
  institution_name = db.Column(db.String(255))  # school or church name
  institution_consent_obtained = db.Column(db.Boolean, default=False)
  institution_consent_date = db.Column(db.Date)

  # HEALTH & SAFETY DATA
  medical_conditions = db.Column(db.Text)  # Chronic illnesses, health conditions
  allergies = db.Column(db.Text)  # Food, medication, environmental allergies
  mental_health_support = db.Column(db.Text)  # Mental health conditions, support needs
  disabilities = db.Column(db.Text)  # Physical or learning disabilities
  medication_required = db.Column(db.Text)  # Regular medications
  dietary_requirements = db.Column(db.Text)  # Special dietary needs
  health_notes = db.Column(db.Text)  # Additional confidential health information

  # RISK ASSESSMENT & SAFEGUARDING
  risk_level = db.Column(db.String(20), default='Low')  # Low, Medium, High
  risk_assessment_date = db.Column(db.Date)  # Last risk assessment date
  risk_notes = db.Column(db.Text)  # Risk assessment details
  last_contact_date = db.Column(db.Date)  # Last contact with champion
  next_review_date = db.Column(db.Date)  # Scheduled review date

  #Relationships to data tables
  support_records = db.relationship('YouthSupport', backref='champion', lazy='dynamic')
  training_records = db.relationship('TrainingRecord', backref='champion', lazy='dynamic')
  refferal_pathways = db.relationship('RefferalPathway', backref='champion', lazy='dynamic')
  
  @property
  def age(self):
    """Calculate age from date of birth."""
    if self.date_of_birth:
      today = date.today()
      return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    return None


class TrainingRecord(db.Model):
  __tablename__ = 'training_records'
  training_id = db.Column(db.Integer, primary_key=True)  # Fixed typo: was 'traning_record_id'
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'), nullable=False)
  training_module = db.Column(db.String(255), nullable=False)
  training_date = db.Column(db.Date)
  trainer_name = db.Column(db.String(255))
  training_location = db.Column(db.String(255))
  certification_status = db.Column(db.String(50))
  certificate_number = db.Column(db.String(100))
  next_refresher_due_date = db.Column(db.Date)
  
  # MHR-T Specific Fields
  is_mhrt = db.Column(db.Boolean, default=False)  # Mental Health Resilience Training
  mhrt_level = db.Column(db.String(50))  # Level 1, Level 2, Advanced, Master
  skills_acquired = db.Column(db.JSON)  # List of specific skills learned
  practical_hours = db.Column(db.Integer)  # Practical training hours completed
  
  # Symbolic Items
  symbolic_item_received = db.Column(db.Boolean, default=False)
  symbolic_item_type = db.Column(db.String(100))  # Badge, Kit, Certificate, etc.
  symbolic_item_date = db.Column(db.Date)

  __table_args__ = (db.UniqueConstraint('champion_id', 'training_module', name='_champion_module_uc'),)


class YouthSupport(db.Model):
  __tablename__ = 'youth_supports'
  support_id = db.Column(db.Integer, primary_key=True)
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'), nullable=False)
  reporting_period = db.Column(db.Date, nullable=False, default=datetime.utcnow)  

  #ROLE ASSIGNMENTS & OPERATIONAL DATA
  assigned_youth_group_cluster = db.Column(db.String(255))
  number_of_youth_under_support = db.Column(db.Integer)
  check_in_frequency = db.Column(db.String(50))  # Daily, Weekly, Bi-weekly
  weekly_check_in_completion_rate = db.Column(db.Numeric(5,2))
  monthly_mini_screenings_delivered = db.Column(db.Integer)
  referrals_initiated = db.Column(db.Integer)
  follow_up_actions_completed = db.Column(db.Integer)
  engagement_style = db.Column(db.String(100))  # one-on-one, small group, digital circles

  # FLAGGING & SAFEGUARDING
  flag_timestamp = db.Column(db.DateTime)  # when champion raised a flag/referral need

  #PERFORMANCE & ENGAGEMENT METRICS
  documentation_quality_score = db.Column(db.String(50))
  attendance_monthly_forums_percent = db.Column(db.Numeric(5,2))
  participation_in_umv_events = db.Column(db.Text)  # JSON or text list of events
  youth_feedback_score = db.Column(db.Numeric(3,2))  # Quarterly score
  peer_champion_rating = db.Column(db.Numeric(3,2))  # Internal scoring
  outstanding_contributions = db.Column(db.Text)
  flags_and_concerns_logged = db.Column(db.Text)  # lateness, absenteeism, breach

  #SAFEGUARDING & WELLBEING MONITORING
  safeguarding_training_completed = db.Column(db.Boolean, default=False)
  self_reported_wellbeing_check = db.Column(db.Integer)
  availability_for_duty = db.Column(db.Boolean, default=True)
  reported_incidents = db.Column(db.Text)
  supervisor_notes = db.Column(db.Text)
  safeguarding_notes = db.Column(db.Text)  # confidential supervisor-only notes
  referral_escalation_made = db.Column(db.Boolean, default=False)
  follow_up_status = db.Column(db.String(100))

  __table_args__ = (db.UniqueConstraint('champion_id', 'reporting_period', name='_champion_period_uc'),)


class RefferalPathway(db.Model):
  __tablename__ = 'refferal_pathways'
  refferal_id = db.Column(db.Integer, primary_key=True)
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'), nullable=False)  
  date_initiated = db.Column(db.Date, nullable=False, default=datetime.utcnow)

  #REFERRAL PATHWAY DATA
  youth_referred_number = db.Column(db.Integer)
  referral_reasons = db.Column(db.Text)
  referral_destinations = db.Column(db.String(255))
  referal_outcomes = db.Column(db.String(50))
  flag_to_referral_days = db.Column(db.Integer)  # SLA measurement from flag to referral
  feedback_from_service_provider = db.Column(db.Text)


class AccessAuditLog(db.Model):
  """Tracks who accessed sensitive champion data for privacy compliance."""
  __tablename__ = 'access_audit_logs'
  log_id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'))
  action = db.Column(db.String(100), nullable=False)  # e.g. 'viewed_profile', 'edited_report'
  timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
  ip_address = db.Column(db.String(50))
  details = db.Column(db.Text)  # additional context


def get_champions_needing_refresher(days_ahead=30):
  """Return champions whose next_refresher_due_date is within `days_ahead` days."""
  from datetime import timedelta
  cutoff = date.today() + timedelta(days=days_ahead)
  return (
    db.session.query(Champion, TrainingRecord)
    .join(TrainingRecord, Champion.champion_id == TrainingRecord.champion_id)
    .filter(TrainingRecord.next_refresher_due_date <= cutoff)
    .filter(TrainingRecord.next_refresher_due_date >= date.today())
    .all()
  )


def get_high_risk_champions():
  """Return all champions with High risk level."""
  return Champion.query.filter_by(risk_level='High').all()


def get_overdue_reviews():
  """Return champions with overdue review dates."""
  today = date.today()
  return Champion.query.filter(
    Champion.next_review_date < today
  ).filter(
    Champion.next_review_date.isnot(None)
  ).all()


def get_champions_by_risk_level(risk_level):
  """Return champions filtered by risk level (Low, Medium, High)."""
  return Champion.query.filter_by(risk_level=risk_level).all() 


# ============================================================================
# MENTAL HEALTH ASSESSMENT UTILITY FUNCTIONS - PRIVACY-FIRST
# ============================================================================

def map_phq9_to_risk_category(score):
  """
  Convert PHQ-9 score (0-27) to color-coded risk category.
  PHQ-9 measures depression severity.
  
  Returns dict with risk_category, score_range, and description.
  RAW SCORE IS NOT STORED - only the risk category.
  """
  if not isinstance(score, (int, float)) or score < 0 or score > 27:
    return {
      'risk_category': 'Invalid',
      'score_range': 'Invalid',
      'description': 'Invalid Score',
      'auto_flag': False,
      'auto_referral': False
    }
  
  if 0 <= score <= 4:
    return {
      'risk_category': 'Green',
      'score_range': '0-4',
      'description': 'Minimal or no depression',
      'auto_flag': False,
      'auto_referral': False
    }
  elif 5 <= score <= 9:
    return {
      'risk_category': 'Blue',
      'score_range': '5-9',
      'description': 'Mild depression',
      'auto_flag': False,
      'auto_referral': False
    }
  elif 10 <= score <= 14:
    return {
      'risk_category': 'Purple',
      'score_range': '10-14',
      'description': 'Moderate depression',
      'auto_flag': True,
      'auto_referral': False
    }
  elif 15 <= score <= 19:
    return {
      'risk_category': 'Orange',
      'score_range': '15-19',
      'description': 'Moderately severe depression',
      'auto_flag': True,
      'auto_referral': True
    }
  else:  # 20-27
    return {
      'risk_category': 'Red',
      'score_range': '20-27',
      'description': 'Severe depression',
      'auto_flag': True,
      'auto_referral': True
    }


def map_gad7_to_risk_category(score):
  """
  Convert GAD-7 score (0-21) to color-coded risk category.
  GAD-7 measures anxiety severity.
  
  Returns dict with risk_category, score_range, and description.
  RAW SCORE IS NOT STORED - only the risk category.
  """
  if not isinstance(score, (int, float)) or score < 0 or score > 21:
    return {
      'risk_category': 'Invalid',
      'score_range': 'Invalid',
      'description': 'Invalid Score',
      'auto_flag': False,
      'auto_referral': False
    }
  
  if 0 <= score <= 4:
    return {
      'risk_category': 'Green',
      'score_range': '0-4',
      'description': 'Minimal anxiety',
      'auto_flag': False,
      'auto_referral': False
    }
  elif 5 <= score <= 9:
    return {
      'risk_category': 'Blue',
      'score_range': '5-9',
      'description': 'Mild anxiety',
      'auto_flag': False,
      'auto_referral': False
    }
  elif 10 <= score <= 14:
    return {
      'risk_category': 'Purple',
      'score_range': '10-14',
      'description': 'Moderate anxiety',
      'auto_flag': True,
      'auto_referral': False
    }
  else:  # 15-21
    return {
      'risk_category': 'Red',
      'score_range': '15-21',
      'description': 'Severe anxiety',
      'auto_flag': True,
      'auto_referral': True
    }


def generate_champion_code():
  """
  Generate unique champion code in format: UMV-YYYY-NNNNNN
  Example: UMV-2026-000001
  """
  from datetime import datetime
  import random
  
  year = datetime.now().year
  
  # Find the highest existing code for this year
  prefix = f"UMV-{year}-"
  existing_codes = db.session.query(Champion.assigned_champion_code)\
    .filter(Champion.assigned_champion_code.like(f"{prefix}%"))\
    .all()
  
  if existing_codes:
    # Extract numbers and find max
    numbers = [int(code[0].split('-')[-1]) for code in existing_codes if code[0]]
    next_number = max(numbers) + 1 if numbers else 1
  else:
    next_number = 1
  
  # Format with 6 digits, zero-padded
  return f"{prefix}{next_number:06d}"


# ============================================================================


class Event(db.Model):
  """Events and activities for the UNDA Youth Network."""
  __tablename__ = 'events'
  
  event_id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(255), nullable=False)
  description = db.Column(db.Text)
  event_date = db.Column(db.DateTime, nullable=False)
  location = db.Column(db.String(255))
  event_type = db.Column(db.String(100))  # Workshop, Training, Community Event, etc.
  organizer = db.Column(db.String(255))
  max_participants = db.Column(db.Integer)
  registration_deadline = db.Column(db.DateTime)
  status = db.Column(db.String(50), default='Upcoming')  # Upcoming, Ongoing, Completed, Cancelled
  image_url = db.Column(db.String(500))
  motion = db.Column(db.Text)  # Debate motion/topic for Debaters Circle events
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  created_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))

  def to_dict(self):
    return {
      # Snake case for Python/backend compatibility
      'event_id': self.event_id,
      'title': self.title,
      'description': self.description,
      'event_date': self.event_date.isoformat() if self.event_date else None,
      'location': self.location,
      'event_type': self.event_type,
      'organizer': self.organizer,
      'max_participants': self.max_participants,
      'registration_deadline': self.registration_deadline.isoformat() if self.registration_deadline else None,
      'status': self.status,
      'image_url': self.image_url,
      'motion': self.motion,
      'created_at': self.created_at.isoformat() if self.created_at else None,
      'updated_at': self.updated_at.isoformat() if self.updated_at else None,
      'created_by': self.created_by,
      # CamelCase aliases for JavaScript/React frontend compatibility
      'id': self.event_id,
      'eventDate': self.event_date.isoformat() if self.event_date else None,
      'eventType': self.event_type,
      'maxParticipants': self.max_participants,
      'registrationDeadline': self.registration_deadline.isoformat() if self.registration_deadline else None,
      'imageUrl': self.image_url,
      'createdAt': self.created_at.isoformat() if self.created_at else None,
      'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
      'createdBy': self.created_by
    }


class BlogPost(db.Model):
  """Blog posts and articles for the UNDA Youth Network."""
  __tablename__ = 'blog_posts'
  
  post_id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(255), nullable=False)
  slug = db.Column(db.String(255), unique=True, nullable=False)
  content = db.Column(db.Text, nullable=False)
  excerpt = db.Column(db.Text)
  author_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  category = db.Column(db.String(100))  # Success Stories, News, Updates, etc.
  tags = db.Column(db.JSON)  # Array of tags
  featured_image = db.Column(db.String(500))
  published = db.Column(db.Boolean, default=False)
  published_at = db.Column(db.DateTime)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  views = db.Column(db.Integer, default=0)
  
  # Relationships
  author = db.relationship('User', backref='blog_posts', foreign_keys=[author_id])

  def to_dict(self):
    return {
      # Snake case for Python/backend compatibility
      'post_id': self.post_id,
      'title': self.title,
      'slug': self.slug,
      'content': self.content,
      'excerpt': self.excerpt,
      'author_id': self.author_id,
      'category': self.category,
      'tags': self.tags or [],
      'featured_image': self.featured_image,
      'published': self.published,
      'published_at': self.published_at.isoformat() if self.published_at else None,
      'created_at': self.created_at.isoformat() if self.created_at else None,
      'updated_at': self.updated_at.isoformat() if self.updated_at else None,
      'views': self.views,
      # CamelCase aliases for JavaScript/React frontend compatibility
      'id': self.post_id,
      'authorId': self.author_id,
      'featuredImage': self.featured_image,
      'publishedAt': self.published_at.isoformat() if self.published_at else None,
      'createdAt': self.created_at.isoformat() if self.created_at else None,
      'updatedAt': self.updated_at.isoformat() if self.updated_at else None
    }


class MentalHealthAssessment(db.Model):
  """
  Mental health screening assessments - PRIVACY-FIRST DESIGN
  PHQ-9 and GAD-7 only. Stores color-coded risk categories, NOT raw scores.
  Uses champion_code for anonymized tracking, not champion_id.
  """
  __tablename__ = 'mental_health_assessments'
  
  assessment_id = db.Column(db.Integer, primary_key=True)
  
  # PRIVACY: Use champion code instead of foreign key to champion_id
  champion_code = db.Column(db.String(20), nullable=False, index=True)  # UMV-YYYY-NNNNNN
  
  assessment_type = db.Column(db.String(50), nullable=False)  # PHQ-9, GAD-7
  assessment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
  
  # PRIVACY: Color-coded risk categories instead of raw scores
  # Green (0-4), Blue (5-9), Purple (10-14), Orange (15-19), Red (20-27 PHQ-9 or 15-21 GAD-7)
  risk_category = db.Column(db.String(20), nullable=False)  # Green, Blue, Purple, Orange, Red
  score_range = db.Column(db.String(20))  # e.g., "0-4", "5-9", "10-14", "15-19", "20-27"
  
  # Assessment Context
  is_baseline = db.Column(db.Boolean, default=False)  # True for initial screening
  assessment_period = db.Column(db.String(50))  # Initial, Monthly, Quarterly, Follow-up
  
  # REMOVED: total_score, severity_level, item_scores - PRIVACY VIOLATION
  
  # Clinical actions
  risk_flagged = db.Column(db.Boolean, default=False)  # Auto-set for Orange/Red
  referral_recommended = db.Column(db.Boolean, default=False)  # Auto-set for Orange/Red
  referral_made = db.Column(db.Boolean, default=False)  # Set when referral is created
  
  # Tracking - who administered (not who was assessed)
  administered_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  notes = db.Column(db.Text)  # Non-identifiable notes only
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  
  # NO relationship to Champion model - privacy by design


class DailyAffirmation(db.Model):
  """Daily affirmation messages for champion wellbeing support."""
  __tablename__ = 'daily_affirmations'
  
  affirmation_id = db.Column(db.Integer, primary_key=True)
  content = db.Column(db.Text, nullable=False)
  theme = db.Column(db.String(100))  # Resilience, Self-care, Growth, Leadership, etc.
  
  # Scheduling
  scheduled_date = db.Column(db.Date)
  active = db.Column(db.Boolean, default=True)
  
  # Delivery tracking
  times_sent = db.Column(db.Integer, default=0)
  
  # Metadata
  created_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

  def to_dict(self):
    return {
      # Snake case for Python/backend compatibility
      'affirmation_id': self.affirmation_id,
      'content': self.content,
      'theme': self.theme,
      'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
      'active': self.active,
      'times_sent': self.times_sent,
      'created_by': self.created_by,
      'created_at': self.created_at.isoformat() if self.created_at else None,
      'updated_at': self.updated_at.isoformat() if self.updated_at else None,
      # CamelCase aliases for JavaScript/React frontend compatibility
      'id': self.affirmation_id,
      'scheduledDate': self.scheduled_date.isoformat() if self.scheduled_date else None,
      'timesSent': self.times_sent,
      'createdBy': self.created_by,
      'createdAt': self.created_at.isoformat() if self.created_at else None,
      'updatedAt': self.updated_at.isoformat() if self.updated_at else None
    }


class AffirmationDelivery(db.Model):
  """Tracks affirmation delivery to individual champions."""
  __tablename__ = 'affirmation_deliveries'
  
  delivery_id = db.Column(db.Integer, primary_key=True)
  affirmation_id = db.Column(db.Integer, db.ForeignKey('daily_affirmations.affirmation_id', ondelete='CASCADE'), nullable=False)
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'), nullable=False)
  
  # Delivery details
  delivery_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
  delivery_method = db.Column(db.String(50))  # SMS, Email, App Push, WhatsApp
  
  # Engagement tracking
  viewed = db.Column(db.Boolean, default=False)
  viewed_at = db.Column(db.DateTime)
  liked = db.Column(db.Boolean, default=False)
  
  # Relationships
  affirmation = db.relationship('DailyAffirmation', backref='deliveries')
  champion = db.relationship('Champion', backref='affirmation_deliveries')


class EventParticipation(db.Model):
  """Tracks champion participation in events (especially quarterly pillar events)."""
  __tablename__ = 'event_participations'
  
  participation_id = db.Column(db.Integer, primary_key=True)
  event_id = db.Column(db.Integer, db.ForeignKey('events.event_id', ondelete='CASCADE'), nullable=False)
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'), nullable=False)
  
  # Registration
  registered_at = db.Column(db.DateTime, default=datetime.utcnow)
  registration_status = db.Column(db.String(50), default='Registered')  # Registered, Waitlisted, Cancelled
  
  # Attendance
  attended = db.Column(db.Boolean, default=False)
  attendance_confirmed_at = db.Column(db.DateTime)
  attendance_confirmed_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  
  # Engagement
  feedback_score = db.Column(db.Integer)  # 1-10 rating
  feedback_comments = db.Column(db.Text)
  certificate_issued = db.Column(db.Boolean, default=False)
  
  # Relationships
  event = db.relationship('Event', backref='participations')
  champion = db.relationship('Champion', backref='event_participations')


class SymbolicItem(db.Model):
  """Inventory and distribution of symbolic items (badges, kits, certificates)."""
  __tablename__ = 'symbolic_items'
  
  item_id = db.Column(db.Integer, primary_key=True)
  item_name = db.Column(db.String(255), nullable=False)
  item_type = db.Column(db.String(100))  # Badge, Certificate, Resilience Kit, T-Shirt, etc.
  description = db.Column(db.Text)
  
  # Association with training/events
  linked_to_training_module = db.Column(db.String(255))  # e.g., "MHR-T Level 1"
  linked_to_event_type = db.Column(db.String(100))  # e.g., "Quarterly Pillar Event"
  
  # Inventory
  total_quantity = db.Column(db.Integer, default=0)
  distributed_quantity = db.Column(db.Integer, default=0)
  
  # Metadata
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

  def to_dict(self):
    return {
      # Snake case for Python/backend compatibility
      'item_id': self.item_id,
      'item_name': self.item_name,
      'item_type': self.item_type,
      'description': self.description,
      'linked_to_training_module': self.linked_to_training_module,
      'linked_to_event_type': self.linked_to_event_type,
      'total_quantity': self.total_quantity,
      'distributed_quantity': self.distributed_quantity,
      'available_quantity': self.total_quantity - self.distributed_quantity,
      'created_at': self.created_at.isoformat() if self.created_at else None,
      'updated_at': self.updated_at.isoformat() if self.updated_at else None,
      # CamelCase aliases for JavaScript/React frontend compatibility
      'id': self.item_id,
      'itemName': self.item_name,
      'itemType': self.item_type,
      'linkedToTrainingModule': self.linked_to_training_module,
      'linkedToEventType': self.linked_to_event_type,
      'totalQuantity': self.total_quantity,
      'distributedQuantity': self.distributed_quantity,
      'availableQuantity': self.total_quantity - self.distributed_quantity,
      'createdAt': self.created_at.isoformat() if self.created_at else None,
      'updatedAt': self.updated_at.isoformat() if self.updated_at else None
    }


class MediaGallery(db.Model):
  """Media gallery for images/videos used in blog posts and campaigns."""
  __tablename__ = 'media_gallery'

  gallery_id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(255), nullable=False)
  description = db.Column(db.Text)
  media_items = db.Column(db.JSON)  # list of {url, type, caption, metadata}
  featured_media = db.Column(db.String(500))
  published = db.Column(db.Boolean, default=False)
  published_at = db.Column(db.DateTime)
  created_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

  def to_dict(self):
    return {
      'gallery_id': self.gallery_id,
      'title': self.title,
      'description': self.description,
      'media_items': self.media_items or [],
      'featured_media': self.featured_media,
      'published': self.published,
      'published_at': self.published_at.isoformat() if self.published_at else None,
      'created_by': self.created_by,
      'created_at': self.created_at.isoformat() if self.created_at else None,
      'updated_at': self.updated_at.isoformat() if self.updated_at else None,
      'id': self.gallery_id,
      'featuredMedia': self.featured_media,
      'publishedAt': self.published_at.isoformat() if self.published_at else None,
      'createdAt': self.created_at.isoformat() if self.created_at else None,
      'updatedAt': self.updated_at.isoformat() if self.updated_at else None
    }


class InstitutionalToolkitItem(db.Model):
  """Items for the institutional toolkit: guides, templates, checklists."""
  __tablename__ = 'institutional_toolkit'

  item_id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(255), nullable=False)
  summary = db.Column(db.Text)
  content = db.Column(db.Text)
  attachments = db.Column(db.JSON)  # list of {url, label, mime}
  category = db.Column(db.String(100))
  published = db.Column(db.Boolean, default=False)
  created_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

  def to_dict(self):
    return {
      'item_id': self.item_id,
      'title': self.title,
      'summary': self.summary,
      'content': self.content,
      'attachments': self.attachments or [],
      'category': self.category,
      'published': self.published,
      'created_by': self.created_by,
      'created_at': self.created_at.isoformat() if self.created_at else None,
      'updated_at': self.updated_at.isoformat() if self.updated_at else None,
      'id': self.item_id,
      'createdAt': self.created_at.isoformat() if self.created_at else None,
      'updatedAt': self.updated_at.isoformat() if self.updated_at else None
    }


class UMVGlobalEntry(db.Model):
  """Small key/value entries for UMV global config-like content (announcements, short items)."""
  __tablename__ = 'umv_global'

  entry_id = db.Column(db.Integer, primary_key=True)
  key = db.Column(db.String(255), nullable=False, unique=True)
  value = db.Column(db.Text)
  meta = db.Column('metadata', db.JSON)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

  def to_dict(self):
    return {
      'entry_id': self.entry_id,
      'key': self.key,
      'value': self.value,
      'metadata': self.meta or {},
      'created_at': self.created_at.isoformat() if self.created_at else None,
      'updated_at': self.updated_at.isoformat() if self.updated_at else None,
      'id': self.entry_id
    }


class ResourceItem(db.Model):
  """External/internal resources (links, PDFs, learning resources)."""
  __tablename__ = 'resources'

  resource_id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(255), nullable=False)
  url = db.Column(db.String(1000))
  description = db.Column(db.Text)
  resource_type = db.Column(db.String(100))  # Guide, External Link, Dataset, Video
  tags = db.Column(db.JSON)
  published = db.Column(db.Boolean, default=False)
  published_at = db.Column(db.DateTime)
  created_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

  def to_dict(self):
    return {
      'resource_id': self.resource_id,
      'title': self.title,
      'url': self.url,
      'description': self.description,
      'resource_type': self.resource_type,
      'tags': self.tags or [],
      'published': self.published,
      'published_at': self.published_at.isoformat() if self.published_at else None,
      'created_by': self.created_by,
      'created_at': self.created_at.isoformat() if self.created_at else None,
      'updated_at': self.updated_at.isoformat() if self.updated_at else None,
      'id': self.resource_id,
      'resourceType': self.resource_type,
      'publishedAt': self.published_at.isoformat() if self.published_at else None
    }


class ItemDistribution(db.Model):
  """Tracks distribution of symbolic items to champions."""
  __tablename__ = 'item_distributions'
  
  distribution_id = db.Column(db.Integer, primary_key=True)
  item_id = db.Column(db.Integer, db.ForeignKey('symbolic_items.item_id', ondelete='CASCADE'), nullable=False)
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'), nullable=False)
  
  # Distribution details
  distributed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
  distributed_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  distribution_reason = db.Column(db.String(255))  # Training completion, Event participation, etc.
  
  # Linked records
  training_record_id = db.Column(db.Integer, db.ForeignKey('training_records.training_id', ondelete='SET NULL'))
  event_participation_id = db.Column(db.Integer, db.ForeignKey('event_participations.participation_id', ondelete='SET NULL'))
  
  notes = db.Column(db.Text)
  
  # Relationships
  item = db.relationship('SymbolicItem', backref='distributions')
  champion = db.relationship('Champion', backref='item_distributions')


class MemberRegistration(db.Model):
  """Model for tracking member registration requests"""
  __tablename__ = 'member_registrations'
  
  registration_id = db.Column(db.Integer, primary_key=True)
  full_name = db.Column(db.String(255), nullable=False)
  email = db.Column(db.String(100), nullable=True)
  phone_number = db.Column(db.String(20), nullable=False)
  username = db.Column(db.String(100), unique=True, nullable=False)
  password_hash = db.Column(db.String(255), nullable=False)
  
  # Additional info
  date_of_birth = db.Column(db.Date)
  gender = db.Column(db.String(20))
  county_sub_county = db.Column(db.String(100))
  
  # Status tracking
  status = db.Column(db.String(50), default='Pending')  # Pending, Approved, Rejected
  submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
  reviewed_at = db.Column(db.DateTime)
  reviewed_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  rejection_reason = db.Column(db.Text)
  
  # Created user reference
  created_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  
  # Token to allow a registrant to cancel their pending registration
  cancellation_token = db.Column(db.String(64), nullable=True, unique=True)
  
  def set_password(self, password):
    self.password_hash = hash_password(password)


class Certificate(db.Model):
    """Issued membership certificates (stored as PDF blobs with a signature)."""
    __tablename__ = 'certificates'

    certificate_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    pdf_data = db.Column(db.LargeBinary)  # Raw PDF bytes
    signature = db.Column(db.String(255), nullable=False)  # HMAC or JWT

    user = db.relationship('User', backref='certificates')


class ChampionApplication(db.Model):
  """Model for tracking champion applications from registered members"""
  __tablename__ = 'champion_applications'
  
  application_id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
  
  # Application details
  full_name = db.Column(db.String(255), nullable=False)
  email = db.Column(db.String(100), nullable=True)
  phone_number = db.Column(db.String(20), nullable=False)
  alternative_phone_number = db.Column(db.String(20))
  
  # Personal information
  gender = db.Column(db.String(20), nullable=False)
  date_of_birth = db.Column(db.Date, nullable=False)
  county_sub_county = db.Column(db.String(100))
  
  # Emergency contact
  emergency_contact_name = db.Column(db.String(255))
  emergency_contact_relationship = db.Column(db.String(100))
  emergency_contact_phone = db.Column(db.String(20))
  
  # Education & occupation
  current_education_level = db.Column(db.String(100))
  education_institution_name = db.Column(db.String(255))
  course_field_of_study = db.Column(db.String(255))
  year_of_study = db.Column(db.String(50))
  workplace_organization = db.Column(db.String(255))
  
  # Why they want to be a champion
  motivation = db.Column(db.Text)
  skills_interests = db.Column(db.Text)
  
  # Status tracking
  status = db.Column(db.String(50), default='Pending')  # Pending, Approved, Rejected
  submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
  reviewed_at = db.Column(db.DateTime)
  reviewed_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  rejection_reason = db.Column(db.Text)
  
  # Created champion reference
  created_champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='SET NULL'))
  
  # Relationships
  user = db.relationship('User', foreign_keys=[user_id], backref='champion_applications')


class SeedFundingApplication(db.Model):
  """Model for tracking seed funding applications from members under Campus Edition"""
  __tablename__ = 'seed_funding_applications'
  
  application_id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'))
  
  # Applicant Information (can be member or champion)
  applicant_name = db.Column(db.String(255), nullable=False)
  email = db.Column(db.String(100), nullable=True)
  phone_number = db.Column(db.String(20), nullable=False)
  institution_name = db.Column(db.String(255))  # University, College, etc.
  student_id_number = db.Column(db.String(100))
  
  # Project Information
  project_title = db.Column(db.String(255), nullable=False)
  project_description = db.Column(db.Text, nullable=False)
  project_category = db.Column(db.String(100))  # Mental Health Awareness, Community Service, etc.
  target_beneficiaries = db.Column(db.String(255))  # Who will benefit
  expected_impact = db.Column(db.Text)  # Expected outcomes
  
  # Budget Information
  total_budget_requested = db.Column(db.Numeric(10, 2), nullable=False)  # Amount in KES
  budget_breakdown = db.Column(db.JSON)  # Detailed budget items
  other_funding_sources = db.Column(db.Text)  # Other funding if any
  
  # Timeline
  project_start_date = db.Column(db.Date)
  project_end_date = db.Column(db.Date)
  implementation_timeline = db.Column(db.Text)  # Detailed timeline
  
  # Supporting Documents
  proposal_document_url = db.Column(db.String(500))  # Link to full proposal
  budget_document_url = db.Column(db.String(500))  # Link to detailed budget
  
  # Team Information
  team_members = db.Column(db.JSON)  # Array of team member details
  team_size = db.Column(db.Integer)
  
  # Application Status
  status = db.Column(db.String(50), default='Pending')  # Pending, Under Review, Approved, Rejected, Funded
  submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
  reviewed_at = db.Column(db.DateTime)
  reviewed_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  
  # Approval Details
  approved_amount = db.Column(db.Numeric(10, 2))  # May be less than requested
  approval_conditions = db.Column(db.Text)  # Any conditions for funding
  rejection_reason = db.Column(db.Text)
  admin_notes = db.Column(db.Text)  # Internal notes
  
  # Funding Disbursement
  disbursement_date = db.Column(db.Date)
  disbursement_method = db.Column(db.String(100))  # M-Pesa, Bank Transfer, etc.
  disbursement_reference = db.Column(db.String(255))
  
  # Relationships
  applicant = db.relationship('User', foreign_keys=[user_id], backref='seed_funding_applications')
  reviewer = db.relationship('User', foreign_keys=[reviewed_by])
  
  def to_dict(self):
    return {
      # Snake case for Python
      'application_id': self.application_id,
      'user_id': self.user_id,
      'applicant_name': self.applicant_name,
      'email': self.email,
      'phone_number': self.phone_number,
      'institution_name': self.institution_name,
      'student_id_number': self.student_id_number,
      'project_title': self.project_title,
      'project_description': self.project_description,
      'project_category': self.project_category,
      'target_beneficiaries': self.target_beneficiaries,
      'expected_impact': self.expected_impact,
      'total_budget_requested': float(self.total_budget_requested) if self.total_budget_requested else None,
      'budget_breakdown': self.budget_breakdown or [],
      'other_funding_sources': self.other_funding_sources,
      'project_start_date': self.project_start_date.isoformat() if self.project_start_date else None,
      'project_end_date': self.project_end_date.isoformat() if self.project_end_date else None,
      'implementation_timeline': self.implementation_timeline,
      'proposal_document_url': self.proposal_document_url,
      'budget_document_url': self.budget_document_url,
      'team_members': self.team_members or [],
      'team_size': self.team_size,
      'status': self.status,
      'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
      'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
      'reviewed_by': self.reviewed_by,
      'approved_amount': float(self.approved_amount) if self.approved_amount else None,
      'approval_conditions': self.approval_conditions,
      'rejection_reason': self.rejection_reason,
      'admin_notes': self.admin_notes,
      'disbursement_date': self.disbursement_date.isoformat() if self.disbursement_date else None,
      'disbursement_method': self.disbursement_method,
      'disbursement_reference': self.disbursement_reference,
      # CamelCase for JavaScript/React
      'id': self.application_id,
      'userId': self.user_id,
      'applicantName': self.applicant_name,
      'phoneNumber': self.phone_number,
      'institutionName': self.institution_name,
      'studentIdNumber': self.student_id_number,
      'projectTitle': self.project_title,
      'projectDescription': self.project_description,
      'projectCategory': self.project_category,
      'targetBeneficiaries': self.target_beneficiaries,
      'expectedImpact': self.expected_impact,
      'totalBudgetRequested': float(self.total_budget_requested) if self.total_budget_requested else None,
      'budgetBreakdown': self.budget_breakdown or [],
      'otherFundingSources': self.other_funding_sources,
      'projectStartDate': self.project_start_date.isoformat() if self.project_start_date else None,
      'projectEndDate': self.project_end_date.isoformat() if self.project_end_date else None,
      'implementationTimeline': self.implementation_timeline,
      'proposalDocumentUrl': self.proposal_document_url,
      'budgetDocumentUrl': self.budget_document_url,
      'teamMembers': self.team_members or [],
      'teamSize': self.team_size,
      'submittedAt': self.submitted_at.isoformat() if self.submitted_at else None,
      'reviewedAt': self.reviewed_at.isoformat() if self.reviewed_at else None,
      'reviewedBy': self.reviewed_by,
      'approvedAmount': float(self.approved_amount) if self.approved_amount else None,
      'approvalConditions': self.approval_conditions,
      'rejectionReason': self.rejection_reason,
      'adminNotes': self.admin_notes,
      'disbursementDate': self.disbursement_date.isoformat() if self.disbursement_date else None,
      'disbursementMethod': self.disbursement_method,
      'disbursementReference': self.disbursement_reference
    }


class Podcast(db.Model):
  __tablename__ = 'podcasts'
  
  podcast_id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(255), nullable=False)
  description = db.Column(db.Text)
  guest = db.Column(db.String(255))  # Guest name
  audio_url = db.Column(db.String(500), nullable=False)
  thumbnail_url = db.Column(db.String(500))
  duration = db.Column(db.Integer)  # Duration in seconds
  episode_number = db.Column(db.Integer)
  season_number = db.Column(db.Integer)
  category = db.Column(db.String(100))
  tags = db.Column(db.JSON)  # Array of tags
  published = db.Column(db.Boolean, default=False)
  published_at = db.Column(db.DateTime)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  created_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  
  # Relationships
  creator = db.relationship('User', backref='podcasts')
  
  def to_dict(self):
    return {
      # Snake case for Python/backend compatibility
      'podcast_id': self.podcast_id,
      'title': self.title,
      'description': self.description,
      'guest': self.guest,
      'audio_url': self.audio_url,
      'thumbnail_url': self.thumbnail_url,
      'duration': self.duration,
      'episode_number': self.episode_number,
      'season_number': self.season_number,
      'category': self.category,
      'tags': self.tags or [],
      'published': self.published,
      'published_at': self.published_at.isoformat() if self.published_at else None,
      'created_at': self.created_at.isoformat() if self.created_at else None,
      'updated_at': self.updated_at.isoformat() if self.updated_at else None,
      'created_by': self.created_by,
      # CamelCase aliases for JavaScript/React frontend compatibility
      'id': self.podcast_id,
      'audioUrl': self.audio_url,
      'thumbnailUrl': self.thumbnail_url,
      'episodeNumber': self.episode_number,
      'seasonNumber': self.season_number,
      'publishedAt': self.published_at.isoformat() if self.published_at else None,
      'createdAt': self.created_at.isoformat() if self.created_at else None,
      'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
      'createdBy': self.created_by
    }















