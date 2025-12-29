from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, MentalHealthAssessment, Champion
from decorators import supervisor_required
from datetime import datetime

assessments_bp = Blueprint('assessments', __name__, url_prefix='/api/assessments')


@assessments_bp.route('/', methods=['GET'])
@login_required
@supervisor_required
def list_assessments():
    """Get all mental health assessments with optional filtering."""
    champion_id = request.args.get('champion_id', type=int)
    assessment_type = request.args.get('type')  # PHQ-9, GAD-7, PHQ-2, GAD-2
    baseline_only = request.args.get('baseline', 'false').lower() == 'true'
    
    query = MentalHealthAssessment.query
    
    if champion_id:
        query = query.filter_by(champion_id=champion_id)
    if assessment_type:
        query = query.filter_by(assessment_type=assessment_type)
    if baseline_only:
        query = query.filter_by(is_baseline=True)
    
    query = query.order_by(MentalHealthAssessment.assessment_date.desc())
    assessments = query.all()
    
    return jsonify({
        'success': True,
        'total': len(assessments),
        'assessments': [{
            'assessment_id': a.assessment_id,
            'champion_id': a.champion_id,
            'assessment_type': a.assessment_type,
            'assessment_date': a.assessment_date.isoformat() if a.assessment_date else None,
            'total_score': a.total_score,
            'severity_level': a.severity_level,
            'is_baseline': a.is_baseline,
            'assessment_period': a.assessment_period,
            'risk_flagged': a.risk_flagged,
            'referral_recommended': a.referral_recommended,
            'referral_made': a.referral_made
        } for a in assessments]
    }), 200


@assessments_bp.route('/<int:assessment_id>', methods=['GET'])
@login_required
@supervisor_required
def get_assessment(assessment_id):
    """Get detailed assessment including item scores."""
    assessment = MentalHealthAssessment.query.get_or_404(assessment_id)
    
    return jsonify({
        'success': True,
        'assessment': {
            'assessment_id': assessment.assessment_id,
            'champion_id': assessment.champion_id,
            'champion_name': assessment.champion.full_name if assessment.champion else None,
            'assessment_type': assessment.assessment_type,
            'assessment_date': assessment.assessment_date.isoformat() if assessment.assessment_date else None,
            'total_score': assessment.total_score,
            'severity_level': assessment.severity_level,
            'is_baseline': assessment.is_baseline,
            'assessment_period': assessment.assessment_period,
            'item_scores': assessment.item_scores,
            'risk_flagged': assessment.risk_flagged,
            'referral_recommended': assessment.referral_recommended,
            'referral_made': assessment.referral_made,
            'notes': assessment.notes,
            'administered_by': assessment.administered_by,
            'created_at': assessment.created_at.isoformat() if assessment.created_at else None
        }
    }), 200


@assessments_bp.route('/', methods=['POST'])
@login_required
@supervisor_required
def create_assessment():
    """Record a new mental health assessment."""
    data = request.get_json()
    
    required_fields = ['champion_id', 'assessment_type', 'total_score']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'message': f'Missing required fields: {required_fields}'
        }), 400
    
    # Validate champion exists
    champion = Champion.query.get(data['champion_id'])
    if not champion:
        return jsonify({
            'success': False,
            'message': 'Champion not found'
        }), 404
    
    # Determine severity based on score and assessment type
    severity = determine_severity(data['assessment_type'], data['total_score'])
    
    assessment = MentalHealthAssessment(
        champion_id=data['champion_id'],
        assessment_type=data['assessment_type'],
        total_score=data['total_score'],
        severity_level=severity,
        is_baseline=data.get('is_baseline', False),
        assessment_period=data.get('assessment_period', 'Follow-up'),
        item_scores=data.get('item_scores'),
        risk_flagged=data.get('risk_flagged', False),
        referral_recommended=data.get('referral_recommended', False),
        referral_made=data.get('referral_made', False),
        administered_by=current_user.user_id,
        notes=data.get('notes')
    )
    
    db.session.add(assessment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Assessment recorded successfully',
        'assessment_id': assessment.assessment_id,
        'severity_level': severity
    }), 201


@assessments_bp.route('/<int:assessment_id>', methods=['PUT'])
@login_required
@supervisor_required
def update_assessment(assessment_id):
    """Update an existing assessment."""
    assessment = MentalHealthAssessment.query.get_or_404(assessment_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Update fields
    if 'total_score' in data:
        assessment.total_score = data['total_score']
        assessment.severity_level = determine_severity(assessment.assessment_type, data['total_score'])
    if 'item_scores' in data:
        assessment.item_scores = data['item_scores']
    if 'risk_flagged' in data:
        assessment.risk_flagged = data['risk_flagged']
    if 'referral_recommended' in data:
        assessment.referral_recommended = data['referral_recommended']
    if 'referral_made' in data:
        assessment.referral_made = data['referral_made']
    if 'notes' in data:
        assessment.notes = data['notes']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Assessment updated successfully'
    }), 200


def determine_severity(assessment_type, score):
    """Determine severity level based on assessment type and score."""
    if assessment_type == 'PHQ-9':
        if score >= 20:
            return 'Severe'
        elif score >= 15:
            return 'Moderately Severe'
        elif score >= 10:
            return 'Moderate'
        elif score >= 5:
            return 'Mild'
        else:
            return 'None'
    elif assessment_type == 'GAD-7':
        if score >= 15:
            return 'Severe'
        elif score >= 10:
            return 'Moderate'
        elif score >= 5:
            return 'Mild'
        else:
            return 'None'
    elif assessment_type in ['PHQ-2', 'GAD-2']:
        if score >= 3:
            return 'Positive Screen'
        else:
            return 'Negative Screen'
    return 'Unknown'


@assessments_bp.route('/champion/<int:champion_id>/trend', methods=['GET'])
@login_required
@supervisor_required
def get_champion_trend(champion_id):
    """Get assessment trend for a champion over time."""
    assessment_type = request.args.get('type', 'PHQ-9')
    
    assessments = MentalHealthAssessment.query.filter_by(
        champion_id=champion_id,
        assessment_type=assessment_type
    ).order_by(MentalHealthAssessment.assessment_date.asc()).all()
    
    if not assessments:
        return jsonify({
            'success': True,
            'champion_id': champion_id,
            'assessment_type': assessment_type,
            'trend': [],
            'message': 'No assessments found for this champion'
        }), 200
    
    trend_data = [{
        'date': a.assessment_date.isoformat() if a.assessment_date else None,
        'score': a.total_score,
        'severity': a.severity_level,
        'is_baseline': a.is_baseline
    } for a in assessments]
    
    # Calculate improvement
    if len(assessments) >= 2:
        baseline = next((a for a in assessments if a.is_baseline), assessments[0])
        latest = assessments[-1]
        improvement = baseline.total_score - latest.total_score
        improvement_percent = (improvement / baseline.total_score * 100) if baseline.total_score > 0 else 0
    else:
        improvement = 0
        improvement_percent = 0
    
    return jsonify({
        'success': True,
        'champion_id': champion_id,
        'assessment_type': assessment_type,
        'trend': trend_data,
        'baseline_score': assessments[0].total_score if assessments[0].is_baseline else None,
        'latest_score': assessments[-1].total_score,
        'improvement': improvement,
        'improvement_percent': round(improvement_percent, 1)
    }), 200
