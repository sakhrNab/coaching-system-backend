"""
Data Storage Hierarchy: Google Sheets → Database → Contact List
"""

import logging
import asyncio
from typing import List, Dict, Optional
from ..database import db
import os
import json

logger = logging.getLogger(__name__)

class DataStorageManager:
    """Manages data storage with fallback hierarchy"""
    
    def __init__(self):
        self.google_sheets_available = bool(os.getenv("GOOGLE_CLIENT_ID"))
        self.database_available = True  # Always available
        
    async def save_client_data(self, coach_id: str, clients: List[Dict]) -> Dict[str, str]:
        """Save client data with hierarchy: Sheets → DB → Contacts"""
        results = {
            "google_sheets": "not_attempted",
            "database": "not_attempted", 
            "contact_list": "not_attempted",
            "primary_storage": None
        }
        
        # Try Google Sheets first
        if self.google_sheets_available:
            try:
                sheet_result = await self._save_to_google_sheets(coach_id, clients)
                results["google_sheets"] = "success"
                results["primary_storage"] = "google_sheets"
                results["sheet_url"] = sheet_result.get("sheet_url")
                logger.info(f"Data saved to Google Sheets for coach {coach_id}")
            except Exception as e:
                logger.error(f"Google Sheets save failed: {e}")
                results["google_sheets"] = f"failed: {str(e)}"
        
        # Always save to database as backup
        try:
            await self._save_to_database(coach_id, clients)
            results["database"] = "success"
            if not results["primary_storage"]:
                results["primary_storage"] = "database"
            logger.info(f"Data saved to database for coach {coach_id}")
        except Exception as e:
            logger.error(f"Database save failed: {e}")
            results["database"] = f"failed: {str(e)}"
        
        # If both fail, save to contact list format
        if results["primary_storage"] is None:
            try:
                contact_result = await self._save_to_contact_list(coach_id, clients)
                results["contact_list"] = "success"
                results["primary_storage"] = "contact_list"
                results["contact_file"] = contact_result.get("file_path")
                logger.info(f"Data saved to contact list for coach {coach_id}")
            except Exception as e:
                logger.error(f"Contact list save failed: {e}")
                results["contact_list"] = f"failed: {str(e)}"
        
        return results
    
    async def _save_to_google_sheets(self, coach_id: str, clients: List[Dict]) -> Dict:
        """Save client data to Google Sheets"""
        from .google_sheets_service import GoogleSheetsService
        
        sheets_service = GoogleSheetsService()
        
        # Check if sheet exists for this coach
        async with db.pool.acquire() as conn:
            existing_sheet = await conn.fetchrow(
                "SELECT sheet_id, sheet_url FROM google_sheets_sync WHERE coach_id = $1 ORDER BY created_at DESC LIMIT 1",
                coach_id
            )
        
        if existing_sheet:
            # Update existing sheet
            sheet_id = existing_sheet['sheet_id']
            await sheets_service.update_sheet_data(sheet_id, clients)
            sheet_url = existing_sheet['sheet_url']
        else:
            # Create new sheet
            sheet_result = await sheets_service.create_client_sheet(coach_id, clients)
            sheet_id = sheet_result['sheet_id']
            sheet_url = sheet_result['sheet_url']
            
            # Save sheet info to database
            async with db.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO google_sheets_sync (coach_id, sheet_id, sheet_url, last_sync_at, sync_status)
                       VALUES ($1, $2, $3, NOW(), 'success')""",
                    coach_id, sheet_id, sheet_url
                )
        
        return {"sheet_id": sheet_id, "sheet_url": sheet_url}
    
    async def _save_to_database(self, coach_id: str, clients: List[Dict]) -> Dict:
        """Save client data to PostgreSQL database"""
        async with db.pool.acquire() as conn:
            saved_count = 0
            for client in clients:
                try:
                    # Insert or update client
                    await conn.execute(
                        """INSERT INTO clients (coach_id, name, phone_number, country, timezone) 
                           VALUES ($1, $2, $3, $4, $5)
                           ON CONFLICT (coach_id, phone_number) 
                           DO UPDATE SET name = EXCLUDED.name, country = EXCLUDED.country, timezone = EXCLUDED.timezone""",
                        coach_id, client.get('name'), client.get('phone_number'), 
                        client.get('country'), client.get('timezone')
                    )
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"Failed to save client {client.get('name')}: {e}")
        
        return {"saved_count": saved_count, "total_count": len(clients)}
    
    async def _save_to_contact_list(self, coach_id: str, clients: List[Dict]) -> Dict:
        """Save client data as contact list file (fallback)"""
        import os
        import json
        from datetime import datetime
        
        # Create contacts directory if not exists
        contacts_dir = "data/contacts"
        os.makedirs(contacts_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"coach_{coach_id}_contacts_{timestamp}.json"
        file_path = os.path.join(contacts_dir, filename)
        
        # Prepare contact data
        contact_data = {
            "coach_id": coach_id,
            "export_time": datetime.now().isoformat(),
            "total_clients": len(clients),
            "clients": clients
        }
        
        # Save to JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(contact_data, f, indent=2, ensure_ascii=False)
        
        # Also save reference in database if possible
        try:
            async with db.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO contact_exports (coach_id, file_path, client_count, exported_at)
                       VALUES ($1, $2, $3, NOW())""",
                    coach_id, file_path, len(clients)
                )
        except Exception as e:
            logger.warning(f"Could not log contact export to database: {e}")
        
        return {"file_path": file_path, "client_count": len(clients)}
    
    async def get_client_data(self, coach_id: str) -> Dict:
        """Retrieve client data from best available source"""
        # Try Google Sheets first
        if self.google_sheets_available:
            try:
                sheet_data = await self._get_from_google_sheets(coach_id)
                if sheet_data:
                    return {"source": "google_sheets", "data": sheet_data}
            except Exception as e:
                logger.warning(f"Could not retrieve from Google Sheets: {e}")
        
        # Fall back to database
        try:
            db_data = await self._get_from_database(coach_id)
            if db_data:
                return {"source": "database", "data": db_data}
        except Exception as e:
            logger.warning(f"Could not retrieve from database: {e}")
        
        # Last resort: contact files
        try:
            contact_data = await self._get_from_contact_files(coach_id)
            return {"source": "contact_files", "data": contact_data}
        except Exception as e:
            logger.error(f"Could not retrieve from any source: {e}")
            return {"source": "none", "data": []}
    
    async def _get_from_google_sheets(self, coach_id: str) -> List[Dict]:
        """Retrieve data from Google Sheets"""
        from .google_sheets_service import GoogleSheetsService
        
        sheets_service = GoogleSheetsService()
        
        async with db.pool.acquire() as conn:
            sheet_record = await conn.fetchrow(
                "SELECT sheet_id FROM google_sheets_sync WHERE coach_id = $1 ORDER BY created_at DESC LIMIT 1",
                coach_id
            )
        
        if not sheet_record:
            return []
        
        return await sheets_service.get_sheet_data(sheet_record['sheet_id'])
    
    async def _get_from_database(self, coach_id: str) -> List[Dict]:
        """Retrieve data from database"""
        async with db.pool.acquire() as conn:
            clients = await conn.fetch(
                "SELECT * FROM clients WHERE coach_id = $1 AND is_active = true ORDER BY name",
                coach_id
            )
        
        return [dict(client) for client in clients]
    
    async def _get_from_contact_files(self, coach_id: str) -> List[Dict]:
        """Retrieve data from contact files"""
        import glob
        import json
        
        contacts_dir = "data/contacts"
        pattern = f"{contacts_dir}/coach_{coach_id}_contacts_*.json"
        files = glob.glob(pattern)
        
        if not files:
            return []
        
        # Get most recent file
        latest_file = max(files, key=os.path.getctime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('clients', [])
    
    def get_storage_status(self) -> Dict:
        """Get status of all storage systems"""
        return {
            "google_sheets": {
                "available": self.google_sheets_available,
                "status": "configured" if self.google_sheets_available else "not_configured"
            },
            "database": {
                "available": self.database_available,
                "status": "operational"
            },
            "contact_files": {
                "available": True,
                "status": "always_available"
            }
        }

# Global instance
storage_manager = DataStorageManager()

