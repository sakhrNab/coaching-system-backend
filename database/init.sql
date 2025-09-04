-- Database initialization script for production
-- This runs every time the container starts and is safe to run multiple times

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create coaches table if it doesn't exist
CREATE TABLE IF NOT EXISTS coaches (
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

-- Create categories table if it doesn't exist
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    is_predefined BOOLEAN DEFAULT false,
    coach_id UUID REFERENCES coaches(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, coach_id)
);

-- Insert predefined categories if they don't exist
-- Use a more robust approach to prevent duplicates
INSERT INTO categories (name, is_predefined)
SELECT name, true FROM (VALUES
    ('Weight'),
    ('Diet'),
    ('Business'),
    ('Finance'),
    ('Relationship'),
    ('Health'),
    ('Growth'),
    ('Socialization'),
    ('Communication'),
    ('Writing'),
    ('Creativity'),
    ('Career')
) AS predefined_categories(name)
WHERE NOT EXISTS (
    SELECT 1 FROM categories 
    WHERE categories.name = predefined_categories.name 
    AND is_predefined = true
);

-- Create clients table if it doesn't exist
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    country VARCHAR(100),
    timezone VARCHAR(10) DEFAULT 'EST',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(coach_id, phone_number)
);

-- Create client categories junction table
CREATE TABLE IF NOT EXISTS client_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_id, category_id)
);

-- Create goals table
CREATE TABLE IF NOT EXISTS goals (
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

-- Create message templates table
CREATE TABLE IF NOT EXISTS message_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID REFERENCES coaches(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default message templates if they don't exist
-- Use a more robust approach to prevent duplicates
INSERT INTO message_templates (message_type, content, is_default)
SELECT message_type, content, true FROM (VALUES
    ('celebration', '🎉 What are we celebrating today?'),
    ('celebration', '✨ What are you grateful for?'),
    ('celebration', '🌟 What victory are you proud of today?'),
    ('celebration', '🎊 What positive moment made your day?'),
    ('celebration', '💫 What breakthrough did you experience?'),
    ('accountability', '📝 How did you progress on your goals today?'),
    ('accountability', '🎯 What action did you take towards your target?'),
    ('accountability', '💪 What challenge did you overcome today?'),
    ('accountability', '📈 How are you measuring your progress?'),
    ('accountability', '🔥 What will you commit to tomorrow?')
) AS predefined_templates(message_type, content)
WHERE NOT EXISTS (
    SELECT 1 FROM message_templates 
    WHERE message_templates.message_type = predefined_templates.message_type 
    AND message_templates.content = predefined_templates.content
    AND is_default = true
    AND coach_id IS NULL
);

-- Create scheduled messages table
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

-- Create message history table
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

-- Create voice message processing table
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

-- Create Google Sheets sync table
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

-- Create WhatsApp webhooks table
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
CREATE INDEX IF NOT EXISTS idx_voice_processing_status ON voice_message_processing(processing_status);
CREATE INDEX IF NOT EXISTS idx_google_sheets_sync_coach_id ON google_sheets_sync(coach_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_webhooks_status ON whatsapp_webhooks(processing_status);

SELECT 'Database initialized successfully - all tables created' as status;