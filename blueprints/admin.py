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

    # CHAMPION STATUS TRACKING
    total_champions = Champion.query.count()
    active_champions = Champion.query.filter_by(champion_status='Active').count()
    inactive_champions = Champion.query.filter_by(champion_status='Inactive').count()
    on_hold_champions = Champion.query.filter_by(champion_status='On Hold').count()

    # 1. Average Check-In Completion Rate
    # This calculates the rounded average of all weekly check-in completion rates
    average_check_in = db.session.query(func.avg(YouthSupport.weekly_check_in_completion_rate)).scalar() or 0
    avg_check_in_rounded = round(average_check_in, 0)  # Rounded to nearest percentage
    
    # 1b. Average Mini-Screening Completion Rate
    # Calculate percentage of mini-screenings completed vs expected
    total_expected_screenings = db.session.query(func.count(YouthSupport.support_id)).scalar() or 0
    total_completed_screenings = db.session.query(func.sum(YouthSupport.monthly_mini_screenings_delivered)).scalar() or 0
    avg_screening_completion_rate = (total_completed_screenings / total_expected_screenings) if total_expected_screenings > 0 else 0

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
    # Aggregates youth from support records and referrals
    youth_per_champion = (
        db.session.query(
            Champion.champion_id,
            Champion.full_name,
            Champion.assigned_champion_code,
            func.coalesce(func.max(YouthSupport.number_of_youth_under_support), 0).label('total_youth')
        )
        .outerjoin(YouthSupport)
        .group_by(Champion.champion_id, Champion.full_name, Champion.assigned_champion_code)
        .all()
    )
    
    # Total youth reached across all champions
    total_youth_reached = db.session.query(func.sum(YouthSupport.number_of_youth_under_support)).scalar() or 0

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
        # Champion Status Counts
        total_champions=total_champions,
        active_champions=active_champions,
        inactive_champions=inactive_champions,
        on_hold_champions=on_hold_champions,
        
        # Performance Metrics
        avg_check_in=avg_check_in_rounded,
        avg_screening_completion_rate=round(avg_screening_completion_rate, 1),
        conversion_rate=round(conversion_rate, 1),
        training_compliance_rate=round(training_compliance_rate, 1),
        champions_with_core_training=champions_with_core_training,
        
        # Youth Reach
        youth_per_champion=youth_per_champion,
        total_youth_reached=total_youth_reached,
        
        # Satisfaction & Quality
        quarterly_satisfaction=quarterly_satisfaction_rounded,
        
        # Operational Analytics
        recruitment_sources=recruitment_sources,
        avg_flag_to_referral=avg_flag_to_referral_rounded,
        
        # Compliance
        champions_missing_consent=champions_missing_consent,
        champions_missing_institution=champions_missing_institution,
        upcoming_refreshers=upcoming_refreshers
    )


@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('admin/settings.html')
