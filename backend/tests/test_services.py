"""
Service layer tests.

Tests the business logic in:
- TaskGenerator
- BookingEngine
- BookingLogService
"""

from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from models.automation_config import AutomationConfig, HumanPreference
from models.booking import AirbnbBooking, BookingSource
from models.booking_log import BookingLogEvent
from models.property import Property
from models.task import Task, TaskStatus, TaskType
from services.booking_engine import BookingEngine, BookingResult
from services.booking_log_service import BookingLogService, LoggingTimer
from services.rentahuman_client import Booking, Human
from services.task_generator import GeneratedTask, TaskGenerator


class TestTaskGenerator:
    """Tests for TaskGenerator service."""

    @pytest.fixture
    def generator(self) -> TaskGenerator:
        """Create a task generator instance."""
        return TaskGenerator(buffer_percentage=0.1)

    @pytest.fixture
    def sample_property(self) -> Property:
        """Create a sample property."""
        prop = Property(
            id=uuid4(),
            user_id=uuid4(),
            name="Beach House",
            address="123 Beach St",
            city="Miami",
            state="FL",
            zipcode="33139",
            bedrooms=2,
            bathrooms=2,
            cleaning_duration_hours=3.0,
            cleaning_budget=75.0,
            max_guests=4,
            default_checkout_time=time(11, 0),
            default_checkin_time=time(15, 0),
        )
        return prop

    @pytest.fixture
    def sample_booking(self, sample_property: Property) -> AirbnbBooking:
        """Create a sample booking."""
        return AirbnbBooking(
            id=uuid4(),
            property_id=sample_property.id,
            platform_booking_id="AIRBNB123",
            source=BookingSource.AIRBNB,
            guest_name="John Smith",
            guest_email="john@example.com",
            checkin_date=date.today() + timedelta(days=7),
            checkout_date=date.today() + timedelta(days=10),
            checkout_time=time(11, 0),
            guest_count=2,
            total_price=450.0,
        )

    def test_generate_cleaning_task(
        self,
        generator: TaskGenerator,
        sample_property: Property,
        sample_booking: AirbnbBooking,
    ):
        """Test that cleaning task is generated for checkout."""
        tasks = generator.generate_from_booking(sample_booking, sample_property)

        # Find cleaning task
        cleaning_tasks = [t for t in tasks if t.type == TaskType.CLEANING]
        assert len(cleaning_tasks) == 1

        task = cleaning_tasks[0]
        assert task.property_id == sample_property.id
        assert task.booking_id == sample_booking.id
        assert task.scheduled_date == sample_booking.checkout_date
        assert task.scheduled_time == sample_property.default_checkout_time
        assert "cleaning" in task.required_skills
        assert len(task.checklist) > 0

    def test_generate_communication_task(
        self,
        generator: TaskGenerator,
        sample_property: Property,
        sample_booking: AirbnbBooking,
    ):
        """Test that communication task is generated for checkin."""
        tasks = generator.generate_from_booking(sample_booking, sample_property)

        # Find communication task
        comm_tasks = [t for t in tasks if t.type == TaskType.COMMUNICATION]
        assert len(comm_tasks) == 1

        task = comm_tasks[0]
        assert task.scheduled_date == sample_booking.checkin_date - timedelta(days=1)
        assert task.description  # Should include guest name

    def test_tight_turnover_detection(
        self,
        generator: TaskGenerator,
        sample_property: Property,
        sample_booking: AirbnbBooking,
    ):
        """Test tight turnover is detected when gap < 5 hours."""
        # Create next booking with same day checkin
        next_booking = AirbnbBooking(
            id=uuid4(),
            property_id=sample_property.id,
            platform_booking_id="AIRBNB456",
            source=BookingSource.AIRBNB,
            guest_name="Jane Doe",
            guest_email="jane@example.com",
            checkin_date=sample_booking.checkout_date,  # Same day!
            checkout_date=sample_booking.checkout_date + timedelta(days=3),
            checkout_time=time(11, 0),
            guest_count=2,
            total_price=300.0,
        )

        tasks = generator.generate_from_booking(
            sample_booking, sample_property, next_booking
        )

        # Check cleaning task has tight turnover flag
        cleaning_task = next(t for t in tasks if t.type == TaskType.CLEANING)
        assert cleaning_task.is_tight_turnover is True
        assert "TIGHT TURNOVER" in cleaning_task.description

    def test_restocking_task_for_high_occupancy(
        self,
        generator: TaskGenerator,
        sample_property: Property,
    ):
        """Test restocking task is generated when occupancy > 80%."""
        # Set high guest count (> 80% of max_guests=4)
        booking = AirbnbBooking(
            id=uuid4(),
            property_id=sample_property.id,
            platform_booking_id="AIRBNB789",
            source=BookingSource.AIRBNB,
            guest_name="Large Group",
            guest_email="group@example.com",
            checkin_date=date.today() + timedelta(days=7),
            checkout_date=date.today() + timedelta(days=10),
            checkout_time=time(11, 0),
            guest_count=4,  # 100% of max_guests
            total_price=600.0,
        )

        tasks = generator.generate_from_booking(booking, sample_property)

        # Should have restocking task
        restocking_tasks = [t for t in tasks if t.type == TaskType.RESTOCKING]
        assert len(restocking_tasks) == 1
        assert "organizing" in restocking_tasks[0].required_skills

    def test_no_restocking_for_low_occupancy(
        self,
        generator: TaskGenerator,
        sample_property: Property,
    ):
        """Test no restocking task for low occupancy."""
        booking = AirbnbBooking(
            id=uuid4(),
            property_id=sample_property.id,
            platform_booking_id="AIRBNB123",
            source=BookingSource.AIRBNB,
            guest_name="Solo Guest",
            guest_email="solo@example.com",
            checkin_date=date.today() + timedelta(days=7),
            checkout_date=date.today() + timedelta(days=10),
            checkout_time=time(11, 0),
            guest_count=1,  # 25% of max_guests=4
            total_price=300.0,
        )

        tasks = generator.generate_from_booking(booking, sample_property)

        # Should NOT have restocking task
        restocking_tasks = [t for t in tasks if t.type == TaskType.RESTOCKING]
        assert len(restocking_tasks) == 0

    def test_budget_includes_buffer(
        self,
        generator: TaskGenerator,
        sample_property: Property,
        sample_booking: AirbnbBooking,
    ):
        """Test that budget includes configured buffer."""
        tasks = generator.generate_from_booking(sample_booking, sample_property)

        cleaning_task = next(t for t in tasks if t.type == TaskType.CLEANING)
        expected_budget = sample_property.cleaning_budget * 1.1  # 10% buffer
        assert cleaning_task.budget == expected_budget

    def test_cleaning_duration_by_bedrooms(self, generator: TaskGenerator):
        """Test cleaning duration scales with bedroom count."""
        assert generator.CLEANING_DURATION[1] == 2.0
        assert generator.CLEANING_DURATION[2] == 3.0
        assert generator.CLEANING_DURATION[3] == 4.0
        assert generator.CLEANING_DURATION[4] == 5.0


class TestBookingEngine:
    """Tests for BookingEngine service."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock RentAHuman client."""
        client = MagicMock()
        client.search_humans = AsyncMock()
        client.create_booking = AsyncMock()
        return client

    @pytest.fixture
    def engine(self, mock_client: MagicMock) -> BookingEngine:
        """Create a booking engine with mock client."""
        return BookingEngine(client=mock_client)

    @pytest.fixture
    def sample_task(self) -> Task:
        """Create a sample task."""
        return Task(
            id=uuid4(),
            property_id=uuid4(),
            task_type=TaskType.CLEANING,
            status=TaskStatus.PENDING,
            scheduled_date=date.today() + timedelta(days=3),
            scheduled_time=time(11, 0),
            estimated_duration_hours=3.0,
            budget_min=50.0,
            budget_max=100.0,
            title="Turnover cleaning",
            description="Standard cleaning",
        )

    @pytest.fixture
    def sample_config(self) -> AutomationConfig:
        """Create a sample automation config."""
        return AutomationConfig(
            id=uuid4(),
            user_id=uuid4(),
            auto_book_enabled=True,
            minimum_human_rating=4.0,
            cleaning_preference=HumanPreference.CHEAPEST,
            maintenance_preference=HumanPreference.HIGHEST_RATED,
        )

    @pytest.fixture
    def sample_humans(self) -> list[Human]:
        """Create sample humans."""
        return [
            Human(
                id="human_1",
                name="Jane Cleaner",
                rating=4.8,
                reviews=150,
                rate=35.0,
                skills=["cleaning"],
                location="Las Vegas, NV",
                bio="Experienced cleaner",
                available=True,
            ),
            Human(
                id="human_2",
                name="Bob Budget",
                rating=4.2,
                reviews=50,
                rate=25.0,
                skills=["cleaning"],
                location="Las Vegas, NV",
                bio="Affordable cleaner",
                available=True,
            ),
        ]

    @pytest.mark.asyncio
    async def test_successful_booking(
        self,
        engine: BookingEngine,
        mock_client: MagicMock,
        sample_task: Task,
        sample_config: AutomationConfig,
        sample_humans: list[Human],
    ):
        """Test successful booking flow."""
        prop = MagicMock()
        prop.full_address = "123 Test St, Las Vegas, NV"

        mock_client.search_humans.return_value = sample_humans
        mock_client.create_booking.return_value = Booking(
            id="booking_123",
            human_id="human_2",  # Cheapest (Bob)
            status="confirmed",
            total_cost=75.0,
            human_name="Bob Budget",
        )

        result = await engine.book_task(sample_task, prop, sample_config)

        assert result.success is True
        assert result.booking_id == "booking_123"
        assert result.total_cost == 75.0
        mock_client.search_humans.assert_called_once()
        mock_client.create_booking.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_booking_prevention(
        self,
        engine: BookingEngine,
        sample_task: Task,
        sample_config: AutomationConfig,
    ):
        """Test that duplicate bookings are prevented."""
        prop = MagicMock()
        sample_task.rentahuman_booking_id = "existing_booking"

        result = await engine.book_task(sample_task, prop, sample_config)

        assert result.success is False
        assert "already booked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_fallback_when_no_humans_found(
        self,
        engine: BookingEngine,
        mock_client: MagicMock,
        sample_task: Task,
        sample_config: AutomationConfig,
        sample_humans: list[Human],
    ):
        """Test fallback search when initial search returns no humans."""
        prop = MagicMock()
        prop.full_address = "123 Test St, Las Vegas, NV"

        # First search returns empty, fallback returns humans
        mock_client.search_humans.side_effect = [[], sample_humans]
        mock_client.create_booking.return_value = Booking(
            id="booking_fallback",
            human_id="human_1",
            status="confirmed",
            total_cost=90.0,
            human_name="Jane Cleaner",
        )

        result = await engine.book_task(sample_task, prop, sample_config)

        assert result.success is True
        assert result.booking_id == "booking_fallback"
        # Should have been called twice (initial + fallback)
        assert mock_client.search_humans.call_count == 2

    def test_select_cheapest_human(
        self,
        engine: BookingEngine,
        sample_humans: list[Human],
    ):
        """Test selection of cheapest human."""
        selected = engine._select_best_human(sample_humans, HumanPreference.CHEAPEST)
        assert selected.name == "Bob Budget"  # $25/hr vs $35/hr

    def test_select_highest_rated_human(
        self,
        engine: BookingEngine,
        sample_humans: list[Human],
    ):
        """Test selection of highest rated human."""
        selected = engine._select_best_human(
            sample_humans, HumanPreference.HIGHEST_RATED
        )
        assert selected.name == "Jane Cleaner"  # 4.8 vs 4.2 rating

    def test_skill_mapping(self, engine: BookingEngine):
        """Test task type to skill mapping."""
        assert engine._get_skill_for_task_type(TaskType.CLEANING) == "cleaning"
        assert engine._get_skill_for_task_type(TaskType.MAINTENANCE) == "handyman"
        assert engine._get_skill_for_task_type(TaskType.PHOTOGRAPHY) == "photography"
        assert engine._get_skill_for_task_type(TaskType.RESTOCKING) == "organizing"
        assert engine._get_skill_for_task_type(TaskType.COMMUNICATION) is None

    def test_urgent_task_preference(
        self,
        engine: BookingEngine,
        sample_task: Task,
        sample_config: AutomationConfig,
    ):
        """Test that urgent tasks prefer highest rated humans."""
        sample_task._is_urgent = True
        sample_task.is_urgent = True

        # Mock is_urgent property
        with patch.object(Task, "is_urgent", new_callable=lambda: property(lambda s: True)):
            preference = engine._get_preference_for_task(sample_task, sample_config)
            assert preference == HumanPreference.HIGHEST_RATED


class TestBookingLogService:
    """Tests for BookingLogService."""

    @pytest.fixture
    def log_service(self) -> BookingLogService:
        """Create a log service without database."""
        return BookingLogService(session=None)

    @pytest.mark.asyncio
    async def test_log_event_in_memory(self, log_service: BookingLogService):
        """Test that events are logged to in-memory list."""
        task_id = uuid4()

        await log_service.log_event(
            event=BookingLogEvent.SEARCH_INITIATED,
            message="Starting search",
            task_id=task_id,
        )

        logs = log_service.get_in_memory_logs()
        assert len(logs) == 1
        assert logs[0]["event"] == "search_initiated"
        assert logs[0]["message"] == "Starting search"
        assert logs[0]["task_id"] == str(task_id)

    @pytest.mark.asyncio
    async def test_log_search(self, log_service: BookingLogService):
        """Test logging a search event."""
        task_id = uuid4()

        await log_service.log_search(
            task_id=task_id,
            location="Las Vegas, NV",
            skill="cleaning",
            budget_max=100.0,
            results_count=5,
            duration_ms=250,
        )

        logs = log_service.get_in_memory_logs()
        assert len(logs) == 1
        assert logs[0]["event"] == "search_completed"
        assert logs[0]["success"] is True

    @pytest.mark.asyncio
    async def test_log_booking_success(self, log_service: BookingLogService):
        """Test logging a successful booking."""
        task_id = uuid4()

        await log_service.log_booking_success(
            task_id=task_id,
            rentahuman_booking_id="booking_123",
            human_id="human_456",
            human_name="Jane Cleaner",
            total_cost=105.0,
            duration_ms=500,
        )

        logs = log_service.get_in_memory_logs()
        assert len(logs) == 1
        assert logs[0]["event"] == "booking_created"
        assert logs[0]["success"] is True
        assert logs[0]["rentahuman_booking_id"] == "booking_123"

    @pytest.mark.asyncio
    async def test_log_booking_failure(self, log_service: BookingLogService):
        """Test logging a failed booking."""
        task_id = uuid4()

        await log_service.log_booking_failure(
            task_id=task_id,
            error="No humans available",
            attempt_number=3,
        )

        logs = log_service.get_in_memory_logs()
        assert len(logs) == 1
        assert logs[0]["event"] == "booking_failed"
        assert logs[0]["success"] is False

    @pytest.mark.asyncio
    async def test_log_cancellation(self, log_service: BookingLogService):
        """Test logging a cancellation."""
        task_id = uuid4()

        await log_service.log_cancellation(
            task_id=task_id,
            rentahuman_booking_id="booking_123",
            reason="Human cancelled",
        )

        logs = log_service.get_in_memory_logs()
        assert len(logs) == 1
        assert logs[0]["event"] == "cancellation_received"

    def test_logging_timer(self):
        """Test the logging timer context manager."""
        import time as time_module

        timer = LoggingTimer()
        with timer:
            time_module.sleep(0.1)  # 100ms

        assert timer.duration_ms >= 90  # Allow some variance
        assert timer.duration_ms < 200
