# Airbnb/VRBO Hosting Automation

AI-powered hosting assistant that automatically hires humans via RentAHuman for property management tasks including cleaning, maintenance, guest communication, and more.

## Features

- **Automatic Task Generation** - Creates cleaning, restocking, and communication tasks from Airbnb/VRBO bookings
- **Intelligent Human Booking** - Automatically books the best-fit human for each task via RentAHuman API
- **Real-time Webhooks** - Receives booking status updates and handles cancellations with automatic replacement
- **Cost Optimization** - Selects cheapest option for non-urgent tasks, highest-rated for urgent/tight turnovers
- **Full Dashboard** - Web interface for managing properties, viewing tasks, and monitoring analytics
- **MCP Server** - Claude Desktop integration for AI-powered property management

## Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.11+, async)
- **Database:** PostgreSQL with async SQLAlchemy
- **Task Queue:** Celery with Redis
- **APIs:** RentAHuman, Airbnb, VRBO (mock-ready)

### Frontend
- **Framework:** Next.js 14 (React)
- **Styling:** Tailwind CSS
- **State:** TanStack Query
- **Auth:** NextAuth.js

### Infrastructure
- **Storage:** DigitalOcean Spaces (S3-compatible)
- **Container:** Docker + Docker Compose

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Development Setup

1. **Clone and setup environment**

```bash
git clone https://github.com/yourusername/airbnb-automation.git
cd airbnb-automation
cp .env.example .env
# Edit .env with your configuration
```

2. **Start services with Docker Compose**

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache
- Backend API (FastAPI)
- Celery worker
- Celery beat scheduler
- Frontend (Next.js)

3. **Seed test data**

```bash
cd backend
python scripts/seed_data.py
```

4. **Access the application**

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Manual Setup (without Docker)

**Backend:**
```bash
cd backend
pip install -e .
alembic upgrade head
uvicorn main:app --reload
```

**Celery worker:**
```bash
cd backend
celery -A celery_config worker --loglevel=info
```

**Celery beat:**
```bash
cd backend
celery -A celery_config beat --loglevel=info
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

Key environment variables (see `.env.example` for full list):

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/airbnb_automation

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Auth
JWT_SECRET_KEY=your-secret-key

# RentAHuman API
RENTAHUMAN_API_KEY=rah_xxx
RENTAHUMAN_MOCK_MODE=true  # Set to false for real API

# DigitalOcean Spaces
DO_SPACES_KEY=your-key
DO_SPACES_SECRET=your-secret
DO_SPACES_BUCKET=airbnb-automation-photos
```

## MCP Server (Claude Desktop)

The project includes an MCP server for Claude Desktop integration:

1. Copy `backend/mcp_config_example.json` to your Claude Desktop config
2. Update the Python path and project path
3. Restart Claude Desktop

Available tools:
- `search_humans` - Search for available humans
- `create_booking` - Book a human for a task
- `get_booking_status` - Check booking status
- `cancel_booking` - Cancel a booking
- `list_skills` - List available skills

## Project Structure

```
airbnb-automation/
├── backend/
│   ├── api/                 # FastAPI routes
│   ├── models/              # SQLAlchemy models
│   ├── services/            # Business logic
│   │   ├── rentahuman_client.py
│   │   ├── booking_engine.py
│   │   ├── task_generator.py
│   │   └── storage_service.py
│   ├── tasks/               # Celery tasks
│   ├── tests/               # Pytest tests
│   ├── mcp_server.py        # MCP server
│   └── main.py              # FastAPI app
├── frontend/
│   ├── app/                 # Next.js pages
│   └── lib/                 # API client, utils
└── docker-compose.yml
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Create account
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Current user

### Properties
- `GET /api/v1/properties` - List properties
- `POST /api/v1/properties` - Create property
- `GET /api/v1/properties/{id}` - Get property
- `PATCH /api/v1/properties/{id}` - Update property
- `DELETE /api/v1/properties/{id}` - Delete property

### Bookings
- `GET /api/v1/bookings` - List guest bookings
- `GET /api/v1/bookings/{id}` - Get booking details

### Tasks
- `GET /api/v1/tasks` - List tasks (filterable by status)
- `GET /api/v1/tasks/{id}` - Get task details
- `PATCH /api/v1/tasks/{id}` - Update task
- `POST /api/v1/tasks/{id}/book` - Book human for task

### Humans
- `GET /api/v1/humans/search` - Search for humans
- `GET /api/v1/humans/skills` - List available skills

### Webhooks
- `POST /api/v1/webhooks/rentahuman` - RentAHuman callbacks
- `POST /api/v1/webhooks/stripe` - Stripe payment callbacks

## Testing

```bash
cd backend
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

## Automation Flow

1. **Booking Detection** - Celery polls Airbnb/VRBO every 15 minutes
2. **Task Generation** - System creates cleaning/restocking/communication tasks
3. **Human Search** - BookingEngine searches RentAHuman for best match
4. **Booking Creation** - Creates booking with retry logic and fallback
5. **Status Tracking** - Webhooks update task status in real-time
6. **Completion** - Photos uploaded to DigitalOcean Spaces

## License

MIT

---

**Status:** Development
**Owner:** Ethan Aldrich
