#!/usr/bin/env python3
"""
Consolidate all institutions into a single UNIZWA institution.
Migrates all users, courses, enrollments, and related data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, Institution, User, Course, CourseInstructor, CourseWeek, WeekMaterial
from app.models import Enrollment, Exam, ExamQuestion, ExamResult, Survey, SurveyQuestion, SurveyResponse
from datetime import datetime
import hashlib
import uuid

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_uuid():
    return str(uuid.uuid4())

def consolidate_to_unizwa():
    """Consolidate all institutions into UNIZWA"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("CONSOLIDATING ALL INSTITUTIONS INTO UNIZWA")
        print("=" * 60)
        
        # Step 1: Create or get UNIZWA institution
        unizwa = Institution.query.filter_by(slug='unizwa').first()
        
        if not unizwa:
            print("\n📦 Creating UNIZWA institution...")
            unizwa = Institution(
                id=generate_uuid(),
                name='UNIZWA',
                slug='unizwa',
                admin_email='admin@unizwa.edu.om',
                country='Oman',
                billing_status='active',
                subscription_plan='enterprise',
                max_users=1000,
                max_courses=100,
                is_active=True
            )
            db.session.add(unizwa)
            db.session.flush()
            print(f"  ✓ Created UNIZWA with ID: {unizwa.id}")
        else:
            print(f"\n✓ UNIZWA already exists with ID: {unizwa.id}")
        
        # Step 2: Get all other institutions
        other_institutions = Institution.query.filter(Institution.slug != 'unizwa').all()
        print(f"\n📋 Found {len(other_institutions)} other institutions to migrate")
        
        migrated_users = 0
        migrated_courses = 0
        migrated_enrollments = 0
        
        for old_inst in other_institutions:
            print(f"\n🔄 Migrating from: {old_inst.name} ({old_inst.id})")
            
            # Migrate users
            users = User.query.filter_by(institution_id=old_inst.id).all()
            for user in users:
                # Check if username already exists in UNIZWA
                existing = User.query.filter_by(
                    username=user.username,
                    institution_id=unizwa.id
                ).first()
                
                if not existing:
                    user.institution_id = unizwa.id
                    migrated_users += 1
                else:
                    print(f"    ⚠ Skipping duplicate user: {user.username}")
            
            print(f"    ✓ Migrated {len(users)} users")
            
            # Migrate courses
            courses = Course.query.filter_by(institution_id=old_inst.id).all()
            for course in courses:
                course.institution_id = unizwa.id
                migrated_courses += 1
            
            print(f"    ✓ Migrated {len(courses)} courses")
            
            # Deactivate old institution
            old_inst.is_active = False
            print(f"    ✓ Deactivated {old_inst.name}")
        
        # Step 3: Create UNIZWA admin if not exists
        admin_username = 'unizwa_admin'
        existing_admin = User.query.filter_by(
            username=admin_username,
            institution_id=unizwa.id
        ).first()
        
        if not existing_admin:
            print("\n👤 Creating UNIZWA admin user...")
            admin_user = User(
                id=generate_uuid(),
                institution_id=unizwa.id,
                username=admin_username,
                email='admin@unizwa.edu.om',
                password_hash=hash_password('admin123'),
                full_name='UNIZWA Administrator',
                role='institution_admin',
                is_active=True
            )
            db.session.add(admin_user)
            print(f"  ✓ Created admin: {admin_username} / admin123")
        
        # Step 4: Create demo teacher and students for UNIZWA
        demo_teacher = User.query.filter_by(
            username='demoteacher1',
            institution_id=unizwa.id
        ).first()
        
        if not demo_teacher:
            print("\n👨‍🏫 Creating demo teacher...")
            demo_teacher = User(
                id=generate_uuid(),
                institution_id=unizwa.id,
                username='demoteacher1',
                email='teacher@unizwa.edu.om',
                password_hash=hash_password('demo123'),
                full_name='Dr. Demo Teacher',
                role='instructor',
                is_active=True
            )
            db.session.add(demo_teacher)
            print(f"  ✓ Created teacher: demoteacher1 / demo123")
        
        demo_student = User.query.filter_by(
            username='demostudent1',
            institution_id=unizwa.id
        ).first()
        
        if not demo_student:
            print("\n🎓 Creating demo student...")
            demo_student = User(
                id=generate_uuid(),
                institution_id=unizwa.id,
                username='demostudent1',
                email='student@unizwa.edu.om',
                password_hash=hash_password('demo123'),
                full_name='Demo Student',
                role='student',
                is_active=True
            )
            db.session.add(demo_student)
            print(f"  ✓ Created student: demostudent1 / demo123")
        
        # Commit all changes
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("CONSOLIDATION COMPLETE!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"  • UNIZWA Institution ID: {unizwa.id}")
        print(f"  • Users migrated: {migrated_users}")
        print(f"  • Courses migrated: {migrated_courses}")
        print(f"  • Old institutions deactivated: {len(other_institutions)}")
        
        # Count final stats
        total_users = User.query.filter_by(institution_id=unizwa.id).count()
        total_courses = Course.query.filter_by(institution_id=unizwa.id).count()
        
        print(f"\n📈 UNIZWA Statistics:")
        print(f"  • Total Users: {total_users}")
        print(f"  • Total Courses: {total_courses}")
        
        print("\n🔐 Login Credentials:")
        print("  • Institution Admin: unizwa_admin / admin123")
        print("  • Demo Teacher: demoteacher1 / demo123")
        print("  • Demo Student: demostudent1 / demo123")
        print("  • Super Admin: Go to /admin-login, password: admin123")

if __name__ == '__main__':
    consolidate_to_unizwa()
