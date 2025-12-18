from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from models import db, Champion, YouthSupport, RefferalPathway, TrainingRecord, get_champions_needing_refresher
from decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # HIGH-LEVEL DASHBOARD METRICS

    total_champions = Champion.query.count()

    # 1. Average Check-In Completion Rate
    # This calculates the rounded average of all weekly check-in completion rates
    average_check_in = db.session.query(func.avg(YouthSupport.weekly_check_in_completion_rate)).scalar() or 0
    avg_check_in_rounded = round(average_check_in, 0)  # Rounded to nearest percentage

    # 2. Referral Conversion Rate (Success Rate)
    # Ratio of "Attended" outcomes vs total referrals
    total_referrals = RefferalPathway.query.count()
    successful_referrals = RefferalPathway.query.filter_by(referal_outcomes='Attended').count()
    conversion_rate = (successful_referrals / total_referrals * 100) if total_referrals > 0 else 0

    # 3. Training Compliance Rate
    # Percentage of champions with "Certified" status for core modules
    total_training_records = TrainingRecord.query.count()
    certified_records = TrainingRecord.query.filter_by(certification_status='Certified').count()
    training_compliance_rate = (certified_records / total_training_records * 100) if total_training_records > 0 else 0

    # Core modules compliance check
    core_modules = ['Safeguarding', 'Referral Protocols']
    champions_with_core_training = (
        db.session.query(Champion.champion_id)
        .join(TrainingRecord)
        .filter(TrainingRecord.training_module.in_(core_modules))
        .filter(TrainingRecord.certification_status == 'Certified')
        .distinct()
        .count()
    )

    # 4. Total Youth Reached per Champion
    # Aggregates youth_referred_number from referral pathways per champion
    youth_per_champion = (
        db.session.query(
            Champion.champion_id,
            Champion.full_name,
            Champion.assigned_champion_code,
            func.coalesce(func.sum(RefferalPathway.youth_referred_number), 0).label('total_youth')
        )
        .outerjoin(RefferalPathway)
        .group_by(Champion.champion_id, Champion.full_name, Champion.assigned_champion_code)
        .all()
    )

    # 5. Quarterly Satisfaction Score
    # Average of youth feedback scores (self_reported_wellbeing_check)
    quarterly_satisfaction = db.session.query(func.avg(YouthSupport.self_reported_wellbeing_check)).scalar() or 0
    quarterly_satisfaction_rounded = round(quarterly_satisfaction, 1)

    # 6. Recruitment Source Analytics (Operational Clarity)
    recruitment_sources = (
        db.session.query(
            Champion.recruitment_source,
            func.count(Champion.champion_id).label('count')
        )
        .filter(Champion.recruitment_source.isnot(None))
        .group_by(Champion.recruitment_source)
        .all()
    )

    # 7. Clinical Reliability - Average Flag-to-Referral Time
    avg_flag_to_referral = db.session.query(func.avg(RefferalPathway.flag_to_referral_days)).scalar() or 0
    avg_flag_to_referral_rounded = round(avg_flag_to_referral, 1)

    # CONSENT & LEGAL COMPLIANCE CHECK
    champions_missing_consent = Champion.query.filter_by(consent_obtained=False).count()
    champions_missing_institution = Champion.query.filter_by(institution_consent_obtained=False).count()

    # REFRESHER ALERTS (next 30 days)
    upcoming_refreshers = get_champions_needing_refresher(days_ahead=30)

    return render_template('admin/dashboard.html',
        total_champions=total_champions,
        avg_check_in=avg_check_in_rounded,
        conversion_rate=round(conversion_rate, 1),
        training_compliance_rate=round(training_compliance_rate, 1),
        champions_with_core_training=champions_with_core_training,
        youth_per_champion=youth_per_champion,
        quarterly_satisfaction=quarterly_satisfaction_rounded,
        recruitment_sources=recruitment_sources,
        avg_flag_to_referral=avg_flag_to_referral_rounded,
        champions_missing_consent=champions_missing_consent,
        champions_missing_institution=champions_missing_institution,
        upcoming_refreshers=upcoming_refreshers
    )


@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('admin/settings.html')
