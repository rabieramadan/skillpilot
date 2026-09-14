#!/usr/bin/env python3
"""
Seed Users Script for SkillPilot
Run this in PyCharm to create initial user accounts on your server.

Usage: python run_seed_users.py
"""

import os
import sys

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import hashlib
from app import create_app
from app.models import db, User

def hash_password(password):
    """Hash password using SHA-256 (same as auth.py)"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, role, full_name, email=None):
    """Create a user if they don't exist."""
    existing = User.query.filter_by(username=username).first()
    if existing:
        # Update password hash to correct format
        existing.password_hash = hash_password(password)
        db.session.commit()
        print(f"  User '{username}' already exists - updated password")
        return existing
    
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
        email=email or f"{username}@futurecoverage.ai"
    )
    db.session.add(user)
    db.session.commit()
    # Don't echo passwords; they're stored hashed in the DB and the
    # operator already knows them from the seed config.
    print(f"  Created {role}: {username} (password hidden)")
    return user

def main():
    print("=" * 60)
    print("SkillPilot User Seed Script")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        print("\n1. Creating Superadmin account...")
        create_user(
            username="admin",
            password="admin123",
            role="superadmin",
            full_name="System Administrator",
            email="admin@futurecoverage.ai"
        )
        
        print("\n2. Creating Demo Teachers...")
        create_user(
            username="demoteacher1",
            password="demo123",
            role="instructor",
            full_name="Demo Teacher One"
        )
        create_user(
            username="demoteacher2",
            password="demo123",
            role="instructor",
            full_name="Demo Teacher Two"
        )
        
        print("\n3. Creating Demo Students...")
        for i in range(1, 6):
            create_user(
                username=f"demostudent{i}",
                password="demo123",
                role="student",
                full_name=f"Demo Student {i}"
            )
        
        print("\n" + "=" * 60)
        print("ACCOUNTS CREATED SUCCESSFULLY!")
        print("=" * 60)
        print("\nLogin Credentials:")
        print("-" * 40)
        print("Superadmin:  admin / admin123")
        print("Teachers:    demoteacher1 / demo123")
        print("             demoteacher2 / demo123")
        print("Students:    demostudent1-5 / demo123")
        print("-" * 40)
        print("\nIMPORTANT: Change the admin password after first login!")
        print("=" * 60)

if __name__ == "__main__":
    main()
