"""
PRIVACY-FIRST Mental Health Assessment API
UMV Prevention Program - "Converse. Prevent. Thrive Mentally"

CRITICAL PRIVACY RULES:
1. NO raw scores stored or transmitted
2. NO champion names linked to assessments
3. Only champion_code used (anonymized)
4. Only color-coded risk categories exposed
5. Prevention Advocates can submit assessments
6. Supervisors see only aggregated statistics
7. Auto-referral for Orange/Red flags
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import (
    db, 
    MentalHealthAssessment, 
    Champion, 
    RefferalPathway,
    map_phq9_to_risk_category, 
    map_gad7_to_risk_category
)
from decorators import prevention_advocate_required, supervisor_required, admin_required
from datetime import datetime
from sqlalchemy import func, case

assessments_bp = Blueprint('assessments', __name__, url_prefix='/api/assessments')


# ============================================================================
# PREVENTION ADVOCATE ENDPOINTS - Submit assessments using champion codes
# ============================================================================

@assessments_bp.route('/submit', methods=['POST'])
@login_required
@prevention_advocate_required
def submit_assessment():
    """
    Prevention Advocates submit assessments using champion codes.
    RAW SCORE is processed server-side and NEVER STORED.
    Only risk category is saved.
    """
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['champion_code', 'assessment_type', 'raw_score']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'message': f'Missing required fields: {required_fields}'
        }), 400
    
    champion_code = data['champion_code'].strip().upper()
    assessment_type = data['assessment_type'].strip()
    raw_score = data['raw_score']
    
    # Validate assessment type (PHQ-9 or GAD-7 only)
    if assessment_type not in ['PHQ-9', 'GAD-7']:
        return jsonify({
            'success': False,
            'message': 'Invalid assessment type. Must be PHQ-9 or GAD-7'
        }), 400
    
    # Validate champion code exists
    champion = Champion.query.filter_by(assigned_champion_code=champion_code).first()
    if not champion:
        return jsonify({
            'success': False,
            'message': 'Invalid champion code'
        }), 404
    
    # Map raw score to risk category (PRIVACY: raw score is NOT stored)
    if assessment_type == 'PHQ-9':
        risk_data = map_phq9_to_risk_category(raw_score)
    else:  # GAD-7
        risk_data = map_gad7_to_risk_category(raw_score)
    
    if risk_data['risk_category'] == 'Invalid':
        return jsonify({
            'success': False,
            'message': f'Invalid score for {assessment_type}'
        }), 400
    
    # Create assessment record (PRIVACY: no champion_id, no raw score)
    assessment = MentalHealthAssessment(
        champion_code=champion_code,
        assessment_type=assessment_type,
        risk_category=risk_data['risk_category'],
        score_range=risk_data['score_range'],
        is_baseline=data.get('is_baseline', False),
        assessment_period=data.get('assessment_period', 'Follow-up'),
        risk_flagged=risk_data['auto_flag'],
        referral_recommended=risk_data['auto_referral'],
        referral_made=False,  # Will be set when referral is created
        administered_by=current_user.user_id,
        notes=data.get('notes', '')  # Non-identifiable notes only
    )
    
    db.session.add(assessment)
    db.session.flush()  # Get assessment_id before commit
    
    # Auto-create referral for Orange/Red flags
    referral_id = None
    if risk_data['auto_referral']:
        referral = RefferalPathway(
            champion_id=champion.champion_id,
            refferal_date=datetime.utcnow().date(),
            refferal_reason=f"{assessment_type} screening: {risk_data['description']}",
            reffered_to='Mental Health Professional',
            status='Pending',
            notes=f"Auto-referral triggered by {risk_data['risk_category']} flag on {assessment_type}",
            created_by=current_user.user_id
        )
        db.session.add(referral)
        db.session.flush()
        
        # Update assessment to mark referral as made
        assessment.referral_made = True
        referral_id = referral.refferal_id
    
    db.session.commit()
    
    # PRIVACY: Response does NOT include raw score
    return jsonify({
        'success': True,
        'message': 'Assessment recorded successfully',
        'assessment_id': assessment.assessment_id,
        'risk_category': risk_data['risk_category'],
        'risk_description': risk_data['description'],
        'referral_created': risk_data['auto_referral'],
        'referral_id': referral_id
    }), 201


@assessments_bp.route('/my-submissions', methods=['GET'])
@login_required
@prevention_advocate_required
def my_submissions():
    """Prevention Advocates can view their own assessment submissions."""
    assessments = MentalHealthAssessment.query.filter_by(
        administered_by=current_user.user_id
    ).order_by(MentalHealthAssessment.assessment_date.desc()).limit(50).all()
    
    return jsonify({
        'success': True,
        'total': len(assessments),
        'assessments': [{
            'assessment_id': a.assessment_id,
            'champion_code': a.champion_code,  # Code visible, not name
            'assessment_type': a.assessment_type,
            'assessment_date': a.assessment_date.isoformat() if a.assessment_date else None,
            'risk_category': a.risk_category,
            'referral_recommended': a.referral_recommended,
            'referral_made': a.referral_made
        } for a in assessments]
    }), 200


# ============================================================================
# SUPERVISOR/ADMIN ENDPOINTS - Aggregated statistics only
# ============================================================================

@assessments_bp.route('/dashboard', methods=['GET'])
@login_required
@supervisor_required
def assessment_dashboard():
    """
    Supervisors view aggregated statistics.
    NO individual champion data or raw scores.
    """
    # Time filter
    days = request.args.get('days', 30, type=int)
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = MentalHealthAssessment.query.filter(
        MentalHealthAssessment.assessment_date >= cutoff_date
    )
    
    assessments = query.all()
    
    # Aggregate by risk category
    risk_stats = {
        'Green': 0, 'Blue': 0, 'Purple': 0, 'Orange': 0, 'Red': 0
    }
    
    # Aggregate by assessment type
    type_stats = {'PHQ-9': 0, 'GAD-7': 0}
    
    # Referral statistics
    referrals_recommended = 0
    referrals_made = 0
    
    for a in assessments:
        risk_stats[a.risk_category] = risk_stats.get(a.risk_category, 0) + 1
        type_stats[a.assessment_type] = type_stats.get(a.assessment_type, 0) + 1
        if a.referral_recommended:
            referrals_recommended += 1
        if a.referral_made:
            referrals_made += 1
    
    return jsonify({
        'success': True,
        'period_days': days,
        'total_assessments': len(assessments),
        'risk_distribution': risk_stats,
        'assessment_types': type_stats,
        'high_risk_count': risk_stats['Orange'] + risk_stats['Red'],
        'referrals': {
            'recommended': referrals_recommended,
            'completed': referrals_made,
            'pending': referrals_recommended - referrals_made
        }
    }), 200


@assessments_bp.route('/statistics', methods=['GET'])
@login_required
@supervisor_required
def get_statistics():
    """
    Get comprehensive statistics for supervisors/admins.
    All data is aggregated - NO individual identifiers.
    """
    assessment_type = request.args.get('type')  # Optional filter
    
    query = MentalHealthAssessment.query
    if assessment_type:
        query = query.filter_by(assessment_type=assessment_type)
    
    assessments = query.all()
    
    # Calculate statistics
    total = len(assessments)
    
    if total == 0:
        return jsonify({
            'success': True,
            'message': 'No assessments found',
            'total': 0
        }), 200
    
    # Risk category distribution with percentages
    risk_counts = {}
    for a in assessments:
        risk_counts[a.risk_category] = risk_counts.get(a.risk_category, 0) + 1
    
    risk_distribution = {
        category: {
            'count': count,
            'percentage': round((count / total) * 100, 1)
        }
        for category, count in risk_counts.items()
    }
    
    # Baseline vs follow-up
    baseline_count = sum(1 for a in assessments if a.is_baseline)
    followup_count = total - baseline_count
    
    return jsonify({
        'success': True,
        'total_assessments': total,
        'assessment_type': assessment_type or 'All',
        'risk_distribution': risk_distribution,
        'baseline_assessments': baseline_count,
        'followup_assessments': followup_count,
        'high_risk_percentage': round(
            ((risk_counts.get('Orange', 0) + risk_counts.get('Red', 0)) / total) * 100, 1
        )
    }), 200


@assessments_bp.route('/by-advocate', methods=['GET'])
@login_required
@supervisor_required
def assessments_by_advocate():
    """
    View assessment counts by Prevention Advocate.
    Useful for monitoring advocate activity and performance.
    """
    from models import User
    
    # Query to get counts per advocate
    results = db.session.query(
        User.username,
        User.user_id,
        func.count(MentalHealthAssessment.assessment_id).label('assessment_count'),
        func.sum(case((MentalHealthAssessment.risk_category.in_(['Orange', 'Red']), 1), else_=0)).label('high_risk_count')
    ).join(
        MentalHealthAssessment, 
        MentalHealthAssessment.administered_by == User.user_id
    ).filter(
        User.role == 'Prevention Advocate'
    ).group_by(
        User.user_id, User.username
    ).all()
    
    advocates_data = [{
        'username': r.username,
        'total_assessments': r.assessment_count,
        'high_risk_flagged': r.high_risk_count or 0
    } for r in results]
    
    return jsonify({
        'success': True,
        'advocates': advocates_data,
        'total_advocates': len(advocates_data)
    }), 200


# ============================================================================
# VALIDATION ENDPOINTS
# ============================================================================

@assessments_bp.route('/validate-champion-code', methods=['POST'])
@login_required
@prevention_advocate_required
def validate_champion_code():
    """Validate a champion code before submitting assessment."""
    data = request.get_json()
    champion_code = data.get('champion_code', '').strip().upper()
    
    if not champion_code:
        return jsonify({
            'success': False,
            'valid': False,
            'message': 'Champion code is required'
        }), 400
    
    champion = Champion.query.filter_by(assigned_champion_code=champion_code).first()
    
    if champion:
        return jsonify({
            'success': True,
            'valid': True,
            'message': 'Champion code is valid'
        }), 200
    else:
        return jsonify({
            'success': True,
            'valid': False,
            'message': 'Invalid champion code'
        }), 200


# ============================================================================
# ADMIN ENDPOINTS - Full system oversight
# ============================================================================

@assessments_bp.route('/admin/overview', methods=['GET'])
@login_required
@admin_required
def admin_overview():
    """
    Admin dashboard with comprehensive system-wide metrics.
    PRIVACY: Still no individual identifiers or raw scores.
    """
    total_assessments = MentalHealthAssessment.query.count()
    total_champions = Champion.query.count()
    
    # Champions with at least one assessment
    assessed_champions = db.session.query(
        func.distinct(MentalHealthAssessment.champion_code)
    ).count()
    
    # Recent assessments (last 7 days)
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_count = MentalHealthAssessment.query.filter(
        MentalHealthAssessment.assessment_date >= week_ago
    ).count()
    
    return jsonify({
        'success': True,
        'system_overview': {
            'total_assessments': total_assessments,
            'total_champions': total_champions,
            'champions_assessed': assessed_champions,
            'coverage_percentage': round((assessed_champions / total_champions) * 100, 1) if total_champions > 0 else 0,
            'recent_assessments_7days': recent_count
        }
    }), 200
