"""
MCP Server for RentAHuman API integration.

Exposes RentAHuman functionality as MCP tools for AI agents.
This allows AI assistants like Claude to search for humans,
create bookings, and manage tasks through the RentAHuman platform.

Run with: python -m mcp_server
Or start via uvicorn for SSE transport.
"""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    LATEST_PROTOCOL_VERSION,
    ListToolsResult,
    Tool,
    TextContent,
    CallToolResult,
)

from services.rentahuman_client import get_rentahuman_client, Human, Booking

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
server = Server("rentahuman-mcp")


def human_to_dict(human: Human) -> dict:
    """Convert Human dataclass to dictionary."""
    return {
        "id": human.id,
        "name": human.name,
        "skills": human.skills,
        "location": human.location,
        "rate": human.rate,
        "currency": human.currency,
        "rating": human.rating,
        "reviews": human.reviews,
        "availability": human.availability,
        "bio": human.bio,
        "photo_url": human.photo_url,
    }


def booking_to_dict(booking: Booking) -> dict:
    """Convert Booking dataclass to dictionary."""
    return {
        "id": booking.id,
        "human_id": booking.human_id,
        "human_name": booking.human_name,
        "task_description": booking.task_description,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "budget": booking.budget,
        "status": booking.status,
        "total_cost": booking.total_cost,
    }


@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available RentAHuman tools."""
    return ListToolsResult(
        tools=[
            Tool(
                name="search_humans",
                description="""Search for available humans on RentAHuman by location and criteria.

Use this to find service providers (cleaners, handymen, photographers, etc.)
in a specific area. Returns a list of matching humans with their rates,
ratings, and availability.

Example: Search for cleaners in Las Vegas with a budget of $40/hour.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City, state or ZIP code (e.g., 'Las Vegas, NV' or '89101')",
                        },
                        "skill": {
                            "type": "string",
                            "description": "Skill filter (e.g., 'cleaning', 'handyman', 'photography')",
                        },
                        "budget_max": {
                            "type": "number",
                            "description": "Maximum hourly rate in USD",
                        },
                        "rating_min": {
                            "type": "number",
                            "description": "Minimum rating (3.0-5.0)",
                            "minimum": 3.0,
                            "maximum": 5.0,
                        },
                        "availability": {
                            "type": "string",
                            "enum": ["available", "next_24h", "next_week", "flexible"],
                            "description": "Availability filter",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (1-100)",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                        },
                    },
                    "required": ["location"],
                },
            ),
            Tool(
                name="create_booking",
                description="""Create a booking for a human on RentAHuman.

Books a specific human for a task. Requires the human's ID (from search results),
task details, time window, and budget. Returns booking confirmation with ID.

Important: Ensure the human is available before booking. The budget should
cover the estimated duration at the human's hourly rate.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "human_id": {
                            "type": "string",
                            "description": "ID of the human to book (from search results)",
                        },
                        "task_description": {
                            "type": "string",
                            "description": "Detailed description of the task to be performed",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO 8601 format (e.g., '2026-02-25T09:00:00Z')",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in ISO 8601 format",
                        },
                        "budget": {
                            "type": "number",
                            "description": "Maximum budget in USD for the entire task",
                        },
                        "special_requests": {
                            "type": "string",
                            "description": "Any special instructions or requests",
                        },
                    },
                    "required": ["human_id", "task_description", "start_time", "end_time", "budget"],
                },
            ),
            Tool(
                name="get_booking_status",
                description="""Get the current status of a RentAHuman booking.

Check on an existing booking to see its status (pending, confirmed,
in_progress, completed, cancelled), assigned human details, and
completion information.

Use this to track bookings and verify task completion.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "booking_id": {
                            "type": "string",
                            "description": "The booking ID to check",
                        },
                    },
                    "required": ["booking_id"],
                },
            ),
            Tool(
                name="list_skills",
                description="""Get a list of all available skills on RentAHuman.

Returns all skill categories with descriptions. Use this to understand
what types of services are available before searching for humans.

Common skills: cleaning, handyman, photography, moving, organizing,
deep_cleaning, plumbing, electrical.""",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="cancel_booking",
                description="""Cancel an existing RentAHuman booking.

Cancels a booking by ID. Provide a reason for better service quality.
Cancellation policies may apply depending on timing.

Note: Late cancellations (within 24h) may incur fees.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "booking_id": {
                            "type": "string",
                            "description": "The booking ID to cancel",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for cancellation",
                        },
                    },
                    "required": ["booking_id"],
                },
            ),
            Tool(
                name="get_human_profile",
                description="""Get detailed profile information for a specific human.

Retrieves full profile including bio, skills, rate, rating, reviews,
and availability for a specific human by their ID.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "human_id": {
                            "type": "string",
                            "description": "The human's ID",
                        },
                    },
                    "required": ["human_id"],
                },
            ),
        ]
    )


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    client = get_rentahuman_client()

    try:
        if name == "search_humans":
            humans = await client.search_humans(
                location=arguments["location"],
                skill=arguments.get("skill"),
                availability=arguments.get("availability"),
                budget_max=arguments.get("budget_max"),
                rating_min=arguments.get("rating_min"),
                limit=arguments.get("limit", 10),
            )

            if not humans:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="No humans found matching your criteria. Try expanding your search parameters.",
                        )
                    ]
                )

            result = {
                "total": len(humans),
                "humans": [human_to_dict(h) for h in humans],
            }

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2),
                    )
                ]
            )

        elif name == "create_booking":
            booking = await client.create_booking(
                human_id=arguments["human_id"],
                task_description=arguments["task_description"],
                start_time=arguments["start_time"],
                end_time=arguments["end_time"],
                budget=arguments["budget"],
                special_requests=arguments.get("special_requests"),
            )

            if not booking:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="Failed to create booking. The human may not be available or the request was invalid.",
                        )
                    ],
                    isError=True,
                )

            result = {
                "success": True,
                "booking": booking_to_dict(booking),
                "message": f"Successfully booked {booking.human_name} for ${booking.total_cost:.2f}",
            }

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2),
                    )
                ]
            )

        elif name == "get_booking_status":
            status = await client.get_booking_status(arguments["booking_id"])

            if not status:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Booking {arguments['booking_id']} not found.",
                        )
                    ],
                    isError=True,
                )

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(status, indent=2),
                    )
                ]
            )

        elif name == "list_skills":
            skills = await client.list_skills()

            result = {
                "total": len(skills),
                "skills": skills,
            }

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2),
                    )
                ]
            )

        elif name == "cancel_booking":
            success = await client.cancel_booking(
                booking_id=arguments["booking_id"],
                reason=arguments.get("reason"),
            )

            if success:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Booking {arguments['booking_id']} has been cancelled successfully.",
                        )
                    ]
                )
            else:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Failed to cancel booking {arguments['booking_id']}. It may already be cancelled or completed.",
                        )
                    ],
                    isError=True,
                )

        elif name == "get_human_profile":
            human = await client.get_human(arguments["human_id"])

            if not human:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Human {arguments['human_id']} not found.",
                        )
                    ],
                    isError=True,
                )

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(human_to_dict(human), indent=2),
                    )
                ]
            )

        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Unknown tool: {name}",
                    )
                ],
                isError=True,
            )

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Error: {str(e)}",
                )
            ],
            isError=True,
        )


async def main():
    """Run the MCP server."""
    logger.info("Starting RentAHuman MCP server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
