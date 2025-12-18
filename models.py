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

  #Implement UserMixin required methord
  def get_id(self):
    return str(self.user_id)
  
  def set_password(self, password):
    self.password_hash = hash_password(password)

  def check_password(self, password):
    return check_password(password, self.password_hash)
  
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
  date_of_birth = db.Column(db.Date )
  phone_number = db.Column(db.String(20), unique=True, nullable=False)
  email = db.Column(db.String(100), unique=True, nullable=False)
  county_sub_county = db.Column(db.String(100))
  assigned_champion_code = db.Column(db.String(20), unique=True, nullable=False)

  #UMV PROGRAM ENROLLMENT DATA
  date_of_application = db.Column(db.Date)
  recruitment_source = db.Column(db.String(100))
  assigned_cohort = db.Column(db.String(100))

  #Relationships to data tables
  support_records = db.relationship('YouthSupport', backref='champion', lazy='dynamic')
  training_records = db.relationship('TrainingRecord', backref='champion', lazy='dynamic')
  refferal_pathways = db.relationship('RefferalPathway', backref='champion', lazy='dynamic')


class TrainingRecord(db.Model):
  __tablename__ = 'training_records'
  traning_record_id = db.Column(db.Integer, primary_key=True)
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'), nullable=False)
  training_module = db.Column(db.String(255), nullable=False)
  training_date = db.Column(db.Date)
  certification_status = db.Column(db.String(50))
  next_refresher_due_date = db.Column(db.Date)

  __table_args__ = (db.UniqueConstraint('champion_id', 'training_module', name='_champion_module_uc'),)


class YouthSupport(db.Model):
  __tablename__ = 'youth_supports'
  support_id = db.Column(db.Integer, primary_key=True)
  champion_id = db.Column(db.Integer, db.ForeignKey('champions.champion_id', ondelete='CASCADE'), nullable=False)
  reporting_period = db.Column(db.Date, nullable=False, default=datetime.utcnow)  

  #OPERATIONAL DATA
  weekly_check_in_completion_rate = db.Column(db.Numeric(5,2))
  monthly_mini_screenings_delivered = db.Column(db.Integer)
  referrals_initiated = db.Column(db.Integer)

  # FLAGGING & SAFEGUARDING
  flag_timestamp = db.Column(db.DateTime)  # when champion raised a flag/referral need

  #PERFOMANCE & ENGAGEMENT METRICS
  documentation_quality_score = db.Column(db.String(50))

  #SAFEGUARDING & WELLBEING MONITORING
  self_reported_wellbeing_check = db.Column(db.Integer)
  supervisor_notes = db.Column(db.Text)
  safeguarding_notes = db.Column(db.Text)  # confidential supervisor-only notes

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







