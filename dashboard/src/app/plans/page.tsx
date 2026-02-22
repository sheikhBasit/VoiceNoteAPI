'use client';

import { useState } from 'react';
import { usePlans, useCreatePlan, useUpdatePlan, useDeletePlan, type ServicePlan, type CreatePlanPayload, type UpdatePlanPayload } from '@/hooks/usePlans';
import { useToast } from '@/components/ui/Toast';
import { Package, Plus, Pencil, Trash2, X, Check } from 'lucide-react';

const defaultPlan: CreatePlanPayload = {
    id: '',
    name: '',
    price_per_minute: 10,
    monthly_credits: 100,
    monthly_note_limit: 10,
    monthly_task_limit: 20,
    max_storage_mb: 500,
    can_use_rag: true,
    google_play_product_id: '',
    description: '',
    features: {},
    is_active: true,
};

export default function PlansPage() {
    const { data: plans, isLoading, error } = usePlans();
    const createMutation = useCreatePlan();
    const updateMutation = useUpdatePlan();
    const deleteMutation = useDeletePlan();
    const toast = useToast();

    const [showModal, setShowModal] = useState(false);
    const [editingPlan, setEditingPlan] = useState<ServicePlan | null>(null);
    const [formData, setFormData] = useState<CreatePlanPayload>(defaultPlan);

    const openCreateModal = () => {
        setEditingPlan(null);
        setFormData({ ...defaultPlan, id: `plan_${Date.now()}` });
        setShowModal(true);
    };

    const openEditModal = (plan: ServicePlan) => {
        setEditingPlan(plan);
        setFormData({
            id: plan.id,
            name: plan.name,
            price_per_minute: plan.price_per_minute,
            monthly_credits: plan.monthly_credits,
            monthly_note_limit: plan.monthly_note_limit,
            monthly_task_limit: plan.monthly_task_limit,
            max_storage_mb: plan.max_storage_mb,
            can_use_rag: plan.can_use_rag,
            google_play_product_id: plan.google_play_product_id || '',
            description: plan.description || '',
            features: plan.features || {},
            is_active: plan.is_active,
        });
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingPlan) {
                const { id: _id, ...updates } = formData;
                await updateMutation.mutateAsync({ id: editingPlan.id, updates: updates as UpdatePlanPayload });
                toast.success('Plan updated successfully');
            } else {
                await createMutation.mutateAsync(formData);
                toast.success('Plan created successfully');
            }
            setShowModal(false);
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            toast.error(error.response?.data?.detail || 'Failed to save plan');
        }
    };

    const handleDelete = async (plan: ServicePlan) => {
        if (!confirm(`Deactivate plan "${plan.name}"?`)) return;
        try {
            await deleteMutation.mutateAsync(plan.id);
            toast.success(`Plan "${plan.name}" deactivated`);
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } } };
            toast.error(error.response?.data?.detail || 'Failed to delete plan');
        }
    };

    const updateField = (field: string, value: any) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    if (error) {
        return (
            <div className="flex items-center justify-center h-64 text-red-400">
                Failed to load plans. Check your connection.
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
                        <Package className="w-8 h-8 text-indigo-400" />
                        Subscription Plans
                    </h2>
                    <p className="text-slate-400 mt-1">Manage billing tiers, limits, and Google Play products.</p>
                </div>
                <button
                    onClick={openCreateModal}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-colors font-medium text-sm"
                >
                    <Plus className="w-4 h-4" />
                    Create Plan
                </button>
            </div>

            {/* Plans Table */}
            <div className="glass-card overflow-hidden">
                <table className="w-full text-left">
                    <thead>
                        <tr className="border-b border-slate-800">
                            <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Plan</th>
                            <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Credits/Mo</th>
                            <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Note Limit</th>
                            <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Task Limit</th>
                            <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Google Play ID</th>
                            <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                            <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                        {isLoading ? (
                            Array(3).fill(0).map((_, i) => (
                                <tr key={i}>
                                    {Array(7).fill(0).map((__, j) => (
                                        <td key={j} className="px-6 py-4">
                                            <div className="h-4 bg-slate-800 rounded animate-pulse w-20" />
                                        </td>
                                    ))}
                                </tr>
                            ))
                        ) : plans && plans.length > 0 ? (
                            plans.map((plan) => (
                                <tr key={plan.id} className="hover:bg-slate-800/30 transition-colors">
                                    <td className="px-6 py-4">
                                        <div>
                                            <p className="text-sm font-semibold text-slate-200">{plan.name}</p>
                                            <p className="text-xs text-slate-500">{plan.description || 'No description'}</p>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-300">{plan.monthly_credits}</td>
                                    <td className="px-6 py-4 text-sm text-slate-300">
                                        {plan.monthly_note_limit === -1 ? 'Unlimited' : plan.monthly_note_limit}
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-300">
                                        {plan.monthly_task_limit === -1 ? 'Unlimited' : plan.monthly_task_limit}
                                    </td>
                                    <td className="px-6 py-4 text-xs text-slate-400 font-mono">
                                        {plan.google_play_product_id || '-'}
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                                            plan.is_active
                                                ? 'bg-emerald-500/10 text-emerald-400'
                                                : 'bg-red-500/10 text-red-400'
                                        }`}>
                                            {plan.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => openEditModal(plan)}
                                                className="p-1.5 text-slate-400 hover:text-indigo-400 hover:bg-slate-800 rounded transition-colors"
                                                title="Edit plan"
                                            >
                                                <Pencil className="w-4 h-4" />
                                            </button>
                                            {plan.is_active && (
                                                <button
                                                    onClick={() => handleDelete(plan)}
                                                    className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded transition-colors"
                                                    title="Deactivate plan"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={7} className="px-6 py-12 text-center text-slate-500">
                                    No plans found. Create your first subscription plan.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Create/Edit Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between p-6 border-b border-slate-800">
                            <h3 className="text-lg font-semibold text-slate-100">
                                {editingPlan ? 'Edit Plan' : 'Create Plan'}
                            </h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-200">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-4">
                            {!editingPlan && (
                                <div>
                                    <label className="block text-xs font-medium text-slate-400 mb-1">Plan ID</label>
                                    <input
                                        type="text"
                                        value={formData.id}
                                        onChange={(e) => updateField('id', e.target.value)}
                                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
                                        required
                                    />
                                </div>
                            )}

                            <div>
                                <label className="block text-xs font-medium text-slate-400 mb-1">Name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => updateField('name', e.target.value)}
                                    placeholder="e.g. FREE, PRO, ENTERPRISE"
                                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-slate-400 mb-1">Description</label>
                                <input
                                    type="text"
                                    value={formData.description || ''}
                                    onChange={(e) => updateField('description', e.target.value)}
                                    placeholder="Plan description for users"
                                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-slate-400 mb-1">Monthly Credits</label>
                                    <input
                                        type="number"
                                        value={formData.monthly_credits}
                                        onChange={(e) => updateField('monthly_credits', parseInt(e.target.value) || 0)}
                                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-slate-400 mb-1">Price/Minute (credits)</label>
                                    <input
                                        type="number"
                                        value={formData.price_per_minute}
                                        onChange={(e) => updateField('price_per_minute', parseInt(e.target.value) || 0)}
                                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-slate-400 mb-1">Monthly Note Limit (-1 = unlimited)</label>
                                    <input
                                        type="number"
                                        value={formData.monthly_note_limit}
                                        onChange={(e) => updateField('monthly_note_limit', parseInt(e.target.value))}
                                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-slate-400 mb-1">Monthly Task Limit (-1 = unlimited)</label>
                                    <input
                                        type="number"
                                        value={formData.monthly_task_limit}
                                        onChange={(e) => updateField('monthly_task_limit', parseInt(e.target.value))}
                                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-slate-400 mb-1">Max Storage (MB)</label>
                                <input
                                    type="number"
                                    value={formData.max_storage_mb}
                                    onChange={(e) => updateField('max_storage_mb', parseInt(e.target.value) || 0)}
                                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-slate-400 mb-1">Google Play Product ID</label>
                                <input
                                    type="text"
                                    value={formData.google_play_product_id || ''}
                                    onChange={(e) => updateField('google_play_product_id', e.target.value || null)}
                                    placeholder="e.g. voicenote_pro_monthly"
                                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
                                />
                            </div>

                            <div className="flex items-center gap-3">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={formData.can_use_rag}
                                        onChange={(e) => updateField('can_use_rag', e.target.checked)}
                                        className="w-4 h-4 rounded border-slate-600 text-indigo-500 focus:ring-indigo-500 bg-slate-800"
                                    />
                                    <span className="text-sm text-slate-300">Can use RAG</span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={formData.is_active}
                                        onChange={(e) => updateField('is_active', e.target.checked)}
                                        className="w-4 h-4 rounded border-slate-600 text-indigo-500 focus:ring-indigo-500 bg-slate-800"
                                    />
                                    <span className="text-sm text-slate-300">Active</span>
                                </label>
                            </div>

                            <div className="flex gap-3 pt-4 border-t border-slate-800">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="flex-1 px-4 py-2 text-sm font-medium text-slate-400 bg-slate-800 rounded-lg hover:bg-slate-700 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={createMutation.isPending || updateMutation.isPending}
                                    className="flex-1 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {(createMutation.isPending || updateMutation.isPending) ? (
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    ) : (
                                        <Check className="w-4 h-4" />
                                    )}
                                    {editingPlan ? 'Update Plan' : 'Create Plan'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
