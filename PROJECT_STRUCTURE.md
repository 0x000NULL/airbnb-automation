# Project Structure

```
airbnb-automation/
├── README.md                          # Project overview
├── PLAN.md                            # Detailed 8-week development plan
├── PROJECT_STRUCTURE.md               # This file
├── .gitignore
├── pyproject.toml                     # Python dependencies
├── docker-compose.yml                 # Local development environment
│
├── backend/
│   ├── main.py                        # FastAPI app entry point
│   ├── requirements.txt
│   ├── config.py                      # Settings & config
│   ├── database.py                    # PostgreSQL setup
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py                    # Authentication endpoints
│   │   ├── properties.py              # Property management
│   │   ├── bookings.py                # Airbnb/VRBO booking data
│   │   ├── tasks.py                   # Task generation & management
│   │   ├── humans.py                  # RentAHuman integration
│   │   ├── config.py                  # Host automation settings
│   │   └── analytics.py               # Analytics & reporting
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── airbnb_service.py          # Airbnb API integration
│   │   ├── vrbo_service.py            # VRBO API integration
│   │   ├── rentahuman_client.py       # RentAHuman MCP client
│   │   ├── task_generator.py          # Auto-generate tasks
│   │   ├── booking_engine.py          # Match tasks to humans
│   │   ├── notification_service.py    # Email/SMS notifications
│   │   └── payment_service.py         # Stripe/RentAHuman payments
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── property.py                # Property model
│   │   ├── booking.py                 # Airbnb booking model
│   │   ├── task.py                    # Task model
│   │   ├── human.py                   # Human profile model
│   │   └── config.py                  # Automation config model
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── polling.py                 # Celery: Poll Airbnb for new bookings
│   │   ├── task_generation.py         # Celery: Generate tasks from bookings
│   │   ├── booking_automation.py      # Celery: Auto-book humans
│   │   ├── status_check.py            # Celery: Check booking status
│   │   └── notifications.py           # Celery: Send notifications
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_api.py
│       ├── test_services.py
│       ├── test_task_generator.py
│       └── test_rentahuman_client.py
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   │
│   ├── app/
│   │   ├── layout.tsx                 # Root layout
│   │   ├── page.tsx                   # Home page
│   │   ├── dashboard/
│   │   │   ├── page.tsx               # Main dashboard
│   │   │   ├── properties.tsx         # Property management
│   │   │   ├── bookings.tsx           # Booking calendar
│   │   │   ├── tasks.tsx              # Task queue
│   │   │   ├── humans.tsx             # Human assignments
│   │   │   ├── analytics.tsx          # Analytics dashboard
│   │   │   └── settings.tsx           # Automation settings
│   │   ├── auth/
│   │   │   ├── login.tsx
│   │   │   ├── signup.tsx
│   │   │   └── oauth-callback.tsx
│   │   └── api/
│   │       └── [...].ts               # API route handlers
│   │
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   ├── PropertyCard.tsx
│   │   ├── BookingCalendar.tsx
│   │   ├── TaskQueue.tsx
│   │   ├── HumanProfile.tsx
│   │   ├── AnalyticsChart.tsx
│   │   └── NotificationBell.tsx
│   │
│   ├── lib/
│   │   ├── api.ts                     # API client
│   │   ├── auth.ts                    # Auth helpers
│   │   └── utils.ts                   # Utility functions
│   │
│   └── tests/
│       ├── __init__.py
│       └── components.test.tsx
│
├── docs/
│   ├── API.md                         # API documentation
│   ├── ARCHITECTURE.md                # System architecture
│   ├── SETUP.md                       # Development setup
│   ├── DEPLOYMENT.md                  # Production deployment
│   └── USER_FLOWS.md                  # User interaction flows
│
├── scripts/
│   ├── setup_db.py                    # Initialize database
│   ├── seed_data.py                   # Load test data
│   ├── generate_migrations.py         # Alembic migrations
│   └── deploy.sh                      # Deployment script
│
└── deployment/
    ├── Dockerfile                     # Backend container
    ├── docker-compose.yml             # Local dev environment
    ├── .env.example                   # Environment variables template
    ├── Procfile                       # Heroku deployment
    ├── Railway.toml                   # Railway.app deployment
    └── k8s/                           # Kubernetes manifests (future)
```

## Key Files

### Backend
- **main.py:** FastAPI app, routes setup
- **database.py:** PostgreSQL connection, SQLAlchemy ORM
- **services/:** Business logic (APIs, integrations, automation)
- **models/:** Database schemas
- **tasks/:** Background jobs (Celery)

### Frontend
- **app/dashboard/:** Main host dashboard
- **components/:** Reusable React components
- **lib/api.ts:** Axios/fetch API client

### Documentation
- **PLAN.md:** 8-week development roadmap (detailed)
- **docs/API.md:** REST API reference
- **docs/ARCHITECTURE.md:** System design
- **docs/SETUP.md:** How to run locally

## Development Flow

1. **Local setup:** `docker-compose up` (spins up backend + frontend + PostgreSQL + Redis)
2. **Backend:** `cd backend && uvicorn main:app --reload`
3. **Frontend:** `cd frontend && npm run dev`
4. **Tests:** `pytest backend/tests/` (backend), `npm test` (frontend)
5. **Deploy:** `./scripts/deploy.sh` (to Heroku/Railway)

---

**Created:** 2026-02-22
