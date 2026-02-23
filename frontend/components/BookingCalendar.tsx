'use client';

import { useState, useMemo } from 'react';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { BookingResponse } from '@/lib/api';

interface BookingCalendarProps {
  bookings: BookingResponse[];
  onDateClick?: (date: Date) => void;
  onBookingClick?: (booking: BookingResponse) => void;
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

export default function BookingCalendar({
  bookings,
  onDateClick,
  onBookingClick,
}: BookingCalendarProps) {
  const [currentDate, setCurrentDate] = useState(new Date());

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const firstDayOfMonth = new Date(year, month, 1);
  const lastDayOfMonth = new Date(year, month + 1, 0);
  const startingDayOfWeek = firstDayOfMonth.getDay();
  const daysInMonth = lastDayOfMonth.getDate();

  const prevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // Build a map of dates to bookings
  const bookingsByDate = useMemo(() => {
    const map: Record<string, BookingResponse[]> = {};

    bookings.forEach((booking) => {
      const checkin = new Date(booking.checkin_date);
      const checkout = new Date(booking.checkout_date);

      // Add booking to each date it spans
      const current = new Date(checkin);
      while (current < checkout) {
        const dateKey = current.toISOString().split('T')[0];
        if (!map[dateKey]) {
          map[dateKey] = [];
        }
        map[dateKey].push(booking);
        current.setDate(current.getDate() + 1);
      }
    });

    return map;
  }, [bookings]);

  const isToday = (day: number) => {
    const today = new Date();
    return (
      day === today.getDate() &&
      month === today.getMonth() &&
      year === today.getFullYear()
    );
  };

  const getDateKey = (day: number) => {
    const date = new Date(year, month, day);
    return date.toISOString().split('T')[0];
  };

  const getBookingsForDay = (day: number) => {
    const dateKey = getDateKey(day);
    return bookingsByDate[dateKey] || [];
  };

  const isCheckinDate = (day: number, booking: BookingResponse) => {
    const dateKey = getDateKey(day);
    return booking.checkin_date === dateKey;
  };

  const isCheckoutDate = (day: number, booking: BookingResponse) => {
    const dateKey = getDateKey(day);
    const checkout = new Date(booking.checkout_date);
    checkout.setDate(checkout.getDate() - 1); // Checkout is exclusive
    return checkout.toISOString().split('T')[0] === dateKey;
  };

  // Generate calendar grid
  const calendarDays = [];

  // Empty cells for days before the first day of the month
  for (let i = 0; i < startingDayOfWeek; i++) {
    calendarDays.push(null);
  }

  // Days of the month
  for (let day = 1; day <= daysInMonth; day++) {
    calendarDays.push(day);
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="card-header flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-medium text-gray-900">
            {MONTHS[month]} {year}
          </h2>
          <button
            onClick={goToToday}
            className="text-sm text-primary-600 hover:text-primary-700"
          >
            Today
          </button>
        </div>
        <div className="flex gap-2">
          <button
            onClick={prevMonth}
            className="p-2 hover:bg-gray-100 rounded-md"
          >
            <ChevronLeftIcon className="h-5 w-5 text-gray-500" />
          </button>
          <button
            onClick={nextMonth}
            className="p-2 hover:bg-gray-100 rounded-md"
          >
            <ChevronRightIcon className="h-5 w-5 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="card-body p-0">
        {/* Day headers */}
        <div className="grid grid-cols-7 border-b border-gray-200">
          {DAYS.map((day) => (
            <div
              key={day}
              className="py-2 text-center text-xs font-medium text-gray-500 uppercase"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Calendar cells */}
        <div className="grid grid-cols-7">
          {calendarDays.map((day, index) => {
            const dayBookings = day ? getBookingsForDay(day) : [];
            const hasBookings = dayBookings.length > 0;

            return (
              <div
                key={index}
                className={`min-h-[100px] border-b border-r border-gray-100 p-1 ${
                  day ? 'cursor-pointer hover:bg-gray-50' : 'bg-gray-50'
                }`}
                onClick={() => {
                  if (day && onDateClick) {
                    onDateClick(new Date(year, month, day));
                  }
                }}
              >
                {day && (
                  <>
                    <div
                      className={`text-sm font-medium mb-1 w-7 h-7 flex items-center justify-center rounded-full ${
                        isToday(day)
                          ? 'bg-primary-600 text-white'
                          : 'text-gray-700'
                      }`}
                    >
                      {day}
                    </div>
                    <div className="space-y-1">
                      {dayBookings.slice(0, 3).map((booking, i) => (
                        <div
                          key={`${booking.id}-${i}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onBookingClick?.(booking);
                          }}
                          className={`text-xs px-1 py-0.5 rounded truncate cursor-pointer ${
                            booking.source === 'airbnb'
                              ? 'bg-red-100 text-red-700 hover:bg-red-200'
                              : 'bg-green-100 text-green-700 hover:bg-green-200'
                          } ${
                            isCheckinDate(day, booking)
                              ? 'rounded-l-full'
                              : ''
                          } ${
                            isCheckoutDate(day, booking)
                              ? 'rounded-r-full'
                              : ''
                          }`}
                        >
                          {isCheckinDate(day, booking) && '> '}
                          {booking.guest_name.split(' ')[0]}
                        </div>
                      ))}
                      {dayBookings.length > 3 && (
                        <div className="text-xs text-gray-500 px-1">
                          +{dayBookings.length - 3} more
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="px-4 py-3 bg-gray-50 rounded-b-lg border-t border-gray-200 flex gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-red-100 border border-red-200" />
          <span className="text-gray-600">Airbnb</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-green-100 border border-green-200" />
          <span className="text-gray-600">VRBO</span>
        </div>
      </div>
    </div>
  );
}
