"""
Analytics-related Pydantic schemas.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsSummary(BaseModel):
    """Schema for analytics summary/overview."""

    total_properties: int = Field(..., description="Total number of properties")
    total_bookings: int = Field(..., description="Total bookings (all time)")
    total_tasks: int = Field(..., description="Total tasks created")
    tasks_completed: int = Field(..., description="Tasks completed successfully")
    tasks_pending: int = Field(..., description="Tasks pending booking")
    total_spent: float = Field(..., description="Total amount spent on humans")
    commission_earned: float = Field(..., description="Commission earned (15%)")
    average_task_cost: float = Field(..., description="Average cost per task")
    booking_success_rate: float = Field(
        ..., description="Percentage of tasks successfully booked"
    )
    completion_rate: float = Field(
        ..., description="Percentage of booked tasks completed"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_properties": 3,
                "total_bookings": 45,
                "total_tasks": 120,
                "tasks_completed": 95,
                "tasks_pending": 5,
                "total_spent": 12500.00,
                "commission_earned": 1875.00,
                "average_task_cost": 131.58,
                "booking_success_rate": 98.3,
                "completion_rate": 97.5,
            }
        }
    )


class PropertyCost(BaseModel):
    """Schema for cost breakdown by property."""

    property_id: str = Field(..., description="Property ID")
    property_name: str = Field(..., description="Property name")
    total_cost: float = Field(..., description="Total cost")
    cleaning_cost: float = Field(..., description="Cleaning costs")
    maintenance_cost: float = Field(..., description="Maintenance costs")
    other_cost: float = Field(..., description="Other costs")
    task_count: int = Field(..., description="Number of tasks")


class TaskTypeCost(BaseModel):
    """Schema for cost breakdown by task type."""

    task_type: str = Field(..., description="Task type")
    total_cost: float = Field(..., description="Total cost")
    task_count: int = Field(..., description="Number of tasks")
    average_cost: float = Field(..., description="Average cost per task")


class CostAnalysis(BaseModel):
    """Schema for detailed cost analysis."""

    period_start: date = Field(..., description="Analysis period start")
    period_end: date = Field(..., description="Analysis period end")
    total_cost: float = Field(..., description="Total cost in period")
    by_property: list[PropertyCost] = Field(..., description="Costs by property")
    by_task_type: list[TaskTypeCost] = Field(..., description="Costs by task type")
    daily_average: float = Field(..., description="Daily average cost")
    projected_monthly: float = Field(..., description="Projected monthly cost")


class HumanStats(BaseModel):
    """Schema for individual human performance stats."""

    human_id: str = Field(..., description="Human ID")
    human_name: str = Field(..., description="Human name")
    tasks_completed: int = Field(..., description="Tasks completed")
    total_spent: float = Field(..., description="Total spent on this human")
    average_rating: float = Field(..., description="Average rating given")
    on_time_rate: float = Field(..., description="Percentage of on-time completions")
    properties_worked: int = Field(..., description="Number of properties worked")


class HumanPerformance(BaseModel):
    """Schema for human performance metrics."""

    period_start: date = Field(..., description="Analysis period start")
    period_end: date = Field(..., description="Analysis period end")
    total_humans_used: int = Field(..., description="Total unique humans")
    top_performers: list[HumanStats] = Field(..., description="Top performing humans")
    most_used: list[HumanStats] = Field(..., description="Most frequently used humans")
    average_rating_given: float = Field(..., description="Average rating you've given")


class ROIAnalysis(BaseModel):
    """Schema for ROI calculation."""

    period_start: date = Field(..., description="Analysis period start")
    period_end: date = Field(..., description="Analysis period end")
    total_automation_cost: float = Field(
        ..., description="Total cost of automated tasks"
    )
    estimated_manual_cost: float = Field(
        ..., description="Estimated cost if done manually"
    )
    time_saved_hours: float = Field(
        ..., description="Estimated hours saved through automation"
    )
    cost_savings: float = Field(..., description="Dollar savings vs manual")
    cost_savings_percentage: float = Field(..., description="Percentage savings")
    roi_percentage: float = Field(..., description="Return on investment percentage")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period_start": "2026-01-01",
                "period_end": "2026-02-22",
                "total_automation_cost": 5000.00,
                "estimated_manual_cost": 7500.00,
                "time_saved_hours": 120.0,
                "cost_savings": 2500.00,
                "cost_savings_percentage": 33.3,
                "roi_percentage": 50.0,
            }
        }
    )
