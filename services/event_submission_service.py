"""Service layer for managing member event submissions and approval workflow."""

from datetime import datetime
from models import Event, db


class EventSubmissionService:
    """Handles event submission, review, and approval logic."""
    
    @staticmethod
    def create_submission(data, user_id):
        """
        Create a new event submission from a member.
        
        Args:
            data: Dict with keys: title, description, event_date, location, event_type
            user_id: ID of the user submitting the event
            
        Returns:
            Dict with success status and event_id or error message
        """
        try:
            event = Event(
                title=data.get('title'),
                description=data.get('description'),
                event_date=data.get('event_date'),
                location=data.get('location'),
                event_type=data.get('event_type'),  # mtaani, baraza, etc.
                created_by=user_id,
                submitted_by=user_id,
                submission_status='Pending Approval',
                status='Pending Approval'  # Will change to Upcoming when approved
            )
            db.session.add(event)
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Event submitted for approval',
                'event_id': event.event_id,
                'submission_status': 'Pending Approval'
            }
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'message': f'Failed to submit event: {str(e)}'
            }
    
    @staticmethod
    def list_submissions(status_filter=None):
        """
        Get all event submissions with optional status filtering.
        
        Args:
            status_filter: Optional status to filter by (Pending Approval, Approved, Rejected)
            
        Returns:
            List of event submissions as dicts
        """
        try:
            query = Event.query.filter(Event.submission_status.isnot(None))
            
            if status_filter:
                query = query.filter_by(submission_status=status_filter)
            
            submissions = query.order_by(Event.created_at.desc()).all()
            return [s.to_dict() for s in submissions]
        except Exception as e:
            return {'error': f'Failed to fetch submissions: {str(e)}'}
    
    @staticmethod
    def get_submission(event_id):
        """
        Get a specific event submission by ID.
        
        Args:
            event_id: ID of the event submission
            
        Returns:
            Event submission dict or None if not found
        """
        try:
            event = Event.query.filter_by(
                event_id=event_id,
                submission_status=Event.submission_status.isnot(None)
            ).first()
            return event.to_dict() if event else None
        except Exception as e:
            return {'error': f'Failed to fetch submission: {str(e)}'}
    
    @staticmethod
    def approve_submission(event_id, reviewer_id, admin_notes=''):
        """
        Approve a member event submission and publish it as Upcoming.
        
        Args:
            event_id: ID of the event submission
            reviewer_id: ID of the admin approving it
            admin_notes: Optional notes from the admin
            
        Returns:
            Dict with success status and updated event
        """
        try:
            event = Event.query.get(event_id)
            if not event:
                return {'success': False, 'message': 'Event not found'}
            
            if event.submission_status != 'Pending Approval':
                return {'success': False, 'message': f'Event is {event.submission_status}, cannot approve'}
            
            # Approve the submission and publish it
            event.submission_status = 'Approved'
            event.status = 'Upcoming'  # Publish as upcoming event
            event.reviewed_by = reviewer_id
            event.reviewed_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Event approved and published as Upcoming',
                'event': event.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Failed to approve event: {str(e)}'}
    
    @staticmethod
    def reject_submission(event_id, reviewer_id, rejection_reason=''):
        """
        Reject a member event submission.
        
        Args:
            event_id: ID of the event submission
            reviewer_id: ID of the admin rejecting it
            rejection_reason: Reason for rejection
            
        Returns:
            Dict with success status and updated event
        """
        try:
            event = Event.query.get(event_id)
            if not event:
                return {'success': False, 'message': 'Event not found'}
            
            if event.submission_status != 'Pending Approval':
                return {'success': False, 'message': f'Event is {event.submission_status}, cannot reject'}
            
            # Reject the submission
            event.submission_status = 'Rejected'
            event.status = 'Rejected'
            event.reviewed_by = reviewer_id
            event.reviewed_at = datetime.utcnow()
            event.rejection_reason = rejection_reason
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Event submission rejected',
                'event': event.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Failed to reject event: {str(e)}'}
