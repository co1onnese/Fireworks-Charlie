#!/bin/bash
# Script to drop and recreate the Trainer-Charlie database

set -e

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_NAME="${DB_NAME:-trainer_charlie}"
DB_USER="${DB_USER:-charlie_user}"
DB_PASSWORD="${DB_PASSWORD:-charlie_password}"

echo "================================================"
echo "Trainer-Charlie Database Reset"
echo "================================================"
echo "WARNING: This will drop the database and all data!"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "================================================"

# Ask for confirmation
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "Dropping existing database..."
sudo -u postgres psql <<EOF
DROP DATABASE IF EXISTS $DB_NAME;
EOF

echo "Creating new database..."
sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo "Granting permissions..."
sudo -u postgres psql -d $DB_NAME <<EOF
GRANT CREATE ON SCHEMA public TO $DB_USER;
GRANT ALL ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF

echo ""
echo "✓ Database reset complete!"
echo ""
echo "The database schema will be automatically created when you run the pipeline."
echo ""