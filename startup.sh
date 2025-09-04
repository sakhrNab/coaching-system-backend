#!/bin/bash
set -e

echo "🚀 Starting Coaching System Backend..."

# Run database migrations
echo "📊 Running database migrations..."
python migration_manager.py

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migrations failed"
    exit 1
fi

# Start the application
echo "🏃 Starting FastAPI application..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
