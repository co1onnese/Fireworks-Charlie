#!/bin/bash
# ============================================================================
# Fireworks-Charlie Database Setup Script
# Automated PostgreSQL database initialization
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Print banner
echo "============================================================================"
echo "  Fireworks-Charlie Database Setup"
echo "  RLVR Training Pipeline - PostgreSQL Initialization"
echo "============================================================================"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Using .env.example as template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_info "Created .env from .env.example"
        print_warning "Please edit .env with your actual configuration before continuing"
        read -p "Press Enter to continue after editing .env, or Ctrl+C to exit..."
    else
        print_error ".env.example not found!"
        exit 1
    fi
fi

# Load environment variables
print_info "Loading environment variables..."
source .env

# Set default values if not in .env
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-fireworks_charlie}"
DB_USER="${DB_USER:-fireworks_app}"
DB_PASSWORD="${DB_PASSWORD:-changeme}"

print_info "Configuration:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# Check if PostgreSQL is installed
print_info "Checking for PostgreSQL installation..."
if ! command -v psql &> /dev/null; then
    print_warning "PostgreSQL not found. Installing..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
        print_success "PostgreSQL installed"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install postgresql
        print_success "PostgreSQL installed"
    else
        print_error "Unsupported OS. Please install PostgreSQL manually."
        exit 1
    fi
else
    print_success "PostgreSQL is already installed"
    psql --version
fi

# Start PostgreSQL service
print_info "Starting PostgreSQL service..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo service postgresql start || sudo systemctl start postgresql
elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew services start postgresql || pg_ctl -D /usr/local/var/postgres start
fi
print_success "PostgreSQL service started"

# Wait for PostgreSQL to be ready
print_info "Waiting for PostgreSQL to be ready..."
sleep 2

# Create database and user as postgres superuser
print_info "Creating database and user..."

sudo -u postgres psql <<EOF 2>/dev/null || print_warning "Note: Some commands may have already been executed"
-- Drop existing database if --force flag is used
-- DROP DATABASE IF EXISTS $DB_NAME;
-- DROP ROLE IF EXISTS $DB_USER;

-- Create user
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD';
        RAISE NOTICE 'Created user: $DB_USER';
    ELSE
        RAISE NOTICE 'User already exists: $DB_USER';
    END IF;
END
\$\$;

-- Create database
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER ENCODING ''UTF8'' LC_COLLATE = ''en_US.UTF-8'' LC_CTYPE = ''en_US.UTF-8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

\c $DB_NAME

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;

EOF

print_success "Database and user created/verified"

# Run SQL initialization scripts
print_info "Initializing database schema..."

# Set PGPASSWORD for non-interactive authentication
export PGPASSWORD="$DB_PASSWORD"

# Check if database directory exists
if [ ! -d "database" ]; then
    print_error "database/ directory not found!"
    print_error "Please run this script from the Fireworks-Charlie root directory"
    exit 1
fi

# Execute SQL files in order
sql_files=(
    "01_tables.sql"
    "02_indexes.sql"
    "03_views.sql"
    "04_functions.sql"
)

for sql_file in "${sql_files[@]}"; do
    if [ -f "database/$sql_file" ]; then
        print_info "Executing: $sql_file"
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "database/$sql_file" -q
        if [ $? -eq 0 ]; then
            print_success "✓ $sql_file executed successfully"
        else
            print_error "✗ Failed to execute $sql_file"
            exit 1
        fi
    else
        print_error "SQL file not found: database/$sql_file"
        exit 1
    fi
done

# Unset PGPASSWORD for security
unset PGPASSWORD

print_success "Database schema initialized successfully!"

# Run health check
print_info "Running database health check..."
export PGPASSWORD="$DB_PASSWORD"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT * FROM database_health_check();" -q
unset PGPASSWORD

# Display summary
echo ""
echo "============================================================================"
print_success "Database Setup Complete!"
echo "============================================================================"
echo ""
echo "Database Details:"
echo "  • Database: $DB_NAME"
echo "  • User: $DB_USER"
echo "  • Host: $DB_HOST"
echo "  • Port: $DB_PORT"
echo ""
echo "Connection String:"
echo "  postgresql://$DB_USER:****@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""
echo "Database Contents:"
echo "  • 14 Tables created"
echo "  • 60+ Indexes created"
echo "  • 7 Views + 2 Materialized Views"
echo "  • 9 Functions/Procedures"
echo ""
echo "Next Steps:"
echo "  1. Update .env with actual API keys"
echo "  2. Run data collection: python main.py --tickers AAPL,MSFT"
echo "  3. Generate RLVR datasets: python rlvr_main.py --mode generate"
echo ""
echo "Useful Commands:"
echo "  • Connect to DB: psql -h $DB_HOST -U $DB_USER -d $DB_NAME"
echo "  • Health check: SELECT * FROM database_health_check();"
echo "  • Refresh views: SELECT refresh_all_materialized_views();"
echo ""
print_success "Ready for RLVR training pipeline!"
echo "============================================================================"
