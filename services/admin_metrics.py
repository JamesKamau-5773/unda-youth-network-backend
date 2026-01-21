from dataclasses import dataclass, field
from typing import List, Any
from sqlalchemy import func
from models import (
    db,
    Champion,
    YouthSupport,
    RefferalPathway,
    TrainingRecord,
    get_champions_needing_refresher,
    get_high_risk_champions,
    get_overdue_reviews,
    MemberRegistration,
    ChampionApplication,
)


@dataclass
class AdminDashboardMetrics:
    total_champions: int = 0
    active_champions: int = 0
    inactive_champions: int = 0
    on_hold_champions: int = 0
    avg_check_in: float = 0.0
    avg_screening_completion_rate: float = 0.0
    conversion_rate: float = 0.0
    training_compliance_rate: float = 0.0
    champions_with_core_training: int = 0
    youth_per_champion: List[Any] = field(default_factory=list)
    total_youth_reached: int = 0
    quarterly_satisfaction: float = 0.0
    recruitment_sources: List[Any] = field(default_factory=list)
    avg_flag_to_referral: float = 0.0
    champions_missing_consent: int = 0
    champions_missing_institution: int = 0
    upcoming_refreshers: List[Any] = field(default_factory=list)
    high_risk_champions: List[Any] = field(default_factory=list)
    overdue_reviews: List[Any] = field(default_factory=list)
    high_risk_count: int = 0
    overdue_count: int = 0
    pending_registrations_count: int = 0
    pending_applications_count: int = 0


def get_dashboard_metrics(days_ahead: int = 30) -> AdminDashboardMetrics:
    # Champion status counts
    total_champions = Champion.query.count()
    active_champions = Champion.query.filter_by(champion_status='Active').count()
    inactive_champions = Champion.query.filter_by(champion_status='Inactive').count()
    on_hold_champions = Champion.query.filter_by(champion_status='On Hold').count()

    # Average check-in completion
    average_check_in = db.session.query(func.avg(YouthSupport.weekly_check_in_completion_rate)).scalar() or 0
    avg_check_in_rounded = round(average_check_in, 0)

    # Screening completion
    total_expected_screenings = db.session.query(func.count(YouthSupport.support_id)).scalar() or 0
    total_completed_screenings = db.session.query(func.sum(YouthSupport.monthly_mini_screenings_delivered)).scalar() or 0
    avg_screening_completion_rate = (total_completed_screenings / total_expected_screenings) if total_expected_screenings > 0 else 0

    # Referral conversion
    total_referrals = RefferalPathway.query.count()
    successful_referrals = RefferalPathway.query.filter_by(referal_outcomes='Attended').count()
    conversion_rate = (successful_referrals / total_referrals * 100) if total_referrals > 0 else 0

    # Training compliance
    total_training_records = TrainingRecord.query.count()
    certified_records = TrainingRecord.query.filter_by(certification_status='Certified').count()
    training_compliance_rate = (certified_records / total_training_records * 100) if total_training_records > 0 else 0

    core_modules = ['Safeguarding', 'Referral Protocols']
    champions_with_core_training = (
        db.session.query(Champion.champion_id)
        .join(TrainingRecord)
        .filter(TrainingRecord.training_module.in_(core_modules))
        .filter(TrainingRecord.certification_status == 'Certified')
        .distinct()
        .count()
    )

    # Youth reach
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

    total_youth_reached = db.session.query(func.sum(YouthSupport.number_of_youth_under_support)).scalar() or 0

    # Satisfaction
    quarterly_satisfaction = db.session.query(func.avg(YouthSupport.self_reported_wellbeing_check)).scalar() or 0
    quarterly_satisfaction_rounded = round(quarterly_satisfaction, 1)

    # Recruitment sources
    recruitment_sources = (
        db.session.query(Champion.recruitment_source, func.count(Champion.champion_id).label('count'))
        .filter(Champion.recruitment_source.isnot(None))
        .group_by(Champion.recruitment_source)
        .all()
    )

    # Flag-to-referral
    avg_flag_to_referral = db.session.query(func.avg(RefferalPathway.flag_to_referral_days)).scalar() or 0
    avg_flag_to_referral_rounded = round(avg_flag_to_referral, 1)

    # Compliance
    champions_missing_consent = Champion.query.filter_by(consent_obtained=False).count()
    champions_missing_institution = Champion.query.filter_by(institution_consent_obtained=False).count()

    # Refreshers and safety lists
    upcoming_refreshers = get_champions_needing_refresher(days_ahead=days_ahead)
    high_risk_champions = get_high_risk_champions()
    overdue_reviews = get_overdue_reviews()

    pending_registrations_count = MemberRegistration.query.filter_by(status='Pending').count()
    pending_applications_count = ChampionApplication.query.filter_by(status='Pending').count()

    return AdminDashboardMetrics(
        total_champions=total_champions,
        active_champions=active_champions,
        inactive_champions=inactive_champions,
        on_hold_champions=on_hold_champions,
        avg_check_in=avg_check_in_rounded,
        avg_screening_completion_rate=round(avg_screening_completion_rate, 1),
        conversion_rate=round(conversion_rate, 1),
        training_compliance_rate=round(training_compliance_rate, 1),
        champions_with_core_training=champions_with_core_training,
        youth_per_champion=list(youth_per_champion),
        total_youth_reached=total_youth_reached,
        quarterly_satisfaction=quarterly_satisfaction_rounded,
        recruitment_sources=list(recruitment_sources),
        avg_flag_to_referral=avg_flag_to_referral_rounded,
        champions_missing_consent=champions_missing_consent,
        champions_missing_institution=champions_missing_institution,
        upcoming_refreshers=list(upcoming_refreshers),
        high_risk_champions=list(high_risk_champions),
        overdue_reviews=list(overdue_reviews),
        high_risk_count=len(high_risk_champions),
        overdue_count=len(overdue_reviews),
        pending_registrations_count=pending_registrations_count,
        pending_applications_count=pending_applications_count,
    )
