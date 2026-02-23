'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { ArrowLeftIcon, PlusIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { tasksApi, propertiesApi, TaskCreate } from '@/lib/api';

const taskSchema = z.object({
  type: z.enum(['cleaning', 'maintenance', 'photography', 'communication', 'restocking']),
  property_id: z.string().min(1, 'Property is required'),
  description: z.string().min(1, 'Description is required').max(1000),
  required_skills: z.array(z.string()).optional(),
  budget: z.number().min(0, 'Budget must be 0 or more'),
  scheduled_date: z.string().min(1, 'Date is required'),
  scheduled_time: z.string().min(1, 'Time is required'),
  duration_hours: z.number().min(0.5, 'Duration must be at least 0.5 hours').max(24),
  checklist: z.array(z.object({ item: z.string() })).optional(),
  host_notes: z.string().max(1000).optional(),
});

type TaskFormData = z.infer<typeof taskSchema>;

const TASK_TYPES = [
  { value: 'cleaning', label: 'Cleaning', defaultBudget: 150, defaultDuration: 3 },
  { value: 'maintenance', label: 'Maintenance', defaultBudget: 200, defaultDuration: 2 },
  { value: 'photography', label: 'Photography', defaultBudget: 200, defaultDuration: 3 },
  { value: 'communication', label: 'Communication', defaultBudget: 0, defaultDuration: 0.5 },
  { value: 'restocking', label: 'Restocking', defaultBudget: 50, defaultDuration: 1 },
];

const SKILL_OPTIONS: Record<string, string[]> = {
  cleaning: ['cleaning', 'deep_cleaning', 'organizing', 'hotel_experience'],
  maintenance: ['plumbing', 'electrical', 'hvac', 'carpentry', 'painting'],
  photography: ['photography', 'videography', 'editing'],
  communication: ['customer_service', 'multilingual'],
  restocking: ['organizing', 'inventory'],
};

export default function NewTaskPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: propertiesData, isLoading: propertiesLoading } = useQuery({
    queryKey: ['properties'],
    queryFn: propertiesApi.list,
  });

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors },
  } = useForm<TaskFormData>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      type: 'cleaning',
      budget: 150,
      duration_hours: 3,
      scheduled_time: '11:00',
      checklist: [],
      required_skills: [],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'checklist',
  });

  const selectedType = watch('type');
  const selectedSkills = watch('required_skills') || [];

  const handleTypeChange = (type: string) => {
    const taskType = TASK_TYPES.find((t) => t.value === type);
    if (taskType) {
      setValue('budget', taskType.defaultBudget);
      setValue('duration_hours', taskType.defaultDuration);
      setValue('required_skills', []);
    }
  };

  const createMutation = useMutation({
    mutationFn: (data: TaskCreate) => tasksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      router.push('/dashboard/tasks');
    },
    onError: (err: unknown) => {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to create task');
    },
  });

  const onSubmit = (data: TaskFormData) => {
    setError(null);
    const taskData: TaskCreate = {
      type: data.type,
      property_id: data.property_id,
      description: data.description,
      required_skills: data.required_skills,
      budget: data.budget,
      scheduled_date: data.scheduled_date,
      scheduled_time: data.scheduled_time,
      duration_hours: data.duration_hours,
      checklist: data.checklist?.map((c) => c.item).filter(Boolean),
      host_notes: data.host_notes,
    };
    createMutation.mutate(taskData);
  };

  const getTomorrowDate = () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split('T')[0];
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/dashboard/tasks"
          className="text-gray-400 hover:text-gray-500"
        >
          <ArrowLeftIcon className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Create New Task</h1>
          <p className="mt-1 text-sm text-gray-500">
            Schedule a manual task for one of your properties
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Task Type & Property */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Task Details</h2>
          </div>
          <div className="card-body space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="type" className="label">
                  Task Type
                </label>
                <select
                  id="type"
                  {...register('type')}
                  onChange={(e) => {
                    register('type').onChange(e);
                    handleTypeChange(e.target.value);
                  }}
                  className="input mt-1"
                >
                  {TASK_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
                {errors.type && (
                  <p className="mt-1 text-sm text-red-600">{errors.type.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="property_id" className="label">
                  Property
                </label>
                <select
                  id="property_id"
                  {...register('property_id')}
                  className="input mt-1"
                  disabled={propertiesLoading}
                >
                  <option value="">Select a property</option>
                  {propertiesData?.properties.map((property) => (
                    <option key={property.id} value={property.id}>
                      {property.name}
                    </option>
                  ))}
                </select>
                {errors.property_id && (
                  <p className="mt-1 text-sm text-red-600">{errors.property_id.message}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="description" className="label">
                Description
              </label>
              <textarea
                id="description"
                rows={3}
                {...register('description')}
                className="input mt-1"
                placeholder="Describe the task..."
              />
              {errors.description && (
                <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
              )}
            </div>
          </div>
        </div>

        {/* Schedule */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Schedule</h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label htmlFor="scheduled_date" className="label">
                  Date
                </label>
                <input
                  id="scheduled_date"
                  type="date"
                  min={getTomorrowDate()}
                  {...register('scheduled_date')}
                  className="input mt-1"
                />
                {errors.scheduled_date && (
                  <p className="mt-1 text-sm text-red-600">{errors.scheduled_date.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="scheduled_time" className="label">
                  Time
                </label>
                <input
                  id="scheduled_time"
                  type="time"
                  {...register('scheduled_time')}
                  className="input mt-1"
                />
                {errors.scheduled_time && (
                  <p className="mt-1 text-sm text-red-600">{errors.scheduled_time.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="duration_hours" className="label">
                  Duration (hours)
                </label>
                <input
                  id="duration_hours"
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="24"
                  {...register('duration_hours', { valueAsNumber: true })}
                  className="input mt-1"
                />
                {errors.duration_hours && (
                  <p className="mt-1 text-sm text-red-600">{errors.duration_hours.message}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Budget & Skills */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Budget & Skills</h2>
          </div>
          <div className="card-body space-y-4">
            <div>
              <label htmlFor="budget" className="label">
                Budget ($)
              </label>
              <input
                id="budget"
                type="number"
                min="0"
                step="10"
                {...register('budget', { valueAsNumber: true })}
                className="input mt-1 max-w-xs"
              />
              {errors.budget && (
                <p className="mt-1 text-sm text-red-600">{errors.budget.message}</p>
              )}
            </div>

            <div>
              <label className="label">Required Skills</label>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
                {SKILL_OPTIONS[selectedType]?.map((skill) => (
                  <label key={skill} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      value={skill}
                      checked={selectedSkills.includes(skill)}
                      onChange={(e) => {
                        const current = selectedSkills || [];
                        if (e.target.checked) {
                          setValue('required_skills', [...current, skill]);
                        } else {
                          setValue(
                            'required_skills',
                            current.filter((s) => s !== skill)
                          );
                        }
                      }}
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
        </div>

        {/* Checklist */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Checklist</h2>
            <p className="mt-1 text-sm text-gray-500">
              Add specific items for the human to complete
            </p>
          </div>
          <div className="card-body space-y-3">
            {fields.map((field, index) => (
              <div key={field.id} className="flex gap-2">
                <input
                  {...register(`checklist.${index}.item`)}
                  className="input flex-1"
                  placeholder={`Item ${index + 1}`}
                />
                <button
                  type="button"
                  onClick={() => remove(index)}
                  className="btn-secondary p-2"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => append({ item: '' })}
              className="btn-secondary flex items-center gap-2"
            >
              <PlusIcon className="h-4 w-4" />
              Add Item
            </button>
          </div>
        </div>

        {/* Host Notes */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-medium text-gray-900">Host Notes</h2>
            <p className="mt-1 text-sm text-gray-500">
              Optional notes for the human
            </p>
          </div>
          <div className="card-body">
            <textarea
              {...register('host_notes')}
              rows={3}
              className="input"
              placeholder="Any special instructions or notes..."
            />
            {errors.host_notes && (
              <p className="mt-1 text-sm text-red-600">{errors.host_notes.message}</p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Link href="/dashboard/tasks" className="btn-secondary">
            Cancel
          </Link>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="btn-primary"
          >
            {createMutation.isPending ? 'Creating...' : 'Create Task'}
          </button>
        </div>
      </form>
    </div>
  );
}
