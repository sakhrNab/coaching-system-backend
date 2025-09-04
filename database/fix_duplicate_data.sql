-- Fix duplicate data in categories and message_templates tables
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
SELECT message_type, content, COUNT(*) as count FROM message_templates WHERE is_default = true AND coach_id IS NULL GROUP BY message_type, content ORDER BY message_type, content;
