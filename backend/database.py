"""
Database connection and management module
"""

import asyncpg
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create database connection pool"""
        try:
            db_password = os.getenv("DB_PASSWORD")
            if not db_password:
                logger.error("DB_PASSWORD environment variable is required")
                raise ValueError("DB_PASSWORD environment variable is required")
            
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = int(os.getenv("DB_PORT", 5432))
            db_user = os.getenv("DB_USER", "postgres")
            db_name = os.getenv("DB_NAME", "coaching_system")
            
            logger.info(f"Connecting to database: {db_user}@{db_host}:{db_port}/{db_name}")
            
            self.pool = await asyncpg.create_pool(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            # Test the connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            
            logger.info("Database connection pool created and tested successfully")
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute(self, query: str, *args):
        """Execute a query without returning results"""
        if not self.pool:
            raise Exception("Database not connected")
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows"""
        if not self.pool:
            raise Exception("Database not connected")
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Fetch a single row"""
        if not self.pool:
            raise Exception("Database not connected")
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch a single value"""
        if not self.pool:
            raise Exception("Database not connected")
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args)

# Global database instance
db = Database()
