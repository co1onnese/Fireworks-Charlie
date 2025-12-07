# Evalprotocol Stock Prediction Evaluator

This directory contains the new evalprotocol-compatible reward function server for the Fireworks-Charlie RLVR training pipeline.

## Overview

The evalprotocol server replaces the old reward-kit based system with a modern HTTP API that evaluates stock predictions against actual 3-day performance data.

### Key Features

- **HTTP API**: Implements evalprotocol `/init` endpoint specification
- **Ground Truth Evaluation**: Evaluates predictions against actual stock price movements
- **Multi-Metric Scoring**: Uses the existing sophisticated reward calculation system
- **3-Day Performance Tracking**: Measures actual returns over 3 trading days
- **Fireworks Tracing**: Integrated logging for rollout completion signaling

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Evalprotocol  │───▶│  FastAPI Server  │───▶│   Database      │
│   Client        │    │  (Port 8000)     │    │   (PostgreSQL)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Position        │
                       │  Tracker         │
                       │  (3-day eval)    │
                       └──────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r rlvr/requirements_evalprotocol.txt
```

### 2. Run the Server

```bash
python rlvr/run_evalprotocol_server.py
```

The server will start on `http://localhost:8000`

### 3. Test the Server

```bash
curl http://localhost:8000/health
```

## Development Setup

### Using Docker Compose

```bash
cd rlvr
docker-compose -f docker-compose.evalprotocol.yml up
```

This will start:
- Evalprotocol server on port 8000
- PostgreSQL database on port 5432
- Redis cache on port 6379

### Manual Setup

1. **Database Setup**: Ensure PostgreSQL is running with the Fireworks-Charlie schema
2. **Environment Variables**: Set database connection variables
3. **Run Server**: Use the development runner script

```bash
# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/fireworks_charlie"

# Run with auto-reload for development
python rlvr/run_evalprotocol_server.py --reload --log-level debug
```

## API Endpoints

### POST /init

Evalprotocol endpoint for stock prediction evaluation.

**Request Body** (InitRequest):
```json
{
  "completion_params": {...},
  "messages": [...],
  "tools": [...],
  "model_base_url": "...",
  "metadata": {
    "rollout_id": "unique-id"
  },
  "api_key": "..."
}
```

**Response**:
```json
{
  "status": "success",
  "rollout_id": "unique-id",
  "evaluation": {
    "score": 0.85,
    "reason": "R:0.850 | Dir:✓ | Mag:0.92 | Sharpe:0.65 | Cal:0.80 | buy→+2.3%",
    "metrics": {...},
    "actual_return_pct": 2.3
  }
}
```

### GET /health

Health check endpoint.

## Configuration

The server can be configured via environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `LOG_LEVEL`: Logging level (debug, info, warning, error)
- `SERVER_HOST`: Host to bind to (default: 0.0.0.0)
- `SERVER_PORT`: Port to bind to (default: 8000)

## 🚀 Fireworks RFT Integration

### Creating RFT Jobs

Use the RFT manager to create and manage Fireworks RFT training jobs:

```bash
# Create a new RFT job
python rlvr/rft_manager.py create \
    --dataset-path storage/rlvr_datasets/train.jsonl \
    --validation-dataset-path storage/rlvr_datasets/val.jsonl \
    --job-name "fireworks_charlie_v2" \
    --epochs 3 \
    --learning-rate 1e-4

# Monitor job progress
python rlvr/rft_manager.py monitor --job-id your-job-id --follow

# List all jobs
python rlvr/rft_manager.py list

# Cancel a job
python rlvr/rft_manager.py cancel --job-id your-job-id
```

### Environment Variables for RFT

```bash
# Required for RFT integration
export FIREWORKS_API_KEY="your_fireworks_api_key"
export FIREWORKS_ACCOUNT_ID="your_account_id"
export EVALPROTOCOL_SERVER_URL="http://localhost:8000"
```

### RFT Job Configuration

The evalprotocol server automatically handles:
- **Metadata Correlation**: All rollout metadata (invocation_id, experiment_id, rollout_id, run_id, row_id) is properly tracked
- **Fireworks Tracing**: Model calls are traced through Fireworks logging infrastructure
- **Status Reporting**: Rollout completion and error status is reported back to Fireworks
- **Error Handling**: Comprehensive retry logic and timeout management

### Monitoring RFT Jobs

```bash
# Real-time monitoring with detailed metrics
python rlvr/rft_manager.py monitor --job-id your-job-id --follow

# Check server health during training
curl http://localhost:8000/health

# View server logs
docker-compose -f rlvr/docker-compose.evalprotocol.yml logs -f evalprotocol-server
```

## 🧪 Testing

### Unit Tests
```bash
# Run all tests
python rlvr/run_tests.py

# Run specific test file
python -m pytest rlvr/tests/test_evalprotocol_server.py -v

# Run with coverage
python -m pytest rlvr/tests/ --cov=rlvr --cov-report=html
```

### RFT Integration Tests
```bash
# Start server first
python rlvr/run_evalprotocol_server.py &

# Run comprehensive RFT integration tests
python rlvr/tests/test_rft_integration.py

# Or use pytest
python -m pytest rlvr/tests/test_rft_integration.py -v
```

### Integration Tests
```bash
# Start server first
python rlvr/run_evalprotocol_server.py &

# Run integration tests
python -m pytest rlvr/tests/test_evalprotocol_server.py::TestEvalprotocolIntegration -v
```

## 🚀 Production Deployment

### Quick Production Setup

```bash
# Copy environment configuration
cp rlvr/.env.example rlvr/.env

# Edit configuration (set your API keys, passwords, etc.)
nano rlvr/.env

# Deploy with production script
./rlvr/deploy_production.sh
```

### Manual Production Deployment

For production deployment, use the enhanced Docker setup:

```bash
# Production deployment with all services
docker-compose -f rlvr/docker-compose.evalprotocol.yml --profile production up -d

# Or deploy with Gunicorn
gunicorn rlvr.evalprotocol_server:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Production Features

- **Health Checks**: Automatic container health monitoring
- **Resource Limits**: Memory and CPU constraints for stability
- **Logging**: Structured logging with log rotation
- **Backup**: Automated database backups
- **Monitoring**: Metrics collection and alerting
- **SSL/TLS**: Nginx reverse proxy with SSL support
- **Scaling**: Horizontal scaling with load balancing

### Environment Configuration

See `rlvr/.env.example` for complete configuration options including:
- Database settings and connection pooling
- Fireworks API credentials
- Performance tuning parameters
- Security and CORS settings
- Monitoring and alerting configuration
