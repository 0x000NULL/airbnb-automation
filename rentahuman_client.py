"""
RentAHuman MCP Client
Provides a Model Context Protocol server for integrating RentAHuman API with AI agents.
"""

import os
import json
import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API key from environment
RENTAHUMAN_API_KEY = os.getenv("RENTAHUMAN_API_KEY", "rah_your_api_key_here")
RENTAHUMAN_BASE_URL = "https://api.rentahuman.ai"

# Mock mode for testing
MOCK_MODE = os.getenv("RENTAHUMAN_MOCK_MODE", "false").lower() == "true"


@dataclass
class Human:
    """Represents a human available for hire"""
    id: str
    name: str
    skills: List[str]
    location: str
    rate: float
    currency: str = "USD"
    rating: float = 4.5
    reviews: int = 0
    availability: str = "available"
    bio: str = ""


@dataclass
class Booking:
    """Represents a booking request"""
    id: str
    human_id: str
    human_name: str
    task_description: str
    start_time: str
    end_time: str
    budget: float
    status: str  # pending, confirmed, in_progress, completed, cancelled
    total_cost: float = 0.0


class RentAHumanClient:
    """
    Client for RentAHuman API
    Provides methods to search for humans and create bookings
    """

    def __init__(self, api_key: str = RENTAHUMAN_API_KEY, base_url: str = RENTAHUMAN_BASE_URL):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "RentAHuman-MCP/1.0"
        }

    def search_humans(
        self,
        location: str,
        skill: Optional[str] = None,
        availability: Optional[str] = None,
        budget_max: Optional[float] = None,
        rating_min: Optional[float] = 3.0,
        limit: int = 10
    ) -> List[Human]:
        """
        Search for available humans by location and skill
        
        Args:
            location: City, state or zip code (e.g., "Las Vegas, NV")
            skill: Skill type (e.g., "cleaning", "handyman", "photography")
            availability: "available", "next_24h", "next_week", "flexible"
            budget_max: Maximum hourly rate in USD
            rating_min: Minimum rating (3.0-5.0)
            limit: Max results (10-100)
        
        Returns:
            List of Human objects matching criteria
        """
        if MOCK_MODE:
            return self._mock_search_humans(location, skill)

        try:
            params = {
                "location": location,
                "limit": min(limit, 100)
            }
            if skill:
                params["skill"] = skill
            if availability:
                params["availability"] = availability
            if budget_max:
                params["budget_max"] = budget_max
            if rating_min:
                params["rating_min"] = rating_min

            response = requests.get(
                f"{self.base_url}/humans/search",
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            humans = [Human(**h) for h in data.get("humans", [])]
            
            logger.info(f"Found {len(humans)} humans in {location} with skill={skill}")
            return humans

        except requests.RequestException as e:
            logger.error(f"Error searching humans: {str(e)}")
            return []

    def create_booking(
        self,
        human_id: str,
        task_description: str,
        start_time: str,
        end_time: str,
        budget: float,
        special_requests: Optional[str] = None
    ) -> Optional[Booking]:
        """
        Create a booking for a human
        
        Args:
            human_id: ID of the human to book
            task_description: Detailed description of the task
            start_time: ISO 8601 datetime (e.g., "2026-02-25T09:00:00Z")
            end_time: ISO 8601 datetime (e.g., "2026-02-25T17:00:00Z")
            budget: Maximum budget in USD
            special_requests: Special instructions or requirements
        
        Returns:
            Booking object if successful, None otherwise
        """
        if MOCK_MODE:
            return self._mock_create_booking(human_id, task_description)

        try:
            payload = {
                "human_id": human_id,
                "task_description": task_description,
                "start_time": start_time,
                "end_time": end_time,
                "budget": budget
            }
            if special_requests:
                payload["special_requests"] = special_requests

            response = requests.post(
                f"{self.base_url}/bookings",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            booking = Booking(**data)
            
            logger.info(f"Booking created: {booking.id} for {booking.human_name}")
            return booking

        except requests.RequestException as e:
            logger.error(f"Error creating booking: {str(e)}")
            return None

    def get_booking_status(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a booking
        
        Args:
            booking_id: ID of the booking to check
        
        Returns:
            Booking details dictionary, or None if error
        """
        if MOCK_MODE:
            return self._mock_get_booking_status(booking_id)

        try:
            response = requests.get(
                f"{self.base_url}/bookings/{booking_id}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Booking {booking_id} status: {data.get('status')}")
            return data

        except requests.RequestException as e:
            logger.error(f"Error getting booking status: {str(e)}")
            return None

    def list_skills(self) -> List[Dict[str, str]]:
        """
        Get list of all available skills on RentAHuman
        
        Returns:
            List of skill dictionaries with name and description
        """
        if MOCK_MODE:
            return self._mock_list_skills()

        try:
            response = requests.get(
                f"{self.base_url}/skills",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Found {len(data)} available skills")
            return data

        except requests.RequestException as e:
            logger.error(f"Error listing skills: {str(e)}")
            return []

    def cancel_booking(self, booking_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancel an existing booking
        
        Args:
            booking_id: ID of the booking to cancel
            reason: Reason for cancellation
        
        Returns:
            True if successful, False otherwise
        """
        if MOCK_MODE:
            return True

        try:
            payload = {}
            if reason:
                payload["reason"] = reason

            response = requests.post(
                f"{self.base_url}/bookings/{booking_id}/cancel",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            logger.info(f"Booking {booking_id} cancelled")
            return True

        except requests.RequestException as e:
            logger.error(f"Error cancelling booking: {str(e)}")
            return False

    # Mock data for testing
    @staticmethod
    def _mock_search_humans(location: str, skill: Optional[str] = None) -> List[Human]:
        """Mock search results for testing"""
        mock_humans = [
            Human(
                id="human_001",
                name="Maria Garcia",
                skills=["cleaning", "organizing"],
                location=location,
                rate=25.0,
                rating=4.8,
                reviews=127,
                bio="Professional cleaner with 8 years experience"
            ),
            Human(
                id="human_002",
                name="John Smith",
                skills=["handyman", "maintenance", "repairs"],
                location=location,
                rate=35.0,
                rating=4.6,
                reviews=89,
                bio="Licensed handyman, all repairs welcome"
            ),
            Human(
                id="human_003",
                name="Alex Chen",
                skills=["photography", "videography"],
                location=location,
                rate=50.0,
                rating=4.9,
                reviews=156,
                bio="Professional photographer, Airbnb listing specialist"
            ),
        ]
        return mock_humans

    @staticmethod
    def _mock_create_booking(human_id: str, task: str) -> Booking:
        """Mock booking creation for testing"""
        return Booking(
            id=f"booking_{datetime.now().timestamp()}",
            human_id=human_id,
            human_name="Mock Human",
            task_description=task,
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            budget=150.0,
            status="pending",
            total_cost=150.0
        )

    @staticmethod
    def _mock_get_booking_status(booking_id: str) -> Dict[str, Any]:
        """Mock booking status check"""
        return {
            "id": booking_id,
            "status": "confirmed",
            "human_name": "Mock Human",
            "task": "Mock task",
            "total_cost": 150.0
        }

    @staticmethod
    def _mock_list_skills() -> List[Dict[str, str]]:
        """Mock skills list"""
        return [
            {"name": "cleaning", "description": "Household and commercial cleaning"},
            {"name": "handyman", "description": "General repairs and maintenance"},
            {"name": "photography", "description": "Professional photography services"},
            {"name": "moving", "description": "Moving and packing assistance"},
            {"name": "organizing", "description": "Organizing and decluttering"},
        ]


# Quick test
if __name__ == "__main__":
    client = RentAHumanClient()
    
    print("Testing RentAHuman API Client (Mock Mode)")
    print("=" * 60)
    
    # Test search
    print("\n1. Searching for cleaners in Las Vegas...")
    humans = client.search_humans("Las Vegas, NV", skill="cleaning")
    for human in humans:
        print(f"   • {human.name} - ${human.rate}/hr - ⭐{human.rating}")
    
    # Test booking
    print("\n2. Creating a booking...")
    booking = client.create_booking(
        human_id=humans[0].id if humans else "human_001",
        task_description="Professional cleaning for Airbnb turnover",
        start_time="2026-02-25T09:00:00Z",
        end_time="2026-02-25T17:00:00Z",
        budget=200.0
    )
    if booking:
        print(f"   Booking {booking.id}: {booking.status}")
    
    # Test status
    print("\n3. Checking booking status...")
    if booking:
        status = client.get_booking_status(booking.id)
        print(f"   Status: {status['status'] if status else 'Unknown'}")
    
    # Test skills
    print("\n4. Available skills...")
    skills = client.list_skills()
    for skill in skills[:5]:
        print(f"   • {skill['name']}: {skill['description']}")
    
    print("\n" + "=" * 60)
    print("✅ Client test complete!")
