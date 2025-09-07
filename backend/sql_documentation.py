"""
SQL Documentation Page - Password Protected
Contains all SQL queries created during development with detailed explanations
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
import os
import hashlib
import secrets
from typing import Optional

router = APIRouter(prefix="/sql-docs", tags=["SQL Documentation"])

# Initialize templates
template_env = Environment(loader=FileSystemLoader("templates"))

# Password hash (you can set this in .env)
SQL_DOCS_PASSWORD = os.getenv("SQL_DOCS_PASSWORD", "admin123")
PASSWORD_HASH = hashlib.sha256(SQL_DOCS_PASSWORD.encode()).hexdigest()

# Session storage (in production, use Redis or database)
active_sessions = set()

def verify_password(password: str) -> bool:
    """Verify the provided password"""
    return hashlib.sha256(password.encode()).hexdigest() == PASSWORD_HASH

def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

# SQL Queries Documentation with chronological ordering
SQL_QUERIES = {
    "database_schema": {
        "title": "Database Schema Queries",
        "description": "Queries to inspect database structure and tables",
        "queries": [
            {
                "name": "Check Table Existence",
                "description": "Verify if WhatsApp-related tables exist in the database",
                "query": """SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('whatsapp_conversations', 'whatsapp_webhooks', 'conversation_messages');""",
                "migration": "Creates tables for WhatsApp conversation tracking and webhook handling",
                "created_at": "2024-12-07 10:00:00",
                "updated_at": "2024-12-07 10:00:00"
            },
            {
                "name": "Check Function Existence", 
                "description": "Verify if custom functions exist in the database",
                "query": """SELECT routine_name FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name IN ('can_send_free_message', 'get_active_conversation');""",
                "migration": "Creates custom functions for 24-hour rule checking and conversation management",
                "created_at": "2024-12-07 10:15:00",
                "updated_at": "2024-12-07 10:15:00"
            },
            {
                "name": "List All Tables",
                "description": "Get complete list of all tables in the public schema",
                "query": """SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;""",
                "migration": "General database inspection query",
                "created_at": "2024-12-07 10:30:00",
                "updated_at": "2024-12-07 10:30:00"
            }
        ]
    },
    "whatsapp_functions": {
        "title": "WhatsApp 24-Hour Rule Functions",
        "description": "Functions for managing WhatsApp's 24-hour messaging window",
        "queries": [
            {
                "name": "Check Free Message Status",
                "description": "Check if a phone number can send free messages (within 24-hour window)",
                "query": """SELECT can_send_free_message('1234567890') as can_send_free;""",
                "migration": "Creates function to check if client is within 24-hour window for free messaging",
                "created_at": "2024-12-07 11:00:00",
                "updated_at": "2024-12-07 11:00:00"
            },
            {
                "name": "Get Active Conversation",
                "description": "Get the active conversation for a phone number",
                "query": """SELECT get_active_conversation('1234567890') as conversation_id;""",
                "migration": "Creates function to retrieve active conversation ID for a phone number",
                "created_at": "2024-12-07 11:15:00",
                "updated_at": "2024-12-07 11:15:00"
            },
            {
                "name": "Test 24-Hour Window",
                "description": "Test the 24-hour window logic with a specific phone number",
                "query": """SELECT 
    phone_number,
    can_send_free_message(phone_number) as can_send_free,
    get_active_conversation(phone_number) as conversation_id,
    last_message_time,
    EXTRACT(EPOCH FROM (NOW() - last_message_time))/3600 as hours_since_last_message
FROM whatsapp_conversations 
WHERE phone_number = '1234567890';""",
                "migration": "Comprehensive test query for 24-hour window functionality",
                "created_at": "2024-12-07 11:30:00",
                "updated_at": "2024-12-07 11:30:00"
            }
        ]
    },
    "conversation_management": {
        "title": "Conversation Management Queries",
        "description": "Queries for managing WhatsApp conversations and messages",
        "queries": [
            {
                "name": "Create New Conversation",
                "description": "Insert a new conversation record for a phone number",
                "query": """INSERT INTO whatsapp_conversations (phone_number, conversation_id, status, created_at, last_message_time)
VALUES ('1234567890', 'conv_123', 'active', NOW(), NOW())
RETURNING *;""",
                "migration": "Creates conversation tracking table with phone number and status",
                "created_at": "2024-12-07 12:00:00",
                "updated_at": "2024-12-07 12:00:00"
            },
            {
                "name": "Update Conversation Status",
                "description": "Update conversation status and last message time",
                "query": """UPDATE whatsapp_conversations 
SET status = 'active', last_message_time = NOW()
WHERE phone_number = '1234567890'
RETURNING *;""",
                "migration": "Updates conversation status when new messages are received",
                "created_at": "2024-12-07 12:15:00",
                "updated_at": "2024-12-07 12:15:00"
            },
            {
                "name": "Get Conversation History",
                "description": "Retrieve conversation history for a phone number",
                "query": """SELECT 
    wc.phone_number,
    wc.status,
    wc.created_at,
    wc.last_message_time,
    COUNT(wm.id) as message_count
FROM whatsapp_conversations wc
LEFT JOIN conversation_messages wm ON wc.conversation_id = wm.conversation_id
WHERE wc.phone_number = '1234567890'
GROUP BY wc.phone_number, wc.status, wc.created_at, wc.last_message_time;""",
                "migration": "Creates relationship between conversations and messages",
                "created_at": "2024-12-07 12:30:00",
                "updated_at": "2024-12-07 12:30:00"
            }
        ]
    },
    "webhook_management": {
        "title": "Webhook Management Queries",
        "description": "Queries for handling WhatsApp webhooks and message processing",
        "queries": [
            {
                "name": "Log Webhook Event",
                "description": "Insert webhook event data for debugging and tracking",
                "query": """INSERT INTO whatsapp_webhooks (event_type, phone_number, message_id, payload, received_at)
VALUES ('message', '1234567890', 'msg_123', '{"text": "Hello"}', NOW())
RETURNING *;""",
                "migration": "Creates webhook logging table for debugging and monitoring",
                "created_at": "2024-12-07 13:00:00",
                "updated_at": "2024-12-07 13:00:00"
            },
            {
                "name": "Get Recent Webhooks",
                "description": "Retrieve recent webhook events for debugging",
                "query": """SELECT 
    event_type,
    phone_number,
    message_id,
    received_at,
    payload
FROM whatsapp_webhooks 
WHERE received_at >= NOW() - INTERVAL '1 hour'
ORDER BY received_at DESC
LIMIT 10;""",
                "migration": "Query for debugging recent webhook activity",
                "created_at": "2024-12-07 13:15:00",
                "updated_at": "2024-12-07 13:15:00"
            },
            {
                "name": "Clean Old Webhooks",
                "description": "Clean up old webhook records to prevent database bloat",
                "query": """DELETE FROM whatsapp_webhooks 
WHERE received_at < NOW() - INTERVAL '30 days'
RETURNING COUNT(*) as deleted_count;""",
                "migration": "Maintenance query to clean up old webhook data",
                "created_at": "2024-12-07 13:30:00",
                "updated_at": "2024-12-07 13:30:00"
            }
        ]
    },
    "migration_scripts": {
        "title": "Database Migration Scripts",
        "description": "Complete migration scripts for setting up WhatsApp functionality",
        "queries": [
            {
                "name": "Create WhatsApp Tables",
                "description": "Complete script to create all WhatsApp-related tables",
                "query": """-- ============================================
-- WhatsApp Database Schema Creation Script
-- This script creates all tables needed for WhatsApp integration
-- ============================================

-- Create whatsapp_conversations table
-- This table tracks active conversations and 24-hour window status
CREATE TABLE IF NOT EXISTS whatsapp_conversations (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    conversation_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    last_message_time TIMESTAMP DEFAULT NOW()
);

-- Create whatsapp_webhooks table
-- This table logs all incoming webhook events for debugging
CREATE TABLE IF NOT EXISTS whatsapp_webhooks (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    phone_number VARCHAR(20),
    message_id VARCHAR(100),
    payload JSONB,
    received_at TIMESTAMP DEFAULT NOW()
);

-- Create conversation_messages table
-- This table stores all messages in conversations
CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) REFERENCES whatsapp_conversations(conversation_id),
    message_id VARCHAR(100) UNIQUE NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    content TEXT,
    direction VARCHAR(10) NOT NULL,
    sent_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Performance Indexes
-- These indexes improve query performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_conversations_phone ON whatsapp_conversations(phone_number);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON whatsapp_conversations(status);
CREATE INDEX IF NOT EXISTS idx_webhooks_received_at ON whatsapp_webhooks(received_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON conversation_messages(conversation_id);""",
                "migration": "Complete database schema for WhatsApp integration",
                "created_at": "2024-12-07 14:00:00",
                "updated_at": "2024-12-07 14:00:00"
            },
            {
                "name": "Create WhatsApp Functions",
                "description": "Complete script to create all WhatsApp-related functions",
                "query": """-- ============================================
-- WhatsApp Business API Functions
-- These functions handle the 24-hour messaging window rule
-- ============================================

-- Function to check if phone number can send free messages
-- WhatsApp allows free messages only within 24 hours of last client message
CREATE OR REPLACE FUNCTION can_send_free_message(phone_num VARCHAR(20))
RETURNS BOOLEAN AS $$
DECLARE
    last_msg_time TIMESTAMP;                  -- Store last message timestamp
    hours_since_last_message NUMERIC;         -- Calculate hours since last message
BEGIN
    -- Get last message time for the phone number
    SELECT last_message_time INTO last_msg_time
    FROM whatsapp_conversations
    WHERE phone_number = phone_num;
    
    -- If no conversation exists, they can send free messages
    -- This handles new clients who haven't messaged before
    IF last_msg_time IS NULL THEN
        RETURN TRUE;
    END IF;
    
    -- Calculate hours since last message
    -- Convert timestamp difference to hours
    hours_since_last_message := EXTRACT(EPOCH FROM (NOW() - last_msg_time)) / 3600;
    
    -- Return true if within 24 hours (WhatsApp's free messaging window)
    RETURN hours_since_last_message <= 24;
END;
$$ LANGUAGE plpgsql;

-- Function to get active conversation for a phone number
-- Returns the conversation ID if there's an active conversation
CREATE OR REPLACE FUNCTION get_active_conversation(phone_num VARCHAR(20))
RETURNS VARCHAR(100) AS $$
DECLARE
    conv_id VARCHAR(100);                     -- Store conversation ID
BEGIN
    -- Find active conversation for this phone number
    SELECT conversation_id INTO conv_id
    FROM whatsapp_conversations
    WHERE phone_number = phone_num AND status = 'active';
    
    -- Return the conversation ID (NULL if no active conversation)
    RETURN conv_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update conversation status
-- Updates both status and last message time
CREATE OR REPLACE FUNCTION update_conversation_status(
    phone_num VARCHAR(20),                    -- Phone number to update
    new_status VARCHAR(20)                    -- New status: active, closed, expired
)
RETURNS VOID AS $$
BEGIN
    -- Update conversation with new status and current timestamp
    UPDATE whatsapp_conversations
    SET status = new_status, 
        last_message_time = NOW()             -- Update timestamp for 24h rule
    WHERE phone_number = phone_num;
END;
$$ LANGUAGE plpgsql;""",
                "migration": "Creates all custom functions for WhatsApp 24-hour rule management",
                "created_at": "2024-12-07 14:30:00",
                "updated_at": "2024-12-07 14:30:00"
            },
            {
                "name": "QR Onboarding Schema",
                "description": "Complete QR-based coach onboarding system with session management",
                "query": """-- QR Onboarding System Database Schema
-- Implements the correct dual-purpose QR flow (register or login)

-- Onboarding sessions table
CREATE TABLE onboarding_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    coach_id UUID REFERENCES coaches(id) ON DELETE CASCADE,
    phone VARCHAR(20),
    display_name VARCHAR(255),
    phone_resource_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Login sessions table for 5-day auto-login
CREATE TABLE login_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- QR codes table for tracking generated QR codes
CREATE TABLE qr_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    qr_data_url TEXT NOT NULL,
    onboarding_url TEXT NOT NULL,
    generated_by UUID REFERENCES coaches(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_onboarding_sessions_session_id ON onboarding_sessions(session_id);
CREATE INDEX idx_onboarding_sessions_expires_at ON onboarding_sessions(expires_at);
CREATE INDEX idx_onboarding_sessions_status ON onboarding_sessions(status);
CREATE INDEX idx_onboarding_sessions_coach_id ON onboarding_sessions(coach_id);

CREATE INDEX idx_login_sessions_session_id ON login_sessions(session_id);
CREATE INDEX idx_login_sessions_coach_id ON login_sessions(coach_id);
CREATE INDEX idx_login_sessions_expires_at ON login_sessions(expires_at);

CREATE INDEX idx_qr_codes_session_id ON qr_codes(session_id);
CREATE INDEX idx_qr_codes_expires_at ON qr_codes(expires_at);
CREATE INDEX idx_qr_codes_generated_by ON qr_codes(generated_by);

-- Update coaches table for QR onboarding
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS phone_e164 VARCHAR(20);
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS onboarding_method VARCHAR(20) DEFAULT 'qr';
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0;

-- Add comments
COMMENT ON TABLE onboarding_sessions IS 'Tracks QR-based onboarding sessions';
COMMENT ON TABLE login_sessions IS 'Tracks 5-day auto-login sessions';
COMMENT ON TABLE qr_codes IS 'Tracks generated QR codes for onboarding';

-- Cleanup functions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    -- Clean up expired onboarding sessions
    DELETE FROM onboarding_sessions WHERE expires_at < NOW();
    
    -- Clean up expired login sessions
    DELETE FROM login_sessions WHERE expires_at < NOW();
    
    -- Clean up expired QR codes
    DELETE FROM qr_codes WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to get active coach session
CREATE OR REPLACE FUNCTION get_active_coach_session(session_token VARCHAR(255))
RETURNS TABLE(
    coach_id UUID,
    coach_name VARCHAR(255),
    phone_e164 VARCHAR(20),
    phone_display_name VARCHAR(255),
    session_expires_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.name,
        c.phone_e164,
        c.phone_display_name,
        ls.expires_at
    FROM login_sessions ls
    JOIN coaches c ON ls.coach_id = c.id
    WHERE ls.session_id = session_token 
    AND ls.expires_at > NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to create login session
CREATE OR REPLACE FUNCTION create_login_session(
    coach_uuid UUID,
    session_token VARCHAR(255),
    session_days INTEGER DEFAULT 5
)
RETURNS BOOLEAN AS $$
DECLARE
    expires_at TIMESTAMP WITH TIME ZONE;
BEGIN
    expires_at := NOW() + (session_days || ' days')::INTERVAL;
    
    INSERT INTO login_sessions (session_id, coach_id, expires_at)
    VALUES (session_token, coach_uuid, expires_at)
    ON CONFLICT (session_id) DO UPDATE SET
        coach_id = EXCLUDED.coach_id,
        expires_at = EXCLUDED.expires_at,
        last_used_at = NOW();
    
    -- Update coach login stats
    UPDATE coaches 
    SET last_login_at = NOW(), login_count = login_count + 1
    WHERE id = coach_uuid;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to validate session
CREATE OR REPLACE FUNCTION validate_session(session_token VARCHAR(255))
RETURNS BOOLEAN AS $$
DECLARE
    session_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM login_sessions 
        WHERE session_id = session_token 
        AND expires_at > NOW()
    ) INTO session_exists;
    
    IF session_exists THEN
        -- Update last used timestamp
        UPDATE login_sessions 
        SET last_used_at = NOW()
        WHERE session_id = session_token;
    END IF;
    
    RETURN session_exists;
END;
$$ LANGUAGE plpgsql;""",
                "migration": "Implements complete QR-based coach onboarding system with session management",
                "created_at": "2024-12-07 15:00:00",
                "updated_at": "2024-12-07 15:00:00"
            },
            {
                "name": "Local Migration Script",
                "description": "Local development migration with test data for QR onboarding",
                "query": """-- Local Database Migration for QR Onboarding
-- Run this locally before testing

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Onboarding sessions table
CREATE TABLE IF NOT EXISTS onboarding_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    coach_id UUID REFERENCES coaches(id) ON DELETE CASCADE,
    phone VARCHAR(20),
    display_name VARCHAR(255),
    phone_resource_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Login sessions table for 5-day auto-login
CREATE TABLE IF NOT EXISTS login_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    coach_id UUID NOT NULL REFERENCES coaches(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- QR codes table for tracking generated QR codes
CREATE TABLE IF NOT EXISTS qr_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    qr_data_url TEXT NOT NULL,
    onboarding_url TEXT NOT NULL,
    generated_by UUID REFERENCES coaches(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_onboarding_sessions_session_id ON onboarding_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_sessions_expires_at ON onboarding_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_onboarding_sessions_status ON onboarding_sessions(status);
CREATE INDEX IF NOT EXISTS idx_onboarding_sessions_coach_id ON onboarding_sessions(coach_id);

CREATE INDEX IF NOT EXISTS idx_login_sessions_session_id ON login_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_login_sessions_coach_id ON login_sessions(coach_id);
CREATE INDEX IF NOT EXISTS idx_login_sessions_expires_at ON login_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_qr_codes_session_id ON qr_codes(session_id);
CREATE INDEX IF NOT EXISTS idx_qr_codes_expires_at ON qr_codes(expires_at);
CREATE INDEX IF NOT EXISTS idx_qr_codes_generated_by ON qr_codes(generated_by);

-- Update coaches table for QR onboarding
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS phone_e164 VARCHAR(20);
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS onboarding_method VARCHAR(20) DEFAULT 'qr';
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0;

-- Add comments
COMMENT ON TABLE onboarding_sessions IS 'Tracks QR-based onboarding sessions';
COMMENT ON TABLE login_sessions IS 'Tracks 5-day auto-login sessions';
COMMENT ON TABLE qr_codes IS 'Tracks generated QR codes for onboarding';

-- Cleanup functions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    -- Clean up expired onboarding sessions
    DELETE FROM onboarding_sessions WHERE expires_at < NOW();
    
    -- Clean up expired login sessions
    DELETE FROM login_sessions WHERE expires_at < NOW();
    
    -- Clean up expired QR codes
    DELETE FROM qr_codes WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to get active coach session
CREATE OR REPLACE FUNCTION get_active_coach_session(session_token VARCHAR(255))
RETURNS TABLE(
    coach_id UUID,
    coach_name VARCHAR(255),
    phone_e164 VARCHAR(20),
    phone_display_name VARCHAR(255),
    session_expires_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.name,
        c.phone_e164,
        c.phone_display_name,
        ls.expires_at
    FROM login_sessions ls
    JOIN coaches c ON ls.coach_id = c.id
    WHERE ls.session_id = session_token 
    AND ls.expires_at > NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to create login session
CREATE OR REPLACE FUNCTION create_login_session(
    coach_uuid UUID,
    session_token VARCHAR(255),
    session_days INTEGER DEFAULT 5
)
RETURNS BOOLEAN AS $$
DECLARE
    expires_at TIMESTAMP WITH TIME ZONE;
BEGIN
    expires_at := NOW() + (session_days || ' days')::INTERVAL;
    
    INSERT INTO login_sessions (session_id, coach_id, expires_at)
    VALUES (session_token, coach_uuid, expires_at)
    ON CONFLICT (session_id) DO UPDATE SET
        coach_id = EXCLUDED.coach_id,
        expires_at = EXCLUDED.expires_at,
        last_used_at = NOW();
    
    -- Update coach login stats
    UPDATE coaches 
    SET last_login_at = NOW(), login_count = login_count + 1
    WHERE id = coach_uuid;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to validate session
CREATE OR REPLACE FUNCTION validate_session(session_token VARCHAR(255))
RETURNS BOOLEAN AS $$
DECLARE
    session_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM login_sessions 
        WHERE session_id = session_token 
        AND expires_at > NOW()
    ) INTO session_exists;
    
    IF session_exists THEN
        -- Update last used timestamp
        UPDATE login_sessions 
        SET last_used_at = NOW()
        WHERE session_id = session_token;
    END IF;
    
    RETURN session_exists;
END;
$$ LANGUAGE plpgsql;

-- Insert a test coach for local testing
INSERT INTO coaches (id, name, email, timezone, registration_barcode, whatsapp_token, created_at, updated_at)
VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'Test Coach',
    'test@coach.com',
    'EST',
    'TEST_BARCODE_123',
    'test_token_123',
    NOW(),
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Show migration status
SELECT 'QR Onboarding Migration Complete' as status;
SELECT COUNT(*) as coaches_count FROM coaches;
SELECT COUNT(*) as onboarding_sessions_count FROM onboarding_sessions;
SELECT COUNT(*) as login_sessions_count FROM login_sessions;""",
                "migration": "Local development migration with test data for QR onboarding system",
                "created_at": "2024-12-07 15:30:00",
                "updated_at": "2024-12-07 15:30:00"
            },
            {
                "name": "Language Codes Migration",
                "description": "Adds language code support for WhatsApp message templates",
                "query": """-- Add language_code column to message_templates table
-- This allows storing WhatsApp template language codes in the database

-- Add language_code column to message_templates table
ALTER TABLE message_templates 
ADD COLUMN IF NOT EXISTS language_code VARCHAR(10) DEFAULT 'en_US';

-- Add whatsapp_template_name column to store the actual WhatsApp template name
ALTER TABLE message_templates 
ADD COLUMN IF NOT EXISTS whatsapp_template_name VARCHAR(100);

-- Update existing templates with their language codes and WhatsApp template names
-- All messages use 'en' language code and have 'Hi {{1}},' prefix in WhatsApp

-- Celebration messages (6-10)
UPDATE message_templates 
SET language_code = 'en', whatsapp_template_name = 'celebration_message_6', message_type = 'celebration'
WHERE content = '🎉 What are we celebrating today?' AND is_default = true;

UPDATE message_templates 
SET language_code = 'en', whatsapp_template_name = 'celebration_message_7', message_type = 'celebration'
WHERE content = '✨ What are you grateful for?' AND is_default = true;

UPDATE message_templates 
SET language_code = 'en', whatsapp_template_name = 'celebration_message_8', message_type = 'celebration'
WHERE content = '💫 What breakthrough did you experience?' AND is_default = true;

UPDATE message_templates 
SET language_code = 'en', whatsapp_template_name = 'celebration_message_9', message_type = 'celebration'
WHERE content = '🌟 What victory are you proud of today?' AND is_default = true;

UPDATE message_templates 
SET language_code = 'en', whatsapp_template_name = 'celebration_message_10', message_type = 'celebration'
WHERE content = '🎊 What positive moment made your day?' AND is_default = true;

-- Accountability messages (1-5) - these should be renamed to accountability_message_1-5
UPDATE message_templates 
SET language_code = 'en', whatsapp_template_name = 'accountability_message_1', message_type = 'accountability'
WHERE content = '🔥 What will you commit to tomorrow?' AND is_default = true;

UPDATE message_templates 
SET language_code = 'en', whatsapp_template_name = 'accountability_message_2', message_type = 'accountability'
WHERE content = '📝 How did you progress on your goals today?' AND is_default = true;

UPDATE message_templates 
SET language_code = 'en', whatsapp_template_name = 'accountability_message_3', message_type = 'accountability'
WHERE content = '🎯 What action did you take towards your target?' AND is_default = true;

UPDATE message_templates 
SET language_code = 'en', whatsapp_template_name = 'accountability_message_4', message_type = 'accountability'
WHERE content = '💪 What challenge did you overcome today?' AND is_default = true;

UPDATE message_templates 
SET language_code = 'en', whatsapp_template_name = 'accountability_message_5', message_type = 'accountability'
WHERE content = '📈 How are you measuring your progress?' AND is_default = true;

-- Add a default template for fallback
INSERT INTO message_templates (message_type, content, is_default, language_code, whatsapp_template_name)
SELECT 'system', 'Hello! How can I help you today?', true, 'en_US', 'hello_world'
WHERE NOT EXISTS (
    SELECT 1 FROM message_templates 
    WHERE whatsapp_template_name = 'hello_world'
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_message_templates_whatsapp_name 
ON message_templates(whatsapp_template_name) 
WHERE whatsapp_template_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_message_templates_language_code 
ON message_templates(language_code) 
WHERE language_code IS NOT NULL;

-- Verify the updates
SELECT 
    content,
    whatsapp_template_name,
    language_code,
    message_type,
    is_default
FROM message_templates 
WHERE is_default = true
ORDER BY message_type, content;""",
                "migration": "Adds language code support and WhatsApp template name mapping for message templates",
                "created_at": "2024-12-07 16:00:00",
                "updated_at": "2024-12-07 16:00:00"
            },
            {
                "name": "Conversation Tracking Schema",
                "description": "WhatsApp conversation tracking for 24-hour window management",
                "query": """-- Conversation tracking for WhatsApp 24-hour window management
-- This table tracks when users initiate conversations and when they expire

CREATE TABLE IF NOT EXISTS whatsapp_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wa_id VARCHAR(20) NOT NULL,
    user_name VARCHAR(255),
    conversation_id VARCHAR(255),
    origin_type VARCHAR(20) NOT NULL,
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
$$ LANGUAGE plpgsql;""",
                "migration": "Implements WhatsApp conversation tracking for 24-hour messaging window management",
                "created_at": "2024-12-07 16:30:00",
                "updated_at": "2024-12-07 16:30:00"
            },
            {
                "name": "Unique Constraints Migration",
                "description": "Adds unique constraints to prevent duplicate data in categories and templates",
                "query": """-- PostgreSQL Constraints to Prevent Duplications
-- This script adds proper constraints to prevent duplicate data

-- 1. For Categories Table
-- Add a partial unique index for predefined categories
-- This ensures only one predefined category per name
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS unique_predefined_category_name 
ON categories (name) 
WHERE is_predefined = true;

-- Add a partial unique index for custom categories per coach
-- This ensures only one custom category per name per coach
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS unique_custom_category_per_coach 
ON categories (name, coach_id) 
WHERE is_predefined = false AND coach_id IS NOT NULL;

-- 2. For Message Templates Table
-- Add a partial unique index for predefined templates
-- This ensures only one predefined template per message_type and content
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS unique_predefined_template 
ON message_templates (message_type, content) 
WHERE is_default = true AND coach_id IS NULL;

-- Add a partial unique index for custom templates per coach
-- This ensures only one custom template per message_type and content per coach
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS unique_custom_template_per_coach 
ON message_templates (message_type, content, coach_id) 
WHERE is_default = false AND coach_id IS NOT NULL;

-- 3. Verify the constraints are working
-- Test that we can't insert duplicate predefined categories
-- This should fail:
-- INSERT INTO categories (name, is_predefined) VALUES ('Business', true);

-- Test that we can't insert duplicate predefined templates
-- This should fail:
-- INSERT INTO message_templates (message_type, content, is_default) VALUES ('celebration', '🎉 What are we celebrating today?', true);

-- 4. Show current constraints
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('categories', 'message_templates')
AND indexname LIKE '%unique%'
ORDER BY tablename, indexname;""",
                "migration": "Adds unique constraints to prevent duplicate data in categories and message templates",
                "created_at": "2024-12-07 17:00:00",
                "updated_at": "2024-12-07 17:00:00"
            },
            {
                "name": "Fix Duplicate Data",
                "description": "Removes duplicate data and adds proper constraints to prevent future duplicates",
                "query": """-- Fix duplicate data in categories and message_templates tables
-- This script removes duplicates and adds proper constraints

-- First, let's see what duplicates we have
-- SELECT name, COUNT(*) as count FROM categories WHERE is_predefined = true GROUP BY name HAVING COUNT(*) > 1;

-- Remove duplicate predefined categories
-- Keep only the first occurrence of each predefined category
WITH duplicates AS (
    SELECT id, 
           ROW_NUMBER() OVER (PARTITION BY name ORDER BY created_at) as rn
    FROM categories 
    WHERE is_predefined = true
)
DELETE FROM categories 
WHERE id IN (
    SELECT id FROM duplicates WHERE rn > 1
);

-- Remove duplicate predefined message templates
-- Keep only the first occurrence of each predefined template
WITH duplicates AS (
    SELECT id, 
           ROW_NUMBER() OVER (PARTITION BY message_type, content ORDER BY created_at) as rn
    FROM message_templates 
    WHERE is_default = true AND coach_id IS NULL
)
DELETE FROM message_templates 
WHERE id IN (
    SELECT id FROM duplicates WHERE rn > 1
);

-- Add a proper unique constraint for predefined categories
-- This ensures only one predefined category per name
ALTER TABLE categories 
ADD CONSTRAINT unique_predefined_category 
UNIQUE (name) 
WHERE is_predefined = true;

-- Add a proper unique constraint for predefined message templates
-- This ensures only one predefined template per message_type and content
ALTER TABLE message_templates 
ADD CONSTRAINT unique_predefined_template 
UNIQUE (message_type, content) 
WHERE is_default = true AND coach_id IS NULL;

-- Verify the fixes
SELECT 'Categories after cleanup:' as info;
SELECT name, COUNT(*) as count FROM categories WHERE is_predefined = true GROUP BY name ORDER BY name;

SELECT 'Templates after cleanup:' as info;
SELECT message_type, content, COUNT(*) as count FROM message_templates WHERE is_default = true AND coach_id IS NULL GROUP BY message_type, content ORDER BY message_type, content;""",
                "migration": "Removes duplicate data and adds constraints to prevent future duplicates",
                "created_at": "2024-12-07 17:30:00",
                "updated_at": "2024-12-07 17:30:00"
            }
        ]
    },
    "testing_queries": {
        "title": "Testing and Debugging Queries",
        "description": "Queries for testing and debugging WhatsApp functionality",
        "queries": [
            {
                "name": "Test 24-Hour Rule Logic",
                "description": "Comprehensive test of the 24-hour rule implementation",
                "query": """-- Test 24-hour rule with various scenarios
WITH test_cases AS (
    SELECT '1234567890' as phone_number, NOW() - INTERVAL '1 hour' as last_msg_time UNION ALL
    SELECT '0987654321' as phone_number, NOW() - INTERVAL '25 hours' as last_msg_time UNION ALL
    SELECT '5555555555' as phone_number, NULL as last_msg_time
)
SELECT 
    tc.phone_number,
    tc.last_msg_time,
    can_send_free_message(tc.phone_number) as can_send_free,
    CASE 
        WHEN tc.last_msg_time IS NULL THEN 'No conversation'
        WHEN EXTRACT(EPOCH FROM (NOW() - tc.last_msg_time))/3600 <= 24 THEN 'Within 24h'
        ELSE 'Outside 24h'
    END as status
FROM test_cases tc;""",
                "migration": "Test query to verify 24-hour rule logic works correctly",
                "created_at": "2024-12-07 18:00:00",
                "updated_at": "2024-12-07 18:00:00"
            },
            {
                "name": "Performance Analysis",
                "description": "Analyze performance of WhatsApp-related queries",
                "query": """-- Analyze table sizes and performance
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation,
    most_common_vals
FROM pg_stats 
WHERE schemaname = 'public' 
AND tablename IN ('whatsapp_conversations', 'whatsapp_webhooks', 'conversation_messages')
ORDER BY tablename, attname;""",
                "migration": "Performance analysis query for database optimization",
                "created_at": "2024-12-07 18:15:00",
                "updated_at": "2024-12-07 18:15:00"
            }
        ]
    }
}

@router.get("/", response_class=HTMLResponse)
async def sql_documentation_page(request: Request, session_token: Optional[str] = None):
    """Main SQL documentation page with password protection"""
    
    # Check if user has valid session
    if session_token and session_token in active_sessions:
        template = template_env.get_template("sql_docs.html")
        sorted_queries = sort_queries_chronologically(SQL_QUERIES)
        return HTMLResponse(template.render(
            request=request,
            sql_queries=sorted_queries,
            session_token=session_token
        ))
    
    # Show login form
    template = template_env.get_template("sql_login.html")
    return HTMLResponse(template.render(request=request))

@router.post("/login")
async def login_sql_docs(request: Request, password: str = Form(...)):
    """Handle password authentication for SQL docs"""
    
    if verify_password(password):
        # Generate session token
        session_token = generate_session_token()
        active_sessions.add(session_token)
        
        template = template_env.get_template("sql_docs.html")
        sorted_queries = sort_queries_chronologically(SQL_QUERIES)
        return HTMLResponse(template.render(
            request=request,
            sql_queries=sorted_queries,
            session_token=session_token
        ))
    else:
        template = template_env.get_template("sql_login.html")
        return HTMLResponse(template.render(
            request=request,
            error="Invalid password"
        ))

@router.post("/logout")
async def logout_sql_docs(session_token: str = Form(...)):
    """Handle logout and session cleanup"""
    
    if session_token in active_sessions:
        active_sessions.remove(session_token)
    
    return {"message": "Logged out successfully"}

@router.get("/api/queries")
async def get_sql_queries(session_token: Optional[str] = None):
    """API endpoint to get SQL queries (requires authentication)"""
    
    if not session_token or session_token not in active_sessions:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return {"queries": SQL_QUERIES}

def convert_to_oneliner(query: str) -> str:
    """Convert multi-line SQL query to single line"""
    return " ".join(line.strip() for line in query.split('\n') if line.strip())

def remove_inline_comments(query: str) -> str:
    """Remove inline comments from SQL query"""
    import re
    # Remove -- comments at end of lines
    cleaned = re.sub(r'\s*--.*$', '', query, flags=re.MULTILINE)
    # Remove /* */ comments
    cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)
    # Clean up extra whitespace
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
    return cleaned.strip()

def sort_queries_chronologically(sql_queries: dict) -> dict:
    """Sort all queries within each category by creation date (oldest first)"""
    sorted_queries = {}
    
    for category_key, category_data in sql_queries.items():
        sorted_queries[category_key] = category_data.copy()
        
        # Sort queries by created_at timestamp
        if 'queries' in category_data:
            sorted_queries[category_key]['queries'] = sorted(
                category_data['queries'],
                key=lambda x: x.get('created_at', '1970-01-01 00:00:00')
            )
    
    return sorted_queries
