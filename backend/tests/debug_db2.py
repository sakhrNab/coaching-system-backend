import asyncio
import aiosqlite

async def test_client_add():
    """Test adding a client manually"""
    try:
        async with aiosqlite.connect("coaching_system.db") as db:
            
            # Check client_categories table structure
            print("🔗 Client_categories table structure:")
            cursor = await db.execute("PRAGMA table_info(client_categories)")
            columns = await cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Test category lookup
            print("\n🔍 Testing category lookup:")
            cursor = await db.execute(
                "SELECT id FROM categories WHERE name = ? AND (is_predefined = 1 OR coach_id = ?)",
                ("Health", "test-coach-id")
            )
            result = await cursor.fetchone()
            print(f"Health category lookup: {result}")
            
            cursor = await db.execute(
                "SELECT id FROM categories WHERE name = ? AND (is_predefined = 1 OR coach_id = ?)",
                ("Finance", "test-coach-id")
            )
            result = await cursor.fetchone()
            print(f"Finance category lookup: {result}")
            
            # Check existing clients
            print("\n👥 Existing clients:")
            cursor = await db.execute("SELECT id, name, coach_id FROM clients")
            clients = await cursor.fetchall()
            for client in clients:
                print(f"  - {client[1]} (ID: {client[0]}, Coach: {client[2]})")
                
            # Try manual insert
            print("\n🧪 Testing manual client insert:")
            import uuid
            client_id = str(uuid.uuid4())
            coach_id = "d8042594-9b1d-4d95-9c6b-97cb49e4b044"
            
            await db.execute(
                """INSERT INTO clients (id, coach_id, name, phone_number, country, timezone)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (client_id, coach_id, "Manual Test Client", "+9999999999", "US", "EST")
            )
            await db.commit()
            print(f"✅ Manual insert successful! Client ID: {client_id}")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_client_add())
