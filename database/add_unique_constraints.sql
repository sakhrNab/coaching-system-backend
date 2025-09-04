-- PostgreSQL Constraints to Prevent Duplications
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
ORDER BY tablename, indexname;

