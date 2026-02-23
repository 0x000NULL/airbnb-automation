'use client';

import { useQuery } from '@tanstack/react-query';
import { PlusIcon } from '@heroicons/react/24/outline';
import { propertiesApi } from '@/lib/api';
import Link from 'next/link';

export default function PropertiesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['properties'],
    queryFn: propertiesApi.list,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Properties</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your rental properties
          </p>
        </div>
        <Link href="/dashboard/properties/new" className="btn-primary flex items-center gap-2">
          <PlusIcon className="h-5 w-5" />
          Add Property
        </Link>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-48 bg-gray-200 rounded-t-lg" />
              <div className="p-4 space-y-3">
                <div className="h-4 bg-gray-200 rounded w-3/4" />
                <div className="h-4 bg-gray-200 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : data?.properties?.length ? (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {data.properties.map((property) => (
            <Link
              key={property.id}
              href={`/dashboard/properties/${property.id}`}
              className="card hover:shadow-md transition-shadow"
            >
              <div className="h-48 bg-gradient-to-br from-primary-100 to-primary-200 rounded-t-lg flex items-center justify-center">
                <span className="text-4xl">🏠</span>
              </div>
              <div className="p-4">
                <h3 className="text-lg font-medium text-gray-900">
                  {property.name}
                </h3>
                <p className="text-sm text-gray-500">
                  {property.location.city}, {property.location.state}
                </p>
                <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                  <span>{property.bedrooms} bed</span>
                  <span>{property.bathrooms} bath</span>
                  <span>{property.max_guests} guests</span>
                </div>
                <div className="mt-3 flex gap-2">
                  {property.airbnb_listing_id && (
                    <span className="badge-info">Airbnb</span>
                  )}
                  {property.vrbo_listing_id && (
                    <span className="badge-success">VRBO</span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <h3 className="text-sm font-medium text-gray-900">No properties</h3>
          <p className="mt-1 text-sm text-gray-500">
            Get started by adding your first property.
          </p>
          <div className="mt-6">
            <Link href="/dashboard/properties/new" className="btn-primary inline-flex items-center">
              <PlusIcon className="h-5 w-5 mr-2" />
              Add Property
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
