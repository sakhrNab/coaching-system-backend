"""
SQLite database implementation for local testing
"""

import aiosqlite
import os
import logging
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

class SQLiteDatabase:
    def __init__(self):
        self.db_path = "coaching_system.db"
        self.connection: Optional[aiosqlite.Connection] = None
        # Create a mock pool object for compatibility
        self.pool = self
    
    async def connect(self):
        """Create database connection"""
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            logger.info("SQLite database connection created successfully")
            await self.create_tables()
        except Exception as e:
            logger.error(f"Failed to create SQLite database connection: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            logger.info("SQLite database connection closed")
    
    async def create_tables(self):
        """Create basic tables for testing"""
        try:
            # Create coaches table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS coaches (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    whatsapp_token TEXT NOT NULL,
                    whatsapp_phone_number TEXT,
                    timezone TEXT DEFAULT 'EST',
                    registration_barcode TEXT UNIQUE NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            # Create clients table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    coach_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    country TEXT DEFAULT 'USA',
                    timezone TEXT DEFAULT 'EST',
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (coach_id) REFERENCES coaches (id)
                )
            """)
            
            # Create categories table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    is_predefined BOOLEAN DEFAULT false,
                    coach_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (coach_id) REFERENCES coaches (id)
                )
            """)
            
            # Insert predefined categories
            predefined_categories = [
                'Weight', 'Diet', 'Business', 'Finance', 'Relationship',
                'Health', 'Growth', 'Socialization', 'Communication',
                'Writing', 'Creativity', 'Career'
            ]
            
            for category in predefined_categories:
                await self.connection.execute(
                    "INSERT OR IGNORE INTO categories (id, name, is_predefined) VALUES (?, ?, ?)",
                    (f"cat_{category.lower()}", category, True)
                )
            
            await self.connection.commit()
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def _convert_query(self, query: str):
        """Convert PostgreSQL query to SQLite compatible query"""
        # Convert $1, $2, etc. to ?
        import re
        converted = re.sub(r'\$\d+', '?', query)
        
        # Convert common PostgreSQL syntax to SQLite
        converted = converted.replace('ON CONFLICT DO NOTHING', 'OR IGNORE')
        converted = converted.replace('true', '1')
        converted = converted.replace('false', '0')
        converted = converted.replace('boolean', 'BOOLEAN')
        
        # Remove RETURNING clauses for simple cases (we'll handle this separately)
        if 'RETURNING id' in converted and 'INSERT' in converted:
            converted = re.sub(r'\s+RETURNING\s+id\s*$', '', converted, flags=re.IGNORECASE)
            
        return converted

    async def execute(self, query: str, *args):
        """Execute a query without returning results"""
        converted_query = self._convert_query(query)
        cursor = await self.connection.execute(converted_query, args)
        await self.connection.commit()
        return cursor
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows"""
        converted_query = self._convert_query(query)
        cursor = await self.connection.execute(converted_query, args)
        return await cursor.fetchall()
    
    async def fetchrow(self, query: str, *args):
        """Fetch a single row"""
        converted_query = self._convert_query(query)
        cursor = await self.connection.execute(converted_query, args)
        return await cursor.fetchone()
    
    async def fetchval(self, query: str, *args):
        """Fetch a single value"""
        converted_query = self._convert_query(query)
        cursor = await self.connection.execute(converted_query, args)
        row = await cursor.fetchone()
        return row[0] if row else None
    
    def acquire(self):
        """Return a context manager that yields this database instance for compatibility"""
        return SQLiteConnectionContext(self)

class SQLiteConnectionContext:
    """Context manager to mimic asyncpg connection interface"""
    def __init__(self, db_instance):
        self.db = db_instance
        
    async def __aenter__(self):
        return self.db
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

# Global database instance for SQLite
db = SQLiteDatabase()
