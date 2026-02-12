"""Service layer for managing member event submissions and approval workflow."""

from datetime import datetime
from models import Event, db
import logging
import traceback

logger = logging.getLogger(__name__)


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
            logger.info(f'Creating event submission from user {user_id}: {data.get("title")}')
            event = Event(
                title=data.get('title'),
                description=data.get('description'),
                event_date=data.get('event_date'),
                location=data.get('location'),
                event_type=data.get('event_type'),  # mtaani, baraza, etc.
                created_by=user_id,
                submitted_by=user_id,
                submission_status='Pending Approval',
                # Note: status is left as default 'Upcoming' but event is not yet published
                # It will only be published (visible) after admin approves it
            )
            db.session.add(event)
            db.session.commit()
            
            logger.info(f'Event submission created successfully: event_id={event.event_id}, user={user_id}')
            return {
                'success': True,
                'message': 'Event submitted for approval',
                'event_id': event.event_id,
                'submission_status': 'Pending Approval'
            }
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            logger.error(f'Failed to create event submission for user {user_id}: {error_msg}')
            logger.error(f'Traceback: {traceback.format_exc()}')
            return {
                'success': False,
                'message': f'Failed to submit event: {error_msg}'
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
            logger.info(f'Listing event submissions with filter: {status_filter}')
            query = Event.query.filter(Event.submission_status.isnot(None))
            
            if status_filter:
                query = query.filter_by(submission_status=status_filter)
                logger.debug(f'Applied status filter: {status_filter}')
            
            submissions = query.order_by(Event.created_at.desc()).all()
            logger.info(f'Retrieved {len(submissions)} event submissions')
            return [s.to_dict() for s in submissions]
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Failed to fetch submissions: {error_msg}')
            logger.error(f'Traceback: {traceback.format_exc()}')
            return {'error': f'Failed to fetch submissions: {error_msg}'}
    
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
            logger.info(f'Retrieving event submission: event_id={event_id}')
            event = Event.query.filter(
                Event.event_id == event_id,
                Event.submission_status.isnot(None)
            ).first()
            
            if event:
                logger.info(f'Event submission found: {event.title}')
                return event.to_dict()
            else:
                logger.warning(f'Event submission not found: event_id={event_id}')
                return None
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Failed to fetch submission {event_id}: {error_msg}')
            logger.error(f'Traceback: {traceback.format_exc()}')
            return {'error': f'Failed to fetch submission: {error_msg}'}
    
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
            logger.info(f'Approving event submission: event_id={event_id}, reviewer_id={reviewer_id}')
            event = Event.query.get(event_id)
            if not event:
                error_msg = f'Event not found: event_id={event_id}'
                logger.warning(error_msg)
                return {'success': False, 'message': 'Event not found'}
            
            if event.submission_status != 'Pending Approval':
                error_msg = f'Cannot approve event {event_id}: current status is {event.submission_status}'
                logger.warning(error_msg)
                return {'success': False, 'message': f'Event is {event.submission_status}, cannot approve'}
            
            # Approve the submission and publish it
            event.submission_status = 'Approved'
            event.status = 'Upcoming'  # Publish as upcoming event
            event.reviewed_by = reviewer_id
            event.reviewed_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f'Event submission approved successfully: event_id={event_id}, title={event.title}')
            return {
                'success': True,
                'message': 'Event approved and published as Upcoming',
                'event': event.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            logger.error(f'Failed to approve event submission {event_id}: {error_msg}')
            logger.error(f'Traceback: {traceback.format_exc()}')
            return {'success': False, 'message': f'Failed to approve event: {error_msg}'}
    
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
            logger.info(f'Rejecting event submission: event_id={event_id}, reviewer_id={reviewer_id}, reason={rejection_reason}')
            event = Event.query.get(event_id)
            if not event:
                error_msg = f'Event not found: event_id={event_id}'
                logger.warning(error_msg)
                return {'success': False, 'message': 'Event not found'}
            
            if event.submission_status != 'Pending Approval':
                error_msg = f'Cannot reject event {event_id}: current status is {event.submission_status}'
                logger.warning(error_msg)
                return {'success': False, 'message': f'Event is {event.submission_status}, cannot reject'}
            
            # Reject the submission
            # Note: We set submission_status to 'Rejected' but do NOT change the status field
            # (which has valid values: Upcoming, Ongoing, Completed, Cancelled)
            event.submission_status = 'Rejected'
            event.reviewed_by = reviewer_id
            event.reviewed_at = datetime.utcnow()
            event.rejection_reason = rejection_reason
            
            db.session.commit()
            
            logger.info(f'Event submission rejected successfully: event_id={event_id}, title={event.title}')
            return {
                'success': True,
                'message': 'Event submission rejected',
                'event': event.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            logger.error(f'Failed to reject event submission {event_id}: {error_msg}')
            logger.error(f'Traceback: {traceback.format_exc()}')
            return {'success': False, 'message': f'Failed to reject event: {error_msg}'}
