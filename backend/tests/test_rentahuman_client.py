"""
RentAHuman client tests.

Tests both mock mode and HTTP behavior of the RentAHuman API client.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.rentahuman_client import Booking, Human, RentAHumanClient


class TestRentAHumanClientMockMode:
    """Tests for RentAHuman client in mock mode."""

    @pytest.fixture
    def mock_client(self) -> RentAHumanClient:
        """Create a client in mock mode."""
        return RentAHumanClient(mock_mode=True)

    @pytest.mark.asyncio
    async def test_search_humans_returns_results(self, mock_client: RentAHumanClient):
        """Test that search returns mock humans."""
        humans = await mock_client.search_humans(location="Las Vegas, NV")

        assert len(humans) > 0
        assert all(isinstance(h, Human) for h in humans)

    @pytest.mark.asyncio
    async def test_search_humans_filter_by_skill(self, mock_client: RentAHumanClient):
        """Test search filtering by skill."""
        humans = await mock_client.search_humans(
            location="Las Vegas, NV",
            skill="cleaning",
        )

        assert len(humans) > 0
        for human in humans:
            assert "cleaning" in [s.lower() for s in human.skills]

    @pytest.mark.asyncio
    async def test_search_humans_filter_by_budget(self, mock_client: RentAHumanClient):
        """Test search filtering by budget."""
        budget_max = 30.0
        humans = await mock_client.search_humans(
            location="Las Vegas, NV",
            budget_max=budget_max,
        )

        for human in humans:
            assert human.rate <= budget_max

    @pytest.mark.asyncio
    async def test_search_humans_filter_by_rating(self, mock_client: RentAHumanClient):
        """Test search filtering by minimum rating."""
        rating_min = 4.7
        humans = await mock_client.search_humans(
            location="Las Vegas, NV",
            rating_min=rating_min,
        )

        for human in humans:
            assert human.rating >= rating_min

    @pytest.mark.asyncio
    async def test_create_booking_success(self, mock_client: RentAHumanClient):
        """Test creating a booking."""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=3)

        booking = await mock_client.create_booking(
            human_id="human_001",
            task_description="Turnover cleaning",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            budget=100.0,
        )

        assert booking is not None
        assert isinstance(booking, Booking)
        assert booking.status == "confirmed"
        assert booking.human_id == "human_001"
        assert booking.total_cost > 0

    @pytest.mark.asyncio
    async def test_get_booking_status(self, mock_client: RentAHumanClient):
        """Test getting booking status."""
        status = await mock_client.get_booking_status("booking_123")

        assert status is not None
        assert "status" in status
        assert status["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_list_skills(self, mock_client: RentAHumanClient):
        """Test listing available skills."""
        skills = await mock_client.list_skills()

        assert len(skills) > 0
        assert all("name" in s for s in skills)
        assert all("description" in s for s in skills)

        # Check expected skills exist
        skill_names = [s["name"] for s in skills]
        assert "cleaning" in skill_names
        assert "handyman" in skill_names

    @pytest.mark.asyncio
    async def test_cancel_booking(self, mock_client: RentAHumanClient):
        """Test cancelling a booking."""
        result = await mock_client.cancel_booking(
            booking_id="booking_123",
            reason="Test cancellation",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_get_human(self, mock_client: RentAHumanClient):
        """Test getting a human profile."""
        human = await mock_client.get_human("human_001")

        assert human is not None
        assert isinstance(human, Human)
        assert human.id == "human_001"


class TestRentAHumanClientHTTP:
    """Tests for RentAHuman client HTTP behavior."""

    @pytest.fixture
    def client(self) -> RentAHumanClient:
        """Create a client with mock mode disabled."""
        return RentAHumanClient(
            api_key="test_api_key",
            base_url="https://api.test.rentahuman.ai",
            mock_mode=False,
        )

    @pytest.mark.asyncio
    async def test_search_humans_http_call(self, client: RentAHumanClient):
        """Test that search makes correct HTTP call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "humans": [
                {
                    "id": "human_123",
                    "name": "Test Human",
                    "skills": ["cleaning"],
                    "location": "Test City",
                    "rate": 25.0,
                    "rating": 4.5,
                    "reviews": 10,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = mock_response
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_async_client

            humans = await client.search_humans(
                location="Las Vegas, NV",
                skill="cleaning",
                budget_max=50.0,
            )

            assert len(humans) == 1
            assert humans[0].name == "Test Human"

            # Verify the HTTP call
            mock_async_client.get.assert_called_once()
            call_args = mock_async_client.get.call_args
            assert "/humans/search" in call_args[0][0]
            assert call_args[1]["params"]["location"] == "Las Vegas, NV"
            assert call_args[1]["params"]["skill"] == "cleaning"

    @pytest.mark.asyncio
    async def test_search_humans_http_error(self, client: RentAHumanClient):
        """Test that search handles HTTP errors gracefully."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_async_client = AsyncMock()
            mock_async_client.get.side_effect = httpx.HTTPError("Connection error")
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_async_client

            humans = await client.search_humans(location="Las Vegas, NV")

            # Should return empty list on error
            assert humans == []

    @pytest.mark.asyncio
    async def test_create_booking_http_call(self, client: RentAHumanClient):
        """Test that booking creation makes correct HTTP call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "booking_abc",
            "human_id": "human_123",
            "human_name": "Test Human",
            "task_description": "Test task",
            "start_time": "2024-01-01T10:00:00",
            "end_time": "2024-01-01T13:00:00",
            "budget": 100.0,
            "status": "confirmed",
            "total_cost": 95.0,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_async_client = AsyncMock()
            mock_async_client.post.return_value = mock_response
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_async_client

            booking = await client.create_booking(
                human_id="human_123",
                task_description="Test task",
                start_time="2024-01-01T10:00:00",
                end_time="2024-01-01T13:00:00",
                budget=100.0,
            )

            assert booking is not None
            assert booking.id == "booking_abc"
            assert booking.status == "confirmed"

            # Verify the HTTP call
            mock_async_client.post.assert_called_once()
            call_args = mock_async_client.post.call_args
            assert "/bookings" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_booking_retry_on_error(self, client: RentAHumanClient):
        """Test that booking retries on transient errors."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "booking_abc",
            "human_id": "human_123",
            "human_name": "Test Human",
            "task_description": "Test task",
            "start_time": "2024-01-01T10:00:00",
            "end_time": "2024-01-01T13:00:00",
            "budget": 100.0,
            "status": "confirmed",
            "total_cost": 95.0,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_async_client = AsyncMock()
            # Fail first two times, succeed on third
            mock_async_client.post.side_effect = [
                httpx.HTTPError("Error 1"),
                httpx.HTTPError("Error 2"),
                mock_response,
            ]
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_async_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                booking = await client.create_booking(
                    human_id="human_123",
                    task_description="Test task",
                    start_time="2024-01-01T10:00:00",
                    end_time="2024-01-01T13:00:00",
                    budget=100.0,
                )

            # Should succeed after retries
            assert booking is not None
            assert mock_async_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_headers_include_api_key(self, client: RentAHumanClient):
        """Test that requests include API key in headers."""
        headers = client._get_headers()

        assert "Authorization" in headers
        assert "Bearer test_api_key" in headers["Authorization"]
        assert headers["Content-Type"] == "application/json"


class TestHumanDataclass:
    """Tests for Human dataclass."""

    def test_human_creation(self):
        """Test creating a Human object."""
        human = Human(
            id="test_123",
            name="Test Human",
            skills=["cleaning", "organizing"],
            location="Las Vegas, NV",
            rate=30.0,
        )

        assert human.id == "test_123"
        assert human.name == "Test Human"
        assert len(human.skills) == 2
        assert human.currency == "USD"  # default
        assert human.rating == 4.5  # default

    def test_human_with_all_fields(self):
        """Test Human with all optional fields."""
        human = Human(
            id="test_456",
            name="Full Human",
            skills=["photography"],
            location="Miami, FL",
            rate=50.0,
            currency="USD",
            rating=4.9,
            reviews=200,
            availability="available",
            bio="Professional photographer",
            photo_url="https://example.com/photo.jpg",
        )

        assert human.rating == 4.9
        assert human.reviews == 200
        assert human.photo_url == "https://example.com/photo.jpg"


class TestBookingDataclass:
    """Tests for Booking dataclass."""

    def test_booking_creation(self):
        """Test creating a Booking object."""
        booking = Booking(
            id="booking_123",
            human_id="human_456",
            human_name="Test Human",
            task_description="Cleaning task",
            start_time="2024-01-01T10:00:00",
            end_time="2024-01-01T13:00:00",
            budget=100.0,
            status="confirmed",
        )

        assert booking.id == "booking_123"
        assert booking.status == "confirmed"
        assert booking.total_cost == 0.0  # default
