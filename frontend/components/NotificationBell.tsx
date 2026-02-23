'use client';

import { Fragment, useState } from 'react';
import { Popover, Transition } from '@headlessui/react';
import { BellIcon, CheckCircleIcon, ExclamationCircleIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import { BellIcon as BellSolidIcon } from '@heroicons/react/24/solid';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  link?: string;
  read: boolean;
  created_at: string;
}

// Mock notifications - in production, these would come from an API
const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'success',
    title: 'Task Completed',
    message: 'Cleaning task for Luxury Strip View has been completed',
    link: '/dashboard/tasks',
    read: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '2',
    type: 'warning',
    title: 'Upcoming Checkout',
    message: 'John Smith checking out tomorrow from Desert Oasis House',
    link: '/dashboard/bookings',
    read: false,
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: '3',
    type: 'info',
    title: 'New Booking',
    message: 'Sarah Johnson booked Downtown Vegas Condo for next week',
    link: '/dashboard/bookings',
    read: true,
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: '4',
    type: 'error',
    title: 'Booking Failed',
    message: 'Could not find available cleaner for maintenance task',
    link: '/dashboard/tasks',
    read: true,
    created_at: new Date(Date.now() - 172800000).toISOString(),
  },
];

const typeIcons = {
  info: InformationCircleIcon,
  success: CheckCircleIcon,
  warning: ExclamationCircleIcon,
  error: ExclamationCircleIcon,
};

const typeColors = {
  info: 'text-blue-500',
  success: 'text-green-500',
  warning: 'text-yellow-500',
  error: 'text-red-500',
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return date.toLocaleDateString();
}

export default function NotificationBell() {
  // In production, fetch notifications from API
  const [notifications, setNotifications] = useState<Notification[]>(mockNotifications);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const clearAll = () => {
    setNotifications([]);
  };

  return (
    <Popover className="relative">
      {({ open, close }) => (
        <>
          <Popover.Button className="relative p-2 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded-full">
            {unreadCount > 0 ? (
              <BellSolidIcon className="h-6 w-6 text-primary-600" />
            ) : (
              <BellIcon className="h-6 w-6" />
            )}
            {unreadCount > 0 && (
              <span className="absolute top-0 right-0 block h-4 w-4 rounded-full bg-red-500 text-[10px] font-medium text-white flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </Popover.Button>

          <Transition
            as={Fragment}
            enter="transition ease-out duration-200"
            enterFrom="opacity-0 translate-y-1"
            enterTo="opacity-100 translate-y-0"
            leave="transition ease-in duration-150"
            leaveFrom="opacity-100 translate-y-0"
            leaveTo="opacity-0 translate-y-1"
          >
            <Popover.Panel className="absolute right-0 z-10 mt-2 w-80 sm:w-96 origin-top-right rounded-lg bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
                <div className="flex gap-2">
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllAsRead}
                      className="text-xs text-primary-600 hover:text-primary-700"
                    >
                      Mark all read
                    </button>
                  )}
                  {notifications.length > 0 && (
                    <button
                      onClick={clearAll}
                      className="text-xs text-gray-500 hover:text-gray-700"
                    >
                      Clear all
                    </button>
                  )}
                </div>
              </div>

              {/* Notifications List */}
              <div className="max-h-96 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="py-8 text-center">
                    <BellIcon className="mx-auto h-8 w-8 text-gray-300" />
                    <p className="mt-2 text-sm text-gray-500">No notifications</p>
                  </div>
                ) : (
                  <ul className="divide-y divide-gray-100">
                    {notifications.map((notification) => {
                      const Icon = typeIcons[notification.type];
                      const colorClass = typeColors[notification.type];

                      return (
                        <li
                          key={notification.id}
                          className={`px-4 py-3 hover:bg-gray-50 cursor-pointer ${
                            !notification.read ? 'bg-primary-50/50' : ''
                          }`}
                          onClick={() => {
                            markAsRead(notification.id);
                            if (notification.link) {
                              close();
                            }
                          }}
                        >
                          {notification.link ? (
                            <Link href={notification.link} className="block">
                              <NotificationContent
                                notification={notification}
                                Icon={Icon}
                                colorClass={colorClass}
                              />
                            </Link>
                          ) : (
                            <NotificationContent
                              notification={notification}
                              Icon={Icon}
                              colorClass={colorClass}
                            />
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              {/* Footer */}
              {notifications.length > 0 && (
                <div className="px-4 py-3 bg-gray-50 rounded-b-lg border-t border-gray-200">
                  <Link
                    href="/dashboard/notifications"
                    className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                    onClick={() => close()}
                  >
                    View all notifications
                  </Link>
                </div>
              )}
            </Popover.Panel>
          </Transition>
        </>
      )}
    </Popover>
  );
}

function NotificationContent({
  notification,
  Icon,
  colorClass,
}: {
  notification: Notification;
  Icon: typeof InformationCircleIcon;
  colorClass: string;
}) {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0">
        <Icon className={`h-5 w-5 ${colorClass}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <p className={`text-sm font-medium ${!notification.read ? 'text-gray-900' : 'text-gray-700'}`}>
            {notification.title}
          </p>
          {!notification.read && (
            <span className="ml-2 h-2 w-2 rounded-full bg-primary-500" />
          )}
        </div>
        <p className="text-sm text-gray-500 truncate">{notification.message}</p>
        <p className="mt-1 text-xs text-gray-400">
          {formatTimeAgo(notification.created_at)}
        </p>
      </div>
    </div>
  );
}
