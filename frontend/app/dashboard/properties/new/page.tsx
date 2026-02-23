'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { propertiesApi, PropertyCreate } from '@/lib/api';

const propertySchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  location: z.object({
    city: z.string().min(1, 'City is required'),
    state: z.string().min(1, 'State is required'),
    zip: z.string().min(5, 'ZIP code must be at least 5 characters'),
  }),
  property_type: z.string().min(1, 'Property type is required'),
  bedrooms: z.number().min(0, 'Bedrooms must be 0 or more'),
  bathrooms: z.number().min(0, 'Bathrooms must be 0 or more'),
  max_guests: z.number().min(1, 'At least 1 guest required'),
  airbnb_listing_id: z.string().optional(),
  vrbo_listing_id: z.string().optional(),
  default_checkin_time: z.string().min(1, 'Check-in time is required'),
  default_checkout_time: z.string().min(1, 'Check-out time is required'),
  cleaning_budget: z.number().min(0, 'Cleaning budget must be 0 or more'),
  maintenance_budget: z.number().min(0, 'Maintenance budget must be 0 or more'),
  preferred_skills: z.array(z.string()).optional(),
});

type PropertyFormData = z.infer<typeof propertySchema>;

const PROPERTY_TYPES = [
  { value: 'apartment', label: 'Apartment' },
  { value: 'house', label: 'House' },
  { value: 'condo', label: 'Condo' },
  { value: 'townhouse', label: 'Townhouse' },
  { value: 'villa', label: 'Villa' },
  { value: 'cabin', label: 'Cabin' },
];

const SKILL_OPTIONS = [
  'cleaning',
  'deep_cleaning',
  'pool_maintenance',
  'landscaping',
  'plumbing',
  'electrical',
  'hvac',
  'organizing',
  'hotel_experience',
  'photography',
];

export default function NewPropertyPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<PropertyFormData>({
    resolver: zodResolver(propertySchema),
    defaultValues: {
      property_type: 'apartment',
      bedrooms: 1,
      bathrooms: 1,
      max_guests: 2,
      default_checkin_time: '15:00',
      default_checkout_time: '11:00',
      cleaning_budget: 100,
      maintenance_budget: 150,
      preferred_skills: [],
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: PropertyCreate) => propertiesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['properties'] });
      router.push('/dashboard/properties');
    },
    onError: (err: unknown) => {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to create property');
    },
  });

  const onSubmit = (data: PropertyFormData) => {
    setError(null);
    createMutation.mutate(data as PropertyCreate);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/dashboard/properties"
          className="text-gray-400 hover:text-gray-500"
        >
          <ArrowLeftIcon className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Add New Property</h1>
          <p className="mt-1 text-sm text-gray-500">
            Enter the details for your new rental property
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Basic Information */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Basic Information</h2>
          </div>
          <div className="card-body space-y-4">
            <div>
              <label htmlFor="name" className="label">
                Property Name
              </label>
              <input
                id="name"
                type="text"
                {...register('name')}
                className="input mt-1"
                placeholder="e.g., Luxury Strip View Apartment"
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="property_type" className="label">
                Property Type
              </label>
              <select
                id="property_type"
                {...register('property_type')}
                className="input mt-1"
              >
                {PROPERTY_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              {errors.property_type && (
                <p className="mt-1 text-sm text-red-600">{errors.property_type.message}</p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label htmlFor="bedrooms" className="label">
                  Bedrooms
                </label>
                <input
                  id="bedrooms"
                  type="number"
                  min="0"
                  {...register('bedrooms', { valueAsNumber: true })}
                  className="input mt-1"
                />
                {errors.bedrooms && (
                  <p className="mt-1 text-sm text-red-600">{errors.bedrooms.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="bathrooms" className="label">
                  Bathrooms
                </label>
                <input
                  id="bathrooms"
                  type="number"
                  min="0"
                  step="0.5"
                  {...register('bathrooms', { valueAsNumber: true })}
                  className="input mt-1"
                />
                {errors.bathrooms && (
                  <p className="mt-1 text-sm text-red-600">{errors.bathrooms.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="max_guests" className="label">
                  Max Guests
                </label>
                <input
                  id="max_guests"
                  type="number"
                  min="1"
                  {...register('max_guests', { valueAsNumber: true })}
                  className="input mt-1"
                />
                {errors.max_guests && (
                  <p className="mt-1 text-sm text-red-600">{errors.max_guests.message}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Location */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Location</h2>
          </div>
          <div className="card-body space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="sm:col-span-2">
                <label htmlFor="city" className="label">
                  City
                </label>
                <input
                  id="city"
                  type="text"
                  {...register('location.city')}
                  className="input mt-1"
                  placeholder="Las Vegas"
                />
                {errors.location?.city && (
                  <p className="mt-1 text-sm text-red-600">{errors.location.city.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="state" className="label">
                  State
                </label>
                <input
                  id="state"
                  type="text"
                  {...register('location.state')}
                  className="input mt-1"
                  placeholder="NV"
                />
                {errors.location?.state && (
                  <p className="mt-1 text-sm text-red-600">{errors.location.state.message}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="zip" className="label">
                ZIP Code
              </label>
              <input
                id="zip"
                type="text"
                {...register('location.zip')}
                className="input mt-1 max-w-xs"
                placeholder="89101"
              />
              {errors.location?.zip && (
                <p className="mt-1 text-sm text-red-600">{errors.location.zip.message}</p>
              )}
            </div>
          </div>
        </div>

        {/* Check-in/Check-out Times */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Check-in & Check-out</h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="default_checkin_time" className="label">
                  Default Check-in Time
                </label>
                <input
                  id="default_checkin_time"
                  type="time"
                  {...register('default_checkin_time')}
                  className="input mt-1"
                />
                {errors.default_checkin_time && (
                  <p className="mt-1 text-sm text-red-600">{errors.default_checkin_time.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="default_checkout_time" className="label">
                  Default Check-out Time
                </label>
                <input
                  id="default_checkout_time"
                  type="time"
                  {...register('default_checkout_time')}
                  className="input mt-1"
                />
                {errors.default_checkout_time && (
                  <p className="mt-1 text-sm text-red-600">{errors.default_checkout_time.message}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Platform Connections */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Platform Connections</h2>
            <p className="mt-1 text-sm text-gray-500">
              Optional: Link this property to your Airbnb or VRBO listings
            </p>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="airbnb_listing_id" className="label">
                  Airbnb Listing ID
                </label>
                <input
                  id="airbnb_listing_id"
                  type="text"
                  {...register('airbnb_listing_id')}
                  className="input mt-1"
                  placeholder="Optional"
                />
              </div>

              <div>
                <label htmlFor="vrbo_listing_id" className="label">
                  VRBO Listing ID
                </label>
                <input
                  id="vrbo_listing_id"
                  type="text"
                  {...register('vrbo_listing_id')}
                  className="input mt-1"
                  placeholder="Optional"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Budgets */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Task Budgets</h2>
            <p className="mt-1 text-sm text-gray-500">
              Default budgets for automated task booking
            </p>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="cleaning_budget" className="label">
                  Cleaning Budget ($)
                </label>
                <input
                  id="cleaning_budget"
                  type="number"
                  min="0"
                  step="10"
                  {...register('cleaning_budget', { valueAsNumber: true })}
                  className="input mt-1"
                />
                {errors.cleaning_budget && (
                  <p className="mt-1 text-sm text-red-600">{errors.cleaning_budget.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="maintenance_budget" className="label">
                  Maintenance Budget ($)
                </label>
                <input
                  id="maintenance_budget"
                  type="number"
                  min="0"
                  step="10"
                  {...register('maintenance_budget', { valueAsNumber: true })}
                  className="input mt-1"
                />
                {errors.maintenance_budget && (
                  <p className="mt-1 text-sm text-red-600">{errors.maintenance_budget.message}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Preferred Skills */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Preferred Skills</h2>
            <p className="mt-1 text-sm text-gray-500">
              Select skills to prioritize when matching humans for this property
            </p>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-5">
              {SKILL_OPTIONS.map((skill) => (
                <label key={skill} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    value={skill}
                    {...register('preferred_skills')}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-600"
                  />
                  <span className="text-sm text-gray-700">
                    {skill.replace(/_/g, ' ')}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Link
            href="/dashboard/properties"
            className="btn-secondary"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="btn-primary"
          >
            {createMutation.isPending ? 'Creating...' : 'Create Property'}
          </button>
        </div>
      </form>
    </div>
  );
}
