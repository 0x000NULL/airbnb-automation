'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6'];

export default function AnalyticsPage() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: analyticsApi.summary,
  });

  const { data: costs, isLoading: costsLoading } = useQuery({
    queryKey: ['analytics', 'costs'],
    queryFn: () => analyticsApi.costs(),
  });

  const { data: roi, isLoading: roiLoading } = useQuery({
    queryKey: ['analytics', 'roi'],
    queryFn: analyticsApi.roi,
  });

  const isLoading = summaryLoading || costsLoading || roiLoading;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="mt-1 text-sm text-gray-500">
          Track your property management performance and costs
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card p-5">
          <dt className="text-sm font-medium text-gray-500">Total Spend</dt>
          <dd className="mt-1 text-3xl font-semibold text-gray-900">
            {isLoading ? (
              <div className="h-9 w-24 bg-gray-200 rounded animate-pulse" />
            ) : (
              `$${summary?.total_spend?.toLocaleString() || 0}`
            )}
          </dd>
        </div>
        <div className="card p-5">
          <dt className="text-sm font-medium text-gray-500">Tasks Completed</dt>
          <dd className="mt-1 text-3xl font-semibold text-gray-900">
            {isLoading ? (
              <div className="h-9 w-16 bg-gray-200 rounded animate-pulse" />
            ) : (
              summary?.tasks_completed || 0
            )}
          </dd>
        </div>
        <div className="card p-5">
          <dt className="text-sm font-medium text-gray-500">Avg Task Cost</dt>
          <dd className="mt-1 text-3xl font-semibold text-gray-900">
            {isLoading ? (
              <div className="h-9 w-20 bg-gray-200 rounded animate-pulse" />
            ) : (
              `$${summary?.average_task_cost?.toFixed(2) || 0}`
            )}
          </dd>
        </div>
        <div className="card p-5">
          <dt className="text-sm font-medium text-gray-500">ROI</dt>
          <dd className="mt-1 text-3xl font-semibold text-green-600">
            {isLoading ? (
              <div className="h-9 w-16 bg-gray-200 rounded animate-pulse" />
            ) : (
              `${roi?.roi_percentage?.toFixed(1) || 0}%`
            )}
          </dd>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Cost by Property */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Cost by Property</h2>
          </div>
          <div className="card-body">
            {isLoading ? (
              <div className="h-64 bg-gray-100 rounded animate-pulse" />
            ) : costs?.by_property?.length ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={costs.by_property}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="property_name"
                    tick={{ fontSize: 12 }}
                    interval={0}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value: number) => `$${value.toFixed(2)}`} />
                  <Bar dataKey="total_cost" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center py-8 text-gray-500">No data available</p>
            )}
          </div>
        </div>

        {/* Cost by Type */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Cost by Task Type</h2>
          </div>
          <div className="card-body">
            {isLoading ? (
              <div className="h-64 bg-gray-100 rounded animate-pulse" />
            ) : costs?.by_type?.length ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={costs.by_type}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) =>
                      `${name} (${(percent * 100).toFixed(0)}%)`
                    }
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="total_cost"
                    nameKey="type"
                  >
                    {costs.by_type.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => `$${value.toFixed(2)}`} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center py-8 text-gray-500">No data available</p>
            )}
          </div>
        </div>
      </div>

      {/* Time Saved */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-medium text-gray-900">Time & Cost Savings</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="text-center">
              <p className="text-4xl font-bold text-primary-600">
                {isLoading ? '-' : `${roi?.time_saved_hours || 0}h`}
              </p>
              <p className="mt-1 text-sm text-gray-500">Time Saved</p>
            </div>
            <div className="text-center">
              <p className="text-4xl font-bold text-green-600">
                {isLoading ? '-' : `$${roi?.net_profit?.toLocaleString() || 0}`}
              </p>
              <p className="mt-1 text-sm text-gray-500">Net Profit</p>
            </div>
            <div className="text-center">
              <p className="text-4xl font-bold text-blue-600">
                {isLoading ? '-' : `$${roi?.cost_per_booking?.toFixed(2) || 0}`}
              </p>
              <p className="mt-1 text-sm text-gray-500">Cost per Booking</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
