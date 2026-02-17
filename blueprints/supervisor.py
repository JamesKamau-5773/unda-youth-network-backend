from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash as flask_flash, abort, current_app
from flask_login import login_required, current_user
from models import db, Champion, YouthSupport, RefferalPathway, AccessAuditLog
from decorators import supervisor_required
from sqlalchemy import func, or_
from services import user_service

supervisor_bp = Blueprint('supervisor', __name__, url_prefix='/supervisor', template_folder='templates')


def _looks_technical_error(message: str) -> bool:
  text = (message or '').lower()
  technical_markers = (
    'traceback',
    'sqlalchemy',
    'psycopg2',
    'integrityerror',
    'operationalerror',
    'programmingerror',
    'database',
    'constraint',
    'null value',
    'foreign key',
    '[sql:',
    'error changing',
    'error updating',
    'error deleting',
    'error creating',
  )
  return any(marker in text for marker in technical_markers)


def flash(message, category='message'):
  if category == 'danger':
    raw_message = str(message or '')
    if _looks_technical_error(raw_message):
      try:
        current_app.logger.error(
          'User-facing supervisor error suppressed: endpoint=%s path=%s user_id=%s detail=%s',
          request.endpoint,
          request.path,
          getattr(current_user, 'user_id', None),
          raw_message,
        )
      except Exception:
        pass
      message = 'We could not complete your request right now. Please try again. If the issue persists, contact support.'

  return flask_flash(message, category)


def _build_supervisor_advocates_context():
  """Build common advocates/filter context for supervisor pages."""
  query = Champion.query.filter_by(supervisor_id=current_user.user_id)

  filter_status = request.args.get('status')
  filter_risk = request.args.get('risk')
  filter_county = request.args.get('county')
  filter_institution = request.args.get('institution')

  if filter_status and filter_status != 'all':
    query = query.filter_by(champion_status=filter_status)

  if filter_risk and filter_risk != 'all':
    query = query.filter_by(risk_level=filter_risk)

  if filter_county and filter_county != 'all':
    query = query.filter_by(county_sub_county=filter_county)

  if filter_institution and filter_institution != 'all':
    query = query.filter_by(education_institution_name=filter_institution)

  champions = query.all()

  all_counties = db.session.query(Champion.county_sub_county).filter(
    Champion.supervisor_id == current_user.user_id
  ).distinct().all()

  all_institutions = db.session.query(Champion.education_institution_name).filter(
    Champion.supervisor_id == current_user.user_id
  ).distinct().all()

  return {
    'champions': champions,
    'all_counties': [c[0] for c in all_counties if c[0]],
    'all_institutions': [i[0] for i in all_institutions if i[0]],
    'current_filters': {
      'status': filter_status or 'all',
      'risk': filter_risk or 'all',
      'county': filter_county or 'all',
      'institution': filter_institution or 'all'
    }
  }


@supervisor_bp.route('/dashboard')
@login_required
@supervisor_required
def dashboard():
  context = _build_supervisor_advocates_context()
  champions = context['champions']

  # Dashboard metrics (real computed values)
  today = datetime.now(timezone.utc).date()
  week_start = today - timedelta(days=7)

  active_cases_count = (
    db.session.query(func.count(func.distinct(YouthSupport.champion_id)))
    .join(Champion, YouthSupport.champion_id == Champion.champion_id)
    .filter(
      Champion.supervisor_id == current_user.user_id,
      YouthSupport.reporting_period >= week_start
    )
    .scalar()
  ) or 0

  pending_review_count = (
    db.session.query(func.count(YouthSupport.support_id))
    .join(Champion, YouthSupport.champion_id == Champion.champion_id)
    .filter(
      Champion.supervisor_id == current_user.user_id,
      or_(
        YouthSupport.supervisor_notes.is_(None),
        func.trim(YouthSupport.supervisor_notes) == ''
      )
    )
    .scalar()
  ) or 0

  team_health_rate = (
    db.session.query(func.avg(YouthSupport.weekly_check_in_completion_rate))
    .join(Champion, YouthSupport.champion_id == Champion.champion_id)
    .filter(Champion.supervisor_id == current_user.user_id)
    .scalar()
  )
  team_health_rate = int(round(float(team_health_rate))) if team_health_rate is not None else 0
  team_health_rate = max(0, min(team_health_rate, 100))

  return render_template('supervisor/dashboard.html', 
                        champions=champions,
                        all_counties=context['all_counties'],
                        all_institutions=context['all_institutions'],
                        active_cases_count=active_cases_count,
                        pending_review_count=pending_review_count,
                        team_health_rate=team_health_rate,
                        current_filters=context['current_filters'])


@supervisor_bp.route('/my-advocates')
@login_required
@supervisor_required
def my_advocates():
  context = _build_supervisor_advocates_context()
  return render_template('supervisor/my_advocates.html',
                        champions=context['champions'],
                        all_counties=context['all_counties'],
                        all_institutions=context['all_institutions'],
                        current_filters=context['current_filters'])


@supervisor_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
@supervisor_required
def change_password():
  if request.method == 'POST':
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not current_password or not new_password or not confirm_password:
      flash('All fields are required', 'danger')
      return render_template('admin/change_password.html')

    if new_password != confirm_password:
      flash('New passwords do not match', 'danger')
      return render_template('admin/change_password.html')

    try:
      user_service.change_password(current_user.user_id, current_password, new_password)
      flash('Password changed successfully!', 'success')
      flash('You can now use your new password on next login.', 'info')
      return redirect(url_for('supervisor.dashboard'))
    except ValueError as e:
      flash(str(e), 'danger')
      return render_template('admin/change_password.html')
    except Exception as e:
      db.session.rollback()
      current_app.logger.exception('Error changing password for supervisor')
      flash(f'Error changing password: {str(e)}', 'danger')
      return render_template('admin/change_password.html')

  return render_template('admin/change_password.html')

@supervisor_bp.route('/review/<int:champion_id>', methods=['GET', 'POST'])
@login_required
@supervisor_required
def review_champion(champion_id):
  # Verify authorization for this specific champion
  champion = db.session.get(Champion, champion_id)
  if not champion:
    abort(404, 'Champion not found')
  
  # Check if this champion is assigned to the current supervisor
  if champion.supervisor_id != current_user.user_id:
    abort(403, 'Unauthorized access')


  # AUDIT LOG: Record sensitive data access
  audit_entry = AccessAuditLog(
    user_id=current_user.user_id,
    champion_id=champion_id,
    action='viewed_champion_profile',
    ip_address=request.remote_addr,
    details='Supervisor accessed champion detail page'
  )
  db.session.add(audit_entry)
  db.session.commit()

  # Fetch history to monitor program impact
  history = (
    YouthSupport.query
    .filter_by(champion_id=champion_id)
    .order_by(YouthSupport.reporting_period.desc())
    .all()
  )

  referrals = (
    RefferalPathway.query
    .filter_by(champion_id=champion_id)
    .order_by(RefferalPathway.date_initiated.desc())
    .all()
  )

  # Controls whether the form pre-populates after a save; set to False to render empty fields
  prefill = request.args.get('prefill', '1') != '0'

  if request.method == 'POST':
    action = request.form.get('action')

    if action == 'update_notes':
      report_id = request.form.get('report_id')
      report = db.session.get(YouthSupport, report_id)
      if report and report.champion_id == champion_id:
        report.supervisor_notes = request.form.get('notes')
        db.session.commit()
        flash('Supervisor notes saved.', 'success')
        return redirect(url_for('supervisor.review_champion', champion_id=champion_id, prefill=0))
      else:
        abort(403, 'Unauthorized access to report')

    elif action == 'update_safeguarding':
      report_id = request.form.get('report_id')
      report = db.session.get(YouthSupport, report_id)
      if report and report.champion_id == champion_id:
        report.safeguarding_notes = request.form.get('safeguarding_notes')
        db.session.commit()
        flash('Safeguarding notes saved.', 'success')
        return redirect(url_for('supervisor.review_champion', champion_id=champion_id, prefill=0))
      else:
        abort(403, 'Unauthorized access to report')

    elif action == 'update_quality':
      report_id = request.form.get('report_id')
      report = db.session.get(YouthSupport, report_id)
      if report and report.champion_id == champion_id:
        report.documentation_quality_score = request.form.get('doc_quality')
        db.session.commit()
        flash('Documentation quality updated.', 'success')
      else:
        abort(403, 'Unauthorized access to report')

    elif action == 'add_referral':
      # Track referral destinations and outcomes linked to this champion
      destination = request.form.get('referral_destination')
      outcome = request.form.get('referral_outcome')
      youth_number = request.form.get('youth_referred_number')

      latest_flag = (
        YouthSupport.query
        .filter(YouthSupport.champion_id == champion_id, YouthSupport.flag_timestamp.isnot(None))
        .order_by(YouthSupport.flag_timestamp.desc())
        .first()
      )

      new_referral = RefferalPathway(
        champion_id=champion_id,
        youth_referred_number=int(youth_number) if youth_number else None,
        referral_destinations=destination,
        referal_outcomes=outcome,
      )

      if latest_flag and latest_flag.flag_timestamp:
        delta = datetime.now(timezone.utc).date() - latest_flag.flag_timestamp.date()
        new_referral.flag_to_referral_days = delta.days
      db.session.add(new_referral)
      db.session.commit()
      flash('Referral pathway recorded.', 'success')

    elif action == 'update_health_risk':
      # Update health and safety information
      champion.medical_conditions = request.form.get('medical_conditions')
      champion.allergies = request.form.get('allergies')
      champion.mental_health_support = request.form.get('mental_health_support')
      champion.disabilities = request.form.get('disabilities')
      champion.medication_required = request.form.get('medication_required')
      champion.dietary_requirements = request.form.get('dietary_requirements')
      champion.health_notes = request.form.get('health_notes')
      
      # Update risk assessment
      champion.risk_level = request.form.get('risk_level')
      champion.risk_notes = request.form.get('risk_notes')
      champion.risk_assessment_date = datetime.now(timezone.utc)
      
      # Update contact and review dates
      last_contact = request.form.get('last_contact_date')
      next_review = request.form.get('next_review_date')
      
      if last_contact:
        champion.last_contact_date = datetime.strptime(last_contact, '%Y-%m-%d').date()
      if next_review:
        champion.next_review_date = datetime.strptime(next_review, '%Y-%m-%d').date()
      
      db.session.commit()
      flash('Health and risk assessment data updated successfully.', 'success')
      return redirect(url_for('supervisor.review_champion', champion_id=champion_id, prefill=0))

    return redirect(url_for('supervisor.review_champion', champion_id=champion_id))

  return render_template('supervisor/champion_details.html', champion=champion, history=history, referrals=referrals, prefill=prefill)