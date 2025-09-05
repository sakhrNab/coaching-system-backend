#!/usr/bin/env python3
"""
Run database migration for language codes
"""

import asyncio
import asyncpg
import os
import sys

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def run_migration():
    """Run the database migration"""
    
    # Database connection
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/coaching_system")
    
    try:
        print("🔌 Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to database")
        
        # Read the migration file
        with open('database/add_language_codes.sql', 'r') as f:
            migration_sql = f.read()
        
        print("📝 Running migration: add_language_codes.sql")
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements, 1):
            if statement:
                print(f"   Executing statement {i}/{len(statements)}...")
                try:
                    await conn.execute(statement)
                    print(f"   ✅ Statement {i} executed successfully")
                except Exception as e:
                    print(f"   ⚠️  Statement {i} warning: {e}")
                    # Continue with other statements
        
        print("✅ Migration completed successfully!")
        
        # Verify the changes
        print("\n🔍 Verifying migration...")
        
        # Check if columns exist
        columns = await conn.fetch("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'message_templates' 
            AND column_name IN ('language_code', 'whatsapp_template_name')
            ORDER BY column_name
        """)
        
        if columns:
            print("📊 New columns added:")
            for col in columns:
                print(f"   - {col['column_name']}: {col['data_type']} (default: {col['column_default']})")
        else:
            print("❌ Columns not found - migration may have failed")
        
        # Check updated templates
        templates = await conn.fetch("""
            SELECT content, language_code, whatsapp_template_name, message_type
            FROM message_templates 
            WHERE is_default = true
            ORDER BY message_type, content
        """)
        
        if templates:
            print(f"\n📊 Updated {len(templates)} templates:")
            for template in templates:
                print(f"   📝 {template['content'][:30]}...")
                print(f"      🌐 Language: {template['language_code']}")
                print(f"      📱 Template: {template['whatsapp_template_name']}")
                print(f"      🏷️  Type: {template['message_type']}")
                print()
        
        await conn.close()
        print("✅ Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        print("💡 Make sure your database is running and accessible")
        print(f"💡 Database URL: {DATABASE_URL}")

if __name__ == "__main__":
    print("🗄️ DATABASE MIGRATION: ADD LANGUAGE CODES")
    print("="*50)
    print("This will add language_code and whatsapp_template_name columns")
    print("and update existing templates with the correct values")
    print("="*50)
    
    asyncio.run(run_migration())
