import { describe, it, expect } from 'vitest';
import { cn } from '@/lib/utils';

describe('cn utility', () => {
    it('merges tailwind classes correctly', () => {
        expect(cn('bg-red-500', 'p-4')).toBe('bg-red-500 p-4');
    });

    it('handles conditional classes', () => {
        expect(cn('p-4', true && 'bg-blue-500', false && 'text-white')).toBe('p-4 bg-blue-500');
    });

    it('resolves tailwind conflicts', () => {
        expect(cn('p-4 p-8')).toBe('p-8');
    });
});
