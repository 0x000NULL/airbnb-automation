"""
Pytest fixtures for backend tests.

Provides:
- Async test database with in-memory SQLite
- Test client with authentication
- Mock RentAHuman client
- Sample data fixtures
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import date, datetime, time, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from api.deps import get_db
from database import Base
from main import app
from models.booking import AirbnbBooking, BookingSource
from models.property import Property
from models.task import Task, TaskStatus, TaskType
from models.user import User
from services.rentahuman_client import RentAHumanClient


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async_session = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.uJxG4yqYnqDZy.",  # "password123"
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_property(db_session: AsyncSession, test_user: User) -> Property:
    """Create a test property."""
    property_ = Property(
        id=uuid4(),
        user_id=test_user.id,
        name="Test Property",
        address="123 Test St, Las Vegas, NV 89101",
        city="Las Vegas",
        state="NV",
        zipcode="89101",
        bedrooms=2,
        bathrooms=1,
        cleaning_duration_hours=3.0,
        is_active=True,
    )
    db_session.add(property_)
    await db_session.commit()
    await db_session.refresh(property_)
    return property_


@pytest_asyncio.fixture
async def test_booking(
    db_session: AsyncSession,
    test_property: Property,
) -> AirbnbBooking:
    """Create a test booking."""
    booking = AirbnbBooking(
        id=uuid4(),
        property_id=test_property.id,
        platform_booking_id="AIRBNB123456",
        source=BookingSource.AIRBNB,
        guest_name="John Guest",
        guest_email="guest@example.com",
        checkin_date=date.today() + timedelta(days=7),
        checkout_date=date.today() + timedelta(days=10),
        checkout_time=time(11, 0),
        guest_count=2,
        total_price=450.00,
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)
    return booking


@pytest_asyncio.fixture
async def test_task(
    db_session: AsyncSession,
    test_property: Property,
    test_booking: AirbnbBooking,
) -> Task:
    """Create a test task."""
    task = Task(
        id=uuid4(),
        property_id=test_property.id,
        booking_id=test_booking.id,
        task_type=TaskType.TURNOVER_CLEAN,
        status=TaskStatus.PENDING,
        scheduled_date=test_booking.checkout_date,
        scheduled_time=time(11, 0),
        estimated_duration_hours=3.0,
        budget_min=50.0,
        budget_max=80.0,
        title="Turnover cleaning",
        description="Standard turnover cleaning after guest checkout.",
        instructions="Clean all rooms, change linens, restock supplies.",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict[str, str]:
    """Get authentication headers for test user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    token = response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_rentahuman_client() -> MagicMock:
    """Create a mock RentAHuman client."""
    client = MagicMock(spec=RentAHumanClient)

    # Mock search_humans
    client.search_humans = AsyncMock(return_value={
        "humans": [
            {
                "id": "human_123",
                "name": "Jane Cleaner",
                "rating": 4.8,
                "reviews": 156,
                "rate": 35.0,
                "skills": ["cleaning", "organizing"],
                "location": "Las Vegas, NV",
                "bio": "Professional cleaner with 5 years experience.",
                "available": True,
            },
            {
                "id": "human_456",
                "name": "Bob Handyman",
                "rating": 4.5,
                "reviews": 89,
                "rate": 45.0,
                "skills": ["handyman", "cleaning"],
                "location": "Las Vegas, NV",
                "bio": "Experienced handyman and cleaner.",
                "available": True,
            },
        ],
        "total": 2,
    })

    # Mock create_booking
    client.create_booking = AsyncMock(return_value={
        "booking_id": "booking_abc123",
        "status": "pending",
        "human_id": "human_123",
        "human_name": "Jane Cleaner",
        "scheduled_start": datetime.now().isoformat(),
        "scheduled_end": (datetime.now() + timedelta(hours=3)).isoformat(),
        "total_cost": 105.0,
    })

    # Mock get_booking_status
    client.get_booking_status = AsyncMock(return_value={
        "booking_id": "booking_abc123",
        "status": "confirmed",
        "human_id": "human_123",
        "human_name": "Jane Cleaner",
    })

    # Mock cancel_booking
    client.cancel_booking = AsyncMock(return_value={
        "booking_id": "booking_abc123",
        "status": "cancelled",
        "refund_amount": 105.0,
    })

    # Mock list_skills
    client.list_skills = AsyncMock(return_value={
        "skills": [
            {"id": "cleaning", "name": "Cleaning", "category": "Home Services"},
            {"id": "handyman", "name": "Handyman", "category": "Home Services"},
            {"id": "photography", "name": "Photography", "category": "Creative"},
            {"id": "organizing", "name": "Organizing", "category": "Home Services"},
        ]
    })

    # Mock get_human_profile
    client.get_human_profile = AsyncMock(return_value={
        "id": "human_123",
        "name": "Jane Cleaner",
        "rating": 4.8,
        "reviews": 156,
        "rate": 35.0,
        "skills": ["cleaning", "organizing"],
        "location": "Las Vegas, NV",
        "bio": "Professional cleaner with 5 years experience.",
        "available": True,
        "completed_jobs": 234,
        "response_time": "< 1 hour",
    })

    return client


@pytest.fixture
def sample_human_search_params() -> dict[str, Any]:
    """Sample parameters for human search."""
    return {
        "location": "Las Vegas, NV",
        "skill": "cleaning",
        "rating_min": 4.0,
        "budget_max": 50.0,
    }


@pytest.fixture
def sample_booking_params() -> dict[str, Any]:
    """Sample parameters for creating a booking."""
    start_time = datetime.now() + timedelta(days=1)
    return {
        "human_id": "human_123",
        "task_description": "Turnover cleaning for 2BR apartment",
        "start_time": start_time.isoformat(),
        "end_time": (start_time + timedelta(hours=3)).isoformat(),
        "budget": 100.0,
    }
