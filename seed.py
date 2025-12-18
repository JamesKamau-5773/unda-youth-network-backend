"""
Seed script to populate the database with sample data for testing.
Run with: python seed.py
"""
from app import create_app
from models import db, User, Champion, YouthSupport, TrainingRecord, RefferalPathway, AccessAuditLog
from datetime import date, datetime, timedelta

def seed_data():
    app, _ = create_app()
    
    with app.app_context():
        print("Clearing existing data...")
        # Disable foreign key checks for PostgreSQL to handle circular dependencies
        db.session.execute(db.text('TRUNCATE users, champions, youth_supports, training_records, refferal_pathways, access_audit_logs RESTART IDENTITY CASCADE;'))
        db.session.commit()
        
        print("Creating users...")
        # Admin user
        admin = User(username='admin', role='Admin')
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Supervisor users
        sup1 = User(username='supervisor1', role='Supervisor')
        sup1.set_password('super123')
        db.session.add(sup1)
        
        sup2 = User(username='supervisor2', role='Supervisor')
        sup2.set_password('super123')
        db.session.add(sup2)
        
        db.session.commit()
        
        print("Creating champions...")
        # Champion 1 - supervised by supervisor1
        champ1 = Champion(
            full_name='Alice Wanjiru',
            gender='Female',
            date_of_birth=date(1998, 5, 15),
            phone_number='+254700123456',
            email='alice.wanjiru@example.com',
            county_sub_county='Nairobi/Westlands',
            assigned_champion_code='CH001',
            date_of_application=date(2024, 1, 10),
            recruitment_source='Community Health Worker',
            assigned_cohort='Cohort 2024-A',
            consent_obtained=True,
            consent_date=date(2024, 1, 15),
            consent_document_link='/documents/consent_ch001.pdf',
            institution_name='St. Mary\'s School',
            institution_consent_obtained=True,
            institution_consent_date=date(2024, 1, 20)
        )
        db.session.add(champ1)
        
        # Champion 2 - supervised by supervisor1
        champ2 = Champion(
            full_name='Brian Ochieng',
            gender='Male',
            date_of_birth=date(1999, 8, 22),
            phone_number='+254700234567',
            email='brian.ochieng@example.com',
            county_sub_county='Kisumu/Kisumu East',
            assigned_champion_code='CH002',
            date_of_application=date(2024, 2, 5),
            recruitment_source='Church Partnership',
            assigned_cohort='Cohort 2024-A',
            consent_obtained=True,
            consent_date=date(2024, 2, 10),
            consent_document_link='/documents/consent_ch002.pdf',
            institution_name='Grace Community Church',
            institution_consent_obtained=False  # Missing institutional consent
        )
        db.session.add(champ2)
        
        # Champion 3 - supervised by supervisor2
        champ3 = Champion(
            full_name='Catherine Muthoni',
            gender='Female',
            date_of_birth=date(1997, 11, 30),
            phone_number='+254700345678',
            email='catherine.muthoni@example.com',
            county_sub_county='Nakuru/Nakuru West',
            assigned_champion_code='CH003',
            date_of_application=date(2024, 1, 20),
            recruitment_source='NGO Referral',
            assigned_cohort='Cohort 2024-B',
            consent_obtained=False,  # Missing consent
            institution_name='Hope Secondary School',
            institution_consent_obtained=True,
            institution_consent_date=date(2024, 2, 1)
        )
        db.session.add(champ3)
        
        db.session.commit()
        
        print("Creating champion user accounts...")
        # Link champions to user accounts
        champ1_user = User(username='alice', role='Champion', champion_id=champ1.champion_id)
        champ1_user.set_password('alice123')
        db.session.add(champ1_user)
        
        champ2_user = User(username='brian', role='Champion', champion_id=champ2.champion_id)
        champ2_user.set_password('brian123')
        db.session.add(champ2_user)
        
        champ3_user = User(username='catherine', role='Champion', champion_id=champ3.champion_id)
        champ3_user.set_password('cath123')
        db.session.add(champ3_user)
        
        db.session.commit()
        
        # Assign champions to supervisors
        sup1.supervised_champion_ids = [champ1.champion_id, champ2.champion_id]
        sup2.supervised_champion_ids = [champ3.champion_id]
        db.session.commit()
        
        print("Creating training records...")
        # Training records for champion 1
        training1 = TrainingRecord(
            champion_id=champ1.champion_id,
            training_module='Safeguarding & Child Protection',
            training_date=date(2024, 1, 25),
            certification_status='Certified',
            next_refresher_due_date=date.today() + timedelta(days=15)  # Due soon
        )
        db.session.add(training1)
        
        training2 = TrainingRecord(
            champion_id=champ1.champion_id,
            training_module='Mental Health First Aid',
            training_date=date(2024, 2, 10),
            certification_status='Certified',
            next_refresher_due_date=date.today() + timedelta(days=90)
        )
        db.session.add(training2)
        
        # Training for champion 2
        training3 = TrainingRecord(
            champion_id=champ2.champion_id,
            training_module='Safeguarding & Child Protection',
            training_date=date(2024, 2, 15),
            certification_status='Certified',
            next_refresher_due_date=date.today() + timedelta(days=5)  # Urgent
        )
        db.session.add(training3)
        
        # Training for champion 3
        training4 = TrainingRecord(
            champion_id=champ3.champion_id,
            training_module='Safeguarding & Child Protection',
            training_date=date(2024, 1, 30),
            certification_status='Pending',
            next_refresher_due_date=date.today() + timedelta(days=120)
        )
        db.session.add(training4)
        
        db.session.commit()
        
        print("Creating youth support reports...")
        # Reports for champion 1 (with flag for referral tracking)
        report1 = YouthSupport(
            champion_id=champ1.champion_id,
            reporting_period=date(2024, 11, 1),
            weekly_check_in_completion_rate=92.5,
            monthly_mini_screenings_delivered=15,
            referrals_initiated=3,
            flag_timestamp=datetime(2024, 11, 12, 10, 30),
            documentation_quality_score='complete',
            self_reported_wellbeing_check=8,
            supervisor_notes='Excellent performance. Consistently meeting targets.'
        )
        db.session.add(report1)
        
        report2 = YouthSupport(
            champion_id=champ1.champion_id,
            reporting_period=date.today().replace(day=1),
            weekly_check_in_completion_rate=88.0,
            monthly_mini_screenings_delivered=12,
            referrals_initiated=2,
            flag_timestamp=datetime.utcnow(),
            documentation_quality_score='complete',
            self_reported_wellbeing_check=7
        )
        db.session.add(report2)
        
        # Reports for champion 2
        report3 = YouthSupport(
            champion_id=champ2.champion_id,
            reporting_period=date(2024, 11, 1),
            weekly_check_in_completion_rate=75.0,
            monthly_mini_screenings_delivered=8,
            referrals_initiated=1,
            flag_timestamp=datetime(2024, 11, 20, 14, 15),
            documentation_quality_score='partial',
            self_reported_wellbeing_check=5,
            supervisor_notes='Needs support with documentation. Follow-up scheduled.',
            safeguarding_notes='Champion reported feeling overwhelmed. Monitoring closely.'
        )
        db.session.add(report3)
        
        # Reports for champion 3
        report4 = YouthSupport(
            champion_id=champ3.champion_id,
            reporting_period=date(2024, 11, 1),
            weekly_check_in_completion_rate=95.0,
            monthly_mini_screenings_delivered=18,
            referrals_initiated=4,
            flag_timestamp=datetime(2024, 11, 8, 9, 0),
            documentation_quality_score='complete',
            self_reported_wellbeing_check=9
        )
        db.session.add(report4)
        
        db.session.commit()
        
        print("Creating referral pathways...")
        # Referrals from champion 1
        referral1 = RefferalPathway(
            champion_id=champ1.champion_id,
            date_initiated=date(2024, 11, 15),
            youth_referred_number=3,
            referral_reasons='Depression screening positive',
            referral_destinations='Nairobi Mental Health Clinic',
            referal_outcomes='Attended',
            flag_to_referral_days=3,
            feedback_from_service_provider='All three youth attended initial consultation.'
        )
        db.session.add(referral1)
        
        # Referrals from champion 2
        referral2 = RefferalPathway(
            champion_id=champ2.champion_id,
            date_initiated=date(2024, 11, 25),
            youth_referred_number=1,
            referral_reasons='Anxiety concerns',
            referral_destinations='Kisumu Counseling Center',
            referal_outcomes='Pending',
            flag_to_referral_days=5
        )
        db.session.add(referral2)
        
        # Referrals from champion 3
        referral3 = RefferalPathway(
            champion_id=champ3.champion_id,
            date_initiated=date(2024, 11, 10),
            youth_referred_number=4,
            referral_reasons='Multiple high-risk screenings',
            referral_destinations='Nakuru Youth Support Services',
            referal_outcomes='Attended',
            flag_to_referral_days=2,
            feedback_from_service_provider='Three attended, one declined.'
        )
        db.session.add(referral3)
        
        db.session.commit()
        
        print("Creating access audit logs...")
        # Sample audit entries
        audit1 = AccessAuditLog(
            user_id=sup1.user_id,
            champion_id=champ1.champion_id,
            action='viewed_champion_profile',
            timestamp=datetime(2024, 11, 28, 10, 15),
            ip_address='192.168.1.10',
            details='Supervisor reviewed monthly report'
        )
        db.session.add(audit1)
        
        audit2 = AccessAuditLog(
            user_id=sup1.user_id,
            champion_id=champ2.champion_id,
            action='viewed_champion_profile',
            timestamp=datetime(2024, 11, 29, 14, 30),
            ip_address='192.168.1.10',
            details='Supervisor reviewed wellbeing concerns'
        )
        db.session.add(audit2)
        
        audit3 = AccessAuditLog(
            user_id=admin.user_id,
            champion_id=champ1.champion_id,
            action='viewed_champion_profile',
            timestamp=datetime(2024, 12, 1, 9, 0),
            ip_address='192.168.1.5',
            details='Admin compliance audit'
        )
        db.session.add(audit3)
        
        db.session.commit()
        
        print("\n✅ Seed data created successfully!")
        print("\n📋 Sample credentials:")
        print("  Admin:       username='admin'        password='admin123'")
        print("  Supervisor1: username='supervisor1'  password='super123'")
        print("  Supervisor2: username='supervisor2'  password='super123'")
        print("  Champion1:   username='alice'        password='alice123'")
        print("  Champion2:   username='brian'        password='brian123'")
        print("  Champion3:   username='catherine'    password='cath123'")
        print("\n📊 Data summary:")
        print(f"  Users: {User.query.count()}")
        print(f"  Champions: {Champion.query.count()}")
        print(f"  Reports: {YouthSupport.query.count()}")
        print(f"  Training Records: {TrainingRecord.query.count()}")
        print(f"  Referrals: {RefferalPathway.query.count()}")
        print(f"  Audit Logs: {AccessAuditLog.query.count()}")
        print("\n🔔 Alerts:")
        print(f"  Champions missing consent: {Champion.query.filter_by(consent_obtained=False).count()}")
        print(f"  Training refreshers due soon: {len([t for t in TrainingRecord.query.all() if t.next_refresher_due_date and t.next_refresher_due_date <= date.today() + timedelta(days=30)])}")


if __name__ == '__main__':
    seed_data()
