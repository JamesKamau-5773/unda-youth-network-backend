from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Champion, YouthSupport
from decorators import champion_required
from datetime import date
from sqlalchemy.exc import IntegrityError


champion_bp = Blueprint('champion', __name__, url_prefix='/champion', template_folder='templates')


@champion_bp.route('/dashboard', methods=['GET'])
@login_required
@champion_required  # Champions, Supervisors, Admins can view; Supervisors/Admins may act on behalf
def dashboard():
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

	return render_template(
		'champion/dashboard.html',
		champion=champion_profile,
		reports=recent_reports,
		current_reporting_date=current_reporting_date,
	)


@champion_bp.route('/submit-report', methods=['POST'])
@login_required
@champion_required
def submit_report():
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
