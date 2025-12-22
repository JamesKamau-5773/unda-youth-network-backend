from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, Champion, YouthSupport, RefferalPathway, AccessAuditLog
from decorators import supervisor_required

supervisor_bp = Blueprint('supervisor', __name__, url_prefix='/supervisor', template_folder='templates')


@supervisor_bp.route('/dashboard',)
@login_required
@supervisor_required
def dashboard():
  # SECURITY FILTER: Only fetch champions assigned to this supervisor
  # Filter champions where supervisor_id matches current user's ID
  query = Champion.query.filter_by(supervisor_id=current_user.user_id)
  
  # ADVANCED FILTERING
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
  
  # Get unique values for filter dropdowns (only from assigned champions)
  all_counties = db.session.query(Champion.county_sub_county).filter(
    Champion.supervisor_id == current_user.user_id
  ).distinct().all()
  
  all_institutions = db.session.query(Champion.education_institution_name).filter(
    Champion.supervisor_id == current_user.user_id
  ).distinct().all()

  return render_template('supervisor/dashboard.html', 
                        champions=champions,
                        counties=[c[0] for c in all_counties if c[0]],
                        institutions=[i[0] for i in all_institutions if i[0]],
                        current_filters={
                          'status': filter_status or 'all',
                          'risk': filter_risk or 'all',
                          'county': filter_county or 'all',
                          'institution': filter_institution or 'all'
                        })

@supervisor_bp.route('/review/<int:champion_id>', methods=['GET', 'POST'])
@login_required
@supervisor_required
def review_champion(champion_id):
  # Verify authorization for this specific champion
  champion = Champion.query.get_or_404(champion_id)
  
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

  if request.method == 'POST':
    action = request.form.get('action')

    if action == 'update_notes':
      report_id = request.form.get('report_id')
      report = YouthSupport.query.get(report_id)
      if report and report.champion_id == champion_id:
        report.supervisor_notes = request.form.get('notes')
        db.session.commit()
        flash('Supervisor notes saved.', 'success')
      else:
        abort(403, 'Unauthorized access to report')

    elif action == 'update_safeguarding':
      report_id = request.form.get('report_id')
      report = YouthSupport.query.get(report_id)
      if report and report.champion_id == champion_id:
        report.safeguarding_notes = request.form.get('safeguarding_notes')
        db.session.commit()
        flash('Safeguarding notes saved.', 'success')
      else:
        abort(403, 'Unauthorized access to report')

    elif action == 'update_quality':
      report_id = request.form.get('report_id')
      report = YouthSupport.query.get(report_id)
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
        delta = datetime.utcnow().date() - latest_flag.flag_timestamp.date()
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
      champion.risk_assessment_date = datetime.utcnow()
      
      # Update contact and review dates
      last_contact = request.form.get('last_contact_date')
      next_review = request.form.get('next_review_date')
      
      if last_contact:
        champion.last_contact_date = datetime.strptime(last_contact, '%Y-%m-%d').date()
      if next_review:
        champion.next_review_date = datetime.strptime(next_review, '%Y-%m-%d').date()
      
      db.session.commit()
      flash('Health and risk assessment data updated successfully.', 'success')

    return redirect(url_for('supervisor.review_champion', champion_id=champion_id))

  return render_template('supervisor/champion_details.html', champion=champion, history=history, referrals=referrals)