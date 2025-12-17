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
		flash("Champion profile data not found.", 'danger')
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

		new_report = YouthSupport(
			champion_id=current_user.champion_id,
			reporting_period=reporting_date,
			weekly_check_in_completion_rate=request.form.get('check_in_rate'),
			monthly_mini_screenings_delivered=int(request.form.get('screenings_delivered')),
			referrals_initiated=int(request.form.get('referrals_initiated')),
			documentation_quality_score=request.form.get('doc_quality'),
			self_reported_wellbeing_check=request.form.get('wellbeing_check'),
		)

		db.session.add(new_report)
		db.session.commit()

		flash(
			f'Monthly Operational Report for {reporting_date.strftime("%B %Y")} submitted successfully.',
			'success',
		)

	except ValueError:
		db.session.rollback()
		flash('Error: Please ensure all numeric fields are entered correctly.', 'danger')
	except IntegrityError:
		db.session.rollback()
		flash(f'Error: Report for {reporting_date.strftime("%B %Y")} already exists. Submission denied.', 'warning')
	except Exception as e:
		db.session.rollback()
		flash(f'An unexpected error occurred: {str(e)}', 'danger')

	return redirect(url_for('champion.dashboard'))
