"""
Google Sheets Integration Service
Handles creating, updating, and managing Google Sheets for coaches
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .database import db

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.credentials = None
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Sheets API service"""
        try:
            # Check for service account credentials
            service_account_info = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            if service_account_info:
                # Parse JSON credentials
                credentials_dict = json.loads(service_account_info)
                self.credentials = Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                self.service = build('sheets', 'v4', credentials=self.credentials)
                logger.info("Google Sheets service initialized with service account")
            else:
                logger.warning("Google Sheets service account credentials not found")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")
            self.service = None
    
    async def create_or_update_sheet(self, coach_id: str, client_data: List[Dict[str, Any]]) -> Optional[str]:
        """Create a new Google Sheet or update existing one for a coach"""
        if not self.service:
            logger.error("Google Sheets service not initialized")
            return None
        
        try:
            # Check if coach already has a sheet
            existing_sheet = await self._get_existing_sheet(coach_id)
            
            if existing_sheet:
                # Update existing sheet
                sheet_id = existing_sheet['sheet_id']
                await self._update_sheet_data(sheet_id, client_data)
                logger.info(f"Updated existing sheet {sheet_id} for coach {coach_id}")
            else:
                # Create new sheet
                sheet_id = await self._create_new_sheet(coach_id, client_data)
                if sheet_id:
                    await self._save_sheet_info(coach_id, sheet_id)
                    logger.info(f"Created new sheet {sheet_id} for coach {coach_id}")
            
            return sheet_id
            
        except Exception as e:
            logger.error(f"Failed to create/update sheet for coach {coach_id}: {e}")
            return None
    
    async def _get_existing_sheet(self, coach_id: str) -> Optional[Dict[str, Any]]:
        """Get existing sheet info for a coach"""
        try:
            sheet_info = await db.fetchrow(
                "SELECT * FROM google_sheets_sync WHERE coach_id = $1 ORDER BY created_at DESC LIMIT 1",
                coach_id
            )
            return dict(sheet_info) if sheet_info else None
        except Exception as e:
            logger.error(f"Failed to get existing sheet for coach {coach_id}: {e}")
            return None
    
    async def _create_new_sheet(self, coach_id: str, client_data: List[Dict[str, Any]]) -> Optional[str]:
        """Create a new Google Sheet"""
        try:
            # Get coach info
            coach = await db.fetchrow("SELECT name FROM coaches WHERE id = $1", coach_id)
            coach_name = coach['name'] if coach else 'Coach'
            
            # Create spreadsheet
            spreadsheet_body = {
                'properties': {
                    'title': f'{coach_name} - Client Data ({datetime.now().strftime("%Y-%m-%d")})'
                },
                'sheets': [{
                    'properties': {
                        'title': 'Clients',
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 20
                        }
                    }
                }]
            }
            
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet_body).execute()
            sheet_id = spreadsheet.get('spreadsheetId')
            
            # Add data to the sheet
            await self._update_sheet_data(sheet_id, client_data)
            
            # Make the sheet publicly readable (optional)
            await self._make_sheet_readable(sheet_id)
            
            return sheet_id
            
        except Exception as e:
            logger.error(f"Failed to create new sheet: {e}")
            return None
    
    async def _update_sheet_data(self, sheet_id: str, client_data: List[Dict[str, Any]]):
        """Update sheet with client data"""
        try:
            # Prepare headers
            headers = [
                'Client Name', 'Phone Number', 'Country', 'Timezone', 'Categories',
                'Goals Count', 'Last Celebration Sent', 'Last Accountability Sent',
                'Status', 'Created Date', 'Updated Date'
            ]
            
            # Prepare data rows
            rows = [headers]
            for client in client_data:
                row = [
                    client.get('name', ''),
                    client.get('phone_number', ''),
                    client.get('country', ''),
                    client.get('timezone', ''),
                    ', '.join(client.get('categories', [])),
                    str(client.get('goals_count', 0)),
                    client.get('last_celebration_sent', ''),
                    client.get('last_accountability_sent', ''),
                    client.get('status', 'Active'),
                    client.get('created_at', ''),
                    client.get('updated_at', '')
                ]
                rows.append(row)
            
            # Clear existing data and update
            range_name = 'Clients!A1:Z1000'
            
            # Clear the sheet first
            self.service.spreadsheets().values().clear(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            # Update with new data
            body = {
                'values': rows
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            # Format the header row
            await self._format_header_row(sheet_id)
            
            logger.info(f"Updated sheet {sheet_id} with {len(client_data)} clients")
            
        except Exception as e:
            logger.error(f"Failed to update sheet data: {e}")
            raise
    
    async def _format_header_row(self, sheet_id: str):
        """Format the header row to make it bold and colored"""
        try:
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': 11
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {
                                'bold': True
                            },
                            'backgroundColor': {
                                'red': 0.2,
                                'green': 0.6,
                                'blue': 1.0
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                }
            }]
            
            body = {
                'requests': requests
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body=body
            ).execute()
            
        except Exception as e:
            logger.error(f"Failed to format header row: {e}")
    
    async def _make_sheet_readable(self, sheet_id: str):
        """Make the sheet readable by anyone with the link"""
        try:
            from googleapiclient.discovery import build
            
            drive_service = build('drive', 'v3', credentials=self.credentials)
            
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            drive_service.permissions().create(
                fileId=sheet_id,
                body=permission
            ).execute()
            
            logger.info(f"Made sheet {sheet_id} publicly readable")
            
        except Exception as e:
            logger.error(f"Failed to make sheet readable: {e}")
    
    async def _save_sheet_info(self, coach_id: str, sheet_id: str):
        """Save sheet information to database"""
        try:
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
            
            await db.execute(
                """INSERT INTO google_sheets_sync 
                   (coach_id, sheet_id, sheet_url, last_sync_at, sync_status, row_count)
                   VALUES ($1, $2, $3, $4, 'success', 0)""",
                coach_id, sheet_id, sheet_url, datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to save sheet info: {e}")
    
    async def get_sheet_url(self, coach_id: str) -> Optional[str]:
        """Get the sheet URL for a coach"""
        try:
            sheet_info = await db.fetchrow(
                "SELECT sheet_url FROM google_sheets_sync WHERE coach_id = $1 ORDER BY created_at DESC LIMIT 1",
                coach_id
            )
            return sheet_info['sheet_url'] if sheet_info else None
        except Exception as e:
            logger.error(f"Failed to get sheet URL for coach {coach_id}: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if Google Sheets service is available"""
        return self.service is not None

# Global instance
sheets_service = GoogleSheetsService()

