"""
Auto-migration script for event submission columns.
This runs on application startup and creates columns if they don't exist.
"""

from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError


def create_event_submission_columns(db, app):
    """
    Create event submission tracking columns if they don't exist.
    Safe to run multiple times - checks for column existence first.
    """
    
    try:
        with app.app_context():
            # Get database inspector
            inspector = inspect(db.engine)
            events_columns = [col['name'] for col in inspector.get_columns('events')]
            
            required_columns = [
                'submission_status',
                'submitted_by',
                'reviewed_by',
                'reviewed_at',
                'rejection_reason'
            ]
            
            missing_columns = [col for col in required_columns if col not in events_columns]
            
            if not missing_columns:
                print("✅ All submission tracking columns already exist")
                return True
            
            print(f"[AlertTriangle] Missing columns: {missing_columns}")
            print("Creating missing columns...")
            
            with db.engine.connect() as conn:
                migration_sql = f"""
                BEGIN;
                
                -- Add submission tracking columns if they don't exist
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='events' AND column_name='submission_status') THEN
                        ALTER TABLE events ADD COLUMN submission_status VARCHAR(50);
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='events' AND column_name='submitted_by') THEN
                        ALTER TABLE events ADD COLUMN submitted_by INTEGER;
                        ALTER TABLE events ADD CONSTRAINT fk_events_submitted_by
                            FOREIGN KEY(submitted_by) REFERENCES users(user_id) ON DELETE SET NULL;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='events' AND column_name='reviewed_by') THEN
                        ALTER TABLE events ADD COLUMN reviewed_by INTEGER;
                        ALTER TABLE events ADD CONSTRAINT fk_events_reviewed_by
                            FOREIGN KEY(reviewed_by) REFERENCES users(user_id) ON DELETE SET NULL;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='events' AND column_name='reviewed_at') THEN
                        ALTER TABLE events ADD COLUMN reviewed_at TIMESTAMP;
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='events' AND column_name='rejection_reason') THEN
                        ALTER TABLE events ADD COLUMN rejection_reason TEXT;
                    END IF;
                END $$;
                
                COMMIT;
                """
                
                # Execute migration
                try:
                    conn.execute(text(migration_sql))
                    conn.commit()
                    print("[CheckCircle] All event submission columns created successfully")
                    return True
                except ProgrammingError as e:
                    print(f"[AlertTriangle] Column creation issue: {e}")
                    # Columns might already exist, which is fine
                    return True
                    
    except Exception as e:
        print(f"[AlertTriangle] Could not auto-create columns: {e}")
        print("Note: This is fine if using Flask-Migrate. Migration will run separately.")
        return False


def ensure_event_submission_columns(db, app):
    """
    Convenience wrapper that attempts to create columns on app startup.
    Safe to call even if columns already exist.
    """
    try:
        return create_event_submission_columns(db, app)
    except Exception as e:
        app.logger.warning(f"Auto-migration skipped: {e}")
        return False
