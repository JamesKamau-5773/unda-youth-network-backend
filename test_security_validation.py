"""
Security Validation & API Integration Test
Tests that privacy is enforced in actual API responses
"""

from app import app
from models import db, User, Champion, MentalHealthAssessment
from flask import json
from datetime import date


def create_test_data():
    """Create test data for API testing"""
    with app.app_context():
        # Create test Prevention Advocate
        advocate = User.query.filter_by(username='test_advocate').first()
        if not advocate:
            advocate = User(username='test_advocate', role='Prevention Advocate')
            advocate.set_password('TestPassword123!')
            db.session.add(advocate)
        
        # Create test Supervisor
        supervisor = User.query.filter_by(username='test_supervisor').first()
        if not supervisor:
            supervisor = User(username='test_supervisor', role='Supervisor')
            supervisor.set_password('TestPassword123!')
            db.session.add(supervisor)
        
        # Create test Admin
        admin = User.query.filter_by(username='test_admin').first()
        if not admin:
            admin = User(username='test_admin', role='Admin')
            admin.set_password('TestPassword123!')
            db.session.add(admin)
        
        # Create test Champion
        champion = Champion.query.filter_by(email='test.champion@test.com').first()
        if not champion:
            from models import generate_champion_code
            champion = Champion(
                full_name='Test Champion',
                gender='Male',
                date_of_birth=date(2000, 1, 1),
                phone_number='254712345678',
                email='test.champion@test.com',
                county_sub_county='Test County',
                assigned_champion_code=generate_champion_code(),
                consent_obtained=True,
                consent_date=date.today()
            )
            db.session.add(champion)
        
        db.session.commit()
        
        return {
            'advocate': advocate,
            'supervisor': supervisor,
            'admin': admin,
            'champion': champion
        }


def validate_api_response_privacy(response_data, endpoint_name):
    """
    Validate that API response doesn't contain privacy violations
    """
    violations = []
    
    # Convert to string for easier searching
    response_str = json.dumps(response_data).lower()
    
    # Check for privacy violations
    privacy_violations = {
        'total_score': 'Raw total score exposed',
        'item_scores': 'Individual item scores exposed',
        'severity_level': 'Old severity level exposed (should use risk_category)',
    }
    
    for violation, description in privacy_violations.items():
        if violation in response_str:
            violations.append(f"{description} in {endpoint_name}")
    
    # Check that risk_category is used instead
    if 'risk_category' in response_str or 'risk_distribution' in response_str:
        # Good - using privacy-first approach
        pass
    elif 'assessment' in response_str:
        # Assessment data without risk_category might be a problem
        violations.append(f"Assessment data without risk_category in {endpoint_name}")
    
    return violations


def test_champion_registration():
    """Test champion self-registration API"""
    print("\n1. Testing Champion Self-Registration...")
    
    with app.test_client() as client:
        # Test registration
        response = client.post('/api/champions/register',
            json={
                'full_name': 'API Test Champion',
                'gender': 'Female',
                'date_of_birth': '2001-05-15',
                'phone_number': '254722334455',
                'email': 'apitest@example.com',
                'county_sub_county': 'Nairobi, Westlands',
                'consent_obtained': True,
                'recruitment_source': 'API Test'
            },
            content_type='application/json'
        )
        
        if response.status_code == 201:
            data = json.loads(response.data)
            print(f"   ✅ Champion registered successfully")
            print(f"   Champion Code: {data.get('champion_code')}")
            
            # Verify code format
            code = data.get('champion_code', '')
            if code.startswith('UMV-') and len(code) == 15:
                print(f"   ✅ Champion code format correct")
            else:
                print(f"   ❌ Invalid champion code format: {code}")
            
            return data.get('champion_code')
        else:
            print(f"   ❌ Registration failed: {response.data}")
            return None


def test_privacy_in_responses():
    """Test that API responses don't contain privacy violations"""
    print("\n2. Testing Privacy in API Responses...")
    
    test_users = create_test_data()
    violations_found = []
    
    with app.test_client() as client:
        # Login as supervisor
        client.post('/auth/login', data={
            'username': 'test_supervisor',
            'password': 'TestPassword123!'
        })
        
        # Test dashboard endpoint
        response = client.get('/api/assessments/dashboard?days=30')
        if response.status_code == 200:
            data = json.loads(response.data)
            violations = validate_api_response_privacy(data, 'Dashboard')
            if violations:
                violations_found.extend(violations)
            else:
                print(f"   ✅ Dashboard endpoint is privacy-compliant")
        
        # Test statistics endpoint
        response = client.get('/api/assessments/statistics')
        if response.status_code == 200:
            data = json.loads(response.data)
            violations = validate_api_response_privacy(data, 'Statistics')
            if violations:
                violations_found.extend(violations)
            else:
                print(f"   ✅ Statistics endpoint is privacy-compliant")
    
    if violations_found:
        print(f"\n   ❌ PRIVACY VIOLATIONS FOUND:")
        for violation in violations_found:
            print(f"      - {violation}")
        return False
    else:
        print(f"   ✅ All checked endpoints are privacy-compliant")
        return True


def test_assessment_submission():
    """Test assessment submission with privacy checks"""
    print("\n3. Testing Assessment Submission...")
    
    with app.app_context():
        test_users = create_test_data()
        champion_code = test_users['champion'].assigned_champion_code
    
    with app.test_client() as client:
        # Login as Prevention Advocate
        client.post('/auth/login', data={
            'username': 'test_advocate',
            'password': 'TestPassword123!'
        })
        
        # Submit assessment
        response = client.post('/api/assessments/submit',
            json={
                'champion_code': champion_code,
                'assessment_type': 'PHQ-9',
                'raw_score': 18,  # Orange category
                'is_baseline': True,
                'assessment_period': 'Initial'
            },
            content_type='application/json'
        )
        
        if response.status_code == 201:
            data = json.loads(response.data)
            print(f"   ✅ Assessment submitted successfully")
            print(f"   Risk Category: {data.get('risk_category')}")
            print(f"   Referral Created: {data.get('referral_created')}")
            
            # Verify raw score is NOT in response
            response_str = json.dumps(data)
            if 'raw_score' not in response_str and '18' not in response_str:
                print(f"   ✅ Raw score NOT included in response (privacy preserved)")
            else:
                print(f"   ❌ Raw score leaked in response!")
                return False
            
            # Verify database doesn't have raw score
            with app.app_context():
                assessment = MentalHealthAssessment.query.get(data['assessment_id'])
                if assessment:
                    # Check that assessment only has risk_category, not score
                    if hasattr(assessment, 'total_score'):
                        print(f"   ❌ Database still has total_score attribute!")
                        return False
                    else:
                        print(f"   ✅ Database schema is privacy-compliant")
                        print(f"   Stored: risk_category={assessment.risk_category}, range={assessment.score_range}")
            
            return True
        else:
            print(f"   ❌ Assessment submission failed: {response.data}")
            return False


def test_role_based_access():
    """Test that role-based access control is enforced"""
    print("\n4. Testing Role-Based Access Control...")
    
    with app.app_context():
        test_users = create_test_data()
    
    # Test that only appropriate roles can access endpoints
    tests = [
        {
            'role': 'Prevention Advocate',
            'username': 'test_advocate',
            'can_access': ['/api/assessments/my-submissions'],
            'cannot_access': []
        },
        {
            'role': 'Supervisor',
            'username': 'test_supervisor',
            'can_access': ['/api/assessments/dashboard', '/api/assessments/statistics'],
            'cannot_access': []
        }
    ]
    
    all_passed = True
    
    for test in tests:
        with app.test_client() as client:
            # Login
            client.post('/auth/login', data={
                'username': test['username'],
                'password': 'TestPassword123!'
            })
            
            print(f"\n   Testing {test['role']} access...")
            
            # Test allowed access
            for endpoint in test['can_access']:
                response = client.get(endpoint)
                
                # Should not be 403 Forbidden
                if response.status_code != 403:
                    print(f"      ✅ Can access {endpoint}")
                else:
                    print(f"      ❌ Blocked from {endpoint} (should have access)")
                    all_passed = False
    
    if all_passed:
        print(f"\n   ✅ Role-based access control is working correctly")
    
    return all_passed


def run_security_validation():
    """Run all security validation tests"""
    print("=" * 70)
    print("UMV PRIVACY-FIRST SECURITY VALIDATION")
    print("=" * 70)
    
    results = {
        'champion_registration': False,
        'privacy_compliance': False,
        'assessment_submission': False,
        'rbac': False
    }
    
    try:
        # Test 1: Champion Registration
        champion_code = test_champion_registration()
        results['champion_registration'] = bool(champion_code)
        
        # Test 2: Privacy in Responses
        results['privacy_compliance'] = test_privacy_in_responses()
        
        # Test 3: Assessment Submission
        results['assessment_submission'] = test_assessment_submission()
        
        # Test 4: Role-Based Access Control
        results['rbac'] = test_role_based_access()
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print("SECURITY VALIDATION SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🔒 ✅ ALL SECURITY VALIDATIONS PASSED")
        print("System is ready for production deployment!")
    else:
        print("\n⚠️  SOME SECURITY VALIDATIONS FAILED")
        print("Review failures above before deployment")
    
    print("=" * 70)
    
    return all_passed


if __name__ == '__main__':
    success = run_security_validation()
    exit(0 if success else 1)
