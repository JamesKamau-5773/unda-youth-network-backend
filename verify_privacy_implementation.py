"""
Verification script for UMV Privacy-First Implementation
Checks database schema and privacy compliance
"""

from app import app
from models import db, User, MentalHealthAssessment, Champion
from sqlalchemy import inspect

def verify_migrations():
    """Verify that migrations were applied successfully"""
    with app.app_context():
        print("=" * 70)
        print("UMV PRIVACY-FIRST IMPLEMENTATION VERIFICATION")
        print("=" * 70)
        
        # Check User roles
        print("\n1. CHECKING USER ROLES...")
        users = User.query.all()
        role_counts = {}
        for user in users:
            role_counts[user.role] = role_counts.get(user.role, 0) + 1
        
        print(f"   Total users: {len(users)}")
        for role, count in role_counts.items():
            print(f"   - {role}: {count}")
        
        # Verify Prevention Advocate role exists
        prevention_advocates = User.query.filter_by(role='Prevention Advocate').count()
        old_champions = User.query.filter_by(role='Champion').count()
        
        if old_champions > 0:
            print(f"   ⚠️  WARNING: Found {old_champions} users with old 'Champion' role")
        else:
            print(f"   ✅ No old 'Champion' roles found")
        
        if prevention_advocates > 0:
            print(f"   ✅ Found {prevention_advocates} Prevention Advocate(s)")
        
        # Check MentalHealthAssessment schema
        print("\n2. CHECKING MENTAL HEALTH ASSESSMENT SCHEMA...")
        inspector = inspect(db.engine)
        columns = inspector.get_columns('mental_health_assessments')
        column_names = [col['name'] for col in columns]
        
        print(f"   Columns found: {len(column_names)}")
        
        # Check for REMOVED columns (privacy violations)
        privacy_violations = []
        if 'champion_id' in column_names:
            privacy_violations.append('champion_id (FK to champion)')
        if 'total_score' in column_names:
            privacy_violations.append('total_score (raw score)')
        if 'item_scores' in column_names:
            privacy_violations.append('item_scores (individual responses)')
        if 'severity_level' in column_names:
            privacy_violations.append('severity_level (text description)')
        
        if privacy_violations:
            print(f"   ❌ PRIVACY VIOLATIONS FOUND:")
            for violation in privacy_violations:
                print(f"      - {violation}")
        else:
            print(f"   ✅ No privacy-violating columns found")
        
        # Check for NEW columns (privacy-first)
        required_columns = ['champion_code', 'risk_category', 'score_range']
        missing_columns = []
        for col in required_columns:
            if col not in column_names:
                missing_columns.append(col)
        
        if missing_columns:
            print(f"   ❌ MISSING REQUIRED COLUMNS:")
            for col in missing_columns:
                print(f"      - {col}")
        else:
            print(f"   ✅ All privacy-first columns present")
            for col in required_columns:
                print(f"      - {col}")
        
        # Check assessment data
        print("\n3. CHECKING ASSESSMENT DATA...")
        assessment_count = MentalHealthAssessment.query.count()
        print(f"   Total assessments: {assessment_count}")
        
        if assessment_count == 0:
            print(f"   ✅ Old data cleaned (starting fresh as specified)")
        else:
            print(f"   📊 Found {assessment_count} assessments")
            # Check if any have privacy violations
            sample = MentalHealthAssessment.query.first()
            if sample:
                print(f"   Sample assessment:")
                print(f"      - champion_code: {sample.champion_code}")
                print(f"      - risk_category: {sample.risk_category}")
                print(f"      - score_range: {sample.score_range}")
                print(f"      - assessment_type: {sample.assessment_type}")
        
        # Check Champion codes
        print("\n4. CHECKING CHAMPION CODES...")
        champions = Champion.query.all()
        print(f"   Total champions: {len(champions)}")
        
        codes_with_format = 0
        for champion in champions:
            if champion.assigned_champion_code and champion.assigned_champion_code.startswith('UMV-'):
                codes_with_format += 1
        
        print(f"   Champions with UMV-YYYY-NNNNNN format: {codes_with_format}/{len(champions)}")
        
        # Sample codes
        if len(champions) > 0:
            print(f"   Sample champion codes:")
            for champion in champions[:5]:
                print(f"      - {champion.assigned_champion_code}")
        
        # Valid Roles check
        print("\n5. CHECKING VALID_ROLES CONSTANT...")
        print(f"   Valid roles: {User.VALID_ROLES}")
        if 'Prevention Advocate' in User.VALID_ROLES:
            print(f"   ✅ 'Prevention Advocate' in VALID_ROLES")
        else:
            print(f"   ❌ 'Prevention Advocate' NOT in VALID_ROLES")
        
        if 'Champion' in User.VALID_ROLES:
            print(f"   ⚠️  'Champion' still in VALID_ROLES (should be removed)")
        else:
            print(f"   ✅ 'Champion' removed from VALID_ROLES")
        
        # Final summary
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        
        all_good = True
        
        if old_champions > 0:
            print("❌ Old 'Champion' roles still exist")
            all_good = False
        
        if privacy_violations:
            print("❌ Privacy-violating columns still in database")
            all_good = False
        
        if missing_columns:
            print("❌ Required privacy-first columns missing")
            all_good = False
        
        if 'Prevention Advocate' not in User.VALID_ROLES:
            print("❌ VALID_ROLES not updated")
            all_good = False
        
        if all_good:
            print("✅ ALL CHECKS PASSED - Privacy-first implementation verified!")
        else:
            print("⚠️  SOME ISSUES FOUND - Review output above")
        
        print("=" * 70)

if __name__ == '__main__':
    verify_migrations()
