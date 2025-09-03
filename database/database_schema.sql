-- Coaching System Database Schema
-- Comprehensive PostgreSQL schema for the coaching platform

-- Enable UUID extension for unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Coaches table - stores coach registration and WhatsApp API info
CREATE TABLE coaches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    whatsapp_token TEXT NOT NULL,
    whatsapp_phone_number VARCHAR(20),
    timezone VARCHAR(10) DEFAULT 'EST',
    registration_barcode VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Categories table - predefined and custom categories
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    is_predefined BOOLEAN DEFAULT false,
    coach_id UUID REFERENCES coaches(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, coach_id) -- Prevent duplicate categories per coach
);

-- Insert predefined categories
INSERT INTO categories (name, is_predefined) VALUES 
    ('Weight', true),
    ('Diet', true),
    ('Business', true),
    ('Finance', true),
    ('Relationship', true),
    ('Health', true),
    ('Growth', true),
    ('Socialization', true),
    ('Communication', true),
    ('Writing', true),
    ('Creativity', true),
    ('Career', true);

-- Clients table - stores client information
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    country VARCHAR(100),
    timezone VARCHAR(10) DEFAULT 'EST',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(coach_id, phone_number) -- Prevent duplicate phone numbers per coach
);

-- Client categories junction table - many-to-many relationship
CREATE TABLE client_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_id, category_id)
);

-- Goals table - specific goals for clients
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category_id UUID REFERENCES categories(id),
    target_date DATE,
    is_achieved BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Message templates table - default and custom messages
CREATE TABLE message_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID REFERENCES coaches(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL, -- 'celebration', 'accountability'
    content TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default celebration messages
INSERT INTO message_templates (message_type, content, is_default) VALUES 
    ('celebration', '🎉 What are we celebrating today?', true),
    ('celebration', '✨ What are you grateful for?', true),
    ('celebration', '🌟 What victory are you proud of today?', true),
    ('celebration', '🎊 What positive moment made your day?', true),
    ('celebration', '💫 What breakthrough did you experience?', true);

-- Scheduled messages table - manages message timing and delivery
CREATE TABLE scheduled_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL, -- 'celebration', 'accountability'
    content TEXT NOT NULL,
    schedule_type VARCHAR(20) NOT NULL, -- 'now', 'specific', 'recurring'
    scheduled_time TIMESTAMP WITH TIME ZONE,
    recurring_pattern JSONB, -- Store recurring schedule details
    timezone VARCHAR(10),
    status VARCHAR(20) DEFAULT 'scheduled', -- 'scheduled', 'sent', 'failed', 'cancelled'
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Message history table - tracks all sent messages
CREATE TABLE message_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scheduled_message_id UUID REFERENCES scheduled_messages(id) ON DELETE SET NULL,
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    whatsapp_message_id VARCHAR(255), -- WhatsApp API message ID
    delivery_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'delivered', 'read', 'failed'
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- Voice message processing table - handles voice-to-text workflow
CREATE TABLE voice_message_processing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    whatsapp_message_id VARCHAR(255) NOT NULL,
    original_audio_url TEXT,
    transcribed_text TEXT,
    corrected_text TEXT,
    final_text TEXT,
    processing_status VARCHAR(20) DEFAULT 'received', -- 'received', 'transcribed', 'corrected', 'confirmed', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Google Sheets sync table - tracks sheet exports and updates
CREATE TABLE google_sheets_sync (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    sheet_id VARCHAR(255),
    sheet_url TEXT,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'success', 'failed'
    row_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- WhatsApp webhooks table - stores incoming webhook data
CREATE TABLE whatsapp_webhooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID REFERENCES coaches(id) ON DELETE CASCADE,
    webhook_data JSONB NOT NULL,
    message_type VARCHAR(50), -- 'text', 'voice', 'button_click'
    from_number VARCHAR(20),
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_coaches_barcode ON coaches(registration_barcode);
CREATE INDEX idx_coaches_whatsapp_token ON coaches(whatsapp_token);
CREATE INDEX idx_clients_coach_id ON clients(coach_id);
CREATE INDEX idx_clients_phone ON clients(phone_number);
CREATE INDEX idx_scheduled_messages_coach_client ON scheduled_messages(coach_id, client_id);
CREATE INDEX idx_scheduled_messages_time ON scheduled_messages(scheduled_time);
CREATE INDEX idx_scheduled_messages_status ON scheduled_messages(status);
CREATE INDEX idx_message_history_coach_client ON message_history(coach_id, client_id);
CREATE INDEX idx_message_history_sent_at ON message_history(sent_at);
CREATE INDEX idx_voice_processing_status ON voice_message_processing(processing_status);
CREATE INDEX idx_webhooks_processed ON whatsapp_webhooks(processed);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_coaches_updated_at BEFORE UPDATE ON coaches FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_goals_updated_at BEFORE UPDATE ON goals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_scheduled_messages_updated_at BEFORE UPDATE ON scheduled_messages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_voice_processing_updated_at BEFORE UPDATE ON voice_message_processing FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views for easier data access

-- Client summary view with categories and latest message info
CREATE VIEW client_summary AS
SELECT 
    c.id,
    c.coach_id,
    c.name,
    c.phone_number,
    c.country,
    c.timezone,
    ARRAY_AGG(DISTINCT cat.name) as categories,
    COUNT(DISTINCT g.id) as goals_count,
    MAX(mh.sent_at) as last_message_sent,
    MAX(CASE WHEN mh.message_type = 'celebration' THEN mh.sent_at END) as last_celebration_sent,
    MAX(CASE WHEN mh.message_type = 'accountability' THEN mh.sent_at END) as last_accountability_sent,
    CASE 
        WHEN EXISTS (SELECT 1 FROM scheduled_messages sm WHERE sm.client_id = c.id AND sm.status = 'scheduled') 
        THEN 'Scheduled' 
        WHEN EXISTS (SELECT 1 FROM message_history mh WHERE mh.client_id = c.id) 
        THEN 'Sent' 
        ELSE 'Not set up yet' 
    END as status
FROM clients c
LEFT JOIN client_categories cc ON c.id = cc.client_id
LEFT JOIN categories cat ON cc.category_id = cat.id
LEFT JOIN goals g ON c.id = g.client_id
LEFT JOIN message_history mh ON c.id = mh.client_id
WHERE c.is_active = true
GROUP BY c.id, c.coach_id, c.name, c.phone_number, c.country, c.timezone;

-- Message analytics view
CREATE VIEW message_analytics AS
SELECT 
    coach_id,
    message_type,
    DATE(sent_at) as sent_date,
    COUNT(*) as messages_sent,
    COUNT(CASE WHEN delivery_status = 'delivered' THEN 1 END) as delivered_count,
    COUNT(CASE WHEN delivery_status = 'read' THEN 1 END) as read_count,
    COUNT(CASE WHEN delivery_status = 'failed' THEN 1 END) as failed_count
FROM message_history
GROUP BY coach_id, message_type, DATE(sent_at);

-- Sample data for testing
-- (This would be populated through the application)

-- Example coach
INSERT INTO coaches (name, email, whatsapp_token, whatsapp_phone_number, timezone, registration_barcode) 
VALUES ('Coach Alex', 'alex@coaching.com', 'wa_token_demo_123', '+1234567890', 'EST', 'BARCODE_DEMO_123');

-- Example clients (using the coach ID from above)
WITH coach_data AS (
    SELECT id as coach_id FROM coaches WHERE email = 'alex@coaching.com'
)
INSERT INTO clients (coach_id, name, phone_number, country, timezone)
SELECT 
    coach_data.coach_id,
    unnest(ARRAY['Mike Johnson', 'Francis Williams', 'Bernard Smith', 'Sarah Davis', 'John Miller']),
    unnest(ARRAY['+1234567890', '+1234567891', '+1234567892', '+1234567893', '+1234567894']),
    'USA',
    unnest(ARRAY['EST', 'PST', 'CST', 'EST', 'PST'])
FROM coach_data;

-- Database maintenance functions
CREATE OR REPLACE FUNCTION cleanup_old_webhooks() 
RETURNS void AS $$
BEGIN
    -- Delete webhook data older than 30 days
    DELETE FROM whatsapp_webhooks 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Function to get client stats for Google Sheets export
CREATE OR REPLACE FUNCTION get_client_export_data(coach_uuid UUID)
RETURNS TABLE (
    client_name VARCHAR,
    phone_number VARCHAR,
    country VARCHAR,
    goals TEXT,
    categories TEXT,
    last_accountability_sent TIMESTAMP WITH TIME ZONE,
    last_celebration_sent TIMESTAMP WITH TIME ZONE,
    status VARCHAR,
    timezone VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cs.name,
        cs.phone_number,
        cs.country,
        STRING_AGG(DISTINCT g.title, ', ') as goals,
        ARRAY_TO_STRING(cs.categories, ', ') as categories,
        cs.last_accountability_sent,
        cs.last_celebration_sent,
        cs.status,
        cs.timezone
    FROM client_summary cs
    LEFT JOIN goals g ON cs.id = g.client_id AND g.is_achieved = false
    WHERE cs.coach_id = coach_uuid
    GROUP BY cs.id, cs.name, cs.phone_number, cs.country, cs.categories, 
             cs.last_accountability_sent, cs.last_celebration_sent, cs.status, cs.timezone
    ORDER BY cs.name;
END;
$$ LANGUAGE plpgsql;