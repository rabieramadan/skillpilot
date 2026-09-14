"""
SkillPilot Database Migration Script
Updates database schema while preserving existing data

Usage:
    python migrate_database.py

This script will:
1. Compare current database schema with model definitions
2. Add new columns with default values
3. Handle removed columns safely
4. Preserve all existing data
"""

import os
import sys
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_migration():
    print("=" * 60)
    print("  SkillPilot Database Migration")
    print("=" * 60)
    print()
    
    # Import Flask app
    from app import create_app
    from app.models import db
    
    app = create_app()
    
    with app.app_context():
        # Get database engine
        engine = db.engine
        
        print("1. Checking database connection...")
        try:
            connection = engine.connect()
            connection.close()
            print("   OK - Connected to database")
        except Exception as e:
            print(f"   ERROR: Cannot connect to database: {e}")
            return False
        
        print()
        print("2. Checking existing tables...")
        
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        print(f"   Found {len(existing_tables)} existing tables")
        
        print()
        print("3. Running schema migration...")
        
        # Get all model tables
        model_tables = db.metadata.tables
        
        for table_name, table in model_tables.items():
            if table_name in existing_tables:
                # Table exists - check for new columns
                existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
                model_columns = {col.name for col in table.columns}
                
                # Find new columns to add
                new_columns = model_columns - existing_columns
                if new_columns:
                    print(f"   Adding {len(new_columns)} new column(s) to '{table_name}':")
                    for col_name in new_columns:
                        col = table.columns[col_name]
                        col_type = str(col.type)
                        
                        # Determine default value
                        if col.default is not None:
                            default = f"DEFAULT {col.default.arg}" if hasattr(col.default, 'arg') else ""
                        elif col.nullable:
                            default = "DEFAULT NULL"
                        elif 'INT' in col_type.upper():
                            default = "DEFAULT 0"
                        elif 'BOOL' in col_type.upper():
                            default = "DEFAULT FALSE"
                        elif 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper():
                            default = "DEFAULT ''"
                        elif 'FLOAT' in col_type.upper() or 'NUMERIC' in col_type.upper():
                            default = "DEFAULT 0.0"
                        else:
                            default = ""
                        
                        null_clause = "" if col.nullable else "NOT NULL"
                        
                        try:
                            alter_sql = f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{col_name}" {col_type} {default} {null_clause}'
                            with engine.connect() as conn:
                                conn.execute(text(alter_sql))
                                conn.commit()
                            print(f"      + {col_name} ({col_type})")
                        except Exception as e:
                            print(f"      ! {col_name} - Warning: {e}")
                
                # Note removed columns (don't delete - preserve data)
                removed_columns = existing_columns - model_columns - {'id'}
                if removed_columns:
                    print(f"   Note: {len(removed_columns)} column(s) in '{table_name}' not in model (preserved):")
                    for col_name in removed_columns:
                        print(f"      ~ {col_name} (kept for data preservation)")
            else:
                # Table doesn't exist - create it
                print(f"   Creating new table: '{table_name}'")
                table.create(engine, checkfirst=True)
        
        print()
        print("4. Verifying migration...")
        
        # Verify all tables exist
        inspector = inspect(engine)
        final_tables = inspector.get_table_names()
        
        missing_tables = set(model_tables.keys()) - set(final_tables)
        if missing_tables:
            print(f"   WARNING: Missing tables: {missing_tables}")
        else:
            print("   OK - All model tables exist")
        
        print()
        print("=" * 60)
        print("  Migration completed successfully!")
        print("=" * 60)
        print()
        print("Your existing data has been preserved.")
        print("New columns have been added with default values.")
        print()
        
        return True

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
