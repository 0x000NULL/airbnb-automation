'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeftIcon,
  PencilIcon,
  MapPinIcon,
  ClockIcon,
  CurrencyDollarIcon,
  HomeIcon,
} from '@heroicons/react/24/outline';
import { propertiesApi, bookingsApi, tasksApi } from '@/lib/api';

export default function PropertyDetailPage() {
  const params = useParams();
  const propertyId = params.id as string;

  const { data: property, isLoading: propertyLoading } = useQuery({
    queryKey: ['property', propertyId],
    queryFn: () => propertiesApi.get(propertyId),
  });

  const { data: bookingsData } = useQuery({
    queryKey: ['bookings'],
    queryFn: bookingsApi.list,
  });

  const { data: tasksData } = useQuery({
    queryKey: ['tasks', { property_id: propertyId }],
    queryFn: () => tasksApi.list({ property_id: propertyId }),
  });

  const propertyBookings = bookingsData?.bookings.filter(
    (b) => b.property_id === propertyId
  );
  const propertyTasks = tasksData?.tasks;

  if (propertyLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 bg-gray-200 rounded animate-pulse" />
        <div className="card">
          <div className="p-6 space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-6 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!property) {
    return (
      <div className="text-center py-12">
        <h3 className="text-sm font-medium text-gray-900">Property not found</h3>
        <Link href="/dashboard/properties" className="mt-4 btn-primary inline-block">
          Back to Properties
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard/properties"
            className="text-gray-400 hover:text-gray-500"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{property.name}</h1>
            <p className="mt-1 text-sm text-gray-500 flex items-center gap-1">
              <MapPinIcon className="h-4 w-4" />
              {property.location.city}, {property.location.state} {property.location.zip}
            </p>
          </div>
        </div>
        <Link
          href={`/dashboard/properties/${propertyId}/edit`}
          className="btn-primary flex items-center gap-2"
        >
          <PencilIcon className="h-4 w-4" />
          Edit Property
        </Link>
      </div>

      {/* Property Details Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Basic Info Card */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Property Details</h2>
            </div>
            <div className="card-body">
              <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Type</dt>
                  <dd className="mt-1 text-sm text-gray-900 capitalize">
                    {property.property_type}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Bedrooms</dt>
                  <dd className="mt-1 text-sm text-gray-900">{property.bedrooms}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Bathrooms</dt>
                  <dd className="mt-1 text-sm text-gray-900">{property.bathrooms}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Max Guests</dt>
                  <dd className="mt-1 text-sm text-gray-900">{property.max_guests}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Check-in</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {property.default_checkin_time}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Check-out</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {property.default_checkout_time}
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          {/* Budgets Card */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Task Budgets</h2>
            </div>
            <div className="card-body">
              <dl className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                    <CurrencyDollarIcon className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Cleaning</dt>
                    <dd className="text-lg font-semibold text-gray-900">
                      ${property.cleaning_budget}
                    </dd>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                    <CurrencyDollarIcon className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Maintenance</dt>
                    <dd className="text-lg font-semibold text-gray-900">
                      ${property.maintenance_budget}
                    </dd>
                  </div>
                </div>
              </dl>
            </div>
          </div>

          {/* Platform Connections */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Platform Connections</h2>
            </div>
            <div className="card-body">
              <div className="flex gap-4">
                {property.airbnb_listing_id ? (
                  <div className="flex items-center gap-2 px-3 py-2 bg-red-50 rounded-lg">
                    <span className="badge-info">Airbnb</span>
                    <span className="text-sm text-gray-600">
                      {property.airbnb_listing_id}
                    </span>
                  </div>
                ) : (
                  <div className="text-sm text-gray-500">No Airbnb connection</div>
                )}
                {property.vrbo_listing_id ? (
                  <div className="flex items-center gap-2 px-3 py-2 bg-green-50 rounded-lg">
                    <span className="badge-success">VRBO</span>
                    <span className="text-sm text-gray-600">
                      {property.vrbo_listing_id}
                    </span>
                  </div>
                ) : (
                  <div className="text-sm text-gray-500">No VRBO connection</div>
                )}
              </div>
            </div>
          </div>

          {/* Preferred Skills */}
          {property.preferred_skills && property.preferred_skills.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-medium text-gray-900">Preferred Skills</h2>
              </div>
              <div className="card-body">
                <div className="flex flex-wrap gap-2">
                  {property.preferred_skills.map((skill) => (
                    <span
                      key={skill}
                      className="inline-flex items-center rounded-full bg-primary-50 px-3 py-1 text-sm font-medium text-primary-700"
                    >
                      {skill.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Upcoming Bookings */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Upcoming Bookings</h2>
            </div>
            <div className="card-body">
              {propertyBookings && propertyBookings.length > 0 ? (
                <ul className="divide-y divide-gray-200">
                  {propertyBookings.slice(0, 5).map((booking) => (
                    <li key={booking.id} className="py-3">
                      <p className="text-sm font-medium text-gray-900">
                        {booking.guest_name}
                      </p>
                      <p className="text-sm text-gray-500">
                        {booking.checkin_date} - {booking.checkout_date}
                      </p>
                      <p className="text-xs text-gray-400">
                        {booking.guest_count} guests
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-500">No upcoming bookings</p>
              )}
              <Link
                href="/dashboard/bookings"
                className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-500 block"
              >
                View all bookings
              </Link>
            </div>
          </div>

          {/* Recent Tasks */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Recent Tasks</h2>
            </div>
            <div className="card-body">
              {propertyTasks && propertyTasks.length > 0 ? (
                <ul className="divide-y divide-gray-200">
                  {propertyTasks.slice(0, 5).map((task) => (
                    <li key={task.id} className="py-3">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900 capitalize">
                          {task.type}
                        </p>
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                            task.status === 'completed'
                              ? 'bg-green-100 text-green-700'
                              : task.status === 'in_progress'
                              ? 'bg-blue-100 text-blue-700'
                              : task.status === 'pending'
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {task.status.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500">{task.scheduled_date}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-500">No recent tasks</p>
              )}
              <Link
                href="/dashboard/tasks"
                className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-500 block"
              >
                View all tasks
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
