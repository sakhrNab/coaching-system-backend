"""
WhatsApp Template Management
Maps database message templates to WhatsApp Business API templates
"""

import os
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class WhatsAppTemplate:
    name: str
    content: str
    message_type: str
    template_id: str
    language_code: str = "en_US"  # Default language code

class WhatsAppTemplateManager:
    """Manages mapping between database messages and WhatsApp templates"""
    
    def __init__(self):
        # Database connection will be set when needed
        self.db_pool = None
        
        # Fallback mappings for when database is not available
        # These map database content to WhatsApp template names
        self.fallback_template_mapping = {
            # Celebration messages (mapped to correct WhatsApp template numbers)
            "🎉 What are we celebrating today?": "celebration_message_6",
            "✨ What are you grateful for?": "celebration_message_7", 
            "🌟 What victory are you proud of today?": "celebration_message_9",
            "🎊 What positive moment made your day?": "celebration_message_10",
            "💫 What breakthrough did you experience?": "celebration_message_8",
            
            # Accountability messages (mapped to correct WhatsApp template numbers)
            "🔥 What will you commit to tomorrow?": "accountability_message_1",
            "📝 How did you progress on your goals today?": "accountability_message_2",
            "🎯 What action did you take towards your target?": "accountability_message_3",
            "💪 What challenge did you overcome today?": "accountability_message_4",
            "📈 How are you measuring your progress?": "accountability_message_5"
        }
        
        # Fallback language code mapping
        # All messages use 'en' language code
        self.fallback_language_mapping = {
            # Celebration messages
            "celebration_message_6": "en",
            "celebration_message_7": "en",
            "celebration_message_8": "en",
            "celebration_message_9": "en",
            "celebration_message_10": "en",
            # Accountability messages
            "accountability_message_1": "en",
            "accountability_message_2": "en",
            "accountability_message_3": "en",
            "accountability_message_4": "en",
            "accountability_message_5": "en",
            # System messages
            "hello_world": "en_US"
        }
        
        # Cache for database-loaded templates
        self.template_cache = {}
        self.cache_loaded = False
    
    def set_db_pool(self, db_pool):
        """Set the database connection pool"""
        self.db_pool = db_pool
    
    async def load_templates_from_db(self):
        """Load templates from database and cache them"""
        if not self.db_pool:
            logger.warning("No database pool available, using fallback mappings")
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                # Load all templates with their language codes and WhatsApp template names
                templates = await conn.fetch("""
                    SELECT content, whatsapp_template_name, language_code, message_type
                    FROM message_templates 
                    WHERE is_active = true 
                    AND whatsapp_template_name IS NOT NULL
                    ORDER BY is_default DESC, created_at ASC
                """)
                
                # Clear existing cache
                self.template_cache = {}
                
                for template in templates:
                    content = template['content']
                    whatsapp_name = template['whatsapp_template_name']
                    language_code = template['language_code'] or 'en_US'
                    message_type = template['message_type']
                    
                    # Store in cache
                    self.template_cache[content] = {
                        'whatsapp_template_name': whatsapp_name,
                        'language_code': language_code,
                        'message_type': message_type
                    }
                
                self.cache_loaded = True
                logger.info(f"Loaded {len(self.template_cache)} templates from database")
                
        except Exception as e:
            logger.error(f"Failed to load templates from database: {e}")
            self.cache_loaded = False
    
    def get_template_name(self, message_content: str) -> Optional[str]:
        """Get WhatsApp template name for a database message content"""
        # Try database cache first
        if self.cache_loaded and message_content in self.template_cache:
            return self.template_cache[message_content]['whatsapp_template_name']
        
        # Fallback to hardcoded mappings
        if message_content in self.fallback_template_mapping:
            return self.fallback_template_mapping[message_content]
        
        # Try partial match (for emoji encoding issues)
        for content, template_info in self.template_cache.items():
            if content in message_content:
                return template_info['whatsapp_template_name']
        
        # Fallback partial match
        for content, template_name in self.fallback_template_mapping.items():
            if content in message_content:
                return template_name
        
        return None
    
    def get_message_content(self, template_name: str) -> Optional[str]:
        """Get database message content for a WhatsApp template name"""
        # Try database cache first
        if self.cache_loaded:
            for content, template_info in self.template_cache.items():
                if template_info['whatsapp_template_name'] == template_name:
                    return content
        
        # Fallback to hardcoded mappings
        for content, name in self.fallback_template_mapping.items():
            if name == template_name:
                return content
        
        return None
    
    def get_template_language_code(self, template_name: str) -> str:
        """Get the language code for a specific template"""
        # Try database cache first
        if self.cache_loaded:
            for content, template_info in self.template_cache.items():
                if template_info['whatsapp_template_name'] == template_name:
                    return template_info['language_code']
        
        # Fallback to hardcoded mappings
        return self.fallback_language_mapping.get(template_name, "en_US")
    
    def get_template_info(self, message_content: str) -> Optional[Dict[str, str]]:
        """Get both template name and language code for a message content"""
        template_name = self.get_template_name(message_content)
        if template_name:
            return {
                "template_name": template_name,
                "language_code": self.get_template_language_code(template_name)
            }
        return None
    
    def is_template_message(self, message_content: str) -> bool:
        """Check if a message should be sent as a template"""
        # Check database cache first - EXACT match only
        if self.cache_loaded and message_content in self.template_cache:
            return True
        
        # Check fallback mappings - EXACT match only
        if message_content in self.fallback_template_mapping:
            return True
        
        # NO partial matching - only exact matches should be treated as templates
        # This prevents custom messages that contain template text from being sent as templates
        
        return False
    
    def get_all_templates(self) -> List[WhatsAppTemplate]:
        """Get all available templates"""
        templates = []
        
        # Use database cache if available
        if self.cache_loaded:
            for content, template_info in self.template_cache.items():
                templates.append(WhatsAppTemplate(
                    name=template_info['whatsapp_template_name'],
                    content=content,
                    message_type=template_info['message_type'],
                    template_id=template_info['whatsapp_template_name'],
                    language_code=template_info['language_code']
                ))
        else:
            # Fallback to hardcoded mappings
            for content, template_name in self.fallback_template_mapping.items():
                # Determine message type based on content
                message_type = "celebration" if any(emoji in content for emoji in ["🎉", "✨", "🌟", "🎊", "💫"]) else "accountability"
                
                # Get the language code for this template
                language_code = self.get_template_language_code(template_name)
                
                templates.append(WhatsAppTemplate(
                    name=template_name,
                    content=content,
                    message_type=message_type,
                    template_id=template_name,
                    language_code=language_code
                ))
        
        return templates
    
    def validate_template_exists(self, template_name: str) -> bool:
        """Validate that a template exists in our mapping"""
        return template_name in self.reverse_mapping

# Global instance
template_manager = WhatsAppTemplateManager()
