'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RotateCcw, Home } from 'lucide-react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('Uncaught error:', error, errorInfo);
    }

    private handleReset = () => {
        this.setState({ hasError: false, error: null });
        window.location.reload();
    };

    public render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6 font-inter">
                    <div className="max-w-md w-full glass-card p-8 border-rose-500/20 text-center space-y-6">
                        <div className="w-16 h-16 bg-rose-500/10 rounded-full flex items-center justify-center mx-auto">
                            <AlertCircle className="w-10 h-10 text-rose-500" />
                        </div>

                        <div className="space-y-2">
                            <h2 className="text-2xl font-bold text-slate-100">Something went wrong</h2>
                            <p className="text-sm text-slate-400">
                                The application encountered an unexpected error. Don't worry, your data is safe.
                            </p>
                        </div>

                        {this.state.error && (
                            <div className="bg-slate-900/50 rounded-lg p-3 text-left">
                                <p className="text-[10px] font-mono text-rose-400 break-all">
                                    {this.state.error.message}
                                </p>
                            </div>
                        )}

                        <div className="flex flex-col gap-3">
                            <button
                                onClick={this.handleReset}
                                className="flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-lg font-semibold transition-all"
                            >
                                <RotateCcw className="w-4 h-4" />
                                <span>Reload Application</span>
                            </button>
                            <a
                                href="/"
                                className="text-sm text-slate-400 hover:text-slate-200 transition-colors"
                            >
                                Back to Dashboard
                            </a>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
