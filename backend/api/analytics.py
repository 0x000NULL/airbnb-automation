"""
Analytics API endpoints.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, select

from api.deps import CurrentUser, DbSession
from models.booking import AirbnbBooking
from models.property import Property
from models.task import Task, TaskStatus, TaskType
from schemas.analytics import (
    AnalyticsSummary,
    CostAnalysis,
    HumanPerformance,
    HumanStats,
    PropertyCost,
    ROIAnalysis,
    TaskTypeCost,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    current_user: CurrentUser,
    db: DbSession,
) -> AnalyticsSummary:
    """
    Get overview analytics summary.
    """
    try:
        return await _get_analytics_summary(current_user, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching analytics summary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analytics summary: {str(e)}",
        )


async def _get_analytics_summary(current_user, db) -> AnalyticsSummary:
    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    if not property_ids:
        return AnalyticsSummary(
            total_properties=0,
            total_bookings=0,
            total_tasks=0,
            tasks_completed=0,
            tasks_pending=0,
            total_spent=0.0,
            commission_earned=0.0,
            average_task_cost=0.0,
            booking_success_rate=0.0,
            completion_rate=0.0,
        )

    # Count properties
    total_properties = len(property_ids)

    # Count bookings
    booking_count = await db.execute(
        select(func.count(AirbnbBooking.id)).where(
            AirbnbBooking.property_id.in_(property_ids)
        )
    )
    total_bookings = booking_count.scalar() or 0

    # Count tasks by status
    task_counts = await db.execute(
        select(Task.status, func.count(Task.id))
        .where(Task.property_id.in_(property_ids))
        .group_by(Task.status)
    )
    task_status_counts = dict(task_counts.all())

    total_tasks = sum(task_status_counts.values())
    tasks_completed = task_status_counts.get(TaskStatus.COMPLETED, 0)
    tasks_pending = task_status_counts.get(TaskStatus.PENDING, 0)
    tasks_booked = task_status_counts.get(TaskStatus.HUMAN_BOOKED, 0)
    tasks_in_progress = task_status_counts.get(TaskStatus.IN_PROGRESS, 0)

    # Calculate total spent (sum of completed task budgets)
    spent_result = await db.execute(
        select(func.sum(Task.budget)).where(
            and_(
                Task.property_id.in_(property_ids),
                Task.status == TaskStatus.COMPLETED,
            )
        )
    )
    total_spent = spent_result.scalar() or 0.0

    # Calculate commission (15% of total spent)
    commission_earned = total_spent * 0.15

    # Calculate average task cost
    average_task_cost = total_spent / tasks_completed if tasks_completed > 0 else 0.0

    # Calculate success rates
    tasks_that_needed_booking = tasks_completed + tasks_booked + tasks_in_progress
    booking_success_rate = (
        (tasks_that_needed_booking / (tasks_that_needed_booking + tasks_pending) * 100)
        if (tasks_that_needed_booking + tasks_pending) > 0
        else 0.0
    )

    completion_rate = (
        (tasks_completed / tasks_that_needed_booking * 100)
        if tasks_that_needed_booking > 0
        else 0.0
    )

    return AnalyticsSummary(
        total_properties=total_properties,
        total_bookings=total_bookings,
        total_tasks=total_tasks,
        tasks_completed=tasks_completed,
        tasks_pending=tasks_pending,
        total_spent=total_spent,
        commission_earned=commission_earned,
        average_task_cost=average_task_cost,
        booking_success_rate=round(booking_success_rate, 1),
        completion_rate=round(completion_rate, 1),
    )


@router.get("/costs", response_model=CostAnalysis)
async def get_cost_analysis(
    current_user: CurrentUser,
    db: DbSession,
    days: int = Query(30, ge=7, le=365, description="Days to analyze"),
) -> CostAnalysis:
    """
    Get detailed cost analysis.
    """
    try:
        return await _get_cost_analysis(current_user, db, days)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching cost analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch cost analysis: {str(e)}",
        )


async def _get_cost_analysis(current_user, db, days: int) -> CostAnalysis:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Get user's properties
    property_result = await db.execute(
        select(Property).where(Property.host_id == current_user.id)
    )
    properties = {p.id: p for p in property_result.scalars().all()}

    if not properties:
        return CostAnalysis(
            period_start=start_date,
            period_end=end_date,
            total_cost=0.0,
            by_property=[],
            by_task_type=[],
            daily_average=0.0,
            projected_monthly=0.0,
        )

    # Get completed tasks in the period
    result = await db.execute(
        select(Task).where(
            and_(
                Task.property_id.in_(properties.keys()),
                Task.status == TaskStatus.COMPLETED,
                Task.scheduled_date >= start_date,
                Task.scheduled_date <= end_date,
            )
        )
    )
    tasks = result.scalars().all()

    # Calculate by property
    property_costs: dict[str, dict] = {}
    for task in tasks:
        prop_id = str(task.property_id)
        if prop_id not in property_costs:
            prop = properties.get(task.property_id)
            property_costs[prop_id] = {
                "property_id": prop_id,
                "property_name": prop.name if prop else "Unknown",
                "total_cost": 0.0,
                "cleaning_cost": 0.0,
                "maintenance_cost": 0.0,
                "other_cost": 0.0,
                "task_count": 0,
            }

        property_costs[prop_id]["total_cost"] += task.budget
        property_costs[prop_id]["task_count"] += 1

        if task.type == TaskType.CLEANING:
            property_costs[prop_id]["cleaning_cost"] += task.budget
        elif task.type == TaskType.MAINTENANCE:
            property_costs[prop_id]["maintenance_cost"] += task.budget
        else:
            property_costs[prop_id]["other_cost"] += task.budget

    # Calculate by task type
    type_costs: dict[str, dict] = {}
    for task in tasks:
        task_type = task.type.value
        if task_type not in type_costs:
            type_costs[task_type] = {
                "task_type": task_type,
                "total_cost": 0.0,
                "task_count": 0,
            }
        type_costs[task_type]["total_cost"] += task.budget
        type_costs[task_type]["task_count"] += 1

    for type_data in type_costs.values():
        type_data["average_cost"] = (
            type_data["total_cost"] / type_data["task_count"]
            if type_data["task_count"] > 0
            else 0.0
        )

    total_cost = sum(t.budget for t in tasks)
    daily_average = total_cost / days if days > 0 else 0.0
    projected_monthly = daily_average * 30

    return CostAnalysis(
        period_start=start_date,
        period_end=end_date,
        total_cost=total_cost,
        by_property=[PropertyCost(**p) for p in property_costs.values()],
        by_task_type=[TaskTypeCost(**t) for t in type_costs.values()],
        daily_average=round(daily_average, 2),
        projected_monthly=round(projected_monthly, 2),
    )


@router.get("/humans", response_model=HumanPerformance)
async def get_human_performance(
    current_user: CurrentUser,
    db: DbSession,
    days: int = Query(30, ge=7, le=365, description="Days to analyze"),
) -> HumanPerformance:
    """
    Get human performance metrics.
    """
    try:
        return await _get_human_performance(current_user, db, days)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching human performance metrics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch human performance metrics: {str(e)}",
        )


async def _get_human_performance(current_user, db, days: int) -> HumanPerformance:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Get user's properties
    property_result = await db.execute(
        select(Property.id).where(Property.host_id == current_user.id)
    )
    property_ids = [p for p in property_result.scalars().all()]

    if not property_ids:
        return HumanPerformance(
            period_start=start_date,
            period_end=end_date,
            total_humans_used=0,
            top_performers=[],
            most_used=[],
            average_rating_given=0.0,
        )

    # Get completed tasks with humans assigned
    result = await db.execute(
        select(Task).where(
            and_(
                Task.property_id.in_(property_ids),
                Task.status == TaskStatus.COMPLETED,
                Task.assigned_human.is_not(None),
                Task.scheduled_date >= start_date,
                Task.scheduled_date <= end_date,
            )
        )
    )
    tasks = result.scalars().all()

    # Aggregate by human
    human_stats: dict[str, dict] = {}
    for task in tasks:
        if not task.assigned_human:
            continue

        human_id = task.assigned_human.get("id", "unknown")
        if human_id not in human_stats:
            human_stats[human_id] = {
                "human_id": human_id,
                "human_name": task.assigned_human.get("name", "Unknown"),
                "tasks_completed": 0,
                "total_spent": 0.0,
                "ratings": [],
                "properties": set(),
            }

        human_stats[human_id]["tasks_completed"] += 1
        human_stats[human_id]["total_spent"] += task.budget
        if task.assigned_human.get("rating"):
            human_stats[human_id]["ratings"].append(task.assigned_human["rating"])
        human_stats[human_id]["properties"].add(str(task.property_id))

    # Convert to stats objects
    stats_list = []
    for human_id, data in human_stats.items():
        avg_rating = (
            sum(data["ratings"]) / len(data["ratings"])
            if data["ratings"]
            else 0.0
        )
        # Calculate on_time_rate from actual deadline vs completed_at data
        # Reuse already-fetched tasks instead of redundant DB query per human
        tasks_with_deadline = [
            t for t in tasks
            if t.assigned_human and t.assigned_human.get("id") == human_id
            and t.deadline is not None and t.completed_at is not None
        ]
        if tasks_with_deadline:
            on_time_count = sum(1 for t in tasks_with_deadline if t.completed_at <= t.deadline)
            on_time_rate = round((on_time_count / len(tasks_with_deadline)) * 100, 1)
        else:
            on_time_rate = 0.0  # No deadline data available

        stats_list.append(
            HumanStats(
                human_id=human_id,
                human_name=data["human_name"],
                tasks_completed=data["tasks_completed"],
                total_spent=data["total_spent"],
                average_rating=round(avg_rating, 2),
                on_time_rate=on_time_rate,
                properties_worked=len(data["properties"]),
            )
        )

    # Sort for top performers (by rating) and most used (by task count)
    top_performers = sorted(stats_list, key=lambda x: x.average_rating, reverse=True)[:5]
    most_used = sorted(stats_list, key=lambda x: x.tasks_completed, reverse=True)[:5]

    # Calculate overall average rating
    all_ratings = []
    for data in human_stats.values():
        all_ratings.extend(data["ratings"])
    avg_rating_given = sum(all_ratings) / len(all_ratings) if all_ratings else 0.0

    return HumanPerformance(
        period_start=start_date,
        period_end=end_date,
        total_humans_used=len(human_stats),
        top_performers=top_performers,
        most_used=most_used,
        average_rating_given=round(avg_rating_given, 2),
    )


@router.get("/roi", response_model=ROIAnalysis)
async def get_roi_analysis(
    current_user: CurrentUser,
    db: DbSession,
    days: int = Query(30, ge=7, le=365, description="Days to analyze"),
) -> ROIAnalysis:
    """
    Get ROI calculation.
    """
    try:
        return await _get_roi_analysis(current_user, db, days)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching ROI analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch ROI analysis: {str(e)}",
        )


async def _get_roi_analysis(current_user, db, days: int) -> ROIAnalysis:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Get user's properties
    property_result = await db.execute(
        select(Property).where(Property.host_id == current_user.id)
    )
    properties = list(property_result.scalars().all())
    property_ids = [p.id for p in properties]

    if not property_ids:
        return ROIAnalysis(
            period_start=start_date,
            period_end=end_date,
            total_automation_cost=0.0,
            estimated_manual_cost=0.0,
            time_saved_hours=0.0,
            cost_savings=0.0,
            cost_savings_percentage=0.0,
            roi_percentage=0.0,
        )

    # Get completed tasks in the period
    result = await db.execute(
        select(Task).where(
            and_(
                Task.property_id.in_(property_ids),
                Task.status == TaskStatus.COMPLETED,
                Task.scheduled_date >= start_date,
                Task.scheduled_date <= end_date,
            )
        )
    )
    tasks = result.scalars().all()

    # Calculate automation cost (actual task budgets)
    total_automation_cost = sum(t.budget for t in tasks)

    # Estimate manual cost (typically 30-50% higher)
    # Assumptions:
    # - Manual hiring takes 1-2 hours per task at $30/hour for admin time
    # - Manual rates are typically 20% higher (no platform efficiency)
    admin_hours_per_task = 1.5
    admin_rate = 30.0
    manual_rate_premium = 1.2

    estimated_manual_cost = (
        total_automation_cost * manual_rate_premium
        + len(tasks) * admin_hours_per_task * admin_rate
    )

    # Calculate time saved
    # Assumptions:
    # - 2 hours saved per task (searching, hiring, coordinating, payment)
    time_saved_hours = len(tasks) * 2.0

    # Calculate savings
    cost_savings = estimated_manual_cost - total_automation_cost
    cost_savings_percentage = (
        (cost_savings / estimated_manual_cost * 100)
        if estimated_manual_cost > 0
        else 0.0
    )

    # Calculate ROI
    # ROI = (Savings / Cost) * 100
    roi_percentage = (
        (cost_savings / total_automation_cost * 100)
        if total_automation_cost > 0
        else 0.0
    )

    return ROIAnalysis(
        period_start=start_date,
        period_end=end_date,
        total_automation_cost=round(total_automation_cost, 2),
        estimated_manual_cost=round(estimated_manual_cost, 2),
        time_saved_hours=round(time_saved_hours, 1),
        cost_savings=round(cost_savings, 2),
        cost_savings_percentage=round(cost_savings_percentage, 1),
        roi_percentage=round(roi_percentage, 1),
    )
