'use client';

import { useState, useEffect } from 'react';
import { useAISettings, useUpdateAISettings, useAPIKeys, AISettings } from "@/hooks/useSettings";
import { useToast } from "@/components/ui/Toast";
import {
    Settings,
    Cpu,
    Mic,
    Key,
    Save,
    RefreshCw,
    AlertCircle,
    CheckCircle2,
    Sliders,
    Zap,
    ShieldCheck
} from 'lucide-react';

export default function SettingsPage() {
    const { data: currentSettings, isLoading: isSettingsLoading } = useAISettings();
    const { data: apiKeys, isLoading: isKeysLoading } = useAPIKeys();
    const updateMutation = useUpdateAISettings();
    const toast = useToast();

    const [formData, setFormData] = useState<Partial<AISettings>>({});

    useEffect(() => {
        if (currentSettings) {
            setFormData(currentSettings);
        }
    }, [currentSettings]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: name === 'temperature' || name === 'top_p' ? parseFloat(value) : name === 'max_tokens' ? parseInt(value, 10) : value
        }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Basic Validation
        if (!formData.semantic_analysis_prompt?.trim()) {
            toast.error('Semantic Analysis Prompt cannot be empty');
            return;
        }

        if (formData.temperature && (formData.temperature < 0 || formData.temperature > 10)) {
            toast.error('Temperature must be between 0 and 10');
            return;
        }

        try {
            await updateMutation.mutateAsync(formData);
            toast.success('Settings updated successfully');
        } catch (err) {
            toast.error('Failed to update settings');
        }
    };

    if (isSettingsLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-end border-b border-slate-800 pb-6">
                <div>
                    <h2 className="text-3xl font-bold text-slate-100 flex items-center space-x-3">
                        <Settings className="w-8 h-8 text-indigo-500" />
                        <span>System Settings</span>
                    </h2>
                    <p className="text-slate-400 mt-1">Configure global AI parameters and manage engine fallbacks.</p>
                </div>
                <button
                    onClick={handleSubmit}
                    disabled={updateMutation.isPending}
                    className="flex items-center space-x-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-indigo-600/20"
                >
                    {updateMutation.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    <span>{updateMutation.isPending ? 'Saving...' : 'Save Changes'}</span>
                </button>
            </div>

            <form className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* LLM Configuration */}
                <div className="glass-card p-6 space-y-6">
                    <div className="flex items-center space-x-2 text-indigo-400 border-b border-slate-800 pb-4">
                        <Cpu className="w-5 h-5" />
                        <h3 className="font-bold uppercase tracking-wider text-xs">LLM Configuration</h3>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase">Primary Model (Groq)</label>
                            <select
                                name="llm_model"
                                value={formData.llm_model}
                                onChange={handleChange}
                                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                            >
                                <option value="llama-3.3-70b-versatile">Llama 3.3 70B Versatile</option>
                                <option value="llama-3.1-70b-versatile">Llama 3.1 70B Versatile</option>
                                <option value="mixtral-8x7b-32768">Mixtral 8x7B</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase">Fast Path Model</label>
                            <select
                                name="llm_fast_model"
                                value={formData.llm_fast_model}
                                onChange={handleChange}
                                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                            >
                                <option value="llama-3.1-8b-instant">Llama 3.1 8B Instant</option>
                                <option value="llama3-8b-8192">Llama 3 8B</option>
                            </select>
                        </div>

                        <div className="grid grid-cols-2 gap-4 pt-2">
                            <div>
                                <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase flex items-center space-x-1">
                                    <Sliders className="w-3 h-3" />
                                    <span>Temperature ({formData.temperature})</span>
                                </label>
                                <input
                                    type="range"
                                    name="temperature"
                                    min="0"
                                    max="10"
                                    value={formData.temperature}
                                    onChange={handleChange}
                                    className="w-full accent-indigo-500"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase flex items-center space-x-1">
                                    <Zap className="w-3 h-3" />
                                    <span>Top P ({formData.top_p})</span>
                                </label>
                                <input
                                    type="range"
                                    name="top_p"
                                    min="0"
                                    max="10"
                                    value={formData.top_p}
                                    onChange={handleChange}
                                    className="w-full accent-indigo-500"
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* STT Configuration */}
                <div className="glass-card p-6 space-y-6">
                    <div className="flex items-center space-x-2 text-indigo-400 border-b border-slate-800 pb-4">
                        <Mic className="w-5 h-5" />
                        <h3 className="font-bold uppercase tracking-wider text-xs">STT Configuration</h3>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase">Primary Engine</label>
                            <select
                                name="stt_engine"
                                value={formData.stt_engine}
                                onChange={handleChange}
                                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                            >
                                <option value="deepgram">Deepgram (Recommended)</option>
                                <option value="groq">Groq Whisper</option>
                                <option value="both">Parallel Comparison</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase">Deepgram Model</label>
                            <select
                                name="deepgram_model"
                                value={formData.deepgram_model}
                                onChange={handleChange}
                                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                            >
                                <option value="nova-3">Nova-3 (Latest)</option>
                                <option value="nova-2">Nova-2</option>
                                <option value="whisper-large">Whisper Large</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase">Whisper Model (Groq)</label>
                            <select
                                name="groq_whisper_model"
                                value={formData.groq_whisper_model}
                                onChange={handleChange}
                                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                            >
                                <option value="whisper-large-v3-turbo">Whisper Large V3 Turbo</option>
                                <option value="whisper-large-v3">Whisper Large V3</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* Advanced Prompting */}
                <div className="glass-card p-6 space-y-4 md:col-span-2">
                    <div className="flex items-center space-x-2 text-indigo-400 border-b border-slate-800 pb-4">
                        <ShieldCheck className="w-5 h-5" />
                        <h3 className="font-bold uppercase tracking-wider text-xs">System Semantic Analysis Prompt</h3>
                    </div>
                    <textarea
                        name="semantic_analysis_prompt"
                        value={formData.semantic_analysis_prompt || ''}
                        onChange={handleChange}
                        rows={4}
                        placeholder="Global instructions for AI transcript analysis..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-3 text-sm text-slate-300 outline-none focus:ring-2 focus:ring-indigo-500 transition-all font-mono"
                    />
                    <p className="text-[10px] text-slate-500 italic italic uppercase tracking-widest">This prompt overrides the default analysis logic for all users.</p>
                </div>

                {/* API Key Monitoring */}
                <div className="glass-card p-6 md:col-span-2 space-y-6">
                    <div className="flex justify-between items-center border-b border-slate-800 pb-4">
                        <div className="flex items-center space-x-2 text-indigo-400">
                            <Key className="w-5 h-5" />
                            <h3 className="font-bold uppercase tracking-wider text-xs">Active API Keys</h3>
                        </div>
                        <button className="text-[10px] font-bold text-indigo-500 hover:text-indigo-400 uppercase tracking-widest transition-colors flex items-center space-x-1">
                            <span>Manage Key Store</span>
                        </button>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead>
                                <tr className="text-[10px] font-bold text-slate-500 uppercase tracking-widest border-b border-slate-800">
                                    <th className="pb-3 px-2">Service</th>
                                    <th className="pb-3 px-2">Key Mask</th>
                                    <th className="pb-3 px-2">Priority</th>
                                    <th className="pb-3 px-2 text-right">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/50">
                                {isKeysLoading ? (
                                    <tr><td colSpan={4} className="py-4 text-center text-xs text-slate-600 italic">Gathering key telemetry...</td></tr>
                                ) : (
                                    apiKeys?.map(key => (
                                        <tr key={key.id} className="text-xs group hover:bg-slate-800/20 transition-colors">
                                            <td className="py-3 px-2 font-bold text-slate-300">{key.service_name.toUpperCase()}</td>
                                            <td className="py-3 px-2 text-slate-500 font-mono">{key.masked_key || '****'}</td>
                                            <td className="py-3 px-2">
                                                <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-400">{key.priority}</span>
                                            </td>
                                            <td className="py-3 px-2 text-right">
                                                <span className={key.is_active ? "text-emerald-500" : "text-rose-500"}>
                                                    {key.is_active ? 'ACTIVE' : 'INACTIVE'}
                                                </span>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </form>
        </div>
    );
}
