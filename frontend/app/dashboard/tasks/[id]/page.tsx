'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeftIcon,
  ClockIcon,
  CurrencyDollarIcon,
  UserIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { tasksApi, propertiesApi } from '@/lib/api';

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  human_booked: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-purple-100 text-purple-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const taskId = params.id as string;

  const { data: task, isLoading } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => tasksApi.get(taskId),
  });

  const { data: propertiesData } = useQuery({
    queryKey: ['properties'],
    queryFn: propertiesApi.list,
  });

  const property = propertiesData?.properties.find(
    (p) => p.id === task?.property_id
  );

  const bookMutation = useMutation({
    mutationFn: () => tasksApi.book(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const completeMutation = useMutation({
    mutationFn: () => tasksApi.complete(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  if (isLoading) {
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

  if (!task) {
    return (
      <div className="text-center py-12">
        <h3 className="text-sm font-medium text-gray-900">Task not found</h3>
        <Link href="/dashboard/tasks" className="mt-4 btn-primary inline-block">
          Back to Tasks
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
            href="/dashboard/tasks"
            className="text-gray-400 hover:text-gray-500"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 capitalize">
                {task.type} Task
              </h1>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  statusColors[task.status] || 'bg-gray-100 text-gray-800'
                }`}
              >
                {task.status.replace('_', ' ')}
              </span>
              {task.is_urgent && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                  <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
                  Urgent
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-500">
              {property?.name || 'Unknown Property'}
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          {task.status === 'pending' && (
            <button
              onClick={() => bookMutation.mutate()}
              disabled={bookMutation.isPending}
              className="btn-primary"
            >
              {bookMutation.isPending ? 'Booking...' : 'Book Human'}
            </button>
          )}
          {(task.status === 'human_booked' || task.status === 'in_progress') && (
            <button
              onClick={() => completeMutation.mutate()}
              disabled={completeMutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              <CheckCircleIcon className="h-4 w-4" />
              {completeMutation.isPending ? 'Completing...' : 'Mark Complete'}
            </button>
          )}
        </div>
      </div>

      {bookMutation.isError && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">
            Failed to book human. Please try again.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Description</h2>
            </div>
            <div className="card-body">
              <p className="text-gray-700">{task.description}</p>
            </div>
          </div>

          {/* Schedule & Budget */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Details</h2>
            </div>
            <div className="card-body">
              <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Date</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {new Date(task.scheduled_date).toLocaleDateString()}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Time</dt>
                  <dd className="mt-1 text-sm text-gray-900">{task.scheduled_time}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Duration</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {task.duration_hours} hours
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Budget</dt>
                  <dd className="mt-1 text-sm text-gray-900">${task.budget}</dd>
                </div>
              </dl>
            </div>
          </div>

          {/* Required Skills */}
          {task.required_skills && task.required_skills.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-medium text-gray-900">Required Skills</h2>
              </div>
              <div className="card-body">
                <div className="flex flex-wrap gap-2">
                  {task.required_skills.map((skill: string) => (
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

          {/* Checklist */}
          {task.checklist && task.checklist.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-medium text-gray-900">Checklist</h2>
              </div>
              <div className="card-body">
                <ul className="space-y-2">
                  {task.checklist.map((item: string, index: number) => (
                    <li key={index} className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-5 h-5 rounded-full border-2 border-gray-300 flex items-center justify-center">
                        <span className="text-xs text-gray-500">{index + 1}</span>
                      </div>
                      <span className="text-sm text-gray-700">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Host Notes */}
          {task.host_notes && (
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-medium text-gray-900">Host Notes</h2>
              </div>
              <div className="card-body">
                <p className="text-gray-700">{task.host_notes}</p>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Assigned Human */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Assigned Human</h2>
            </div>
            <div className="card-body">
              {task.assigned_human ? (
                <div className="flex items-center gap-4">
                  <div className="flex-shrink-0">
                    {task.assigned_human.photo ? (
                      <img
                        src={task.assigned_human.photo}
                        alt={task.assigned_human.name}
                        className="h-12 w-12 rounded-full object-cover"
                      />
                    ) : (
                      <div className="h-12 w-12 rounded-full bg-gray-200 flex items-center justify-center">
                        <UserIcon className="h-6 w-6 text-gray-400" />
                      </div>
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {task.assigned_human.name}
                    </p>
                    <p className="text-sm text-gray-500">
                      Rating: {task.assigned_human.rating} ({task.assigned_human.reviews} reviews)
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-4">
                  <UserIcon className="mx-auto h-8 w-8 text-gray-400" />
                  <p className="mt-2 text-sm text-gray-500">No human assigned yet</p>
                  {task.status === 'pending' && (
                    <button
                      onClick={() => bookMutation.mutate()}
                      disabled={bookMutation.isPending}
                      className="mt-3 btn-primary text-sm"
                    >
                      Book Now
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Booking Info */}
          {task.rentahuman_booking_id && (
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-medium text-gray-900">Booking Info</h2>
              </div>
              <div className="card-body">
                <dl className="space-y-2">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Booking ID</dt>
                    <dd className="mt-1 text-sm text-gray-900 font-mono">
                      {task.rentahuman_booking_id}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          )}

          {/* Property Info */}
          {property && (
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-medium text-gray-900">Property</h2>
              </div>
              <div className="card-body">
                <Link
                  href={`/dashboard/properties/${property.id}`}
                  className="group block"
                >
                  <p className="text-sm font-medium text-gray-900 group-hover:text-primary-600">
                    {property.name}
                  </p>
                  <p className="text-sm text-gray-500">
                    {property.location.city}, {property.location.state}
                  </p>
                </Link>
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Activity</h2>
            </div>
            <div className="card-body">
              <dl className="space-y-2">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Created</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {new Date(task.created_at).toLocaleString()}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {new Date(task.updated_at).toLocaleString()}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
