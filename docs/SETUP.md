# Local Development Setup

This guide covers setting up the Airbnb/VRBO Hosting Automation platform for local development.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

## Quick Start

### 1. Copy Environment File (REQUIRED FIRST STEP)

```bash
# Clone the repository
git clone <repository-url>
cd airbnb-automation

# ⚠️  REQUIRED: Copy the environment template before anything else
cp .env.example .env
# Then edit .env with your configuration (see below)
```

> **Note:** The application will not start correctly without a `.env` file.
> At minimum, set `JWT_SECRET_KEY` to a secure random value for non-development use.

### 2. Configure Environment Variables

Edit `.env` with your settings:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/airbnb_automation

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# RentAHuman API (mock mode for development)
RENTAHUMAN_API_KEY=test_key
RENTAHUMAN_MOCK_MODE=true

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start Services with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend API (port 8000)
- Celery Worker
- Celery Beat (scheduler)
- Frontend (port 3000)

### 4. Run Database Migrations

```bash
# Enter backend container
docker-compose exec backend bash

# Run migrations
alembic upgrade head

# Seed test data
python -m scripts.seed_data
```

### 5. Access the Application

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Test Credentials:**
- Email: `ethan@example.com`
- Password: `password123`

## Local Development (Without Docker)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed data
python -m scripts.seed_data

# Start server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Celery Workers

```bash
cd backend

# Start worker
celery -A main.celery_app worker --loglevel=info

# Start beat scheduler (separate terminal)
celery -A main.celery_app beat --loglevel=info
```

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_services.py -v
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage
```

## Common Issues

### Database Connection Errors

Ensure PostgreSQL is running and the DATABASE_URL is correct:
```bash
docker-compose ps  # Check if postgres is running
docker-compose logs postgres  # View postgres logs
```

### Redis Connection Errors

Ensure Redis is running:
```bash
docker-compose logs redis
```

### Celery Tasks Not Running

Check Celery worker logs:
```bash
docker-compose logs celery_worker
docker-compose logs celery_beat
```

### Frontend Can't Connect to Backend

Verify NEXT_PUBLIC_API_URL in frontend environment:
```bash
# Check backend is accessible
curl http://localhost:8000/health
```

## IDE Setup

### VS Code Extensions

Recommended extensions:
- Python
- Pylance
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- Thunder Client (API testing)

### PyCharm Setup

1. Set Python interpreter to venv
2. Mark `backend` as Sources Root
3. Configure pytest as test runner

## Development Workflow

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes
3. Run tests: `pytest` (backend) / `npm test` (frontend)
4. Run linting: `ruff check .` (backend) / `npm run lint` (frontend)
5. Commit with descriptive message
6. Create pull request

## Mock Mode

The application runs in mock mode by default for development:

- **RentAHuman API**: Returns mock human/booking data
- **Airbnb/VRBO Services**: Generate mock bookings

To test with real APIs, set:
```env
RENTAHUMAN_MOCK_MODE=false
RENTAHUMAN_API_KEY=your-real-api-key
```
