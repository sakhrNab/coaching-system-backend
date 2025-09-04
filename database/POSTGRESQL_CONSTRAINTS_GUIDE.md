# PostgreSQL Constraints to Prevent Duplications

## 🎯 **Correct PostgreSQL Syntax for Unique Constraints**

PostgreSQL doesn't support `WHERE` clauses in `UNIQUE` constraints, but it does support **Partial Unique Indexes** which achieve the same result.

## 📋 **Categories Table Constraints**

### **1. Predefined Categories (coach_id = NULL)**
```sql
-- Prevents duplicate predefined categories
CREATE UNIQUE INDEX unique_predefined_category_name 
ON categories (name) 
WHERE is_predefined = true;
```

### **2. Custom Categories per Coach**
```sql
-- Prevents duplicate custom categories per coach
CREATE UNIQUE INDEX unique_custom_category_per_coach 
ON categories (name, coach_id) 
WHERE is_predefined = false AND coach_id IS NOT NULL;
```

## 📋 **Message Templates Table Constraints**

### **1. Predefined Templates (coach_id = NULL)**
```sql
-- Prevents duplicate predefined templates
CREATE UNIQUE INDEX unique_predefined_template 
ON message_templates (message_type, content) 
WHERE is_default = true AND coach_id IS NULL;
```

### **2. Custom Templates per Coach**
```sql
-- Prevents duplicate custom templates per coach
CREATE UNIQUE INDEX unique_custom_template_per_coach 
ON message_templates (message_type, content, coach_id) 
WHERE is_default = false AND coach_id IS NOT NULL;
```

## 🔧 **Complete Setup Script**

```sql
-- 1. Categories constraints
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS unique_predefined_category_name 
ON categories (name) 
WHERE is_predefined = true;

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS unique_custom_category_per_coach 
ON categories (name, coach_id) 
WHERE is_predefined = false AND coach_id IS NOT NULL;

-- 2. Message templates constraints
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS unique_predefined_template 
ON message_templates (message_type, content) 
WHERE is_default = true AND coach_id IS NULL;

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS unique_custom_template_per_coach 
ON message_templates (message_type, content, coach_id) 
WHERE is_default = false AND coach_id IS NOT NULL;
```

## ✅ **Key Points**

1. **Partial Unique Indexes** are the correct PostgreSQL way to create conditional unique constraints
2. **CONCURRENTLY** allows creating indexes without blocking table access
3. **IF NOT EXISTS** prevents errors if indexes already exist
4. **WHERE clauses** in indexes filter which rows the uniqueness applies to
5. **NULL handling** is important - predefined data should have `coach_id = NULL`

## 🚫 **What NOT to Use**

```sql
-- ❌ This doesn't work in PostgreSQL
ALTER TABLE categories 
ADD CONSTRAINT unique_predefined_category 
UNIQUE (name) WHERE is_predefined = true;

-- ❌ This doesn't work in PostgreSQL  
CREATE UNIQUE INDEX unique_predefined_category 
ON categories (name) 
WHERE is_predefined = true AND coach_id = ''; -- Empty string comparison fails for UUID
```

## 🧪 **Testing the Constraints**

```sql
-- Test predefined categories constraint
INSERT INTO categories (name, is_predefined) VALUES ('Business', true);
-- Should fail with: duplicate key value violates unique constraint

-- Test predefined templates constraint  
INSERT INTO message_templates (message_type, content, is_default) 
VALUES ('celebration', '🎉 What are we celebrating today?', true);
-- Should fail with: duplicate key value violates unique constraint
```

## 📊 **View Current Constraints**

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('categories', 'message_templates')
AND indexname LIKE '%unique%'
ORDER BY tablename, indexname;
```
