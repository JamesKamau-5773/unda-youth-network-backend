from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
import os
from flask_login import login_required, current_user
from models import db, Champion, YouthSupport, EventParticipation, Event
from decorators import champion_required
from datetime import date
from sqlalchemy.exc import IntegrityError


champion_bp = Blueprint('champion', __name__, url_prefix='/champion', template_folder='templates')


@champion_bp.route('/dashboard', methods=['GET'])
@login_required
@champion_required  # Champions, Supervisors, Admins can view; Supervisors/Admins may act on behalf
def dashboard():
	# If configured, route Prevention Advocates (legacy Champions) to the external member portal
	role_lower = (current_user.role or '').lower()
	if role_lower in ['prevention advocate', 'champion']:
		# Prefer explicit environment override (keeps backward compatibility
		# with tests that monkeypatch env). Otherwise use app config when set.
		use_portal = os.environ.get('USE_MEMBER_PORTAL_FOR_ADVOCATES')
		portal_url = os.environ.get('MEMBER_PORTAL_URL')
		if use_portal is None:
			try:
				use_portal = current_app.config.get('USE_MEMBER_PORTAL_FOR_ADVOCATES')
			except RuntimeError:
				use_portal = 'False'
		if portal_url is None:
			try:
				portal_url = current_app.config.get('MEMBER_PORTAL_URL')
			except RuntimeError:
				portal_url = '/member-portal'
		if str(use_portal) == 'True':
			return redirect(portal_url)

	champion_profile = Champion.query.filter_by(champion_id=current_user.champion_id).first()

	if not champion_profile:
		flash("Champion profile data not found. Please contact administrator.", 'danger')
		# Redirect to home page instead of login to prevent redirect loops
		return redirect(url_for('main.index'))

	recent_reports = (
		YouthSupport.query.filter_by(champion_id=current_user.champion_id)
		.order_by(YouthSupport.reporting_period.desc())
		.limit(10)
		.all()
	)

	current_reporting_date = date.today().replace(day=1)

	debate_participations = (
		EventParticipation.query
		.join(Event, EventParticipation.event_id == Event.event_id)
		.filter(EventParticipation.champion_id == current_user.champion_id)
		.filter(Event.event_type.in_(['debate', 'Debaters Circle']))
		.order_by(Event.event_date.desc())
		.all()
	)

	attended_count = sum(1 for p in debate_participations if p.attended)
	certificate_count = sum(1 for p in debate_participations if p.certificate_issued)
	feedback_scores = [p.feedback_score for p in debate_participations if p.feedback_score]
	avg_feedback = round(sum(feedback_scores) / len(feedback_scores), 1) if feedback_scores else None
	participation_score = attended_count * 10 + certificate_count * 5 + (avg_feedback or 0)

	return render_template(
		'champion/dashboard.html',
		champion=champion_profile,
		reports=recent_reports,
		current_reporting_date=current_reporting_date,
		debate_participations=debate_participations,
		debate_stats={
			'total': len(debate_participations),
			'attended': attended_count,
			'certificates': certificate_count,
			'average_feedback': avg_feedback,
			'score': int(participation_score),
		},
	)


@champion_bp.route('/submit-report', methods=['POST'])
@login_required
@champion_required
def submit_report():
	# If advocates have been migrated to the member portal, stop in-place submissions
	role_lower = (current_user.role or '').lower()
	if role_lower in ['prevention advocate', 'champion']:
		use_portal = None
		portal_url = None
		try:
			use_portal = current_app.config.get('USE_MEMBER_PORTAL_FOR_ADVOCATES')
			portal_url = current_app.config.get('MEMBER_PORTAL_URL')
		except RuntimeError:
			pass
		if use_portal is None:
			use_portal = os.environ.get('USE_MEMBER_PORTAL_FOR_ADVOCATES', 'False')
		if portal_url is None:
			portal_url = os.environ.get('MEMBER_PORTAL_URL', '/member-portal')
		if str(use_portal) == 'True':
			flash('This dashboard has moved to the member portal. Please access your reports there.', 'info')
			return redirect(portal_url)

	if not current_user.champion_id:
		flash("Error: Your user account is not linked to a Champion profile.", 'danger')
		return redirect(url_for('champion.dashboard'))

	try:
		reporting_date = date.today().replace(day=1)
		
		# Validate and convert numeric fields
		try:
			screenings_delivered = int(request.form.get('screenings_delivered', 0))
			referrals_initiated = int(request.form.get('referrals_initiated', 0))
			
			# Convert wellbeing check to integer if provided
			wellbeing_check = request.form.get('wellbeing_check', '').strip()
			wellbeing_check_value = int(wellbeing_check) if wellbeing_check else None
			
		except ValueError as ve:
			flash('Error: Please enter valid numbers for screenings delivered, referrals initiated, and wellbeing check (1-10).', 'danger')
			return redirect(url_for('champion.dashboard'))

		new_report = YouthSupport(
			champion_id=current_user.champion_id,
			reporting_period=reporting_date,
			weekly_check_in_completion_rate=request.form.get('check_in_rate'),
			monthly_mini_screenings_delivered=screenings_delivered,
			referrals_initiated=referrals_initiated,
			documentation_quality_score=request.form.get('doc_quality'),
			self_reported_wellbeing_check=wellbeing_check_value,
			flag_timestamp=None,
		)

		# If the champion raised referrals, capture the flag time for SLA tracking
		if new_report.referrals_initiated and int(new_report.referrals_initiated) > 0:
			from datetime import datetime
			new_report.flag_timestamp = datetime.utcnow()

		db.session.add(new_report)
		db.session.commit()

		flash(
			f'Monthly Operational Report for {reporting_date.strftime("%B %Y")} submitted successfully.',
			'success',
		)

	except IntegrityError:
		db.session.rollback()
		flash(f'Error: Report for {reporting_date.strftime("%B %Y")} already exists. Submission denied.', 'warning')
	except Exception as e:
		db.session.rollback()
		# Provide user-friendly error messages for database errors
		error_msg = str(e).lower()
		if 'invalid input syntax for type integer' in error_msg:
			flash('Error: One or more fields contain invalid data. Please ensure numeric fields only contain numbers.', 'danger')
		elif 'duplicate key' in error_msg or 'unique constraint' in error_msg:
			flash('Error: This report already exists. Please check and try again.', 'warning')
		else:
			flash('An error occurred while submitting your report. Please check your data and try again.', 'danger')

	return redirect(url_for('champion.dashboard'))
