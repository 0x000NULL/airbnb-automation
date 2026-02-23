/**
 * Shared API client for the Airbnb Automation frontend.
 *
 * All dashboard pages use these functions via TanStack Query (useQuery).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_V1 = `${API_BASE}/api/v1`;

function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('access_token');
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_V1}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

// ── Types ──────────────────────────────────────────────────────────────

export interface BookingResponse {
  id: string;
  property_id: string;
  property_name?: string;
  guest_name: string;
  checkin_date: string;
  checkout_date: string;
  guest_count: number;
  notes: string | null;
  total_price: number;
  source: string;
  synced_at: string;
  duration_nights: number;
}

export interface BookingList {
  bookings: BookingResponse[];
  total: number;
}

export interface UpcomingBooking {
  id: string;
  property_id: string;
  property_name: string;
  guest_name: string;
  checkin_date: string;
  checkout_date: string;
  guest_count: number;
  days_until_checkin: number;
  tasks_pending: number;
}

export interface TaskResponse {
  id: string;
  type: string;
  property_id: string;
  property_name?: string;
  description: string;
  budget: number;
  scheduled_date: string;
  scheduled_time: string;
  duration_hours: number;
  status: string;
  assigned_human: { id: string; name: string; photo?: string; rating: number; reviews: number } | null;
  checklist: string[];
  host_notes: string | null;
  created_at: string;
  updated_at: string;
  is_urgent: boolean;
}

export interface TaskList {
  tasks: TaskResponse[];
  total: number;
}

export interface PropertyResponse {
  id: string;
  host_id: string;
  name: string;
  location: { city: string; state: string; zip: string };
  property_type: string;
  bedrooms: number;
  bathrooms: number;
  max_guests: number;
  airbnb_listing_id: string | null;
  vrbo_listing_id: string | null;
  cleaning_budget: number;
  maintenance_budget: number;
  created_at: string;
  updated_at: string;
}

export interface PropertyList {
  properties: PropertyResponse[];
  total: number;
}

export interface AnalyticsSummary {
  total_properties: number;
  total_bookings: number;
  total_tasks: number;
  tasks_completed: number;
  tasks_pending: number;
  total_spent: number;
  total_spend: number; // alias used by dashboard
  commission_earned: number;
  average_task_cost: number;
  booking_success_rate: number;
  completion_rate: number;
}

export interface CostAnalysis {
  period_start: string;
  period_end: string;
  total_cost: number;
  by_property: { property_id: string; property_name: string; total_cost: number }[];
  by_task_type: { task_type: string; total_cost: number; task_count: number; average_cost: number }[];
  by_type?: { type: string; total_cost: number }[];
  daily_average: number;
  projected_monthly: number;
}

export interface ROIAnalysis {
  period_start: string;
  period_end: string;
  total_automation_cost: number;
  estimated_manual_cost: number;
  time_saved_hours: number;
  cost_savings: number;
  cost_savings_percentage: number;
  roi_percentage: number;
  net_profit?: number;
  cost_per_booking?: number;
}

export interface NotificationItem {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  link?: string;
  read: boolean;
  created_at: string;
}

export interface NotificationList {
  notifications: NotificationItem[];
  total: number;
  unread_count: number;
}

// ── API namespaces ─────────────────────────────────────────────────────

export const bookingsApi = {
  list: (params?: Record<string, string | undefined>) => {
    const qs = params ? '?' + new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null) as [string, string][])
    ).toString() : '';
    return apiFetch<BookingList>(`/bookings/${qs}`);
  },
  upcoming: () =>
    apiFetch<{ bookings: UpcomingBooking[] }>('/bookings/upcoming').then(r => ({ bookings: r as unknown as UpcomingBooking[] })).catch(() =>
      apiFetch<UpcomingBooking[]>('/bookings/upcoming').then(bookings => ({ bookings }))
    ),
  get: (id: string) => apiFetch<BookingResponse>(`/bookings/${id}`),
  sync: (id: string) => apiFetch<BookingResponse>(`/bookings/${id}/sync`, { method: 'POST' }),
};

export const tasksApi = {
  list: (params?: Record<string, string | undefined>) => {
    const qs = params ? '?' + new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null) as [string, string][])
    ).toString() : '';
    return apiFetch<TaskList>(`/tasks/${qs}`);
  },
  upcoming: () => apiFetch<TaskList>('/tasks/upcoming'),
  get: (id: string) => apiFetch<TaskResponse>(`/tasks/${id}`),
  book: (id: string) => apiFetch<TaskResponse>(`/tasks/${id}/book`, { method: 'POST', body: '{}' }),
};

export const propertiesApi = {
  list: () => apiFetch<PropertyList>('/properties/'),
  get: (id: string) => apiFetch<PropertyResponse>(`/properties/${id}`),
};

export const analyticsApi = {
  summary: () => apiFetch<AnalyticsSummary>('/analytics/summary'),
  costs: (days?: number) => apiFetch<CostAnalysis>(`/analytics/costs${days ? `?days=${days}` : ''}`),
  roi: (days?: number) => apiFetch<ROIAnalysis>(`/analytics/roi${days ? `?days=${days}` : ''}`),
  humans: (days?: number) => apiFetch<any>(`/analytics/humans${days ? `?days=${days}` : ''}`),
};

export const humansApi = {
  search: (params: Record<string, any>) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)]))
    ).toString();
    return apiFetch<{ humans: any[] }>(`/humans/search?${qs}`);
  },
};

export const notificationsApi = {
  list: (params?: { unread_only?: boolean; limit?: number; offset?: number }) => {
    const qs = params ? '?' + new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)]))
    ).toString() : '';
    return apiFetch<NotificationList>(`/notifications/${qs}`);
  },
  markRead: (id: string) => apiFetch<{ ok: boolean }>(`/notifications/${id}/read`, { method: 'POST' }),
  markAllRead: () => apiFetch<{ ok: boolean }>('/notifications/read-all', { method: 'POST' }),
};
