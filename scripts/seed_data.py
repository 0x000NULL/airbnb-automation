"""
Seed data script for development.

Creates:
- Test user (ethan@example.com)
- 3 properties in Las Vegas
- 10 bookings across next 30 days
- Sample tasks with various statuses
- Automation config for test user

Usage:
    python -m scripts.seed_data

Or from project root:
    python scripts/seed_data.py
"""

import asyncio
import sys
from datetime import date, time, timedelta
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


async def seed_database():
    """Seed the database with test data."""
    from database import async_session_maker, engine
    from models.automation_config import (
        AutomationConfig,
        HumanPreference,
        NotificationMethod,
    )
    from models.booking import AirbnbBooking, BookingSource
    from models.property import Property
    from models.task import Task, TaskStatus, TaskType
    from models.user import User
    from sqlalchemy import select, text

    print("Starting database seeding...")

    async with async_session_maker() as session:
        # Check if already seeded
        result = await session.execute(
            select(User).where(User.email == "ethan@example.com")
        )
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping...")
            return

        # Create test user
        print("Creating test user...")
        user = User(
            id=uuid4(),
            email="ethan@example.com",
            hashed_password=hash_password("password123"),
            name="Ethan Aldrich",
            phone="+17025551234",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        print(f"  Created user: {user.email} (ID: {user.id})")

        # Create automation config
        print("Creating automation config...")
        config = AutomationConfig(
            id=uuid4(),
            host_id=user.id,
            auto_book_cleaning=True,
            auto_book_maintenance=True,
            auto_book_photography=False,
            auto_respond_to_guests=False,
            cleaning_preference=HumanPreference.HIGHEST_RATED,
            maintenance_preference=HumanPreference.NEAREST,
            minimum_human_rating=4.0,
            max_booking_lead_time_days=3,
            notification_method=NotificationMethod.EMAIL,
        )
        session.add(config)
        await session.flush()

        # Create 3 Las Vegas properties
        print("Creating properties...")
        properties_data = [
            {
                "name": "The Luxury Strip View",
                "location": {
                    "address": "3750 Las Vegas Blvd S",
                    "city": "Las Vegas",
                    "state": "NV",
                    "zip": "89158",
                },
                "property_type": "apartment",
                "bedrooms": 2,
                "bathrooms": 2,
                "max_guests": 4,
                "airbnb_listing_id": "ab_luxury_strip_001",
                "vrbo_listing_id": None,
                "default_checkin_time": time(15, 0),
                "default_checkout_time": time(11, 0),
                "cleaning_budget": 150.0,
                "maintenance_budget": 200.0,
                "preferred_skills": ["cleaning", "hotel_experience"],
            },
            {
                "name": "Desert Oasis House",
                "location": {
                    "address": "8421 Eldora Ave",
                    "city": "Las Vegas",
                    "state": "NV",
                    "zip": "89117",
                },
                "property_type": "house",
                "bedrooms": 3,
                "bathrooms": 2,
                "max_guests": 6,
                "airbnb_listing_id": "ab_desert_oasis_002",
                "vrbo_listing_id": "vb_desert_oasis_002",
                "default_checkin_time": time(16, 0),
                "default_checkout_time": time(10, 0),
                "cleaning_budget": 200.0,
                "maintenance_budget": 300.0,
                "preferred_skills": ["cleaning", "pool_maintenance"],
            },
            {
                "name": "Downtown Vegas Condo",
                "location": {
                    "address": "200 Hoover Ave",
                    "city": "Las Vegas",
                    "state": "NV",
                    "zip": "89101",
                },
                "property_type": "condo",
                "bedrooms": 4,
                "bathrooms": 3,
                "max_guests": 8,
                "airbnb_listing_id": "ab_downtown_003",
                "vrbo_listing_id": "vb_downtown_003",
                "default_checkin_time": time(15, 0),
                "default_checkout_time": time(11, 0),
                "cleaning_budget": 250.0,
                "maintenance_budget": 350.0,
                "preferred_skills": ["cleaning", "deep_cleaning", "organizing"],
            },
        ]

        properties = []
        for prop_data in properties_data:
            prop = Property(
                id=uuid4(),
                host_id=user.id,
                **prop_data,
            )
            session.add(prop)
            properties.append(prop)
            print(f"  Created property: {prop.name}")

        await session.flush()

        # Create bookings across next 30 days
        print("Creating bookings...")
        guest_names = [
            "John Smith",
            "Sarah Johnson",
            "Michael Brown",
            "Emily Davis",
            "David Wilson",
            "Jessica Martinez",
            "Chris Anderson",
            "Amanda Taylor",
            "Ryan Thomas",
            "Lauren White",
        ]

        today = date.today()
        bookings = []
        booking_idx = 0

        # Distribute bookings across properties
        for prop_idx, prop in enumerate(properties):
            current_date = today + timedelta(days=prop_idx * 2 + 1)

            # 3-4 bookings per property
            num_bookings = 3 + (prop_idx % 2)

            for i in range(num_bookings):
                if booking_idx >= len(guest_names):
                    break

                stay_length = 2 + (booking_idx % 4)  # 2-5 nights
                checkout_date = current_date + timedelta(days=stay_length)
                guest_count = 1 + (booking_idx % prop.max_guests)
                total_price = stay_length * (100 + prop.bedrooms * 50)

                booking = AirbnbBooking(
                    id=uuid4(),
                    property_id=prop.id,
                    external_id=f"ab_{prop.id.hex[:8]}_{i}",
                    guest_name=guest_names[booking_idx],
                    checkin_date=current_date,
                    checkout_date=checkout_date,
                    guest_count=guest_count,
                    total_price=total_price,
                    notes="Early check-in requested" if booking_idx % 3 == 0 else None,
                    source=BookingSource.AIRBNB,
                )
                session.add(booking)
                bookings.append(booking)

                print(
                    f"  Created booking: {booking.guest_name} at {prop.name} "
                    f"({current_date} - {checkout_date})"
                )

                # Move to next available date with gap
                current_date = checkout_date + timedelta(days=1 + (booking_idx % 3))
                booking_idx += 1

        await session.flush()

        # Create sample tasks with various statuses
        print("Creating tasks...")
        task_statuses = [
            TaskStatus.COMPLETED,
            TaskStatus.COMPLETED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.HUMAN_BOOKED,
            TaskStatus.HUMAN_BOOKED,
            TaskStatus.PENDING,
            TaskStatus.PENDING,
            TaskStatus.PENDING,
            TaskStatus.FAILED,
            TaskStatus.PENDING,
        ]

        task_types = [
            TaskType.CLEANING,
            TaskType.CLEANING,
            TaskType.CLEANING,
            TaskType.CLEANING,
            TaskType.MAINTENANCE,
            TaskType.CLEANING,
            TaskType.RESTOCKING,
            TaskType.COMMUNICATION,
            TaskType.CLEANING,
            TaskType.PHOTOGRAPHY,
        ]

        mock_humans = [
            {"id": "h_001", "name": "Maria Garcia", "rating": 4.9, "phone": "+17025559001"},
            {"id": "h_002", "name": "James Wilson", "rating": 4.7, "phone": "+17025559002"},
            {"id": "h_003", "name": "Sofia Rodriguez", "rating": 4.8, "phone": "+17025559003"},
            {"id": "h_004", "name": "Robert Johnson", "rating": 4.5, "phone": "+17025559004"},
            {"id": "h_005", "name": "Emma Thompson", "rating": 4.6, "phone": "+17025559005"},
        ]

        for i, (booking, status, task_type) in enumerate(
            zip(bookings, task_statuses, task_types)
        ):
            prop = next(p for p in properties if p.id == booking.property_id)

            # Determine task schedule based on type
            if task_type == TaskType.CLEANING:
                scheduled_date = booking.checkout_date
                scheduled_time = prop.default_checkout_time
                duration = 2.0 + prop.bedrooms
                budget = prop.cleaning_budget * 1.1
            elif task_type == TaskType.COMMUNICATION:
                scheduled_date = booking.checkin_date - timedelta(days=1)
                scheduled_time = time(9, 0)
                duration = 0.25
                budget = 0.0
            elif task_type == TaskType.RESTOCKING:
                scheduled_date = booking.checkout_date
                scheduled_time = time(14, 0)
                duration = 1.0
                budget = 50.0
            elif task_type == TaskType.MAINTENANCE:
                scheduled_date = booking.checkin_date - timedelta(days=2)
                scheduled_time = time(10, 0)
                duration = 2.0
                budget = prop.maintenance_budget
            else:  # PHOTOGRAPHY
                scheduled_date = today + timedelta(days=14)
                scheduled_time = time(11, 0)
                duration = 3.0
                budget = 200.0

            # Assign human for booked/in_progress/completed tasks
            assigned_human = None
            booking_id = None
            if status in [
                TaskStatus.HUMAN_BOOKED,
                TaskStatus.IN_PROGRESS,
                TaskStatus.COMPLETED,
            ]:
                assigned_human = mock_humans[i % len(mock_humans)]
                booking_id = f"rah_booking_{uuid4().hex[:8]}"

            task = Task(
                id=uuid4(),
                type=task_type,
                property_id=prop.id,
                booking_id=booking.id,
                description=f"{task_type.value.title()} for {prop.name} - {booking.guest_name}",
                required_skills=[task_type.value],
                budget=budget,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                duration_hours=duration,
                status=status,
                rentahuman_booking_id=booking_id,
                assigned_human=assigned_human,
                checklist=[
                    "Arrive on time",
                    "Complete task checklist",
                    "Take completion photos",
                    "Report any issues",
                ],
                host_notes="Priority guest" if i % 4 == 0 else None,
            )
            session.add(task)

            print(f"  Created task: {task_type.value} for {prop.name} ({status.value})")

        await session.commit()

        print("\nDatabase seeding complete!")
        print(f"  Users: 1")
        print(f"  Properties: {len(properties)}")
        print(f"  Bookings: {len(bookings)}")
        print(f"  Tasks: {len(task_statuses)}")
        print(f"\nTest credentials:")
        print(f"  Email: ethan@example.com")
        print(f"  Password: password123")


async def main():
    """Run the seed script."""
    try:
        await seed_database()
    except Exception as e:
        print(f"Error seeding database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
