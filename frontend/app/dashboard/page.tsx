'use client';

import { useQuery } from '@tanstack/react-query';
import {
  BuildingOfficeIcon,
  CalendarIcon,
  ClipboardDocumentListIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';
import { analyticsApi, tasksApi, bookingsApi } from '@/lib/api';
import Link from 'next/link';

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  human_booked: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-purple-100 text-purple-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

export default function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: analyticsApi.summary,
  });

  const { data: upcomingTasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', 'upcoming'],
    queryFn: tasksApi.upcoming,
  });

  const { data: upcomingBookings, isLoading: bookingsLoading } = useQuery({
    queryKey: ['bookings', 'upcoming'],
    queryFn: bookingsApi.upcoming,
  });

  const stats = [
    {
      name: 'Total Properties',
      value: summary?.total_properties ?? '-',
      icon: BuildingOfficeIcon,
      href: '/dashboard/properties',
    },
    {
      name: 'Active Bookings',
      value: summary?.total_bookings ?? '-',
      icon: CalendarIcon,
      href: '/dashboard/bookings',
    },
    {
      name: 'Pending Tasks',
      value: summary?.total_tasks ?? '-',
      icon: ClipboardDocumentListIcon,
      href: '/dashboard/tasks',
    },
    {
      name: 'Total Spend',
      value: summary ? `$${summary.total_spend.toLocaleString()}` : '-',
      icon: CurrencyDollarIcon,
      href: '/dashboard/analytics',
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your property management automation
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Link
            key={stat.name}
            href={stat.href}
            className="card hover:shadow-md transition-shadow"
          >
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <stat.icon className="h-6 w-6 text-gray-400" aria-hidden="true" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      {stat.name}
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900">
                      {summaryLoading ? (
                        <div className="h-6 w-16 bg-gray-200 rounded animate-pulse" />
                      ) : (
                        stat.value
                      )}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Upcoming Tasks */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">Upcoming Tasks</h2>
            <Link
              href="/dashboard/tasks"
              className="text-sm font-medium text-primary-600 hover:text-primary-500"
            >
              View all
            </Link>
          </div>
          <div className="card-body">
            {tasksLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
                ))}
              </div>
            ) : upcomingTasks?.tasks?.length ? (
              <ul className="divide-y divide-gray-200">
                {upcomingTasks.tasks.slice(0, 5).map((task) => (
                  <li key={task.id} className="py-4">
                    <div className="flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {task.type.charAt(0).toUpperCase() + task.type.slice(1)} -{' '}
                          {task.property_name}
                        </p>
                        <p className="text-sm text-gray-500">
                          {new Date(task.scheduled_date).toLocaleDateString()} at{' '}
                          {task.scheduled_time}
                        </p>
                      </div>
                      <div className="ml-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            statusColors[task.status] || 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {task.status.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500 text-center py-8">
                No upcoming tasks
              </p>
            )}
          </div>
        </div>

        {/* Upcoming Bookings */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">Upcoming Bookings</h2>
            <Link
              href="/dashboard/bookings"
              className="text-sm font-medium text-primary-600 hover:text-primary-500"
            >
              View all
            </Link>
          </div>
          <div className="card-body">
            {bookingsLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
                ))}
              </div>
            ) : upcomingBookings?.bookings?.length ? (
              <ul className="divide-y divide-gray-200">
                {upcomingBookings.bookings.slice(0, 5).map((booking) => (
                  <li key={booking.id} className="py-4">
                    <div className="flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {booking.guest_name}
                        </p>
                        <p className="text-sm text-gray-500">
                          {booking.property_name}
                        </p>
                      </div>
                      <div className="ml-4 text-right">
                        <p className="text-sm text-gray-900">
                          {new Date(booking.checkin_date).toLocaleDateString()}
                        </p>
                        <p className="text-xs text-gray-500">
                          {booking.guest_count} guests
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500 text-center py-8">
                No upcoming bookings
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-medium text-gray-900">Quick Actions</h2>
        </div>
        <div className="card-body">
          <div className="flex flex-wrap gap-4">
            <Link href="/dashboard/properties?new=true" className="btn-primary">
              Add Property
            </Link>
            <Link href="/dashboard/tasks" className="btn-secondary">
              View Tasks
            </Link>
            <Link href="/dashboard/settings" className="btn-secondary">
              Automation Settings
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
