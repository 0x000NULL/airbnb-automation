"""
API endpoint tests.

Tests all API routes for correct behavior, authentication,
and authorization.
"""

import pytest
from httpx import AsyncClient

from models.booking import AirbnbBooking
from models.property import Property
from models.task import Task, TaskStatus
from models.user import User


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_signup_success(self, client: AsyncClient):
        """Test successful user signup."""
        response = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "name": "New User",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_signup_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test signup with existing email."""
        response = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_user.email,
                "name": "Another User",
                "password": "password123",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient, test_user: User):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting current user info."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test accessing protected route without auth."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestPropertyEndpoints:
    """Tests for property CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_properties(
        self,
        client: AsyncClient,
        test_property: Property,
        auth_headers: dict,
    ):
        """Test listing user properties."""
        response = await client.get("/api/v1/properties", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "properties" in data
        assert len(data["properties"]) >= 1

    @pytest.mark.asyncio
    async def test_create_property(self, client: AsyncClient, auth_headers: dict):
        """Test creating a new property."""
        response = await client.post(
            "/api/v1/properties",
            headers=auth_headers,
            json={
                "name": "New Beach House",
                "address": "456 Beach Rd, Miami, FL 33139",
                "city": "Miami",
                "state": "FL",
                "zipcode": "33139",
                "bedrooms": 3,
                "bathrooms": 2,
                "cleaning_duration_hours": 4.0,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Beach House"
        assert data["city"] == "Miami"

    @pytest.mark.asyncio
    async def test_get_property(
        self,
        client: AsyncClient,
        test_property: Property,
        auth_headers: dict,
    ):
        """Test getting a single property."""
        response = await client.get(
            f"/api/v1/properties/{test_property.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_property.id)
        assert data["name"] == test_property.name

    @pytest.mark.asyncio
    async def test_update_property(
        self,
        client: AsyncClient,
        test_property: Property,
        auth_headers: dict,
    ):
        """Test updating a property."""
        response = await client.patch(
            f"/api/v1/properties/{test_property.id}",
            headers=auth_headers,
            json={"name": "Updated Property Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Property Name"

    @pytest.mark.asyncio
    async def test_delete_property(
        self,
        client: AsyncClient,
        test_property: Property,
        auth_headers: dict,
    ):
        """Test deleting a property."""
        response = await client.delete(
            f"/api/v1/properties/{test_property.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify deletion
        response = await client.get(
            f"/api/v1/properties/{test_property.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestBookingEndpoints:
    """Tests for booking endpoints."""

    @pytest.mark.asyncio
    async def test_list_bookings(
        self,
        client: AsyncClient,
        test_booking: AirbnbBooking,
        auth_headers: dict,
    ):
        """Test listing bookings."""
        response = await client.get("/api/v1/bookings", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "bookings" in data

    @pytest.mark.asyncio
    async def test_get_booking(
        self,
        client: AsyncClient,
        test_booking: AirbnbBooking,
        auth_headers: dict,
    ):
        """Test getting a single booking."""
        response = await client.get(
            f"/api/v1/bookings/{test_booking.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["guest_name"] == test_booking.guest_name


class TestTaskEndpoints:
    """Tests for task endpoints."""

    @pytest.mark.asyncio
    async def test_list_tasks(
        self,
        client: AsyncClient,
        test_task: Task,
        auth_headers: dict,
    ):
        """Test listing tasks."""
        response = await client.get("/api/v1/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) >= 1

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(
        self,
        client: AsyncClient,
        test_task: Task,
        auth_headers: dict,
    ):
        """Test listing tasks with status filter."""
        response = await client.get(
            "/api/v1/tasks?status=pending",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for task in data["tasks"]:
            assert task["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_task(
        self,
        client: AsyncClient,
        test_task: Task,
        auth_headers: dict,
    ):
        """Test getting a single task."""
        response = await client.get(
            f"/api/v1/tasks/{test_task.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_task.id)
        assert data["title"] == test_task.title

    @pytest.mark.asyncio
    async def test_update_task_status(
        self,
        client: AsyncClient,
        test_task: Task,
        auth_headers: dict,
    ):
        """Test updating task status."""
        response = await client.patch(
            f"/api/v1/tasks/{test_task.id}",
            headers=auth_headers,
            json={"status": "cancelled"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_get_task_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting non-existent task."""
        response = await client.get(
            "/api/v1/tasks/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestHumansEndpoints:
    """Tests for humans search endpoints."""

    @pytest.mark.asyncio
    async def test_search_humans(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test searching for humans."""
        response = await client.get(
            "/api/v1/humans/search",
            headers=auth_headers,
            params={
                "location": "Las Vegas, NV",
                "skill": "cleaning",
                "rating_min": 4.0,
                "budget_max": 100.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "humans" in data

    @pytest.mark.asyncio
    async def test_list_skills(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test listing available skills."""
        response = await client.get("/api/v1/humans/skills", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data


class TestWebhookEndpoints:
    """Tests for webhook endpoints."""

    @pytest.mark.asyncio
    async def test_webhook_health(self, client: AsyncClient):
        """Test webhook health endpoint."""
        response = await client.get("/api/v1/webhooks/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_rentahuman_webhook_invalid_event(
        self,
        client: AsyncClient,
        test_task: Task,
    ):
        """Test RentAHuman webhook with unknown event."""
        response = await client.post(
            "/api/v1/webhooks/rentahuman",
            json={
                "event": "unknown.event",
                "booking_id": "booking_123",
                "timestamp": "2024-01-01T12:00:00Z",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_rentahuman_webhook_task_not_found(self, client: AsyncClient):
        """Test RentAHuman webhook for non-existent task."""
        response = await client.post(
            "/api/v1/webhooks/rentahuman",
            json={
                "event": "booking.confirmed",
                "booking_id": "nonexistent_booking",
                "human_name": "Test Human",
                "timestamp": "2024-01-01T12:00:00Z",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "task_not_found"


class TestAnalyticsEndpoints:
    """Tests for analytics endpoints."""

    @pytest.mark.asyncio
    async def test_get_dashboard_stats(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting dashboard statistics."""
        response = await client.get("/api/v1/analytics/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should return some stats structure
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_get_cost_analytics(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting cost analytics."""
        response = await client.get(
            "/api/v1/analytics/costs",
            headers=auth_headers,
            params={"period": "month"},
        )
        assert response.status_code == 200
