#!/bin/bash

# Manual Database Fix Script for Coolify
# Run this directly in your Coolify application container

echo "🔧 Manual Database Fix for Production"
echo "===================================="

# Check environment variables
if [ -z "$DB_PASSWORD" ]; then
    echo "❌ ERROR: DB_PASSWORD environment variable not set"
    echo "   This script must be run in the application container"
    exit 1
fi

echo "✅ Environment variables found"

# Test database connection
echo ""
echo "🔗 Testing database connection..."
if PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -c "SELECT version();" >/dev/null 2>&1; then
    echo "✅ Database connection successful"
else
    echo "❌ Database connection failed"
    echo "   Check PostgreSQL container and environment variables"
    exit 1
fi

# Check current tables
echo ""
echo "📋 Current database tables:"
TABLES=$(PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" 2>/dev/null)

if [ -z "$TABLES" ]; then
    echo "   No tables found - database is empty"
else
    echo "$TABLES" | while read -r table; do
        if [ -n "$table" ]; then
            COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | tr -d ' ')
            echo "   - $table: $COUNT records"
        fi
    done
fi

# Run the database fix
echo ""
echo "🔨 Running database fix..."
if PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -f /app/fix_production_db.sql; then
    echo "✅ Database fix completed successfully!"
else
    echo "❌ Database fix failed"
    exit 1
fi

# Verify the fix
echo ""
echo "📊 Verifying database fix..."
NEW_TABLES=$(PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" 2>/dev/null)

echo "✅ Database tables after fix:"
echo "$NEW_TABLES" | while read -r table; do
    if [ -n "$table" ]; then
        COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | tr -d ' ')
        echo "   - $table: $COUNT records"
    fi
done

# Test the registration endpoint
echo ""
echo "🧪 Testing registration endpoint..."
TEST_BARCODE="test-fix-$(date +%s)"
if curl -s -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d "{\"barcode\": \"$TEST_BARCODE\", \"name\": \"Test Coach\", \"email\": \"test@example.com\", \"whatsapp_token\": \"test-token\", \"timezone\": \"EST\"}" | grep -q "coach_id"; then
    echo "✅ Registration endpoint working!"
    echo "   Database fix successful!"
else
    echo "❌ Registration endpoint still failing"
    echo "   Check application logs for additional errors"
fi

echo ""
echo "🎉 Manual database fix complete!"
echo ""
echo "💡 Your coaching system should now work properly!"
echo "   Try registering a coach through your application."
