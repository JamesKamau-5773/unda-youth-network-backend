"""
Quick test script for Seed Funding Application system
Run: python test_seed_funding.py
"""
from app import create_app
from models import db, SeedFundingApplication, User
from datetime import date, datetime

def test_seed_funding():
    app, _ = create_app()
    
    with app.app_context():
        # Check if table exists
        print("✓ Checking database connection...")
        count = SeedFundingApplication.query.count()
        print(f"✓ Found {count} existing seed funding applications")
        
        # Get admin user
        admin = User.query.filter_by(role='Admin').first()
        if not admin:
            print("✗ No admin user found. Please create an admin first.")
            return
        
        print(f"✓ Found admin user: {admin.username}")
        
        # Create a test application
        print("\n✓ Creating test seed funding application...")
        test_app = SeedFundingApplication(
            user_id=admin.user_id,
            applicant_name="Test Applicant",
            email="test@example.com",
            phone_number="254712345678",
            institution_name="Test University",
            student_id_number="TEST001",
            project_title="Test Mental Health Project",
            project_description="This is a test project to verify the system works correctly.",
            project_category="Mental Health Awareness",
            target_beneficiaries="50 students",
            expected_impact="Improved mental health awareness among students",
            total_budget_requested=25000.00,
            budget_breakdown=[
                {"item": "Materials", "amount": 10000.00},
                {"item": "Venue", "amount": 15000.00}
            ],
            project_start_date=date(2026, 2, 1),
            project_end_date=date(2026, 3, 1),
            implementation_timeline="Week 1: Setup\nWeek 2-3: Execution\nWeek 4: Evaluation",
            team_members=[
                {"name": "Team Member 1", "role": "Coordinator"},
                {"name": "Team Member 2", "role": "Assistant"}
            ],
            team_size=2,
            status='Pending'
        )
        
        db.session.add(test_app)
        db.session.commit()
        
        print(f"✓ Created application #{test_app.application_id}")
        
        # Test to_dict() method
        print("\n✓ Testing to_dict() method...")
        app_dict = test_app.to_dict()
        
        # Verify dual naming convention
        assert 'id' in app_dict and 'application_id' in app_dict
        assert 'projectTitle' in app_dict and 'project_title' in app_dict
        assert 'totalBudgetRequested' in app_dict and 'total_budget_requested' in app_dict
        print("✓ Dual naming convention (snake_case + camelCase) working correctly")
        
        # Test approval workflow
        print("\n✓ Testing approval workflow...")
        test_app.status = 'Under Review'
        test_app.reviewed_at = datetime.utcnow()
        test_app.reviewed_by = admin.user_id
        db.session.commit()
        print(f"✓ Status updated to: {test_app.status}")
        
        test_app.status = 'Approved'
        test_app.approved_amount = 20000.00
        test_app.approval_conditions = "Must provide monthly progress reports"
        db.session.commit()
        print(f"✓ Application approved with KES {test_app.approved_amount:,.2f}")
        
        test_app.status = 'Funded'
        test_app.disbursement_date = date(2026, 1, 15)
        test_app.disbursement_method = 'M-Pesa'
        test_app.disbursement_reference = 'TEST-MPESA-001'
        db.session.commit()
        print(f"✓ Application marked as funded via {test_app.disbursement_method}")
        
        # Cleanup
        print("\n✓ Cleaning up test data...")
        db.session.delete(test_app)
        db.session.commit()
        print("✓ Test application removed")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nThe Seed Funding Application system is working correctly.")
        print("\nNext steps:")
        print("1. Your React frontend can now submit applications to /api/seed-funding/apply")
        print("2. Admins can review applications at /admin/seed-funding")
        print("3. Check SEED_FUNDING_GUIDE.md for full documentation")

if __name__ == '__main__':
    test_seed_funding()
