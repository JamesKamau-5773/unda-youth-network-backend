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

    # Average Check-In Completion Rate
    average_check_in = db.session.query(func.avg(YouthSupport.weekly_check_in_completion_rate)).scalar() or 0

    # Referral Conversion Rate (Success Rate)
    total_referrals = RefferalPathway.query.count()
    successful_referrals = RefferalPathway.query.filter_by(referal_outcomes='Attended').count()
    conversion_rate = (successful_referrals / total_referrals * 100) if total_referrals > 0 else 0

    # CONSENT & LEGAL COMPLIANCE CHECK
    champions_missing_consent = Champion.query.filter_by(consent_obtained=False).count()
    champions_missing_institution = Champion.query.filter_by(institution_consent_obtained=False).count()

    # REFRESHER ALERTS (next 30 days)
    upcoming_refreshers = get_champions_needing_refresher(days_ahead=30)

    return render_template('admin/dashboard.html',
        total_champions=total_champions,
        avg_check_in=round(average_check_in, 2),
        conversion_rate=round(conversion_rate, 2),
        champions_missing_consent=champions_missing_consent,
        champions_missing_institution=champions_missing_institution,
        upcoming_refreshers=upcoming_refreshers
    )


@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('admin/settings.html')
