#!/usr/bin/env python3
"""
Database Migration Manager
Runs migrations only once, tracks completion in database
"""

import os
import sys
import asyncio
import asyncpg
import hashlib
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationManager:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME', 'coaching_system')
        }
    
    async def create_migration_table(self, conn):
        """Create migrations tracking table if it doesn't exist"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                checksum VARCHAR(64) NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Migration tracking table ready")
    
    def get_migration_checksum(self, filepath):
        """Get SHA256 checksum of migration file"""
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    async def is_migration_applied(self, conn, filename, checksum):
        """Check if migration was already applied"""
        result = await conn.fetchrow(
            "SELECT checksum FROM schema_migrations WHERE filename = $1",
            filename
        )
        if result:
            if result['checksum'] == checksum:
                logger.info(f"Migration {filename} already applied (checksum match)")
                return True
            else:
                logger.warning(f"Migration {filename} checksum mismatch - may need reapplication")
                return False
        return False
    
    async def apply_migration(self, conn, filepath):
        """Apply a single migration file"""
        filename = os.path.basename(filepath)
        checksum = self.get_migration_checksum(filepath)
        
        if await self.is_migration_applied(conn, filename, checksum):
            return True
        
        logger.info(f"Applying migration: {filename}")
        
        try:
            # Read and execute migration
            with open(filepath, 'r') as f:
                migration_sql = f.read()
            
            await conn.execute(migration_sql)
            
            # Record migration as applied
            await conn.execute("""
                INSERT INTO schema_migrations (filename, checksum) 
                VALUES ($1, $2) 
                ON CONFLICT (filename) 
                DO UPDATE SET checksum = $2, applied_at = CURRENT_TIMESTAMP
            """, filename, checksum)
            
            logger.info(f"Migration {filename} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration {filename}: {e}")
            return False
    
    async def run_migrations(self):
        """Run all pending migrations"""
        try:
            # Connect to database
            conn = await asyncpg.connect(**self.db_config)
            
            # Create migration tracking table
            await self.create_migration_table(conn)
            
            # Get migration files in order
            migration_files = []
            
            # Add init.sql (base schema)
            init_sql = Path("database/init.sql")
            if init_sql.exists():
                migration_files.append(init_sql)
            
            # Add production fix migration
            prod_migration = Path("database/migration_fix_production.sql")
            if prod_migration.exists():
                migration_files.append(prod_migration)
            
            # Apply migrations in order
            all_success = True
            for migration_file in migration_files:
                success = await self.apply_migration(conn, migration_file)
                if not success:
                    all_success = False
                    break
            
            await conn.close()
            
            if all_success:
                logger.info("All migrations completed successfully")
                return True
            else:
                logger.error("Some migrations failed")
                return False
                
        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            return False

async def main():
    """Main migration runner"""
    manager = MigrationManager()
    
    # Wait for database to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            conn = await asyncpg.connect(**manager.db_config)
            await conn.execute("SELECT 1")
            await conn.close()
            logger.info("Database connection successful")
            break
        except Exception as e:
            if i == max_retries - 1:
                logger.error(f"Database not ready after {max_retries} attempts: {e}")
                sys.exit(1)
            logger.info(f"Waiting for database... (attempt {i+1}/{max_retries})")
            await asyncio.sleep(2)
    
    # Run migrations
    success = await manager.run_migrations()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
