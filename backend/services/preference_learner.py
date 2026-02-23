"""
Human preference learning service.

Tracks which humans perform best for different properties and task types,
and uses this data to improve future booking decisions.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.property import Property
from models.task import Task, TaskStatus, TaskType

logger = logging.getLogger(__name__)


@dataclass
class HumanPerformance:
    """Performance metrics for a human."""

    human_id: str
    human_name: str
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    average_rating: float
    total_earned: float
    preferred_for_types: list[TaskType] = field(default_factory=list)


@dataclass
class PropertyHumanMatch:
    """Match score between a property and a human."""

    property_id: UUID
    human_id: str
    human_name: str
    match_score: float  # 0-100
    tasks_completed: int
    success_rate: float
    average_rating: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class LearningInsights:
    """Insights from preference learning."""

    top_performers: list[HumanPerformance]
    property_matches: dict[UUID, list[PropertyHumanMatch]]
    recommended_humans: dict[str, list[str]]  # task_type -> human_ids


class PreferenceLearner:
    """
    Learns preferences for humans based on historical task completion.

    Features:
    - Track success rates per human/property combination
    - Learn which humans work best for specific task types
    - Prefer successful humans for future bookings
    - Match premium properties with high-rated humans
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_human_performance(
        self,
        host_id: UUID,
        days_back: int = 90,
    ) -> list[HumanPerformance]:
        """
        Get performance metrics for all humans who worked for this host.

        Args:
            host_id: Host to analyze
            days_back: Number of days of historical data

        Returns:
            List of human performance metrics
        """
        start_date = date.today() - timedelta(days=days_back)

        # Get host's properties
        prop_result = await self.db.execute(
            select(Property.id).where(Property.host_id == host_id)
        )
        property_ids = [p for p in prop_result.scalars().all()]

        if not property_ids:
            return []

        # Get all tasks with assigned humans
        result = await self.db.execute(
            select(Task)
            .where(
                Task.property_id.in_(property_ids),
                Task.assigned_human.isnot(None),
                Task.scheduled_date >= start_date,
            )
            .order_by(Task.scheduled_date.desc())
        )
        tasks = result.scalars().all()

        # Aggregate by human
        human_stats: dict[str, dict] = {}

        for task in tasks:
            human = task.assigned_human
            human_id = human.get("id")

            if human_id not in human_stats:
                human_stats[human_id] = {
                    "name": human.get("name", "Unknown"),
                    "total": 0,
                    "completed": 0,
                    "ratings": [],
                    "earned": 0.0,
                    "types": set(),
                }

            stats = human_stats[human_id]
            stats["total"] += 1
            stats["types"].add(task.type)

            if task.status == TaskStatus.COMPLETED:
                stats["completed"] += 1
                stats["earned"] += task.budget

            if human.get("rating"):
                stats["ratings"].append(human.get("rating"))

        # Build performance objects
        performances = []
        for human_id, stats in human_stats.items():
            completion_rate = (
                stats["completed"] / stats["total"] if stats["total"] > 0 else 0
            )
            avg_rating = (
                sum(stats["ratings"]) / len(stats["ratings"])
                if stats["ratings"]
                else 0
            )

            performances.append(
                HumanPerformance(
                    human_id=human_id,
                    human_name=stats["name"],
                    total_tasks=stats["total"],
                    completed_tasks=stats["completed"],
                    completion_rate=completion_rate,
                    average_rating=avg_rating,
                    total_earned=stats["earned"],
                    preferred_for_types=list(stats["types"]),
                )
            )

        # Sort by completion rate and rating
        performances.sort(
            key=lambda x: (x.completion_rate, x.average_rating), reverse=True
        )

        return performances

    async def get_property_human_matches(
        self,
        property_id: UUID,
        task_type: Optional[TaskType] = None,
        days_back: int = 180,
    ) -> list[PropertyHumanMatch]:
        """
        Get best human matches for a property based on historical data.

        Args:
            property_id: Property to match
            task_type: Optional filter by task type
            days_back: Historical data window

        Returns:
            List of human matches sorted by score
        """
        start_date = date.today() - timedelta(days=days_back)

        # Query tasks for this property
        query = select(Task).where(
            Task.property_id == property_id,
            Task.assigned_human.isnot(None),
            Task.scheduled_date >= start_date,
        )

        if task_type:
            query = query.where(Task.type == task_type)

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        # Aggregate by human
        human_stats: dict[str, dict] = {}

        for task in tasks:
            human = task.assigned_human
            human_id = human.get("id")

            if human_id not in human_stats:
                human_stats[human_id] = {
                    "name": human.get("name", "Unknown"),
                    "total": 0,
                    "completed": 0,
                    "ratings": [],
                    "reasons": [],
                }

            stats = human_stats[human_id]
            stats["total"] += 1

            if task.status == TaskStatus.COMPLETED:
                stats["completed"] += 1

            if human.get("rating"):
                stats["ratings"].append(human.get("rating"))

        # Calculate match scores
        matches = []
        for human_id, stats in human_stats.items():
            success_rate = (
                stats["completed"] / stats["total"] if stats["total"] > 0 else 0
            )
            avg_rating = (
                sum(stats["ratings"]) / len(stats["ratings"])
                if stats["ratings"]
                else 0
            )

            # Calculate match score (0-100)
            # Factors: success rate (40%), rating (40%), experience (20%)
            score = 0
            reasons = []

            # Success rate contribution
            success_score = success_rate * 40
            score += success_score
            if success_rate >= 0.95:
                reasons.append("Excellent completion rate")
            elif success_rate >= 0.8:
                reasons.append("Good completion rate")

            # Rating contribution
            rating_score = (avg_rating / 5) * 40 if avg_rating > 0 else 20
            score += rating_score
            if avg_rating >= 4.8:
                reasons.append("Highly rated")
            elif avg_rating >= 4.5:
                reasons.append("Well rated")

            # Experience contribution
            exp_score = min(20, stats["total"] * 4)  # Max 5 tasks for full score
            score += exp_score
            if stats["total"] >= 5:
                reasons.append("Experienced with this property")
            elif stats["total"] >= 2:
                reasons.append("Has worked here before")

            matches.append(
                PropertyHumanMatch(
                    property_id=property_id,
                    human_id=human_id,
                    human_name=stats["name"],
                    match_score=round(score, 1),
                    tasks_completed=stats["completed"],
                    success_rate=success_rate,
                    average_rating=avg_rating,
                    reasons=reasons,
                )
            )

        # Sort by match score
        matches.sort(key=lambda x: x.match_score, reverse=True)

        return matches

    async def get_recommended_humans(
        self,
        host_id: UUID,
        task_type: TaskType,
        property_id: Optional[UUID] = None,
        min_rating: float = 4.0,
        top_n: int = 5,
    ) -> list[str]:
        """
        Get recommended human IDs for a task.

        Args:
            host_id: Host making the request
            task_type: Type of task
            property_id: Optional property for property-specific recommendations
            min_rating: Minimum rating threshold
            top_n: Number of recommendations

        Returns:
            List of recommended human IDs
        """
        # Get property-specific matches if property provided
        if property_id:
            matches = await self.get_property_human_matches(
                property_id, task_type, days_back=180
            )

            # Filter by rating and return top matches
            qualified = [
                m.human_id for m in matches if m.average_rating >= min_rating
            ]

            if len(qualified) >= top_n:
                return qualified[:top_n]

        # Fall back to host-wide performance
        performances = await self.get_human_performance(host_id, days_back=180)

        # Filter by task type preference and rating
        qualified = [
            p.human_id
            for p in performances
            if task_type in p.preferred_for_types and p.average_rating >= min_rating
        ]

        return qualified[:top_n]

    async def should_prefer_human(
        self,
        human_id: str,
        property_id: UUID,
        task_type: TaskType,
    ) -> tuple[bool, float, list[str]]:
        """
        Check if a human should be preferred for a property/task combination.

        Args:
            human_id: Human to evaluate
            property_id: Property for the task
            task_type: Type of task

        Returns:
            Tuple of (should_prefer, confidence_score, reasons)
        """
        matches = await self.get_property_human_matches(
            property_id, task_type, days_back=180
        )

        for match in matches:
            if match.human_id == human_id:
                should_prefer = match.match_score >= 70
                confidence = match.match_score / 100
                return (should_prefer, confidence, match.reasons)

        return (False, 0.0, ["No prior history with this property"])

    async def generate_insights(
        self,
        host_id: UUID,
    ) -> LearningInsights:
        """
        Generate learning insights for a host.

        Args:
            host_id: Host to analyze

        Returns:
            Learning insights
        """
        # Get top performers
        top_performers = await self.get_human_performance(host_id, days_back=180)
        top_performers = top_performers[:10]  # Top 10

        # Get property matches
        prop_result = await self.db.execute(
            select(Property).where(Property.host_id == host_id)
        )
        properties = prop_result.scalars().all()

        property_matches: dict[UUID, list[PropertyHumanMatch]] = {}
        for prop in properties:
            matches = await self.get_property_human_matches(prop.id, days_back=180)
            property_matches[prop.id] = matches[:5]  # Top 5 per property

        # Get recommended humans by task type
        recommended_humans: dict[str, list[str]] = {}
        for task_type in TaskType:
            recommended = await self.get_recommended_humans(
                host_id, task_type, top_n=5
            )
            recommended_humans[task_type.value] = recommended

        return LearningInsights(
            top_performers=top_performers,
            property_matches=property_matches,
            recommended_humans=recommended_humans,
        )


def get_preference_learner(db: AsyncSession) -> PreferenceLearner:
    """Get preference learner instance."""
    return PreferenceLearner(db)
