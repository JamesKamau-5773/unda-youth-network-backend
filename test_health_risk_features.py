"""
Test suite for health tracking, risk assessment, and advanced filtering features
"""

import sys
from datetime import datetime, timedelta
from app import app, db
from models import Champion, get_high_risk_champions, get_overdue_reviews, get_champions_by_risk_level


def test_health_risk_fields():
    """Test 1: Verify health and risk fields can be set and retrieved"""
    print("\n=== Test 1: Health & Risk Field CRUD ===")
    
    with app.app_context():
        # Get first champion
        champion = Champion.query.first()
        if not champion:
            print("❌ No champions found in database")
            return False
        
        print(f"Testing with champion: {champion.full_name} ({champion.assigned_champion_code})")
        
        # Update health fields
        champion.medical_conditions = "Asthma"
        champion.allergies = "Peanuts, Shellfish"
        champion.mental_health_support = "Weekly counseling sessions"
        champion.disabilities = "None"
        champion.medication_required = "Albuterol inhaler"
        champion.dietary_requirements = "Vegetarian"
        champion.health_notes = "Requires emergency inhaler access"
        
        # Update risk fields
        champion.risk_level = "Medium"
        champion.risk_assessment_date = datetime.utcnow()
        champion.risk_notes = "Some concerns about attendance, monitoring required"
        champion.last_contact_date = (datetime.utcnow() - timedelta(days=5)).date()
        champion.next_review_date = (datetime.utcnow() + timedelta(days=30)).date()
        
        db.session.commit()
        print("✓ Updated champion with health and risk data")
        
        # Retrieve and verify
        db.session.refresh(champion)
        assert champion.medical_conditions == "Asthma", "Medical conditions not saved"
        assert champion.allergies == "Peanuts, Shellfish", "Allergies not saved"
        assert champion.risk_level == "Medium", "Risk level not saved"
        assert champion.next_review_date is not None, "Review date not saved"
        
        print("✓ All fields retrieved successfully")
        print(f"  - Medical: {champion.medical_conditions}")
        print(f"  - Allergies: {champion.allergies}")
        print(f"  - Risk: {champion.risk_level}")
        print(f"  - Next Review: {champion.next_review_date}")
        
        return True


def test_risk_level_filtering():
    """Test 2: Verify risk level filtering helper functions"""
    print("\n=== Test 2: Risk Level Filtering ===")
    
    with app.app_context():
        # Set different risk levels for testing
        champions = Champion.query.limit(3).all()
        
        if len(champions) < 3:
            print(f"⚠️  Only {len(champions)} champions available (need 3 for full test)")
            if len(champions) == 0:
                print("❌ No champions found")
                return False
        
        # Set varied risk levels
        if len(champions) >= 1:
            champions[0].risk_level = "Low"
        if len(champions) >= 2:
            champions[1].risk_level = "Medium"
        if len(champions) >= 3:
            champions[2].risk_level = "High"
        
        db.session.commit()
        print(f"✓ Set risk levels for {len(champions)} champions")
        
        # Test filtering functions
        low_risk = get_champions_by_risk_level("Low")
        medium_risk = get_champions_by_risk_level("Medium")
        high_risk = get_high_risk_champions()
        
        print(f"✓ Risk distribution:")
        print(f"  - Low: {len(low_risk)} champions")
        print(f"  - Medium: {len(medium_risk)} champions")
        print(f"  - High: {len(high_risk)} champions")
        
        # Verify high-risk function works
        if len(champions) >= 3:
            assert len(high_risk) >= 1, "High-risk filtering not working"
            print(f"✓ High-risk champions identified: {[c.full_name for c in high_risk]}")
        
        return True


def test_overdue_reviews():
    """Test 3: Verify overdue review detection"""
    print("\n=== Test 3: Overdue Review Detection ===")
    
    with app.app_context():
        # Set one champion with overdue review
        champion = Champion.query.first()
        if not champion:
            print("❌ No champions found")
            return False
        
        # Set review date in the past
        champion.next_review_date = (datetime.utcnow() - timedelta(days=10)).date()
        db.session.commit()
        print(f"✓ Set overdue review date for {champion.full_name}")
        
        # Test overdue detection
        overdue = get_overdue_reviews()
        print(f"✓ Found {len(overdue)} overdue reviews")
        
        if len(overdue) > 0:
            for c in overdue:
                days_overdue = (datetime.utcnow().date() - c.next_review_date).days
                print(f"  - {c.full_name}: {days_overdue} days overdue")
        
        assert len(overdue) >= 1, "Overdue detection not working"
        return True


def test_alert_system_integration():
    """Test 4: Verify alert data is properly structured for dashboard"""
    print("\n=== Test 4: Alert System Integration ===")
    
    with app.app_context():
        # Get alert data (simulating what admin dashboard does)
        high_risk_champions = get_high_risk_champions()
        overdue_reviews = get_overdue_reviews()
        
        high_risk_count = len(high_risk_champions)
        overdue_count = len(overdue_reviews)
        
        print(f"✓ Alert system data:")
        print(f"  - High-risk champions: {high_risk_count}")
        print(f"  - Overdue reviews: {overdue_count}")
        
        # Verify data structure for template rendering
        if high_risk_count > 0:
            sample = high_risk_champions[0]
            assert hasattr(sample, 'full_name'), "Missing full_name attribute"
            assert hasattr(sample, 'assigned_champion_code'), "Missing champion_code attribute"
            assert hasattr(sample, 'last_contact_date'), "Missing last_contact_date attribute"
            print(f"✓ High-risk champion data structure valid")
        
        if overdue_count > 0:
            sample = overdue_reviews[0]
            assert hasattr(sample, 'full_name'), "Missing full_name attribute"
            assert hasattr(sample, 'next_review_date'), "Missing next_review_date attribute"
            print(f"✓ Overdue review data structure valid")
        
        return True


def test_database_migration_integrity():
    """Test 5: Verify all 12 new columns exist and are accessible"""
    print("\n=== Test 5: Database Schema Integrity ===")
    
    with app.app_context():
        required_fields = [
            'medical_conditions', 'allergies', 'mental_health_support',
            'disabilities', 'medication_required', 'dietary_requirements',
            'health_notes', 'risk_level', 'risk_assessment_date',
            'risk_notes', 'last_contact_date', 'next_review_date'
        ]
        
        champion = Champion.query.first()
        if not champion:
            print("❌ No champions found")
            return False
        
        missing_fields = []
        for field in required_fields:
            if not hasattr(champion, field):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing fields: {missing_fields}")
            return False
        
        print(f"✓ All 12 new fields are accessible:")
        for field in required_fields:
            print(f"  - {field}: ✓")
        
        return True


def run_all_tests():
    """Execute all tests and report results"""
    print("\n" + "="*60)
    print("HEALTH & RISK ASSESSMENT FEATURE TEST SUITE")
    print("="*60)
    
    tests = [
        ("Health & Risk Field CRUD", test_health_risk_fields),
        ("Risk Level Filtering", test_risk_level_filtering),
        ("Overdue Review Detection", test_overdue_reviews),
        ("Alert System Integration", test_alert_system_integration),
        ("Database Schema Integrity", test_database_migration_integrity),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed ({passed*100//total}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Features are working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review output above.")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
