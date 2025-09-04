-- Conversation tracking for WhatsApp 24-hour window management
-- This table tracks when users initiate conversations and when they expire

CREATE TABLE IF NOT EXISTS whatsapp_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wa_id VARCHAR(20) NOT NULL, -- WhatsApp ID (phone number without +)
    user_name VARCHAR(255),
    conversation_id VARCHAR(255), -- Meta's conversation ID
    origin_type VARCHAR(20) NOT NULL, -- 'user_initiated' or 'business_initiated'
    initiated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookups by WhatsApp ID
CREATE INDEX IF NOT EXISTS idx_whatsapp_conversations_wa_id ON whatsapp_conversations(wa_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_conversations_active ON whatsapp_conversations(is_active, expires_at);

-- Index for finding active conversations
CREATE INDEX IF NOT EXISTS idx_whatsapp_conversations_active_expires ON whatsapp_conversations(wa_id, is_active, expires_at);

-- Function to check if user can receive free messages
CREATE OR REPLACE FUNCTION can_send_free_message(wa_id_param VARCHAR(20))
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM whatsapp_conversations 
        WHERE wa_id = wa_id_param 
        AND is_active = true 
        AND expires_at > NOW()
        AND origin_type = 'user_initiated'
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get active conversation for a user
CREATE OR REPLACE FUNCTION get_active_conversation(wa_id_param VARCHAR(20))
RETURNS TABLE(
    conversation_id VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE,
    origin_type VARCHAR(20)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        wc.conversation_id,
        wc.expires_at,
        wc.origin_type
    FROM whatsapp_conversations wc
    WHERE wc.wa_id = wa_id_param 
    AND wc.is_active = true 
    AND wc.expires_at > NOW()
    ORDER BY wc.initiated_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

