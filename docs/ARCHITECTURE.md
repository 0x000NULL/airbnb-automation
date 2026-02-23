# System Architecture

This document describes the architecture of the Airbnb/VRBO Hosting Automation platform.

## Overview

The platform automates property management tasks for short-term rental hosts by:
1. Syncing bookings from Airbnb and VRBO
2. Automatically generating tasks (cleaning, maintenance, check-in/out)
3. Booking humans via RentAHuman to complete tasks
4. Learning preferences to optimize future bookings

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (Next.js)                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Dashboard  │ │ Properties  │ │  Bookings   │ │    Tasks    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Backend API (FastAPI)                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │    Auth     │ │  Properties │ │  Bookings   │ │    Tasks    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                            │
│  │   Humans    │ │  Analytics  │ │ Notifications│                            │
│  └─────────────┘ └─────────────┘ └─────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐
│   PostgreSQL    │  │      Redis      │  │         Celery Workers          │
│   (Database)    │  │ (Cache/Broker)  │  │  ┌───────────┐ ┌───────────┐   │
│                 │  │                 │  │  │  Polling  │ │  Booking  │   │
│  ┌───────────┐  │  │  ┌───────────┐  │  │  │   Tasks   │ │Automation │   │
│  │   Users   │  │  │  │  Sessions │  │  │  └───────────┘ └───────────┘   │
│  ├───────────┤  │  │  ├───────────┤  │  │  ┌───────────┐ ┌───────────┐   │
│  │Properties │  │  │  │Task Queue │  │  │  │   Task    │ │  Status   │   │
│  ├───────────┤  │  │  ├───────────┤  │  │  │Generation │ │  Checks   │   │
│  │ Bookings  │  │  │  │   Cache   │  │  │  └───────────┘ └───────────┘   │
│  ├───────────┤  │  │  └───────────┘  │  └─────────────────────────────────┘
│  │   Tasks   │  │  │                 │
│  └───────────┘  │  │                 │
└─────────────────┘  └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          External Services                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  RentAHuman API │  │   Airbnb API    │  │    VRBO API     │              │
│  │  (Task Booking) │  │ (Booking Sync)  │  │ (Booking Sync)  │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### Frontend (Next.js 14)

**Technology Stack:**
- Next.js 14 with App Router
- React 18 with TypeScript
- TanStack Query for data fetching
- Tailwind CSS for styling
- next-auth for authentication

**Key Features:**
- Server-side rendering for initial page loads
- Client-side navigation with React Query caching
- Responsive design for desktop and mobile
- Real-time notifications via WebSocket

**Directory Structure:**
```
frontend/
├── app/                    # Next.js App Router pages
│   ├── auth/              # Login, register, callbacks
│   ├── dashboard/         # Protected dashboard routes
│   │   ├── properties/    # Property management
│   │   ├── bookings/      # Booking calendar/list
│   │   ├── tasks/         # Task management
│   │   ├── humans/        # Human search/booking
│   │   ├── analytics/     # Analytics dashboard
│   │   └── settings/      # User settings
│   └── layout.tsx         # Root layout
├── components/            # Reusable React components
├── lib/                   # Utilities, API client
└── styles/               # Global styles
```

### Backend API (FastAPI)

**Technology Stack:**
- FastAPI with async support
- SQLAlchemy 2.0 (async ORM)
- Pydantic for validation
- python-jose for JWT auth
- Alembic for migrations

**Directory Structure:**
```
backend/
├── api/                   # API route handlers
│   ├── auth.py           # Authentication endpoints
│   ├── properties.py     # Property CRUD
│   ├── bookings.py       # Booking management
│   ├── tasks.py          # Task management
│   ├── humans.py         # RentAHuman integration
│   ├── analytics.py      # Analytics endpoints
│   └── notifications.py  # Notification endpoints
├── models/               # SQLAlchemy models
│   ├── user.py          # User model
│   ├── property.py      # Property model
│   ├── booking.py       # Booking model
│   └── task.py          # Task model
├── services/             # Business logic
│   ├── rentahuman_client.py  # RentAHuman API client
│   ├── airbnb_service.py     # Airbnb integration
│   ├── vrbo_service.py       # VRBO integration
│   ├── booking_engine.py     # Booking automation
│   ├── optimizer.py          # Cost optimization
│   └── preference_learner.py # Human preference learning
├── tasks/                # Celery tasks
│   ├── booking_sync.py       # Sync bookings from platforms
│   ├── task_generation.py    # Generate tasks from bookings
│   ├── booking_automation.py # Auto-book humans
│   └── status_check.py       # Check task status
├── alembic/              # Database migrations
├── main.py               # Application entry point
└── mcp_server.py         # MCP server for Claude Desktop
```

### Database (PostgreSQL)

**Schema Overview:**

```
┌─────────────────┐       ┌─────────────────┐
│      users      │       │   properties    │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ email           │───┐   │ host_id (FK)    │──┐
│ hashed_password │   │   │ name            │  │
│ name            │   │   │ location (JSON) │  │
│ google_id       │   └──►│ property_type   │  │
│ created_at      │       │ bedrooms        │  │
└─────────────────┘       │ bathrooms       │  │
                          │ max_guests      │  │
                          │ cleaning_budget │  │
                          │ airbnb_enabled  │  │
                          │ vrbo_enabled    │  │
                          └─────────────────┘  │
                                    │          │
                                    ▼          │
┌─────────────────┐       ┌─────────────────┐  │
│    bookings     │       │      tasks      │  │
├─────────────────┤       ├─────────────────┤  │
│ id (PK)         │       │ id (PK)         │  │
│ property_id(FK) │◄──────│ property_id(FK) │◄─┘
│ guest_name      │       │ booking_id (FK) │──┐
│ checkin_date    │       │ type            │  │
│ checkout_date   │       │ status          │  │
│ total_price     │◄──────│ description     │  │
│ source          │   │   │ scheduled_date  │  │
│ external_id     │   │   │ budget          │  │
│ status          │   │   │ assigned_human  │  │
└─────────────────┘   │   │ (JSON)          │  │
                      │   └─────────────────┘  │
                      │                        │
                      └────────────────────────┘
```

### Background Workers (Celery)

**Scheduled Tasks:**

| Task | Schedule | Description |
|------|----------|-------------|
| `sync_airbnb_bookings` | Every 15 min | Poll Airbnb for new bookings |
| `sync_vrbo_bookings` | Every 15 min | Poll VRBO for new bookings |
| `generate_tasks` | Every 30 min | Create tasks from new bookings |
| `auto_book_humans` | Every 5 min | Book humans for pending tasks |
| `check_task_status` | Every 10 min | Update task status from RentAHuman |

**Task Flow:**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Booking Sync   │───►│ Task Generation │───►│ Human Booking   │
│                 │    │                 │    │                 │
│ Poll Airbnb/    │    │ Create cleaning │    │ Search humans   │
│ VRBO APIs       │    │ maintenance,    │    │ Book best match │
│                 │    │ check-in tasks  │    │ Update task     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Bookings     │    │     Tasks       │    │  Assigned Human │
│     Table       │    │     Table       │    │   (in Task)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Caching (Redis)

**Cache Strategy:**

| Key Pattern | TTL | Purpose |
|-------------|-----|---------|
| `session:{user_id}` | 24h | User session data |
| `properties:{user_id}` | 5m | Property list cache |
| `bookings:{property_id}` | 5m | Booking list cache |
| `humans:search:{hash}` | 15m | Human search results |
| `analytics:{user_id}` | 1h | Analytics summary |

---

## Data Flow

### Booking Sync Flow

```
1. Celery Beat triggers sync_airbnb_bookings task
2. Task calls AirbnbService.get_bookings()
3. For each booking:
   a. Check if booking exists (by external_id)
   b. If new: create booking record
   c. If changed: update booking record
   d. If cancelled: mark as cancelled
4. Emit notification for new bookings
5. Trigger task generation for new bookings
```

### Task Generation Flow

```
1. New booking created (or booking sync completes)
2. Task generation triggered
3. For each booking without tasks:
   a. Create cleaning task (checkout time)
   b. Create check-in task if needed
   c. Create check-out task if needed
   d. Set task budget from property settings
   e. Set required skills from property settings
4. Tasks saved with status=PENDING
```

### Human Booking Flow

```
1. Task in PENDING status detected
2. Preference learner queried for recommended humans
3. RentAHuman API searched with:
   - Location (from property)
   - Required skills (from task)
   - Budget (from task)
   - Date/time (from task)
4. Best match selected (rating, price, availability)
5. Booking created via RentAHuman API
6. Task updated with assigned_human
7. Task status changed to BOOKED
```

### Retry & Fallback Logic

```
┌─────────────────┐
│  Search Humans  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     No      ┌─────────────────┐
│  Found Match?   │────────────►│ Expand Search   │
└────────┬────────┘             │ +20% budget     │
         │ Yes                  │ -0.5 min rating │
         ▼                      └────────┬────────┘
┌─────────────────┐                      │
│  Create Booking │◄─────────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐     No      ┌─────────────────┐
│  Booking OK?    │────────────►│ Retry (3x max)  │
└────────┬────────┘             │ Exp. backoff    │
         │ Yes                  └────────┬────────┘
         ▼                               │
┌─────────────────┐                      │
│ Update Task     │◄─────────────────────┘
│ Status = BOOKED │
└─────────────────┘
```

---

## Intelligence Layer

### Cost Optimizer

The cost optimizer analyzes historical task data to suggest budget optimizations:

```python
# backend/services/optimizer.py

class CostOptimizer:
    def analyze_property_costs(property_id, days_back=90):
        """
        Analyzes completed tasks to find:
        - Average cost per task type
        - Suggested budget (5% below average)
        - Potential savings
        - Confidence based on sample size
        """

    def find_bulk_opportunities(host_id, days_ahead=14):
        """
        Finds dates with multiple tasks that could be bundled:
        - 2+ tasks on same day = 10-15% potential savings
        - Same task type = can use same human
        """
```

### Preference Learner

The preference learner tracks human performance to improve future bookings:

```python
# backend/services/preference_learner.py

class PreferenceLearner:
    def get_human_performance(host_id, days_back=90):
        """
        Calculates per-human metrics:
        - Total/completed tasks
        - Completion rate
        - Average rating
        - Preferred task types
        """

    def get_property_human_matches(property_id):
        """
        Scores humans for property compatibility:
        - 40%: Success rate
        - 40%: Average rating
        - 20%: Experience with property
        """

    def get_recommended_humans(host_id, task_type, property_id):
        """
        Returns ranked list of recommended human IDs
        prioritizing property matches, then host-wide performance
        """
```

---

## MCP Integration

The platform includes an MCP (Model Context Protocol) server for Claude Desktop integration:

```python
# backend/mcp_server.py

@server.tool("search_humans")
async def search_humans(location: str, skill: str, date: str):
    """Search for available humans"""

@server.tool("create_booking")
async def create_booking(human_id: str, task_id: str):
    """Book a human for a task"""

@server.tool("get_booking_status")
async def get_booking_status(booking_id: str):
    """Check booking status"""

@server.tool("list_skills")
async def list_skills():
    """Get available skills"""

@server.tool("cancel_booking")
async def cancel_booking(booking_id: str, reason: str):
    """Cancel a booking"""
```

**Claude Desktop Configuration:**

```json
{
  "mcpServers": {
    "airbnb-automation": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/backend",
      "env": {
        "RENTAHUMAN_API_KEY": "your-api-key"
      }
    }
  }
}
```

---

## Security

### Authentication Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Client  │───►│  Login   │───►│  Verify  │
│          │    │ Endpoint │    │ Password │
└──────────┘    └──────────┘    └────┬─────┘
                                     │
                                     ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ API Call │◄───│   JWT    │◄───│  Create  │
│ + Bearer │    │  Token   │    │   JWT    │
└──────────┘    └──────────┘    └──────────┘
```

**JWT Token Structure:**
```json
{
  "sub": "user-uuid",
  "exp": 1706789400,
  "iat": 1706703000,
  "type": "access"
}
```

### Authorization

- All API endpoints require authentication (except /auth/*)
- Users can only access their own properties/bookings/tasks
- Property ownership verified on every request
- Task access verified through property ownership chain

---

## Deployment Architecture

### Single Server (Docker Compose)

```
┌─────────────────────────────────────────────┐
│                   Nginx                      │
│              (SSL Termination)               │
│                Port 80/443                   │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│   Frontend    │   │   Backend     │
│   Port 3000   │   │   Port 8000   │
└───────────────┘   └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  PostgreSQL   │   │    Redis      │   │    Celery     │
│   Port 5432   │   │   Port 6379   │   │   Workers     │
└───────────────┘   └───────────────┘   └───────────────┘
```

### Kubernetes (High Availability)

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────┐
│                    Ingress                               │
│              (TLS, routing rules)                        │
└─────────────────────────┬───────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Frontend    │ │   Backend     │ │   Backend     │
│   Pod (3x)    │ │   Pod (3x)    │ │   Pod (3x)    │
└───────────────┘ └───────────────┘ └───────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  PostgreSQL   │ │    Redis      │ │    Celery     │
│   (Managed)   │ │  (Managed)    │ │   Pods (5x)   │
└───────────────┘ └───────────────┘ └───────────────┘
```

---

## Performance Considerations

### Database Optimization

- **Indexes**: All foreign keys indexed, composite indexes on common queries
- **Connection pooling**: SQLAlchemy async pool with 20 connections
- **Query optimization**: Use eager loading, avoid N+1 queries

### Caching Strategy

- **Redis caching**: Frequently accessed data cached with appropriate TTL
- **Query result caching**: Complex analytics queries cached for 1 hour
- **Invalidation**: Cache invalidated on relevant data changes

### API Performance

- **Async everywhere**: All I/O operations are async
- **Pagination**: All list endpoints paginated (default 100 items)
- **Response compression**: Gzip enabled for responses > 1KB

### Background Processing

- **Task queues**: Celery with Redis broker handles all background work
- **Concurrency**: 4 workers per Celery instance
- **Rate limiting**: External API calls rate-limited to prevent throttling

---

## Error Handling

### API Errors

All errors return consistent JSON structure:
```json
{
  "detail": "Error message",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-01-20T10:30:00Z"
}
```

### Background Task Errors

- Failed tasks logged with full traceback
- Automatic retry with exponential backoff (3 attempts)
- Dead letter queue for manual inspection
- Alert notification on repeated failures

### External Service Errors

- RentAHuman API: Retry with backoff, fallback to expanded search
- Airbnb/VRBO: Log error, skip booking, retry on next sync
- All external calls have timeout (30s default)
