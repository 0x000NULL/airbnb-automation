'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MagnifyingGlassIcon, StarIcon } from '@heroicons/react/24/solid';
import { humansApi } from '@/lib/api';

export default function HumansPage() {
  const [searchParams, setSearchParams] = useState({
    location: 'Las Vegas, NV',
    skill: '',
    rating_min: 4.0,
    budget_max: 100,
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['humans', 'search', searchParams],
    queryFn: () => humansApi.search(searchParams),
    enabled: false,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    refetch();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Find Humans</h1>
        <p className="mt-1 text-sm text-gray-500">
          Search for available humans on RentAHuman
        </p>
      </div>

      {/* Search Form */}
      <div className="card">
        <form onSubmit={handleSearch} className="p-4 space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div>
              <label className="label">Location</label>
              <input
                type="text"
                value={searchParams.location}
                onChange={(e) =>
                  setSearchParams({ ...searchParams, location: e.target.value })
                }
                className="input mt-1"
                placeholder="City, State"
              />
            </div>
            <div>
              <label className="label">Skill</label>
              <select
                value={searchParams.skill}
                onChange={(e) =>
                  setSearchParams({ ...searchParams, skill: e.target.value })
                }
                className="input mt-1"
              >
                <option value="">Any skill</option>
                <option value="cleaning">Cleaning</option>
                <option value="handyman">Handyman</option>
                <option value="photography">Photography</option>
                <option value="organizing">Organizing</option>
              </select>
            </div>
            <div>
              <label className="label">Min Rating</label>
              <input
                type="number"
                step="0.1"
                min="1"
                max="5"
                value={searchParams.rating_min}
                onChange={(e) =>
                  setSearchParams({
                    ...searchParams,
                    rating_min: parseFloat(e.target.value),
                  })
                }
                className="input mt-1"
              />
            </div>
            <div>
              <label className="label">Max Budget ($/hr)</label>
              <input
                type="number"
                min="10"
                max="500"
                value={searchParams.budget_max}
                onChange={(e) =>
                  setSearchParams({
                    ...searchParams,
                    budget_max: parseInt(e.target.value),
                  })
                }
                className="input mt-1"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <button type="submit" className="btn-primary flex items-center gap-2">
              <MagnifyingGlassIcon className="h-5 w-5" />
              Search
            </button>
          </div>
        </form>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="p-4 space-y-3">
                <div className="h-4 bg-gray-200 rounded w-3/4" />
                <div className="h-4 bg-gray-200 rounded w-1/2" />
                <div className="h-20 bg-gray-200 rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : data?.humans?.length ? (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {data.humans.map((human) => (
            <div key={human.id} className="card hover:shadow-md transition-shadow">
              <div className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">
                      {human.name}
                    </h3>
                    <p className="text-sm text-gray-500">{human.location}</p>
                  </div>
                  <div className="flex items-center">
                    <StarIcon className="h-5 w-5 text-yellow-400" />
                    <span className="ml-1 text-sm font-medium text-gray-900">
                      {human.rating}
                    </span>
                    <span className="ml-1 text-sm text-gray-500">
                      ({human.reviews})
                    </span>
                  </div>
                </div>
                <p className="mt-2 text-sm text-gray-600 line-clamp-2">
                  {human.bio}
                </p>
                <div className="mt-3 flex flex-wrap gap-1">
                  {human.skills.map((skill) => (
                    <span key={skill} className="badge-gray">
                      {skill}
                    </span>
                  ))}
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <span className="text-lg font-semibold text-gray-900">
                    ${human.rate}/hr
                  </span>
                  <span
                    className={`badge ${
                      human.available ? 'badge-success' : 'badge-gray'
                    }`}
                  >
                    {human.available ? 'Available' : 'Busy'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : data ? (
        <div className="text-center py-12">
          <p className="text-sm text-gray-500">
            No humans found matching your criteria. Try adjusting your search.
          </p>
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-sm text-gray-500">
            Enter search criteria and click Search to find available humans.
          </p>
        </div>
      )}
    </div>
  );
}
