"""
Comprehensive Test Suite for UMV Privacy-First Mental Health Screening
Tests API endpoints, privacy compliance, and security
"""

import unittest
from app import app
from models import db, User, Champion, MentalHealthAssessment, RefferalPathway
from models import map_phq9_to_risk_category, map_gad7_to_risk_category, generate_champion_code
from datetime import datetime, date
import json


class TestPrivacyFirstImplementation(unittest.TestCase):
    """Test privacy-first implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()


class TestRiskCategoryMapping(unittest.TestCase):
    """Test score to risk category mapping functions"""
    
    def test_phq9_green_category(self):
        """Test PHQ-9 Green category (0-4)"""
        for score in [0, 1, 2, 3, 4]:
            result = map_phq9_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Green')
            self.assertEqual(result['score_range'], '0-4')
            self.assertFalse(result['auto_referral'])
    
    def test_phq9_blue_category(self):
        """Test PHQ-9 Blue category (5-9)"""
        for score in [5, 6, 7, 8, 9]:
            result = map_phq9_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Blue')
            self.assertEqual(result['score_range'], '5-9')
            self.assertFalse(result['auto_referral'])
    
    def test_phq9_purple_category(self):
        """Test PHQ-9 Purple category (10-14)"""
        for score in [10, 11, 12, 13, 14]:
            result = map_phq9_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Purple')
            self.assertEqual(result['score_range'], '10-14')
            self.assertFalse(result['auto_referral'])
            self.assertTrue(result['auto_flag'])
    
    def test_phq9_orange_category(self):
        """Test PHQ-9 Orange category (15-19) - Auto-referral"""
        for score in [15, 16, 17, 18, 19]:
            result = map_phq9_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Orange')
            self.assertEqual(result['score_range'], '15-19')
            self.assertTrue(result['auto_referral'])
            self.assertTrue(result['auto_flag'])
    
    def test_phq9_red_category(self):
        """Test PHQ-9 Red category (20-27) - Auto-referral"""
        for score in [20, 21, 25, 27]:
            result = map_phq9_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Red')
            self.assertEqual(result['score_range'], '20-27')
            self.assertTrue(result['auto_referral'])
            self.assertTrue(result['auto_flag'])
    
    def test_phq9_invalid_scores(self):
        """Test PHQ-9 invalid scores"""
        for score in [-1, 28, 100, 'invalid']:
            result = map_phq9_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Invalid')
    
    def test_gad7_green_category(self):
        """Test GAD-7 Green category (0-4)"""
        for score in [0, 1, 2, 3, 4]:
            result = map_gad7_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Green')
            self.assertEqual(result['score_range'], '0-4')
            self.assertFalse(result['auto_referral'])
    
    def test_gad7_blue_category(self):
        """Test GAD-7 Blue category (5-9)"""
        for score in [5, 6, 7, 8, 9]:
            result = map_gad7_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Blue')
            self.assertEqual(result['score_range'], '5-9')
            self.assertFalse(result['auto_referral'])
    
    def test_gad7_purple_category(self):
        """Test GAD-7 Purple category (10-14)"""
        for score in [10, 11, 12, 13, 14]:
            result = map_gad7_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Purple')
            self.assertEqual(result['score_range'], '10-14')
            self.assertFalse(result['auto_referral'])
            self.assertTrue(result['auto_flag'])
    
    def test_gad7_red_category(self):
        """Test GAD-7 Red category (15-21) - Auto-referral"""
        for score in [15, 16, 18, 21]:
            result = map_gad7_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Red')
            self.assertEqual(result['score_range'], '15-21')
            self.assertTrue(result['auto_referral'])
            self.assertTrue(result['auto_flag'])
    
    def test_gad7_invalid_scores(self):
        """Test GAD-7 invalid scores"""
        for score in [-1, 22, 100, 'invalid']:
            result = map_gad7_to_risk_category(score)
            self.assertEqual(result['risk_category'], 'Invalid')


class TestChampionCodeGeneration(unittest.TestCase):
    """Test champion code generation"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        
    def test_champion_code_format(self):
        """Test that generated codes follow UMV-YYYY-NNNNNN format"""
        with self.app.app_context():
            code = generate_champion_code()
            
            # Check format: UMV-2026-000001
            parts = code.split('-')
            self.assertEqual(len(parts), 3)
            self.assertEqual(parts[0], 'UMV')
            self.assertEqual(len(parts[1]), 4)  # Year (4 digits)
            self.assertEqual(len(parts[2]), 6)  # Sequential (6 digits)
            self.assertTrue(parts[2].isdigit())
    
    def test_champion_code_uniqueness(self):
        """Test that codes are unique when champions are created"""
        with self.app.app_context():
            # Clear any existing test champions
            Champion.query.delete()
            db.session.commit()
            
            codes = []
            # Create 10 champions with generated codes
            for i in range(10):
                code = generate_champion_code()
                champion = Champion(
                    full_name=f'Test Champion {i}',
                    gender='Male',
                    date_of_birth=date(2000, 1, 1),
                    phone_number=f'25471234567{i}',
                    email=f'test{i}@example.com',
                    county_sub_county='Test County',
                    assigned_champion_code=code
                )
                db.session.add(champion)
                db.session.commit()
                codes.append(code)
            
            # All codes should be unique
            self.assertEqual(len(set(codes)), 10, "Generated codes are not unique")
            
            # Clean up
            Champion.query.delete()
            db.session.commit()


class TestUserRoles(unittest.TestCase):
    """Test user role validation"""
    
    def test_valid_roles(self):
        """Test that VALID_ROLES contains correct roles"""
        self.assertIn('Admin', User.VALID_ROLES)
        self.assertIn('Supervisor', User.VALID_ROLES)
        self.assertIn('Prevention Advocate', User.VALID_ROLES)
        self.assertNotIn('Champion', User.VALID_ROLES)
    
    def test_role_normalization(self):
        """Test role normalization"""
        with app.app_context():
            user = User(username='test', password_hash='test')
            
            # Test Prevention Advocate normalization
            user.set_role('prevention advocate')
            self.assertEqual(user.role, 'Prevention Advocate')
            
            # Test legacy Champion mapping
            user.set_role('Champion')
            self.assertEqual(user.role, 'Prevention Advocate')
    
    def test_invalid_role_rejection(self):
        """Test that invalid roles are rejected"""
        with app.app_context():
            user = User(username='test', password_hash='test')
            
            with self.assertRaises(ValueError):
                user.set_role('InvalidRole')


class TestPrivacyCompliance(unittest.TestCase):
    """Test privacy compliance in database schema"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
    
    def test_assessment_has_no_champion_id(self):
        """Verify MentalHealthAssessment does not have champion_id FK"""
        with self.app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = inspector.get_columns('mental_health_assessments')
            column_names = [col['name'] for col in columns]
            
            self.assertNotIn('champion_id', column_names, 
                           "PRIVACY VIOLATION: champion_id found in assessments table")
    
    def test_assessment_has_no_raw_scores(self):
        """Verify MentalHealthAssessment does not store raw scores"""
        with self.app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = inspector.get_columns('mental_health_assessments')
            column_names = [col['name'] for col in columns]
            
            self.assertNotIn('total_score', column_names,
                           "PRIVACY VIOLATION: total_score found in assessments table")
            self.assertNotIn('item_scores', column_names,
                           "PRIVACY VIOLATION: item_scores found in assessments table")
    
    def test_assessment_has_privacy_columns(self):
        """Verify MentalHealthAssessment has privacy-first columns"""
        with self.app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = inspector.get_columns('mental_health_assessments')
            column_names = [col['name'] for col in columns]
            
            self.assertIn('champion_code', column_names,
                         "MISSING: champion_code column")
            self.assertIn('risk_category', column_names,
                         "MISSING: risk_category column")
            self.assertIn('score_range', column_names,
                         "MISSING: score_range column")


def run_tests():
    """Run all tests and display results"""
    print("=" * 70)
    print("RUNNING UMV PRIVACY-FIRST IMPLEMENTATION TESTS")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestRiskCategoryMapping))
    suite.addTests(loader.loadTestsFromTestCase(TestChampionCodeGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestUserRoles))
    suite.addTests(loader.loadTestsFromTestCase(TestPrivacyCompliance))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED - System is privacy-compliant!")
    else:
        print("\n❌ SOME TESTS FAILED - Review output above")
    
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
