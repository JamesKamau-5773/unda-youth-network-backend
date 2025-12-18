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
  managed_ids = current_user.supervised_champion_ids or []

  champions = Champion.query.filter(Champion.champion_id.in_(managed_ids)).all() if managed_ids else []

  return render_template('supervisor/dashboard.html', champions=champions)

@supervisor_bp.route('/review/<int:champion_id>', methods=['GET', 'POST'])
@login_required
@supervisor_required
def review_champion(champion_id):
  # Verify authorization for this specific champion
  if champion_id not in (current_user.supervised_champion_ids or []):
    abort(403, 'Unauthorized access')

  champion = Champion.query.get_or_404(champion_id)

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

    return redirect(url_for('supervisor.review_champion', champion_id=champion_id))

  return render_template('supervisor/champion_details.html', champion=champion, history=history, referrals=referrals)