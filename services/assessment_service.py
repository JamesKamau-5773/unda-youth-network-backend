from datetime import datetime
from models import db, MentalHealthAssessment


def create_assessment(data: dict, administered_by: int) -> MentalHealthAssessment:
    champion_code = (data.get('champion_code') or '').strip()
    assessment_type = (data.get('assessment_type') or '').strip()
    risk_category = (data.get('risk_category') or '').strip()
    notes = data.get('notes')

    if not champion_code or not assessment_type or not risk_category:
        raise ValueError('Champion code, type and risk category are required')

    assessment = MentalHealthAssessment(champion_code=champion_code, assessment_type=assessment_type, risk_category=risk_category, notes=notes, administered_by=administered_by)
    db.session.add(assessment)
    db.session.commit()
    return assessment


def delete_assessment(assessment_id: int) -> None:
    assessment = db.session.get(MentalHealthAssessment, assessment_id)
    if not assessment:
        raise ValueError('Assessment not found')
    db.session.delete(assessment)
    db.session.commit()
