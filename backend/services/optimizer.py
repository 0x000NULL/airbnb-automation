"""
Cost optimization service for task booking.

Analyzes historical data to suggest budget adjustments and optimize costs.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.property import Property
from models.task import Task, TaskStatus, TaskType

logger = logging.getLogger(__name__)


@dataclass
class CostInsight:
    """Cost optimization insight."""

    property_id: UUID
    property_name: str
    task_type: TaskType
    average_cost: float
    suggested_budget: float
    potential_savings: float
    confidence: float  # 0-1, based on data availability


@dataclass
class BulkBookingOpportunity:
    """Opportunity for bulk booking discount."""

    property_ids: list[UUID]
    task_type: TaskType
    scheduled_date: date
    task_count: int
    estimated_savings_percent: float


@dataclass
class OptimizationReport:
    """Full optimization report."""

    cost_insights: list[CostInsight]
    bulk_opportunities: list[BulkBookingOpportunity]
    total_potential_savings: float
    analysis_period_days: int


class CostOptimizer:
    """
    Analyzes historical task costs and suggests optimizations.

    Features:
    - Track historical costs per property/task type
    - Suggest budget adjustments based on market rates
    - Identify bulk booking opportunities
    - Calculate potential savings
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_property_costs(
        self,
        property_id: UUID,
        days_back: int = 90,
    ) -> list[CostInsight]:
        """
        Analyze costs for a specific property.

        Args:
            property_id: Property to analyze
            days_back: Number of days of historical data to analyze

        Returns:
            List of cost insights by task type
        """
        start_date = date.today() - timedelta(days=days_back)

        # Get property info
        prop_result = await self.db.execute(
            select(Property).where(Property.id == property_id)
        )
        property_obj = prop_result.scalar_one_or_none()

        if not property_obj:
            return []

        insights = []

        for task_type in TaskType:
            # Get completed tasks for this type
            result = await self.db.execute(
                select(
                    func.avg(Task.budget).label("avg_cost"),
                    func.count(Task.id).label("task_count"),
                    func.min(Task.budget).label("min_cost"),
                    func.max(Task.budget).label("max_cost"),
                )
                .where(
                    Task.property_id == property_id,
                    Task.type == task_type,
                    Task.status == TaskStatus.COMPLETED,
                    Task.scheduled_date >= start_date,
                )
            )
            row = result.one()

            if row.task_count and row.task_count >= 3:
                avg_cost = float(row.avg_cost or 0)

                # Calculate suggested budget (slightly below average for savings)
                suggested_budget = round(avg_cost * 0.95, 2)

                # Get current budget setting
                if task_type == TaskType.CLEANING:
                    current_budget = property_obj.cleaning_budget
                elif task_type == TaskType.MAINTENANCE:
                    current_budget = property_obj.maintenance_budget
                else:
                    current_budget = avg_cost

                potential_savings = max(0, current_budget - suggested_budget)

                # Confidence based on sample size
                confidence = min(1.0, row.task_count / 20)

                insights.append(
                    CostInsight(
                        property_id=property_id,
                        property_name=property_obj.name,
                        task_type=task_type,
                        average_cost=avg_cost,
                        suggested_budget=suggested_budget,
                        potential_savings=potential_savings,
                        confidence=confidence,
                    )
                )

        return insights

    async def find_bulk_opportunities(
        self,
        host_id: UUID,
        days_ahead: int = 14,
    ) -> list[BulkBookingOpportunity]:
        """
        Find opportunities for bulk booking discounts.

        Multiple tasks on the same day could be bundled for savings.

        Args:
            host_id: Host to analyze
            days_ahead: Number of days to look ahead

        Returns:
            List of bulk booking opportunities
        """
        end_date = date.today() + timedelta(days=days_ahead)

        # Get host's properties
        prop_result = await self.db.execute(
            select(Property.id).where(Property.host_id == host_id)
        )
        property_ids = [p for p in prop_result.scalars().all()]

        if not property_ids:
            return []

        # Find dates with multiple pending tasks of same type
        result = await self.db.execute(
            select(
                Task.scheduled_date,
                Task.type,
                func.count(Task.id).label("task_count"),
                func.array_agg(Task.property_id).label("property_ids"),
            )
            .where(
                Task.property_id.in_(property_ids),
                Task.status == TaskStatus.PENDING,
                Task.scheduled_date >= date.today(),
                Task.scheduled_date <= end_date,
            )
            .group_by(Task.scheduled_date, Task.type)
            .having(func.count(Task.id) >= 2)
        )

        opportunities = []
        for row in result:
            # Estimate savings (typically 10-15% for bulk bookings)
            savings_percent = min(20, 5 + row.task_count * 3)

            opportunities.append(
                BulkBookingOpportunity(
                    property_ids=list(set(row.property_ids)),
                    task_type=row.type,
                    scheduled_date=row.scheduled_date,
                    task_count=row.task_count,
                    estimated_savings_percent=savings_percent,
                )
            )

        return sorted(
            opportunities, key=lambda x: x.estimated_savings_percent, reverse=True
        )

    async def generate_report(
        self,
        host_id: UUID,
        days_back: int = 90,
        days_ahead: int = 14,
    ) -> OptimizationReport:
        """
        Generate full optimization report for a host.

        Args:
            host_id: Host to analyze
            days_back: Historical days for cost analysis
            days_ahead: Future days for opportunity analysis

        Returns:
            Complete optimization report
        """
        # Get all properties
        prop_result = await self.db.execute(
            select(Property).where(Property.host_id == host_id)
        )
        properties = prop_result.scalars().all()

        # Analyze each property
        all_insights = []
        for prop in properties:
            insights = await self.analyze_property_costs(prop.id, days_back)
            all_insights.extend(insights)

        # Find bulk opportunities
        bulk_opportunities = await self.find_bulk_opportunities(host_id, days_ahead)

        # Calculate total potential savings
        cost_savings = sum(i.potential_savings for i in all_insights)
        bulk_savings = sum(
            o.task_count * 20 * (o.estimated_savings_percent / 100)
            for o in bulk_opportunities
        )  # Assume $20 avg task cost for estimation

        return OptimizationReport(
            cost_insights=all_insights,
            bulk_opportunities=bulk_opportunities,
            total_potential_savings=cost_savings + bulk_savings,
            analysis_period_days=days_back,
        )

    async def get_recommended_budget(
        self,
        property_id: UUID,
        task_type: TaskType,
    ) -> Optional[float]:
        """
        Get recommended budget for a specific property and task type.

        Args:
            property_id: Property ID
            task_type: Type of task

        Returns:
            Recommended budget or None if insufficient data
        """
        insights = await self.analyze_property_costs(property_id, days_back=90)

        for insight in insights:
            if insight.task_type == task_type and insight.confidence >= 0.5:
                return insight.suggested_budget

        return None


# Singleton instance
_optimizer: Optional[CostOptimizer] = None


def get_optimizer(db: AsyncSession) -> CostOptimizer:
    """Get or create cost optimizer instance."""
    return CostOptimizer(db)
