"""
WhatsApp Template Management
Maps database message templates to WhatsApp Business API templates
"""

import os
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WhatsAppTemplate:
    name: str
    content: str
    message_type: str
    template_id: str

class WhatsAppTemplateManager:
    """Manages mapping between database messages and WhatsApp templates"""
    
    def __init__(self):
        # Template mapping: database content -> WhatsApp template name
        # Using partial matching to handle emoji encoding issues
        self.template_patterns = {
            # Celebration messages
            "What are we celebrating today?": "celebration_message_6",
            "What are you grateful for?": "celebration_message_7", 
            "What victory are you proud of today?": "celebration_message_9",
            "What positive moment made your day?": "celebration_message_1",
            "What breakthrough did you experience?": "celebration_message_8",
            
            # Accountability messages  
            "How did you progress on your goals today?": "celebration_message_2",
            "What action did you take towards your target?": "celebration_message_3",
            "What challenge did you overcome today?": "celebration_message_4",
            "How are you measuring your progress?": "celebration_message_5",
            "What will you commit to tomorrow?": "celebration_message_1"
        }
        
        # Keep original mapping for exact matches
        self.template_mapping = {
            # Celebration messages
            "🎉 What are we celebrating today?": "celebration_message_6",
            "✨ What are you grateful for?": "celebration_message_7", 
            "🌟 What victory are you proud of today?": "celebration_message_9",
            "🎊 What positive moment made your day?": "celebration_message_1",
            "💫 What breakthrough did you experience?": "celebration_message_8",
            
            # Accountability messages  
            "📝 How did you progress on your goals today?": "celebration_message_2",
            "🎯 What action did you take towards your target?": "celebration_message_3",
            "💪 What challenge did you overcome today?": "celebration_message_4",
            "📈 How are you measuring your progress?": "celebration_message_5",
            "🔥 What will you commit to tomorrow?": "celebration_message_1"
        }
        
        # Reverse mapping: template name -> database content
        self.reverse_mapping = {v: k for k, v in self.template_mapping.items()}
    
    def get_template_name(self, message_content: str) -> Optional[str]:
        """Get WhatsApp template name for a database message content"""
        # Try exact match first
        if message_content in self.template_mapping:
            return self.template_mapping[message_content]
        
        # Try partial match (for emoji encoding issues)
        for pattern, template_name in self.template_patterns.items():
            if pattern in message_content:
                return template_name
        
        return None
    
    def get_message_content(self, template_name: str) -> Optional[str]:
        """Get database message content for a WhatsApp template name"""
        return self.reverse_mapping.get(template_name)
    
    def is_template_message(self, message_content: str) -> bool:
        """Check if a message should be sent as a template"""
        # Check exact match
        if message_content in self.template_mapping:
            return True
        
        # Check partial match
        for pattern in self.template_patterns:
            if pattern in message_content:
                return True
        
        return False
    
    def get_all_templates(self) -> List[WhatsAppTemplate]:
        """Get all available templates"""
        templates = []
        for content, template_name in self.template_mapping.items():
            # Determine message type based on content
            message_type = "celebration" if any(emoji in content for emoji in ["🎉", "✨", "🌟", "🎊", "💫"]) else "accountability"
            
            templates.append(WhatsAppTemplate(
                name=template_name,
                content=content,
                message_type=message_type,
                template_id=template_name
            ))
        
        return templates
    
    def validate_template_exists(self, template_name: str) -> bool:
        """Validate that a template exists in our mapping"""
        return template_name in self.reverse_mapping

# Global instance
template_manager = WhatsAppTemplateManager()
