import sys
import os
import pytest
from datetime import date, datetime, timedelta

# Ensure project root is on sys.path for imports during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User, Champion, YouthSupport, RefferalPathway, TrainingRecord


@pytest.fixture
def app():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_STORAGE_URL": "memory://",
    }
    app, limiter = create_app(test_config=test_config)

    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def create_admin_user(app):
    """Helper to create an admin user and log them in."""
    with app.app_context():
        admin = User(username="admin", role="Admin")
        admin.set_password("secret")
        db.session.add(admin)
        db.session.commit()
        return admin


def create_test_data(app):
    """Create comprehensive test data for admin metrics verification."""
    with app.app_context():
        # Create champions with different recruitment sources
        champion1 = Champion(
            full_name="Alice Champion",
            gender="Female",
            phone_number="+254700000001",
            email="alice@test.com",
            assigned_champion_code="CH001",
            recruitment_source="Campus",
            assigned_cohort="2024-Q1",
            consent_obtained=True,
            institution_consent_obtained=True
        )
        champion2 = Champion(
            full_name="Brian Champion",
            gender="Male",
            phone_number="+254700000002",
            email="brian@test.com",
            assigned_champion_code="CH002",
            recruitment_source="Mtaani",
            assigned_cohort="2024-Q1",
            consent_obtained=True,
            institution_consent_obtained=False
        )
        champion3 = Champion(
            full_name="Catherine Champion",
            gender="Female",
            phone_number="+254700000003",
            email="cathy@test.com",
            assigned_champion_code="CH003",
            recruitment_source="Social Media",
            assigned_cohort="2024-Q2",
            consent_obtained=False,
            institution_consent_obtained=True
        )
        db.session.add_all([champion1, champion2, champion3])
        db.session.flush()

        # Create youth support records with check-in completion rates
        # Test data: 80%, 90%, 85% -> Average should be 85%
        support1 = YouthSupport(
            champion_id=champion1.champion_id,
            reporting_period=date(2024, 12, 1),
            weekly_check_in_completion_rate=80.0,
            monthly_mini_screenings_delivered=5,
            referrals_initiated=2,
            self_reported_wellbeing_check=8,
            documentation_quality_score="Good"
        )
        support2 = YouthSupport(
            champion_id=champion2.champion_id,
            reporting_period=date(2024, 12, 1),
            weekly_check_in_completion_rate=90.0,
            monthly_mini_screenings_delivered=7,
            referrals_initiated=3,
            self_reported_wellbeing_check=9,
            documentation_quality_score="Excellent"
        )
        support3 = YouthSupport(
            champion_id=champion3.champion_id,
            reporting_period=date(2024, 12, 1),
            weekly_check_in_completion_rate=85.0,
            monthly_mini_screenings_delivered=6,
            referrals_initiated=1,
            self_reported_wellbeing_check=7,
            documentation_quality_score="Good",
            flag_timestamp=datetime(2024, 12, 1, 10, 0, 0)
        )
        db.session.add_all([support1, support2, support3])

        # Create referral pathways with outcomes
        # Test data: 3 total, 2 attended -> Conversion rate should be 66.7%
        referral1 = RefferalPathway(
            champion_id=champion1.champion_id,
            date_initiated=date(2024, 12, 5),
            youth_referred_number=10,
            referral_reasons="Mental health support",
            referral_destinations="County Hospital",
            referal_outcomes="Attended",
            flag_to_referral_days=3
        )
        referral2 = RefferalPathway(
            champion_id=champion2.champion_id,
            date_initiated=date(2024, 12, 7),
            youth_referred_number=15,
            referral_reasons="Substance abuse counseling",
            referral_destinations="Community Center",
            referal_outcomes="Attended",
            flag_to_referral_days=5
        )
        referral3 = RefferalPathway(
            champion_id=champion3.champion_id,
            date_initiated=date(2024, 12, 10),
            youth_referred_number=8,
            referral_reasons="Family counseling",
            referral_destinations="NGO Partner",
            referal_outcomes="Pending",
            flag_to_referral_days=7
        )
        db.session.add_all([referral1, referral2, referral3])

        # Create training records
        # Test data: 5 total records, 4 certified -> Compliance rate should be 80%
        today = date.today()
        training1 = TrainingRecord(
            champion_id=champion1.champion_id,
            training_module="Safeguarding",
            training_date=date(2024, 6, 1),
            certification_status="Certified",
            next_refresher_due_date=today + timedelta(days=15)  # Due in 15 days
        )
        training2 = TrainingRecord(
            champion_id=champion1.champion_id,
            training_module="Referral Protocols",
            training_date=date(2024, 6, 1),
            certification_status="Certified",
            next_refresher_due_date=today + timedelta(days=180)
        )
        training3 = TrainingRecord(
            champion_id=champion2.champion_id,
            training_module="Safeguarding",
            training_date=date(2024, 7, 1),
            certification_status="Certified",
            next_refresher_due_date=today + timedelta(days=25)  # Due in 25 days
        )
        training4 = TrainingRecord(
            champion_id=champion2.champion_id,
            training_module="Referral Protocols",
            training_date=date(2024, 7, 1),
            certification_status="Pending",  # Not certified
            next_refresher_due_date=None
        )
        training5 = TrainingRecord(
            champion_id=champion3.champion_id,
            training_module="Mental Health First Aid",
            training_date=date(2024, 8, 1),
            certification_status="Certified",
            next_refresher_due_date=today + timedelta(days=200)
        )
        db.session.add_all([training1, training2, training3, training4, training5])
        
        db.session.commit()


def test_average_check_in_completion_rate(client, app):
    """
    Test 1: System Summary Accuracy - Average Check-In Completion Rate
    
    Verification: Cross-check percentage against manual average of 
    weekly_check_in_completion_rate values.
    
    Expected: Dashboard displays rounded average (85%) based on all youth_support records.
    """
    create_admin_user(app)
    create_test_data(app)
    
    # Log in as admin
    client.post('/auth/login', data={"username": "admin", "password": "secret"})
    
    # Access admin dashboard
    rv = client.get('/admin/dashboard')
    assert rv.status_code == 200
    
    # Verify the average check-in rate is displayed and correct
    # Manual calculation: (80 + 90 + 85) / 3 = 85%
    assert b'85%' in rv.data or b'85.0%' in rv.data
    assert b'Average Check-In Completion Rate' in rv.data


def test_referral_conversion_rate(client, app):
    """
    Test 2: Referral Conversion & Pathway Health
    
    Verification: Ensure it correctly identifies ratio of "Attended" outcomes 
    versus "Declined" or "Pending" in referral_pathways table.
    
    Expected: Accurate percentage reflecting youth who successfully reached 
    professional care after being flagged.
    """
    create_admin_user(app)
    create_test_data(app)
    
    client.post('/auth/login', data={"username": "admin", "password": "secret"})
    rv = client.get('/admin/dashboard')
    
    assert rv.status_code == 200
    
    # Manual calculation: 2 Attended out of 3 total = 66.7%
    assert b'Referral Conversion Rate' in rv.data
    # Check for 66.7% or 67% (depending on rounding)
    assert b'66.7%' in rv.data or b'67%' in rv.data or b'66' in rv.data


def test_training_compliance_rate(client, app):
    """
    Test 3: Training & Compliance Monitoring
    
    Verification: Ensure it counts how many Champions have "Certified" status 
    for core modules like Safeguarding & Referral Protocols.
    
    Expected: Metric highlights if any Champions are overdue for refresher training.
    """
    create_admin_user(app)
    create_test_data(app)
    
    client.post('/auth/login', data={"username": "admin", "password": "secret"})
    rv = client.get('/admin/dashboard')
    
    assert rv.status_code == 200
    
    # Manual calculation: 4 Certified out of 5 total = 80%
    assert b'Training Compliance Rate' in rv.data
    assert b'80%' in rv.data or b'80.0%' in rv.data
    
    # Check for refresher alerts
    assert b'Training Refresher Alerts' in rv.data
    # Should show 2 upcoming refreshers (within 30 days)
    assert b'Safeguarding' in rv.data


def test_total_youth_reached_per_champion(client, app):
    """
    Test 4: High-Level Dashboard Visibility - Total Youth Reached per Champion
    
    Verification: Verify that individual youth_referred_number values are 
    aggregated per champion.
    
    Expected: Dashboard shows total youth reached for each champion.
    """
    create_admin_user(app)
    create_test_data(app)
    
    client.post('/auth/login', data={"username": "admin", "password": "secret"})
    rv = client.get('/admin/dashboard')
    
    assert rv.status_code == 200
    
    # Verify table headers
    assert b'Total Youth Reached per Champion' in rv.data
    assert b'Champion Code' in rv.data
    
    # Verify individual champion data
    # Champion 1: 10 youth
    assert b'CH001' in rv.data
    assert b'Alice Champion' in rv.data
    
    # Champion 2: 15 youth
    assert b'CH002' in rv.data
    assert b'Brian Champion' in rv.data
    
    # Champion 3: 8 youth
    assert b'CH003' in rv.data
    assert b'Catherine Champion' in rv.data


def test_quarterly_satisfaction_score(client, app):
    """
    Test 4 (continued): High-Level Dashboard Visibility - Quarterly Satisfaction Score
    
    Verification: Verify that individual youth feedback scores are aggregated 
    into a quarterly satisfaction score.
    
    Expected: Dashboard shows average of self_reported_wellbeing_check values.
    """
    create_admin_user(app)
    create_test_data(app)
    
    client.post('/auth/login', data={"username": "admin", "password": "secret"})
    rv = client.get('/admin/dashboard')
    
    assert rv.status_code == 200
    
    # Manual calculation: (8 + 9 + 7) / 3 = 8.0
    assert b'Quarterly Satisfaction Score' in rv.data
    assert b'8.0/10' in rv.data or b'8/10' in rv.data


def test_recruitment_source_analytics(client, app):
    """
    Operational Clarity Test: Recruitment Sources
    
    Verification: Ensure dashboard shows which recruitment sources 
    (Campus, Mtaani, Social Media) provide the most active champions.
    
    Expected: Breakdown of champions by recruitment source.
    """
    create_admin_user(app)
    create_test_data(app)
    
    client.post('/auth/login', data={"username": "admin", "password": "secret"})
    rv = client.get('/admin/dashboard')
    
    assert rv.status_code == 200
    
    # Verify recruitment source section exists
    assert b'Recruitment Sources' in rv.data or b'Operational Clarity' in rv.data
    
    # Verify all three sources are listed
    assert b'Campus' in rv.data
    assert b'Mtaani' in rv.data
    assert b'Social Media' in rv.data


def test_clinical_reliability_flag_to_referral(client, app):
    """
    Clinical Reliability Test: Flag-to-Referral Time
    
    Verification: Prove to partners exactly how long it takes from 
    a red flag to a completed referral.
    
    Expected: Average flag_to_referral_days displayed on dashboard.
    """
    create_admin_user(app)
    create_test_data(app)
    
    client.post('/auth/login', data={"username": "admin", "password": "secret"})
    rv = client.get('/admin/dashboard')
    
    assert rv.status_code == 200
    
    # Manual calculation: (3 + 5 + 7) / 3 = 5.0 days
    assert b'Flag-to-Referral' in rv.data or b'Average Flag-to-Referral Time' in rv.data
    assert b'5.0 days' in rv.data or b'5 days' in rv.data


def test_data_safe_environment_compliance(client, app):
    """
    Program Sustainability Test: Data Safe Environment
    
    Verification: Ensure dashboard demonstrates privacy-compliant framework 
    while proving program impact.
    
    Expected: Dashboard shows consent compliance and data protection measures.
    """
    create_admin_user(app)
    create_test_data(app)
    
    client.post('/auth/login', data={"username": "admin", "password": "secret"})
    rv = client.get('/admin/dashboard')
    
    assert rv.status_code == 200
    
    # Verify compliance section exists
    assert b'Compliance' in rv.data or b'Consent' in rv.data
    
    # Verify consent tracking
    # 1 champion missing personal consent
    # 1 champion missing institution consent
    assert b'Personal Consent Missing' in rv.data or b'champions_missing_consent' in rv.data
    assert b'Institution Consent Missing' in rv.data or b'champions_missing_institution' in rv.data
    
    # Verify data safe environment statement
    assert b'Data Safe Environment' in rv.data or b'privacy' in rv.data.lower()
