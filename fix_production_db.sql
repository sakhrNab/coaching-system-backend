-- Manual Database Fix for Production
-- Run this SQL script directly in your PostgreSQL database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop tables if they exist (clean slate)
DROP TABLE IF EXISTS voice_message_processing CASCADE;
DROP TABLE IF EXISTS message_history CASCADE;
DROP TABLE IF EXISTS scheduled_messages CASCADE;
DROP TABLE IF EXISTS message_templates CASCADE;
DROP TABLE IF EXISTS goals CASCADE;
DROP TABLE IF EXISTS client_categories CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS coaches CASCADE;

-- Create coaches table
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

-- Create categories table
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    is_predefined BOOLEAN DEFAULT false,
    coach_id UUID REFERENCES coaches(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, coach_id)
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

-- Create clients table
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
    UNIQUE(coach_id, phone_number)
);

-- Create client categories junction table
CREATE TABLE client_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_id, category_id)
);

-- Create goals table
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

-- Create message templates table
CREATE TABLE message_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coach_id UUID REFERENCES coaches(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL,
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

-- Create scheduled messages table
CREATE TABLE scheduled_messages (
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
CREATE TABLE message_history (
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
CREATE TABLE voice_message_processing (
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_coaches_registration_barcode ON coaches(registration_barcode);
CREATE INDEX IF NOT EXISTS idx_coaches_whatsapp_token ON coaches(whatsapp_token);
CREATE INDEX IF NOT EXISTS idx_clients_coach_id ON clients(coach_id);
CREATE INDEX IF NOT EXISTS idx_clients_phone_number ON clients(phone_number);
CREATE INDEX IF NOT EXISTS idx_message_history_coach_id ON message_history(coach_id);
CREATE INDEX IF NOT EXISTS idx_message_history_client_id ON message_history(client_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_messages_status ON scheduled_messages(status);
CREATE INDEX IF NOT EXISTS idx_voice_processing_status ON voice_message_processing(processing_status);

-- Verify tables were created
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Show success message
SELECT 'Database tables created successfully!' as status;
