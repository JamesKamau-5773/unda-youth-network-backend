"""
Database Migration Script - Add Health & Risk Fields
Adds critical health, safety, and risk assessment fields to Champion model
"""

from app import app, db
from models import Champion
from sqlalchemy import text

def run_migration():
    """Add new columns to champions table"""
    print("=" * 60)
    print("MIGRATING DATABASE - Adding Health & Risk Fields")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('champions')]
            
            print(f"\nExisting columns in champions table: {len(existing_columns)}")
            
            # SQL statements to add new columns
            migrations = [
                # Health & Safety Data
                ("medical_conditions", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS medical_conditions TEXT"),
                ("allergies", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS allergies TEXT"),
                ("mental_health_support", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS mental_health_support TEXT"),
                ("disabilities", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS disabilities TEXT"),
                ("medication_required", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS medication_required TEXT"),
                ("dietary_requirements", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS dietary_requirements TEXT"),
                ("health_notes", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS health_notes TEXT"),
                
                # Risk Assessment & Safeguarding
                ("risk_level", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20) DEFAULT 'Low'"),
                ("risk_assessment_date", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS risk_assessment_date DATE"),
                ("risk_notes", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS risk_notes TEXT"),
                ("last_contact_date", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS last_contact_date DATE"),
                ("next_review_date", "ALTER TABLE champions ADD COLUMN IF NOT EXISTS next_review_date DATE"),
            ]
            
            print("\nAdding new columns...")
            for column_name, sql in migrations:
                if column_name not in existing_columns:
                    print(f"  Adding {column_name}...", end=" ")
                    db.session.execute(text(sql))
                    db.session.commit()
                    print("✓")
                else:
                    print(f"  {column_name} already exists, skipping")
            
            print("\n" + "=" * 60)
            print("MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 60)
            
            # Verify new columns
            inspector = db.inspect(db.engine)
            new_columns = [col['name'] for col in inspector.get_columns('champions')]
            print(f"\nTotal columns after migration: {len(new_columns)}")
            print(f"New columns added: {len(new_columns) - len(existing_columns)}")
            
            # Set default risk_level for existing champions
            print("\nSetting default risk_level='Low' for existing champions...")
            result = db.session.execute(text(
                "UPDATE champions SET risk_level = 'Low' WHERE risk_level IS NULL"
            ))
            db.session.commit()
            print(f"✓ Updated {result.rowcount} champions")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ MIGRATION FAILED: {str(e)}")
            return False


def verify_migration():
    """Verify migration was successful"""
    print("\n" + "=" * 60)
    print("VERIFYING MIGRATION")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Check if new columns exist and are accessible
            test_query = Champion.query.first()
            
            if test_query:
                print("\nTesting new fields on first champion:")
                print(f"  Medical Conditions: {test_query.medical_conditions}")
                print(f"  Allergies: {test_query.allergies}")
                print(f"  Mental Health Support: {test_query.mental_health_support}")
                print(f"  Risk Level: {test_query.risk_level}")
                print(f"  Last Contact Date: {test_query.last_contact_date}")
                print(f"  Next Review Date: {test_query.next_review_date}")
            
            # Check counts by risk level
            low_risk = Champion.query.filter_by(risk_level='Low').count()
            medium_risk = Champion.query.filter_by(risk_level='Medium').count()
            high_risk = Champion.query.filter_by(risk_level='High').count()
            
            print(f"\nRisk Level Distribution:")
            print(f"  Low: {low_risk}")
            print(f"  Medium: {medium_risk}")
            print(f"  High: {high_risk}")
            
            print("\n✓ VERIFICATION SUCCESSFUL")
            return True
            
        except Exception as e:
            print(f"\n✗ VERIFICATION FAILED: {str(e)}")
            return False


def rollback_migration():
    """Rollback migration (remove added columns) - USE WITH CAUTION"""
    print("\n" + "=" * 60)
    print("ROLLING BACK MIGRATION")
    print("=" * 60)
    
    response = input("\nAre you sure you want to rollback? This will DELETE all health and risk data! (yes/no): ")
    
    if response.lower() != 'yes':
        print("Rollback cancelled")
        return False
    
    with app.app_context():
        try:
            columns_to_remove = [
                'medical_conditions', 'allergies', 'mental_health_support',
                'disabilities', 'medication_required', 'dietary_requirements',
                'health_notes', 'risk_level', 'risk_assessment_date',
                'risk_notes', 'last_contact_date', 'next_review_date'
            ]
            
            for column in columns_to_remove:
                print(f"  Removing {column}...", end=" ")
                db.session.execute(text(f"ALTER TABLE champions DROP COLUMN IF EXISTS {column}"))
                db.session.commit()
                print("✓")
            
            print("\n✓ ROLLBACK COMPLETED")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ ROLLBACK FAILED: {str(e)}")
            return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback_migration()
    else:
        success = run_migration()
        if success:
            verify_migration()
        else:
            print("\nMigration failed. Please fix errors and try again.")
