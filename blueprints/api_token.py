from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, date, timezone
from models import db, Champion, YouthSupport, User
from blueprints.api import _check_api_token

api_token_bp = Blueprint('api_token', __name__, url_prefix='/api')


@api_token_bp.route('/checkin', methods=['POST'])
def token_submit_checkin():
    """Token-authenticated endpoint for submitting a champion check-in.

    Requires Authorization: Bearer <token> header and JSON body.
    """
    # Enforce JSON for token endpoints
    if not request.is_json:
        return jsonify({'error': 'Expected application/json'}), 400

    # Require valid API token
    if not _check_api_token():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}

    cid = data.get('champion_id')
    # If no champion_id supplied, try to infer from JWT payload or user record
    if not cid:
        try:
            from flask import g
            payload = getattr(g, 'jwt_payload', {}) or {}
            # token may include champion_id directly
            cid = payload.get('champion_id')
            if not cid and payload.get('sub'):
                # sub is user_id
                try:
                    uid = int(payload.get('sub'))
                    user = db.session.get(User, uid)
                    if user:
                        cid = user.champion_id
                except Exception:
                    cid = None
        except Exception:
            cid = None

    if not cid:
        return jsonify({'error': 'Missing champion_id for token-authenticated request'}), 400

    champion = db.session.get(Champion, int(cid))
    if not champion:
        return jsonify({'error': 'Champion profile not found'}), 404

    # Parse reporting_period
    rp = data.get('reporting_period')
    if not rp:
        reporting_period = date.today()
    else:
        try:
            reporting_period = datetime.strptime(rp, '%Y-%m-%d').date()
        except Exception:
            return jsonify({'error': 'Invalid reporting_period format. Use YYYY-MM-DD'}), 400

    try:
        report = YouthSupport.query.filter_by(champion_id=champion.champion_id, reporting_period=reporting_period).first()
        if not report:
            report = YouthSupport(champion_id=champion.champion_id, reporting_period=reporting_period)

        if 'number_of_youth_under_support' in data:
            report.number_of_youth_under_support = int(data.get('number_of_youth_under_support') or 0)
        if 'weekly_check_in_completion_rate' in data:
            report.weekly_check_in_completion_rate = float(data.get('weekly_check_in_completion_rate') or 0)
        if 'monthly_mini_screenings_delivered' in data:
            report.monthly_mini_screenings_delivered = int(data.get('monthly_mini_screenings_delivered') or 0)
        if 'referrals_initiated' in data:
            report.referrals_initiated = int(data.get('referrals_initiated') or 0)
        if 'flags_and_concerns_logged' in data:
            report.flags_and_concerns_logged = data.get('flags_and_concerns_logged')

        try:
            if report.weekly_check_in_completion_rate is not None and float(report.weekly_check_in_completion_rate) < 50:
                report.flag_timestamp = datetime.now(timezone.utc)
            if report.flags_and_concerns_logged:
                report.flag_timestamp = datetime.now(timezone.utc)
        except Exception:
            pass

        db.session.add(report)
        db.session.commit()

        return jsonify({'success': True, 'report_id': report.support_id, 'flagged': bool(report.flag_timestamp)}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error saving token checkin')
        return jsonify({'error': str(e)}), 500
