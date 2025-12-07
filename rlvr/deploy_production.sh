#!/bin/bash

# Fireworks-Charlie Evalprotocol Server Production Deployment Script
# 
# This script handles production deployment of the evalprotocol server
# with proper environment validation, health checks, and rollback capabilities.
#
# Usage:
#   ./deploy_production.sh [--env-file .env.prod] [--skip-checks] [--rollback]
#
# Author: Fireworks-Charlie Team
# Date: 2025-12-07

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${SCRIPT_DIR}/.env"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.evalprotocol.yml"
BACKUP_DIR="${SCRIPT_DIR}/backups"
LOG_FILE="${SCRIPT_DIR}/deploy.log"

# Docker Compose command detection (handles both legacy and modern formats)
DOCKER_COMPOSE_CMD=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Parse command line arguments
SKIP_CHECKS=false
ROLLBACK=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --skip-checks)
            SKIP_CHECKS=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--env-file .env.prod] [--skip-checks] [--rollback]"
            echo ""
            echo "Options:"
            echo "  --env-file FILE    Use specific environment file (default: .env)"
            echo "  --skip-checks      Skip pre-deployment validation checks"
            echo "  --rollback         Rollback to previous deployment"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create necessary directories
mkdir -p "$BACKUP_DIR" "${SCRIPT_DIR}/logs"

log "🚀 Starting Fireworks-Charlie Evalprotocol Server Production Deployment"
log "📁 Project root: $PROJECT_ROOT"
log "📄 Environment file: $ENV_FILE"
log "🐳 Compose file: $COMPOSE_FILE"

# Check if environment file exists
if [[ ! -f "$ENV_FILE" ]]; then
    error "Environment file not found: $ENV_FILE"
    error "Please copy .env.example to $ENV_FILE and configure your settings"
    exit 1
fi

# Source environment variables
set -a
source "$ENV_FILE"
set +a

# Docker Compose detection function
detect_docker_compose_command() {
    log "🔍 Detecting Docker Compose installation..."

    # Try modern Docker Compose plugin first (docker compose)
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
        local version=$(docker compose version --short 2>/dev/null || docker compose version | head -n1 | awk '{print $NF}')
        success "✅ Found Docker Compose plugin: $version"
        return 0
    fi

    # Try legacy standalone Docker Compose (docker-compose)
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
        local version=$(docker-compose version --short 2>/dev/null || docker-compose --version | awk '{print $3}' | sed 's/,//')
        success "✅ Found Docker Compose standalone: $version"
        return 0
    fi

    # Neither found
    error "Docker Compose is not installed or not in PATH"
    error "Please install Docker Compose:"
    error "  - Modern plugin: https://docs.docker.com/compose/install/"
    error "  - Legacy standalone: https://docs.docker.com/compose/install/standalone/"
    return 1
}

# Validation function
validate_environment() {
    log "🔍 Validating environment configuration..."
    
    local required_vars=(
        "FIREWORKS_API_KEY"
        "POSTGRES_PASSWORD"
        "DB_NAME"
        "DB_USER"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            error "  - $var"
        done
        error "Please configure these variables in $ENV_FILE"
        exit 1
    fi
    
    success "✅ Environment validation passed"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "🔍 Running pre-deployment checks..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        error "Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi

    local docker_version=$(docker --version | awk '{print $3}' | sed 's/,//')
    success "✅ Found Docker: $docker_version"
    
    # Check if ports are available
    local ports=("${SERVER_PORT:-8000}" "${POSTGRES_PORT:-5432}" "${REDIS_PORT:-6379}")
    for port in "${ports[@]}"; do
        if netstat -tuln | grep -q ":$port "; then
            warning "Port $port is already in use"
        fi
    done



    # Check disk space (require at least 2GB free)
    local available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    local required_space=2097152  # 2GB in KB
    
    if [[ $available_space -lt $required_space ]]; then
        error "Insufficient disk space. Required: 2GB, Available: $((available_space/1024/1024))GB"
        exit 1
    fi
    
    success "✅ Pre-deployment checks passed"
}

# Backup current deployment
backup_current_deployment() {
    log "💾 Creating backup of current deployment..."
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="${BACKUP_DIR}/backup_${backup_timestamp}"
    
    mkdir -p "$backup_path"
    
    # Backup database if running
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps postgres | grep -q "Up"; then
        log "📊 Backing up database..."
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres pg_dump -U postgres fireworks_charlie > "${backup_path}/database.sql"
    fi
    
    # Backup configuration
    cp "$ENV_FILE" "${backup_path}/"
    cp "$COMPOSE_FILE" "${backup_path}/"
    
    # Store backup path for potential rollback
    echo "$backup_path" > "${BACKUP_DIR}/latest_backup"
    
    success "✅ Backup created: $backup_path"
}

# Deploy function
deploy() {
    log "🚀 Starting deployment..."

    # Pull latest images
    log "📥 Pulling latest Docker images..."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" pull

    # Build evalprotocol server image
    log "🔨 Building evalprotocol server image..."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" build evalprotocol-server

    # Start services with production profile
    log "🏃 Starting services..."
    if [[ "${NGINX_ENABLED:-false}" == "true" ]]; then
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" --profile production up -d
    else
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d
    fi

    success "✅ Services started"
}

# Health check function
health_check() {
    log "🏥 Performing health checks..."

    local max_attempts=30
    local attempt=1
    local server_url="http://localhost:${SERVER_PORT:-8000}"

    while [[ $attempt -le $max_attempts ]]; do
        log "🔍 Health check attempt $attempt/$max_attempts..."

        if curl -f -s "$server_url/health" > /dev/null; then
            success "✅ Server is healthy!"
            return 0
        fi

        sleep 10
        ((attempt++))
    done

    error "❌ Health check failed after $max_attempts attempts"
    return 1
}

# Rollback function
rollback() {
    log "🔄 Rolling back to previous deployment..."

    if [[ ! -f "${BACKUP_DIR}/latest_backup" ]]; then
        error "No backup found for rollback"
        exit 1
    fi

    local backup_path=$(cat "${BACKUP_DIR}/latest_backup")

    if [[ ! -d "$backup_path" ]]; then
        error "Backup directory not found: $backup_path"
        exit 1
    fi

    # Stop current services
    log "⏹️  Stopping current services..."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" down

    # Restore configuration
    log "📄 Restoring configuration..."
    cp "${backup_path}/.env" "$ENV_FILE"
    cp "${backup_path}/docker-compose.evalprotocol.yml" "$COMPOSE_FILE"

    # Restore database
    if [[ -f "${backup_path}/database.sql" ]]; then
        log "📊 Restoring database..."
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d postgres
        sleep 10
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d fireworks_charlie < "${backup_path}/database.sql"
    fi

    # Start services
    log "🏃 Starting restored services..."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d

    success "✅ Rollback completed"
}

# Cleanup function
cleanup() {
    log "🧹 Cleaning up..."

    # Remove old images
    docker image prune -f

    # Remove old backups (keep last 5)
    find "$BACKUP_DIR" -name "backup_*" -type d | sort -r | tail -n +6 | xargs rm -rf

    success "✅ Cleanup completed"
}

# Main execution
main() {
    if [[ "$ROLLBACK" == "true" ]]; then
        # Detect Docker Compose for rollback operations
        if ! detect_docker_compose_command; then
            exit 1
        fi
        rollback
        exit 0
    fi

    # Detect Docker Compose command early
    if ! detect_docker_compose_command; then
        exit 1
    fi

    # Run validation and checks
    validate_environment

    if [[ "$SKIP_CHECKS" != "true" ]]; then
        pre_deployment_checks
    fi

    # Create backup
    backup_current_deployment

    # Deploy
    deploy

    # Health check
    if ! health_check; then
        error "❌ Deployment failed health check. Rolling back..."
        rollback
        exit 1
    fi

    # Cleanup
    cleanup

    success "🎉 Deployment completed successfully!"
    log "📊 Server is running at: http://localhost:${SERVER_PORT:-8000}"
    log "🏥 Health check: http://localhost:${SERVER_PORT:-8000}/health"
    log "📋 Logs: $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE logs -f"
    log "⏹️  Stop: $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE down"
}

# Make script executable and run
chmod +x "$0"
main "$@"
