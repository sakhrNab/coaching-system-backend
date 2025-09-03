import asyncio
import aiosqlite

async def check_database():
    """Check SQLite database structure"""
    try:
        async with aiosqlite.connect("coaching_system.db") as db:
            print("🔍 Checking database structure...\n")
            
            # Check if tables exist
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = await cursor.fetchall()
            print("📋 Tables:")
            for table in tables:
                print(f"  - {table[0]}")
            
            # Check coaches table structure
            print("\n👨‍💼 Coaches table structure:")
            cursor = await db.execute("PRAGMA table_info(coaches)")
            columns = await cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Check categories
            print("\n📂 Categories in database:")
            cursor = await db.execute("SELECT id, name, is_predefined FROM categories LIMIT 10")
            categories = await cursor.fetchall()
            for cat in categories:
                print(f"  - {cat[1]} (ID: {cat[0]}, Predefined: {cat[2]})")
                
            # Check clients table
            print("\n👥 Clients table structure:")
            cursor = await db.execute("PRAGMA table_info(clients)")
            columns = await cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
                
            # Check if any clients exist
            cursor = await db.execute("SELECT COUNT(*) FROM clients")
            count = await cursor.fetchone()
            print(f"\n📊 Total clients: {count[0]}")
            
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    asyncio.run(check_database())
