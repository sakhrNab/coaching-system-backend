-- Production Database Migration Script
-- Run this script in your production PostgreSQL database to fix missing tables

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create missing tables that might not exist in production

-- Create scheduled messages table if missing
CREATE TABLE IF NOT EXISTS scheduled_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    schedule_type VARCHAR(20) NOT NULL,
    scheduled_time TIMESTAMP WITH TIME ZONE,
    recurring_pattern JSONB,
    timezone VARCHAR(10),
    status VARCHAR(20) DEFAULT 'scheduled',
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create message history table if missing
CREATE TABLE IF NOT EXISTS message_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scheduled_message_id UUID REFERENCES scheduled_messages(id) ON DELETE SET NULL,
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    whatsapp_message_id VARCHAR(255),
    delivery_status VARCHAR(20) DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- Create voice message processing table if missing
CREATE TABLE IF NOT EXISTS voice_message_processing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    whatsapp_message_id VARCHAR(255) NOT NULL,
    original_audio_url TEXT,
    transcribed_text TEXT,
    corrected_text TEXT,
    final_text TEXT,
    processing_status VARCHAR(20) DEFAULT 'received',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Google Sheets sync table if missing
CREATE TABLE IF NOT EXISTS google_sheets_sync (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    sheet_id VARCHAR(255),
    sheet_url TEXT,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(20) DEFAULT 'pending',
    row_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create WhatsApp webhooks table if missing
CREATE TABLE IF NOT EXISTS whatsapp_webhooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    webhook_data JSONB NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_status VARCHAR(20) DEFAULT 'received',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_coaches_registration_barcode ON coaches(registration_barcode);
CREATE INDEX IF NOT EXISTS idx_coaches_whatsapp_token ON coaches(whatsapp_token);
CREATE INDEX IF NOT EXISTS idx_clients_coach_id ON clients(coach_id);
CREATE INDEX IF NOT EXISTS idx_clients_phone_number ON clients(phone_number);
CREATE INDEX IF NOT EXISTS idx_message_history_coach_id ON message_history(coach_id);
CREATE INDEX IF NOT EXISTS idx_message_history_client_id ON message_history(client_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_messages_status ON scheduled_messages(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_messages_coach_id ON scheduled_messages(coach_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_messages_client_id ON scheduled_messages(client_id);
CREATE INDEX IF NOT EXISTS idx_voice_processing_status ON voice_message_processing(processing_status);
CREATE INDEX IF NOT EXISTS idx_google_sheets_sync_coach_id ON google_sheets_sync(coach_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_webhooks_status ON whatsapp_webhooks(processing_status);

-- Insert default message templates if they don't exist
INSERT INTO message_templates (message_type, content, is_default) VALUES
    ('celebration', '🎉 What are we celebrating today?', true),
    ('celebration', '✨ What are you grateful for?', true),
    ('celebration', '🌟 What victory are you proud of today?', true),
    ('celebration', '🎊 What positive moment made your day?', true),
    ('celebration', '💫 What breakthrough did you experience?', true),
    ('accountability', '📝 How did you progress on your goals today?', true),
    ('accountability', '🎯 What action did you take towards your target?', true),
    ('accountability', '💪 What challenge did you overcome today?', true),
    ('accountability', '📈 How are you measuring your progress?', true),
    ('accountability', '🔥 What will you commit to tomorrow?', true)
ON CONFLICT DO NOTHING;

-- Verify all tables exist
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename IN (
        'coaches', 'categories', 'clients', 'client_categories', 
        'goals', 'message_templates', 'scheduled_messages', 
        'message_history', 'voice_message_processing', 
        'google_sheets_sync', 'whatsapp_webhooks'
    )
ORDER BY tablename;

-- Show success message
SELECT 
    'Production database migration completed successfully!' as status,
    COUNT(*) as tables_created
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename IN (
        'coaches', 'categories', 'clients', 'client_categories', 
        'goals', 'message_templates', 'scheduled_messages', 
        'message_history', 'voice_message_processing', 
        'google_sheets_sync', 'whatsapp_webhooks'
    );

