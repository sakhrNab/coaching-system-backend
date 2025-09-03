import asyncpg
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='password123',
            database='coaching_system'
        )
        print('Connected successfully!')
        version = await conn.fetchval('SELECT version()')
        print(f'PostgreSQL version: {version}')
        await conn.close()
    except Exception as e:
        print(f'Connection failed: {e}')

if __name__ == "__main__":
    asyncio.run(test_connection())
