"""
SkillPilot Database Migration
Run directly from PyCharm: Right-click > Run 'run_migration'

This script updates the database schema while preserving existing data:
- Adds new columns with default values
- Creates new tables if needed
- Preserves removed columns (no data loss)
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def run_migration():
    print("=" * 60)
    print("  SkillPilot Database Migration")
    print("=" * 60)
    print()
    
    from app import create_app
    from app.models import db
    
    app = create_app()
    
    with app.app_context():
        engine = db.engine
        
        # Step 1: Check connection
        print("1. Checking database connection...")
        try:
            with engine.connect() as conn:
                conn.execute(db.text("SELECT 1"))
            print("   Connected successfully")
        except Exception as e:
            print(f"   ERROR: {e}")
            return False
        
        # Step 2: Check existing tables
        print()
        print("2. Analyzing existing schema...")
        
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        model_tables = db.metadata.tables
        
        print(f"   Database tables: {len(existing_tables)}")
        print(f"   Model tables: {len(model_tables)}")
        
        # Step 3: Migrate each table
        print()
        print("3. Applying schema changes...")
        
        changes_made = 0
        
        for table_name, table in model_tables.items():
            if table_name in existing_tables:
                # Check for column differences
                existing_cols = {c['name'] for c in inspector.get_columns(table_name)}
                model_cols = {c.name for c in table.columns}
                
                new_cols = model_cols - existing_cols
                for col_name in new_cols:
                    col = table.columns[col_name]
                    col_type = str(col.type)
                    
                    # Build ALTER statement
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    default = ""
                    
                    if col.default is not None and hasattr(col.default, 'arg'):
                        default = f"DEFAULT {repr(col.default.arg)}"
                    elif col.nullable:
                        default = "DEFAULT NULL"
                    elif 'INT' in col_type.upper():
                        default = "DEFAULT 0"
                    elif 'BOOL' in col_type.upper():
                        default = "DEFAULT false"
                    elif 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper():
                        default = "DEFAULT ''"
                    else:
                        default = ""
                    
                    sql = f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{col_name}" {col_type} {default}'
                    
                    try:
                        with engine.connect() as conn:
                            conn.execute(text(sql))
                            conn.commit()
                        print(f"   + Added: {table_name}.{col_name} ({col_type})")
                        changes_made += 1
                    except Exception as e:
                        print(f"   ! Warning: {table_name}.{col_name} - {e}")
            else:
                # Create new table
                print(f"   + Creating table: {table_name}")
                table.create(engine, checkfirst=True)
                changes_made += 1
        
        # Step 4: Summary
        print()
        print("=" * 60)
        if changes_made > 0:
            print(f"  Migration complete! {changes_made} change(s) applied.")
        else:
            print("  Database is already up to date!")
        print("  All existing data has been preserved.")
        print("=" * 60)
        
        return True


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
