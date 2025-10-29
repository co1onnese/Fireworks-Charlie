#!/bin/bash
# Database initialization script for Trainer-Charlie
# Based on Charlie-T1-DB schema

set -e

# Configuration (override with environment variables)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-trainer_charlie}"
DB_USER="${DB_USER:-charlie_user}"
DB_PASSWORD="${DB_PASSWORD:-charlie_pass}"

echo "================================================"
echo "Trainer-Charlie Database Initialization"
echo "================================================"
echo "Host: $DB_HOST:$DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "================================================"

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "ERROR: psql command not found. Please install PostgreSQL client."
    exit 1
fi

# Test database connection
echo "Testing database connection..."
export PGPASSWORD="$DB_PASSWORD"
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo "ERROR: Could not connect to database. Please check your connection settings."
    exit 1
fi
echo "✓ Database connection successful"

# Initialize schema
echo ""
echo "Initializing database schema..."
SQL_FILE="$(dirname "$0")/init_db.sql"
if [ ! -f "$SQL_FILE" ]; then
    echo "ERROR: SQL file not found at $SQL_FILE"
    exit 1
fi

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_FILE"
echo "✓ Schema initialized"

# Verify installation
echo ""
echo "Verifying installation..."
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
echo "✓ Found $TABLE_COUNT tables in database"

echo ""
echo "================================================"
echo "Database initialization completed successfully!"
echo "================================================"

unset PGPASSWORD