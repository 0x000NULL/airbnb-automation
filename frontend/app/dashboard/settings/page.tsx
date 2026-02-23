'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { configApi, AutomationConfigResponse } from '@/lib/api';
import { useEffect } from 'react';

export default function SettingsPage() {
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: configApi.get,
  });

  const { register, handleSubmit, reset, formState: { isDirty } } = useForm<AutomationConfigResponse>();

  useEffect(() => {
    if (config) {
      reset(config);
    }
  }, [config, reset]);

  const updateMutation = useMutation({
    mutationFn: configApi.update,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });

  const onSubmit = (data: AutomationConfigResponse) => {
    updateMutation.mutate(data);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="card">
          <div className="p-6 space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Automation Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Configure how tasks are automatically booked and managed
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Auto-booking Settings */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Auto-booking</h2>
            <p className="mt-1 text-sm text-gray-500">
              Enable automatic booking of humans for different task types
            </p>
          </div>
          <div className="card-body space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-900">
                  Auto-book cleaning tasks
                </label>
                <p className="text-sm text-gray-500">
                  Automatically book cleaners for turnover tasks
                </p>
              </div>
              <input
                type="checkbox"
                {...register('auto_book_cleaning')}
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-600"
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-900">
                  Auto-book maintenance tasks
                </label>
                <p className="text-sm text-gray-500">
                  Automatically book handymen for maintenance tasks
                </p>
              </div>
              <input
                type="checkbox"
                {...register('auto_book_maintenance')}
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-600"
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-900">
                  Auto-book photography
                </label>
                <p className="text-sm text-gray-500">
                  Automatically book photographers when needed
                </p>
              </div>
              <input
                type="checkbox"
                {...register('auto_book_photography')}
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-600"
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-900">
                  Auto-respond to guests
                </label>
                <p className="text-sm text-gray-500">
                  Send automated welcome messages to guests
                </p>
              </div>
              <input
                type="checkbox"
                {...register('auto_respond_to_guests')}
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-600"
              />
            </div>
          </div>
        </div>

        {/* Preferences */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Human Selection Preferences</h2>
            <p className="mt-1 text-sm text-gray-500">
              How to prioritize when selecting humans for tasks
            </p>
          </div>
          <div className="card-body space-y-4">
            <div>
              <label className="label">Cleaning preference</label>
              <select
                {...register('cleaning_preference')}
                className="input mt-1"
              >
                <option value="highest_rated">Highest Rated</option>
                <option value="nearest">Nearest</option>
                <option value="cheapest">Cheapest</option>
              </select>
            </div>
            <div>
              <label className="label">Maintenance preference</label>
              <select
                {...register('maintenance_preference')}
                className="input mt-1"
              >
                <option value="nearest">Nearest</option>
                <option value="highest_rated">Highest Rated</option>
                <option value="cheapest">Cheapest</option>
              </select>
            </div>
            <div>
              <label className="label">Minimum human rating</label>
              <input
                type="number"
                step="0.1"
                min="1"
                max="5"
                {...register('minimum_human_rating', { valueAsNumber: true })}
                className="input mt-1"
              />
              <p className="mt-1 text-sm text-gray-500">
                Only book humans with ratings at or above this value
              </p>
            </div>
          </div>
        </div>

        {/* Notifications */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Notifications</h2>
            <p className="mt-1 text-sm text-gray-500">
              How you want to be notified about task updates
            </p>
          </div>
          <div className="card-body">
            <div>
              <label className="label">Notification method</label>
              <select
                {...register('notification_method')}
                className="input mt-1"
              >
                <option value="email">Email</option>
                <option value="sms">SMS</option>
                <option value="push">Push Notifications</option>
              </select>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!isDirty || updateMutation.isPending}
            className="btn-primary"
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
          </button>
        </div>

        {updateMutation.isSuccess && (
          <p className="text-sm text-green-600 text-right">Settings saved successfully!</p>
        )}
      </form>
    </div>
  );
}
