#!/bin/bash

# Database Troubleshooting Script for Production
# Run this script in your Coolify environment to diagnose and fix database issues

echo "🔍 Coaching System Database Troubleshooter"
echo "=========================================="

# Check if we're running in Coolify/Docker environment
if [ -z "$DB_PASSWORD" ]; then
    echo "❌ Error: DB_PASSWORD environment variable not set"
    echo "   Make sure you're running this in the correct Docker container"
    exit 1
fi

echo "✅ Environment variables found"

# Test database connection
echo ""
echo "🔗 Testing database connection..."
if PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -c "SELECT 'Database connection successful' as status;" 2>/dev/null; then
    echo "✅ Database connection works"
else
    echo "❌ Database connection failed"
    echo "   Check PostgreSQL container is running and environment variables are correct"
    exit 1
fi

# Check if coaches table exists
echo ""
echo "📋 Checking database tables..."
COACHES_EXISTS=$(PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -t -c "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'coaches');" 2>/dev/null | tr -d ' ')

if [ "$COACHES_EXISTS" = "t" ]; then
    echo "✅ Coaches table exists"

    # Count records in coaches table
    COACH_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -t -c "SELECT COUNT(*) FROM coaches;" 2>/dev/null | tr -d ' ')
    echo "   📊 Coaches in database: $COACH_COUNT"

else
    echo "❌ Coaches table does NOT exist"
    echo ""
    echo "🔧 Attempting to create missing tables..."

    # Run the init script manually
    if PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -f /app/database/init.sql 2>/dev/null; then
        echo "✅ Database tables created successfully"

        # Verify tables were created
        TABLES=$(PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -t -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;" 2>/dev/null)
        echo "   📋 Created tables:"
        echo "$TABLES" | while read -r table; do
            if [ -n "$table" ]; then
                echo "      - $table"
            fi
        done

    else
        echo "❌ Failed to create database tables"
        echo "   Check database permissions and init.sql file"
        exit 1
    fi
fi

# List all tables and their record counts
echo ""
echo "📊 Database Status:"
TABLES=$(PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -t -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;" 2>/dev/null)

echo "$TABLES" | while read -r table; do
    if [ -n "$table" ]; then
        COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h postgres -U postgres -d coaching_system -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | tr -d ' ')
        echo "   $table: $COUNT records"
    fi
done

# Test the registration endpoint
echo ""
echo "🧪 Testing registration endpoint..."
if curl -s -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"barcode": "test-troubleshoot-'$(date +%s)'", "name": "Troubleshoot Coach", "email": "troubleshoot@test.com", "whatsapp_token": "test-token", "timezone": "EST"}' | grep -q "coach_id"; then
    echo "✅ Registration endpoint working"
else
    echo "❌ Registration endpoint failed"
    echo "   Check application logs for detailed error information"
fi

echo ""
echo "🎉 Database troubleshooting complete!"
echo ""
echo "💡 If issues persist:"
echo "   1. Check Coolify application logs"
echo "   2. Verify all environment variables are set"
echo "   3. Ensure PostgreSQL container has proper permissions"
echo "   4. Try redeploying the application"
