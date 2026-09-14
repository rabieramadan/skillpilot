"""
SkillPilot Database Setup & Import Script
==========================================
"""

import os
import sys
import json
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_env():
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())
        print("✓ Loaded .env file")

def print_header(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def get_table_columns(db, text_func, table_name):
    try:
        result = db.session.execute(text_func(
            f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
        ))
        return [row[0] for row in result]
    except:
        return []

def setup_database(db, text_func):
    """Create tables and add ALL missing columns"""
    print_header("STEP 1: Database Schema Setup")
    
    db.create_all()
    print("✓ All tables created/verified")
    
    # ALL columns that might be missing
    migrations = [
        # Institution table columns
        ("institutions", "logo_url_2", "VARCHAR(500)"),
        ("institutions", "slogan", "TEXT"),
        ("institutions", "slogan_ar", "TEXT"),
        ("institutions", "hero_image_url", "VARCHAR(500)"),
        ("institutions", "hero_title", "VARCHAR(255)"),
        ("institutions", "hero_title_ar", "VARCHAR(255)"),
        ("institutions", "hero_subtitle", "TEXT"),
        ("institutions", "hero_subtitle_ar", "TEXT"),
        ("institutions", "billing_status", "VARCHAR(20) DEFAULT 'trial'"),
        ("institutions", "billing_waived", "BOOLEAN DEFAULT false"),
        ("institutions", "subscription_plan", "VARCHAR(50) DEFAULT 'basic'"),
        ("institutions", "monthly_rate", "FLOAT DEFAULT 0.0"),
        ("institutions", "max_users", "INTEGER DEFAULT 100"),
        ("institutions", "max_courses", "INTEGER DEFAULT 20"),
        ("institutions", "features_enabled", "JSON"),
        ("institutions", "admin_email", "VARCHAR(255)"),
        ("institutions", "phone", "VARCHAR(50)"),
        ("institutions", "address", "TEXT"),
        ("institutions", "country", "VARCHAR(100)"),
        ("institutions", "is_active", "BOOLEAN DEFAULT true"),
        
        # Course table columns
        ("courses", "title_ar", "VARCHAR(255)"),
        ("courses", "description_ar", "TEXT"),
        
        # Survey/Exam questions
        ("survey_questions", "question_text_ar", "TEXT"),
        ("survey_questions", "options_ar", "TEXT"),
        ("exam_questions", "question_text_ar", "TEXT"),
        ("exam_questions", "options_ar", "TEXT"),
    ]
    
    print("\nAdding missing columns...")
    for table, column, col_type in migrations:
        try:
            sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"
            db.session.execute(text_func(sql))
            db.session.commit()
            print(f"  ✓ {table}.{column}")
        except Exception as e:
            db.session.rollback()
            if "already exists" not in str(e).lower():
                print(f"  - {table}.{column}: {str(e)[:30]}")
    
    # Set default values for existing institutions
    try:
        db.session.execute(text_func(
            "UPDATE institutions SET billing_status = 'trial' WHERE billing_status IS NULL"
        ))
        db.session.execute(text_func(
            "UPDATE institutions SET is_active = true WHERE is_active IS NULL"
        ))
        # Set UNIZWA logos if not set
        db.session.execute(text_func(
            "UPDATE institutions SET logo_url = '/static/images/ac-logo.png' WHERE slug = 'unizwa' AND (logo_url IS NULL OR logo_url = '')"
        ))
        db.session.execute(text_func(
            "UPDATE institutions SET logo_url_2 = '/static/images/aiac-logo.png' WHERE slug = 'unizwa' AND (logo_url_2 IS NULL OR logo_url_2 = '')"
        ))
        db.session.commit()
        print("  ✓ Set default values and logos for UNIZWA")
    except Exception as e:
        db.session.rollback()

def parse_value(value):
    if value is None:
        return None
    if isinstance(value, dict) or isinstance(value, list):
        return json.dumps(value)
    if isinstance(value, str) and 'T' in value and len(value) > 18:
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except:
            pass
    return value

def import_data(db, text_func, export_dir):
    print_header("STEP 2: Data Import")
    
    if not os.path.exists(export_dir):
        print(f"⚠ No exports folder found")
        return
    
    tables = [
        "institutions",
        "users",
        "courses",
        "course_instructors",
        "course_weeks",
        "week_materials",
        "enrollments",
        "surveys",
        "survey_questions",
        "survey_responses",
        "exams",
        "exam_questions",
        "exam_results",
    ]
    
    total_imported = 0
    
    for table in tables:
        filepath = os.path.join(export_dir, f"{table}.json")
        if not os.path.exists(filepath):
            continue
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                continue
            
            db_columns = get_table_columns(db, text_func, table)
            if not db_columns:
                continue
            
            imported = 0
            for record in data:
                valid_columns = [c for c in record.keys() if c in db_columns]
                
                cols = ", ".join(valid_columns)
                placeholders = ", ".join([f":{col}" for col in valid_columns])
                sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                
                values = {}
                for col in valid_columns:
                    values[col] = parse_value(record.get(col))
                
                try:
                    db.session.execute(text_func(sql), values)
                    imported += 1
                except:
                    db.session.rollback()
                    continue
            
            db.session.commit()
            if imported > 0:
                print(f"  ✓ {table}: {imported} records")
                total_imported += imported
            
        except Exception as e:
            db.session.rollback()
            print(f"  ✗ {table}: {str(e)[:40]}")
    
    print(f"\n✓ Total imported: {total_imported} records")

def verify_data(db, text_func):
    print_header("STEP 3: Verification")
    
    checks = [
        ("institutions", "Institutions"),
        ("users", "Users"),
        ("courses", "Courses"),
        ("enrollments", "Enrollments"),
    ]
    
    for table, label in checks:
        try:
            result = db.session.execute(text_func(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  {label}: {count}")
        except:
            print(f"  {label}: Error")

def main():
    print_header("SkillPilot Database Setup & Import")
    
    load_env()
    
    if not os.environ.get('DATABASE_URL'):
        print("✗ ERROR: DATABASE_URL not found in .env")
        return
    
    try:
        from app import create_app
        from app.models import db
        from sqlalchemy import text as text_func
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return
    
    app = create_app()
    export_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
    
    with app.app_context():
        try:
            db.session.execute(text_func("SELECT 1"))
            print("✓ Database connection successful")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return
        
        setup_database(db, text_func)
        import_data(db, text_func, export_dir)
        verify_data(db, text_func)
        
        print_header("Setup Complete!")
        print("\nStart with: waitress-serve --port=5001 wsgi:app")

if __name__ == "__main__":
    main()
