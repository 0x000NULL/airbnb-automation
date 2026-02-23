'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CalendarIcon, ListBulletIcon } from '@heroicons/react/24/outline';
import { bookingsApi, BookingResponse } from '@/lib/api';
import { BookingCalendar } from '@/components';

type ViewMode = 'calendar' | 'list';

export default function BookingsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('calendar');
  const [selectedBooking, setSelectedBooking] = useState<BookingResponse | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['bookings'],
    queryFn: bookingsApi.list,
  });

  const handleBookingClick = (booking: BookingResponse) => {
    setSelectedBooking(booking);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bookings</h1>
          <p className="mt-1 text-sm text-gray-500">
            View all guest bookings across your properties
          </p>
        </div>
        <div className="flex rounded-lg border border-gray-300 p-1">
          <button
            onClick={() => setViewMode('calendar')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium ${
              viewMode === 'calendar'
                ? 'bg-primary-100 text-primary-700'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <CalendarIcon className="h-4 w-4" />
            Calendar
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium ${
              viewMode === 'list'
                ? 'bg-primary-100 text-primary-700'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <ListBulletIcon className="h-4 w-4" />
            List
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="card">
          <div className="p-4 space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        </div>
      ) : viewMode === 'calendar' ? (
        <div className="space-y-6">
          <BookingCalendar
            bookings={data?.bookings || []}
            onBookingClick={handleBookingClick}
          />

          {/* Selected Booking Details */}
          {selectedBooking && (
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h2 className="text-lg font-medium text-gray-900">Booking Details</h2>
                <button
                  onClick={() => setSelectedBooking(null)}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Close
                </button>
              </div>
              <div className="card-body">
                <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Guest</dt>
                    <dd className="mt-1 text-sm text-gray-900">{selectedBooking.guest_name}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Property</dt>
                    <dd className="mt-1 text-sm text-gray-900">{selectedBooking.property_name}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Check-in</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {new Date(selectedBooking.checkin_date).toLocaleDateString()}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Check-out</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {new Date(selectedBooking.checkout_date).toLocaleDateString()}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Guests</dt>
                    <dd className="mt-1 text-sm text-gray-900">{selectedBooking.guest_count}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Total Price</dt>
                    <dd className="mt-1 text-sm text-gray-900">${selectedBooking.total_price}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Source</dt>
                    <dd className="mt-1">
                      <span
                        className={`badge ${
                          selectedBooking.source === 'airbnb' ? 'badge-info' : 'badge-success'
                        }`}
                      >
                        {selectedBooking.source.toUpperCase()}
                      </span>
                    </dd>
                  </div>
                  {selectedBooking.notes && (
                    <div className="col-span-2 sm:col-span-4">
                      <dt className="text-sm font-medium text-gray-500">Notes</dt>
                      <dd className="mt-1 text-sm text-gray-900">{selectedBooking.notes}</dd>
                    </div>
                  )}
                </dl>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card overflow-hidden">
          {data?.bookings?.length ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Guest
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Property
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Check-in
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Check-out
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Guests
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.bookings.map((booking) => (
                  <tr
                    key={booking.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelectedBooking(booking)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {booking.guest_name}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {booking.property_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(booking.checkin_date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(booking.checkout_date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {booking.guest_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      ${booking.total_price}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`badge ${
                          booking.source === 'airbnb' ? 'badge-info' : 'badge-success'
                        }`}
                      >
                        {booking.source.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-12">
              <p className="text-sm text-gray-500">No bookings found</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
