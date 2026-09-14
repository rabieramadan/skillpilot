"""
Database Migration: Convert SkillPilot to Skillgap
From multi-tenant to single-institution architecture

This script:
1. Creates the site_settings table
2. Migrates branding data from institutions table (if exists)
3. Removes institution_id columns from all tables
4. Drops institutions and institution_portal_settings tables
5. Updates user roles to new naming convention

Run with: python -m migrations.convert_to_skillgap
"""

import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_connection():
    """Get database connection from environment"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    from sqlalchemy import create_engine
    return create_engine(database_url)


def run_migration():
    """Run the database migration"""
    engine = get_db_connection()

    print("=" * 60)
    print("Skillgap Database Migration")
    print("Converting from multi-tenant to single-institution")
    print("=" * 60)
    print()

    with engine.connect() as conn:
        from sqlalchemy import text

        # Step 1: Create site_settings table if not exists
        print("[1/6] Creating site_settings table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS site_settings (
                id INTEGER PRIMARY KEY DEFAULT 1,
                site_name VARCHAR(100) DEFAULT 'Skillgap',
                site_name_ar VARCHAR(100) DEFAULT 'سكيلجاب',
                logo_url VARCHAR(500),
                logo_url_2 VARCHAR(500),
                favicon_url VARCHAR(500),
                primary_color VARCHAR(7) DEFAULT '#1B5E20',
                secondary_color VARCHAR(7) DEFAULT '#2E7D32',
                hero_title VARCHAR(255) DEFAULT 'AI-Powered Training Platform',
                hero_title_ar VARCHAR(255),
                hero_subtitle TEXT,
                hero_subtitle_ar TEXT,
                hero_image_url VARCHAR(500),
                footer_text TEXT,
                contact_email VARCHAR(255),
                allow_student_registration BOOLEAN DEFAULT TRUE,
                allow_teacher_registration BOOLEAN DEFAULT TRUE,
                paypal_link VARCHAR(500),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        print("   Done.")

        # Step 2: Migrate branding data from institutions (if exists)
        print("[2/6] Checking for existing institution data to migrate...")
        try:
            result = conn.execute(text("SELECT * FROM institutions LIMIT 1"))
            row = result.fetchone()
            if row:
                print("   Found institution data, migrating to site_settings...")
                # Check if site_settings already has data
                settings_result = conn.execute(text("SELECT id FROM site_settings LIMIT 1"))
                if not settings_result.fetchone():
                    conn.execute(text("""
                        INSERT INTO site_settings (id, site_name, logo_url, logo_url_2,
                            primary_color, secondary_color, contact_email, paypal_link)
                        SELECT 1, name, logo_url, logo_url_2,
                            COALESCE(primary_color, '#1B5E20'),
                            COALESCE(secondary_color, '#2E7D32'),
                            contact_email, paypal_link
                        FROM institutions LIMIT 1
                    """))
                    conn.commit()
                    print("   Branding data migrated.")
                else:
                    print("   Site settings already exist, skipping migration.")
        except Exception as e:
            print(f"   No institutions table found or error: {e}")

        # Step 3: Remove institution_id from users table
        print("[3/6] Removing institution_id from users table...")
        try:
            conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS institution_id"))
            conn.commit()
            print("   Done.")
        except Exception as e:
            print(f"   Note: {e}")

        # Step 4: Remove institution_id from other tables
        print("[4/6] Removing institution_id from other tables...")
        tables_to_update = ['courses', 'surveys', 'prompt_categories', 'prompts', 'audit_log', 'registration_requests']
        for table in tables_to_update:
            try:
                conn.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS institution_id"))
                conn.commit()
                print(f"   Removed from {table}")
            except Exception as e:
                print(f"   Note for {table}: {e}")

        # Step 5: Drop institution tables
        print("[5/6] Dropping institution tables...")
        try:
            conn.execute(text("DROP TABLE IF EXISTS institution_portal_settings CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS invoices CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS institutions CASCADE"))
            conn.commit()
            print("   Done.")
        except Exception as e:
            print(f"   Note: {e}")

        # Step 6: Update user roles
        print("[6/6] Normalizing user roles...")
        try:
            # Update super_admin -> superadmin
            conn.execute(text("UPDATE users SET role = 'superadmin' WHERE role = 'super_admin'"))
            # Update institution_admin -> admin
            conn.execute(text("UPDATE users SET role = 'admin' WHERE role = 'institution_admin'"))
            # Update instructor -> teacher
            conn.execute(text("UPDATE users SET role = 'teacher' WHERE role = 'instructor'"))
            conn.commit()
            print("   Done.")
        except Exception as e:
            print(f"   Note: {e}")

        # Insert default site settings if not exists
        print("\n[Final] Ensuring default site settings exist...")
        try:
            result = conn.execute(text("SELECT id FROM site_settings LIMIT 1"))
            if not result.fetchone():
                conn.execute(text("""
                    INSERT INTO site_settings (id, site_name, site_name_ar, hero_title, hero_subtitle)
                    VALUES (1, 'Skillgap', 'سكيلجاب',
                            'AI-Powered Training Platform',
                            'Empower your learning journey with cutting-edge AI technology')
                """))
                conn.commit()
                print("   Default settings created.")
            else:
                print("   Settings already exist.")
        except Exception as e:
            print(f"   Note: {e}")

    print()
    print("=" * 60)
    print("Migration complete!")
    print()
    print("Next steps:")
    print("1. Restart your application")
    print("2. Log in as superadmin")
    print("3. Configure site settings at /admin -> Site Settings")
    print("=" * 60)


if __name__ == '__main__':
    # Confirm before running
    print("\nWARNING: This will modify your database!")
    print("Make sure you have a backup before proceeding.\n")

    response = input("Continue with migration? (yes/no): ")
    if response.lower() == 'yes':
        run_migration()
    else:
        print("Migration cancelled.")
