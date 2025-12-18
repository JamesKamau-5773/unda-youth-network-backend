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
  traning_record_id = db.Column(db.Integer, primary_key=True)
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'), nullable=False)
  training_module = db.Column(db.String(255), nullable=False)
  training_date = db.Column(db.Date)
  trainer_name = db.Column(db.String(255))
  training_location = db.Column(db.String(255))
  certification_status = db.Column(db.String(50))
  certificate_number = db.Column(db.String(100))
  next_refresher_due_date = db.Column(db.Date)

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







