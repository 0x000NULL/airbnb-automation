# API Reference

This document describes the REST API for the Airbnb/VRBO Hosting Automation platform.

**Base URL**: `http://localhost:8000/api/v1`

**Authentication**: Most endpoints require a JWT Bearer token in the Authorization header:
```
Authorization: Bearer <token>
```

## Authentication

### POST /auth/login

Login with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

### POST /auth/register

Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "User Name"
}
```

**Response (201):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

### POST /auth/google

Authenticate via Google OAuth.

**Request Body:**
```json
{
  "code": "google_authorization_code",
  "redirect_uri": "http://localhost:3000/auth/callback/google"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@gmail.com",
    "name": "User Name"
  }
}
```

### GET /auth/me

Get current authenticated user.

**Response (200):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## Properties

### GET /properties

List all properties for the authenticated user.

**Query Parameters:**
- `skip` (int, default: 0) - Number of records to skip
- `limit` (int, default: 100) - Maximum records to return

**Response (200):**
```json
{
  "properties": [
    {
      "id": "uuid",
      "name": "Downtown Luxury Condo",
      "location": {
        "address": "123 Main St",
        "city": "Las Vegas",
        "state": "NV",
        "zip": "89101"
      },
      "property_type": "condo",
      "bedrooms": 2,
      "bathrooms": 2,
      "max_guests": 4,
      "cleaning_budget": 75.00,
      "maintenance_budget": 100.00,
      "checkin_time": "15:00",
      "checkout_time": "11:00",
      "airbnb_enabled": true,
      "vrbo_enabled": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

### GET /properties/{id}

Get a specific property.

**Response (200):**
```json
{
  "id": "uuid",
  "name": "Downtown Luxury Condo",
  "location": {
    "address": "123 Main St",
    "city": "Las Vegas",
    "state": "NV",
    "zip": "89101"
  },
  "property_type": "condo",
  "bedrooms": 2,
  "bathrooms": 2,
  "max_guests": 4,
  "cleaning_budget": 75.00,
  "maintenance_budget": 100.00,
  "checkin_time": "15:00",
  "checkout_time": "11:00",
  "required_skills": ["cleaning", "laundry", "restocking"],
  "airbnb_enabled": true,
  "vrbo_enabled": true,
  "airbnb_listing_id": "12345",
  "vrbo_listing_id": "67890",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### POST /properties

Create a new property.

**Request Body:**
```json
{
  "name": "Beach House",
  "location": {
    "address": "456 Ocean Ave",
    "city": "San Diego",
    "state": "CA",
    "zip": "92101"
  },
  "property_type": "house",
  "bedrooms": 3,
  "bathrooms": 2,
  "max_guests": 6,
  "cleaning_budget": 100.00,
  "maintenance_budget": 150.00,
  "checkin_time": "16:00",
  "checkout_time": "10:00",
  "required_skills": ["cleaning", "pool_maintenance"]
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "name": "Beach House",
  ...
}
```

### PUT /properties/{id}

Update a property.

**Request Body:** Same as POST, all fields optional.

**Response (200):** Updated property object.

### DELETE /properties/{id}

Delete a property.

**Response (204):** No content.

---

## Bookings

### GET /bookings

List all bookings for the authenticated user's properties.

**Query Parameters:**
- `property_id` (uuid, optional) - Filter by property
- `status` (string, optional) - Filter by status: `upcoming`, `active`, `completed`, `cancelled`
- `start_date` (date, optional) - Filter bookings starting after this date
- `end_date` (date, optional) - Filter bookings ending before this date
- `skip` (int, default: 0)
- `limit` (int, default: 100)

**Response (200):**
```json
{
  "bookings": [
    {
      "id": "uuid",
      "property_id": "uuid",
      "property_name": "Downtown Luxury Condo",
      "guest_name": "John Smith",
      "guest_email": "john@example.com",
      "guest_phone": "+1234567890",
      "guest_count": 2,
      "checkin_date": "2024-02-01",
      "checkout_date": "2024-02-05",
      "total_price": 500.00,
      "source": "airbnb",
      "external_id": "airbnb_12345",
      "status": "upcoming",
      "notes": "Late check-in requested",
      "created_at": "2024-01-20T10:30:00Z"
    }
  ],
  "total": 1
}
```

### GET /bookings/{id}

Get a specific booking.

**Response (200):** Booking object with full details.

### POST /bookings

Create a manual booking (direct booking, not from Airbnb/VRBO).

**Request Body:**
```json
{
  "property_id": "uuid",
  "guest_name": "Jane Doe",
  "guest_email": "jane@example.com",
  "guest_phone": "+1234567890",
  "guest_count": 3,
  "checkin_date": "2024-03-01",
  "checkout_date": "2024-03-05",
  "total_price": 600.00,
  "source": "direct",
  "notes": "Returning guest"
}
```

**Response (201):** Created booking object.

### PUT /bookings/{id}

Update a booking.

**Response (200):** Updated booking object.

### DELETE /bookings/{id}

Cancel/delete a booking.

**Response (204):** No content.

---

## Tasks

### GET /tasks

List all tasks for the authenticated user's properties.

**Query Parameters:**
- `property_id` (uuid, optional) - Filter by property
- `status` (string, optional) - Filter by status: `pending`, `booked`, `in_progress`, `completed`, `failed`, `cancelled`
- `type` (string, optional) - Filter by type: `cleaning`, `maintenance`, `checkin`, `checkout`, `inspection`
- `scheduled_date` (date, optional) - Filter by scheduled date
- `skip` (int, default: 0)
- `limit` (int, default: 100)

**Response (200):**
```json
{
  "tasks": [
    {
      "id": "uuid",
      "property_id": "uuid",
      "property_name": "Downtown Luxury Condo",
      "booking_id": "uuid",
      "type": "cleaning",
      "status": "pending",
      "description": "Post-checkout cleaning",
      "scheduled_date": "2024-02-05",
      "scheduled_time": "11:00",
      "duration_hours": 3,
      "budget": 75.00,
      "required_skills": ["cleaning", "laundry"],
      "checklist": [
        "Strip beds and wash linens",
        "Clean all bathrooms",
        "Vacuum and mop floors",
        "Restock supplies"
      ],
      "assigned_human": null,
      "created_at": "2024-01-20T10:30:00Z"
    }
  ],
  "total": 1
}
```

### GET /tasks/{id}

Get a specific task.

**Response (200):** Task object with full details including assigned human info.

### POST /tasks

Create a new task.

**Request Body:**
```json
{
  "property_id": "uuid",
  "booking_id": "uuid",
  "type": "maintenance",
  "description": "Fix leaky faucet in bathroom",
  "scheduled_date": "2024-02-10",
  "scheduled_time": "10:00",
  "duration_hours": 2,
  "budget": 100.00,
  "required_skills": ["plumbing"],
  "host_notes": "Access code: 1234"
}
```

**Response (201):** Created task object.

### PUT /tasks/{id}

Update a task.

**Response (200):** Updated task object.

### POST /tasks/{id}/book

Book a human for this task (triggers RentAHuman search).

**Request Body (optional):**
```json
{
  "preferred_human_id": "human_123",
  "max_budget": 100.00
}
```

**Response (200):**
```json
{
  "task_id": "uuid",
  "status": "booked",
  "assigned_human": {
    "id": "human_123",
    "name": "Maria Garcia",
    "rating": 4.9,
    "skills": ["cleaning", "laundry"],
    "hourly_rate": 25.00
  },
  "booking_reference": "rah_booking_456"
}
```

### POST /tasks/{id}/complete

Mark a task as completed.

**Request Body:**
```json
{
  "notes": "Completed successfully",
  "rating": 5,
  "photos": ["https://..."]
}
```

**Response (200):** Updated task object.

### POST /tasks/{id}/cancel

Cancel a task.

**Request Body:**
```json
{
  "reason": "Guest cancelled booking"
}
```

**Response (200):** Updated task object.

---

## Humans

### GET /humans/search

Search for available humans on RentAHuman.

**Query Parameters:**
- `location` (string, required) - City, State (e.g., "Las Vegas, NV")
- `skill` (string, optional) - Filter by skill
- `date` (date, optional) - Filter by availability date
- `min_rating` (float, optional) - Minimum rating (1-5)
- `max_rate` (float, optional) - Maximum hourly rate

**Response (200):**
```json
{
  "humans": [
    {
      "id": "human_123",
      "name": "Maria Garcia",
      "rating": 4.9,
      "reviews_count": 156,
      "skills": ["cleaning", "laundry", "organization"],
      "hourly_rate": 25.00,
      "location": "Las Vegas, NV",
      "bio": "Professional cleaner with 5+ years experience",
      "availability": ["2024-02-01", "2024-02-02", "2024-02-03"],
      "profile_image": "https://..."
    }
  ],
  "total": 25
}
```

### GET /humans/{id}

Get details for a specific human.

**Response (200):** Human object with full profile.

### GET /humans/skills

List all available skills.

**Response (200):**
```json
{
  "skills": [
    {"id": "cleaning", "name": "Cleaning", "category": "housekeeping"},
    {"id": "laundry", "name": "Laundry", "category": "housekeeping"},
    {"id": "plumbing", "name": "Plumbing", "category": "maintenance"},
    {"id": "electrical", "name": "Electrical", "category": "maintenance"},
    {"id": "pool_maintenance", "name": "Pool Maintenance", "category": "outdoor"},
    {"id": "landscaping", "name": "Landscaping", "category": "outdoor"}
  ]
}
```

---

## Analytics

### GET /analytics/summary

Get analytics summary for the authenticated user.

**Query Parameters:**
- `start_date` (date, optional) - Start of period
- `end_date` (date, optional) - End of period

**Response (200):**
```json
{
  "total_properties": 5,
  "total_bookings": 47,
  "total_revenue": 15750.00,
  "total_tasks": 142,
  "tasks_completed": 128,
  "tasks_pending": 14,
  "average_task_cost": 68.50,
  "top_performing_property": {
    "id": "uuid",
    "name": "Downtown Luxury Condo",
    "revenue": 5200.00,
    "bookings": 18
  },
  "occupancy_rate": 0.72,
  "period": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  }
}
```

### GET /analytics/revenue

Get revenue breakdown.

**Query Parameters:**
- `group_by` (string) - Group by: `day`, `week`, `month`, `property`
- `start_date` (date, optional)
- `end_date` (date, optional)

**Response (200):**
```json
{
  "data": [
    {"period": "2024-01", "revenue": 5200.00, "bookings": 12},
    {"period": "2024-02", "revenue": 4800.00, "bookings": 10}
  ],
  "total": 10000.00
}
```

### GET /analytics/costs

Get cost breakdown.

**Query Parameters:**
- `group_by` (string) - Group by: `day`, `week`, `month`, `property`, `task_type`
- `start_date` (date, optional)
- `end_date` (date, optional)

**Response (200):**
```json
{
  "data": [
    {"category": "cleaning", "total": 1500.00, "count": 20},
    {"category": "maintenance", "total": 800.00, "count": 8}
  ],
  "total": 2300.00
}
```

### GET /analytics/optimization

Get cost optimization recommendations.

**Response (200):**
```json
{
  "insights": [
    {
      "property_id": "uuid",
      "property_name": "Downtown Luxury Condo",
      "task_type": "cleaning",
      "average_cost": 78.00,
      "suggested_budget": 74.10,
      "potential_savings": 3.90,
      "confidence": 0.85
    }
  ],
  "bulk_opportunities": [
    {
      "date": "2024-02-15",
      "task_type": "cleaning",
      "task_count": 3,
      "estimated_savings_percent": 14
    }
  ],
  "total_potential_savings": 125.50
}
```

---

## Notifications

### GET /notifications

Get notifications for the authenticated user.

**Query Parameters:**
- `unread_only` (bool, default: false)
- `skip` (int, default: 0)
- `limit` (int, default: 50)

**Response (200):**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "type": "booking_new",
      "title": "New Booking",
      "message": "New booking for Downtown Condo: Feb 1-5",
      "read": false,
      "data": {
        "booking_id": "uuid",
        "property_id": "uuid"
      },
      "created_at": "2024-01-20T10:30:00Z"
    }
  ],
  "unread_count": 5,
  "total": 25
}
```

### POST /notifications/{id}/read

Mark notification as read.

**Response (200):** Updated notification.

### POST /notifications/read-all

Mark all notifications as read.

**Response (200):**
```json
{
  "marked_read": 5
}
```

---

## WebSockets

### /ws/notifications

Real-time notification stream.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/notifications?token=<jwt>');
```

**Messages received:**
```json
{
  "type": "notification",
  "data": {
    "id": "uuid",
    "type": "task_completed",
    "title": "Task Completed",
    "message": "Cleaning task completed at Downtown Condo"
  }
}
```

---

## Error Responses

All endpoints return standard error responses:

**400 Bad Request:**
```json
{
  "detail": "Validation error message"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden:**
```json
{
  "detail": "Not authorized to access this resource"
}
```

**404 Not Found:**
```json
{
  "detail": "Resource not found"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

API requests are rate limited to:
- **100 requests per minute** for authenticated users
- **20 requests per minute** for unauthenticated endpoints

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706789400
```

---

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
