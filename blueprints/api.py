from flask import Blueprint, jsonify
from models import db, Champion, YouthSupport, User, RefferalPathway, TrainingRecord, Event, BlogPost
from sqlalchemy import func
from datetime import datetime, date

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/impact-stats', methods=['GET'])
def impact_stats():
    """
    Comprehensive impact statistics endpoint for UNDA Youth Network.
    Returns aggregated data about champions, youth support, training, and overall program impact.
    """
    
    # Champion Statistics
    total_champions = Champion.query.count()
    active_champions = Champion.query.filter_by(champion_status='Active').count()
    inactive_champions = Champion.query.filter_by(champion_status='Inactive').count()
    on_hold_champions = Champion.query.filter_by(champion_status='On Hold').count()
    
    # Youth Support Statistics
    total_youth_reached = db.session.query(
        func.sum(YouthSupport.number_of_youth_under_support)
    ).scalar() or 0
    
    total_reports = YouthSupport.query.count()
    
    # Average check-in completion rate
    avg_check_in_rate = db.session.query(
        func.avg(YouthSupport.weekly_check_in_completion_rate)
    ).scalar() or 0
    
    # Total screenings delivered
    total_screenings = db.session.query(
        func.sum(YouthSupport.monthly_mini_screenings_delivered)
    ).scalar() or 0
    
    # Total referrals
    total_referrals = RefferalPathway.query.count()
    total_referrals_initiated = db.session.query(
        func.sum(YouthSupport.referrals_initiated)
    ).scalar() or 0
    
    # Youth feedback and wellbeing
    avg_youth_feedback = db.session.query(
        func.avg(YouthSupport.youth_feedback_score)
    ).scalar() or 0
    
    avg_wellbeing_score = db.session.query(
        func.avg(YouthSupport.self_reported_wellbeing_check)
    ).scalar() or 0
    
    # Training Statistics
    total_trainings = TrainingRecord.query.count()
    
    # Safeguarding compliance
    safeguarding_completed = YouthSupport.query.filter_by(
        safeguarding_training_completed=True
    ).count()
    safeguarding_rate = (safeguarding_completed / total_reports * 100) if total_reports > 0 else 0
    
    # Consent compliance
    champions_with_consent = Champion.query.filter_by(consent_obtained=True).count()
    consent_rate = (champions_with_consent / total_champions * 100) if total_champions > 0 else 0
    
    # Risk Level Distribution
    high_risk_champions = Champion.query.filter_by(risk_level='High').count()
    medium_risk_champions = Champion.query.filter_by(risk_level='Medium').count()
    low_risk_champions = Champion.query.filter_by(risk_level='Low').count()
    
    # Gender Distribution
    gender_stats = db.session.query(
        Champion.gender,
        func.count(Champion.champion_id).label('count')
    ).filter(Champion.gender.isnot(None)).group_by(Champion.gender).all()
    
    gender_distribution = {gender: count for gender, count in gender_stats}
    
    # Recruitment Sources
    recruitment_sources = db.session.query(
        Champion.recruitment_source,
        func.count(Champion.champion_id).label('count')
    ).filter(Champion.recruitment_source.isnot(None)).group_by(Champion.recruitment_source).all()
    
    recruitment_distribution = {source: count for source, count in recruitment_sources}
    
    # Top Performing Champions (by youth reached)
    top_champions = db.session.query(
        Champion.champion_id,
        Champion.full_name,
        Champion.assigned_champion_code,
        func.sum(YouthSupport.number_of_youth_under_support).label('total_youth')
    ).join(
        YouthSupport, Champion.champion_id == YouthSupport.champion_id
    ).group_by(
        Champion.champion_id, Champion.full_name, Champion.assigned_champion_code
    ).order_by(
        func.sum(YouthSupport.number_of_youth_under_support).desc()
    ).limit(5).all()
    
    top_performers = [{
        'champion_id': c.champion_id,
        'name': c.full_name,
        'code': c.assigned_champion_code,
        'youth_reached': int(c.total_youth) if c.total_youth else 0
    } for c in top_champions]
    
    # User Statistics
    total_users = User.query.count()
    admin_users = User.query.filter_by(role=User.ROLE_ADMIN).count()
    supervisor_users = User.query.filter_by(role=User.ROLE_SUPERVISOR).count()
    # Count both 'Prevention Advocate' and legacy 'Champion' roles
    champion_users = User.query.filter(
        db.or_(User.role == User.ROLE_PREVENTION_ADVOCATE, User.role == 'Champion')
    ).count()
    
    # Event Statistics
    total_events = Event.query.count()
    upcoming_events = Event.query.filter_by(status='Upcoming').count()
    completed_events = Event.query.filter_by(status='Completed').count()
    
    # Blog Statistics
    total_blog_posts = BlogPost.query.count()
    published_posts = BlogPost.query.filter_by(published=True).count()
    total_blog_views = db.session.query(func.sum(BlogPost.views)).scalar() or 0
    
    # Recent Activity
    recent_reports = YouthSupport.query.order_by(
        YouthSupport.reporting_period.desc()
    ).limit(5).all()
    
    recent_activity = [{
        'report_id': r.support_id,
        'champion_id': r.champion_id,
        'reporting_period': r.reporting_period.isoformat() if r.reporting_period else None,
        'youth_under_support': r.number_of_youth_under_support
    } for r in recent_reports]
    
    # Compile comprehensive stats
    stats = {
        'generated_at': datetime.utcnow().isoformat(),
        'overview': {
            'total_champions': total_champions,
            'active_champions': active_champions,
            'inactive_champions': inactive_champions,
            'on_hold_champions': on_hold_champions,
            'total_youth_reached': int(total_youth_reached),
            'total_reports': total_reports,
            'total_trainings': total_trainings,
            'total_referrals': total_referrals,
            'total_users': total_users,
            'total_events': total_events,
            'total_blog_posts': total_blog_posts
        },
        'performance_metrics': {
            'average_check_in_rate': round(float(avg_check_in_rate), 2),
            'total_screenings_delivered': int(total_screenings) if total_screenings else 0,
            'total_referrals_initiated': int(total_referrals_initiated) if total_referrals_initiated else 0,
            'average_youth_feedback_score': round(float(avg_youth_feedback), 2),
            'average_wellbeing_score': round(float(avg_wellbeing_score), 2)
        },
        'compliance': {
            'safeguarding_training_completion_rate': round(safeguarding_rate, 2),
            'consent_obtained_rate': round(consent_rate, 2)
        },
        'risk_distribution': {
            'high_risk': high_risk_champions,
            'medium_risk': medium_risk_champions,
            'low_risk': low_risk_champions
        },
        'demographics': {
            'gender_distribution': gender_distribution,
            'recruitment_sources': recruitment_distribution
        },
        'top_performers': top_performers,
        'user_breakdown': {
            'admins': admin_users,
            'supervisors': supervisor_users,
            'champions': champion_users
        },
        'content': {
            'upcoming_events': upcoming_events,
            'completed_events': completed_events,
            'published_blog_posts': published_posts,
            'total_blog_views': int(total_blog_views)
        },
        'recent_activity': recent_activity
    }
    
    return jsonify({
        'success': True,
        'stats': stats
    }), 200


@api_bp.route('/impact-stats/summary', methods=['GET'])
def impact_stats_summary():
    """
    Quick summary of key impact metrics.
    Lightweight endpoint for dashboard widgets.
    """
    total_champions = Champion.query.filter_by(champion_status='Active').count()
    total_youth_reached = db.session.query(
        func.sum(YouthSupport.number_of_youth_under_support)
    ).scalar() or 0
    total_trainings = TrainingRecord.query.count()
    total_referrals = RefferalPathway.query.count()
    
    return jsonify({
        'success': True,
        'summary': {
            'active_champions': total_champions,
            'youth_reached': int(total_youth_reached),
            'trainings_completed': total_trainings,
            'referrals_made': total_referrals,
            'generated_at': datetime.utcnow().isoformat()
        }
    }), 200


@api_bp.route('/campus-initiatives', methods=['GET', 'OPTIONS'])
def campus_initiatives():
    """Return public list of Campus Edition events."""
    try:
        events = Event.query.filter(Event.event_type == 'campus').order_by(Event.event_date.asc()).all()
        return jsonify({'success': True, 'events': [e.to_dict() for e in events]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/members/me', methods=['GET', 'OPTIONS'])
def get_current_member():
    """Return current authenticated member info for SPA dashboards."""
    from flask_login import current_user

    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify({
        'success': True,
        'user': {
            'user_id': current_user.user_id,
            'username': current_user.username,
            'email': current_user.email,
            'role': current_user.role,
            'champion_id': current_user.champion_id
        }
    }), 200
