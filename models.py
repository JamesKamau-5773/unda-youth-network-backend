from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date
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
  
  # Valid roles constant
  VALID_ROLES = ['Admin', 'Supervisor', 'Champion']
  
  user_id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(100), unique=True, nullable=False)
  password_hash = db.Column(db.String(255), nullable=False)
  role = db.Column(db.String(50), nullable=False, default='Champion')

  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='SET NULL'))

  supervised_champion_ids = db.Column(db.JSON)
  
  # Account lockout fields
  failed_login_attempts = db.Column(db.Integer, default=0)
  account_locked = db.Column(db.Boolean, default=False)
  locked_until = db.Column(db.DateTime)

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
      normalized_role = role.capitalize()
      if normalized_role in self.VALID_ROLES:
        self.role = normalized_role
      else:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {', '.join(self.VALID_ROLES)}")
    else:
      self.role = 'Champion'  # Default
  
  def validate_role(self):
    """Validate and normalize the current role."""
    if self.role:
      normalized = self.role.capitalize()
      if normalized not in self.VALID_ROLES:
        raise ValueError(f"Invalid role '{self.role}'. Must be one of: {', '.join(self.VALID_ROLES)}")
      self.role = normalized
    else:
      self.role = 'Champion'
  
  def is_locked(self):
    """Check if account is currently locked."""
    if self.account_locked and self.locked_until:
      if datetime.utcnow() < self.locked_until:
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
      self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    db.session.commit()
  
  def reset_failed_logins(self):
    """Reset failed login counter after successful login."""
    self.failed_login_attempts = 0
    self.account_locked = False
    self.locked_until = None
    db.session.commit()
  
class Champion(db.Model):
  __tablename__ = 'champions'
  champion_id = db.Column(db.Integer, primary_key=True)
  # Link to user account (one-to-one)
  user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  
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
  email = db.Column(db.String(100), unique=True, nullable=False)
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
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  created_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))


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


class MentalHealthAssessment(db.Model):
  """Mental health screening assessments (PHQ-9, GAD-7, PHQ-2, GAD-2)."""
  __tablename__ = 'mental_health_assessments'
  
  assessment_id = db.Column(db.Integer, primary_key=True)
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'), nullable=False)
  assessment_type = db.Column(db.String(50), nullable=False)  # PHQ-9, GAD-7, PHQ-2, GAD-2
  assessment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
  
  # Scoring
  total_score = db.Column(db.Integer, nullable=False)
  severity_level = db.Column(db.String(50))  # None, Mild, Moderate, Moderately Severe, Severe
  
  # Assessment Context
  is_baseline = db.Column(db.Boolean, default=False)  # True for initial screening
  assessment_period = db.Column(db.String(50))  # Initial, Monthly, Quarterly, Follow-up
  
  # Individual item scores (JSON for flexibility across different assessments)
  item_scores = db.Column(db.JSON)  # e.g., {"q1": 2, "q2": 1, "q3": 3, ...}
  
  # Clinical actions
  risk_flagged = db.Column(db.Boolean, default=False)
  referral_recommended = db.Column(db.Boolean, default=False)
  referral_made = db.Column(db.Boolean, default=False)
  
  # Tracking
  administered_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'))
  notes = db.Column(db.Text)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  
  # Relationships
  champion = db.relationship('Champion', backref='mental_health_assessments')


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
















