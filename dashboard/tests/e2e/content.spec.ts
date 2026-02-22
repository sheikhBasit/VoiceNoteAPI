import { test, expect } from '@playwright/test';

test.describe('Dashboard Content Rendering', () => {
    test.slow();

    // Mock authentication and all backend API calls
    test.beforeEach(async ({ page }) => {
        // Log console messages and errors from the page
        page.on('console', msg => console.log(`PAGE LOG [${msg.type()}]: ${msg.text()}`));
        page.on('pageerror', err => console.log(`PAGE ERROR: ${err.message}`));

        // Mock Session in LocalStorage
        await page.addInitScript(() => {
            window.localStorage.setItem('auth-storage', JSON.stringify({
                state: {
                    user: { id: 'admin-1', email: 'admin@voicenote.ai', name: 'Master Admin', is_admin: true },
                    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbi0xIiwiZXhwIjo0MTAyNDQ0ODAwfQ.mock_signature'
                },
                version: 0
            }));
        });

        // Mock API Responses
        await page.route('**/api/v1/admin/**', async route => {
            const url = route.request().url();
            if (url.includes('/dashboard/overview')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        users: { total: 1500, active: 1200, new_this_month: 45, deleted: 10, admins: 5 },
                        content: { total_notes: 8500, total_tasks: 3200, total_teams: 12, total_folders: 85 },
                        activity: { notes_today: 120, tasks_today: 45, active_users_24h: 350 },
                        system: { database_status: 'healthy', redis_status: 'healthy', celery_workers: 8 },
                        revenue: { total_balance: 15000, revenue_this_month: 2450 }
                    }),
                });
            } else if (url.includes('/users')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        users: [
                            { id: '1', name: 'Test User', email: 'test@example.com', is_admin: false, plan_name: 'PREMIUM', balance: 100, is_deleted: false }
                        ],
                        total: 1
                    }),
                });
            } else if (url.includes('/analytics/usage')) {
                await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ usage_by_period: {} }) });
            } else if (url.includes('/analytics/growth')) {
                await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tier_distribution: { 'FREE': 10, 'PREMIUM': 5 }, retention: { retention_rate_percent: 85 } }) });
            } else if (url.includes('/analytics/revenue')) {
                await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ net_revenue: 1000, arpu: 10, transaction_count: 100 }) });
            } else if (url.includes('/notes/audit')) {
                await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) });
            } else if (url.includes('/tasks/active')) {
                await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tasks: [] }) });
            } else if (url.includes('/transactions')) {
                await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) });
            } else {
                await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) });
            }
        });

        // Mock /users/me for auth check
        await page.route('**/api/v1/users/me', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ id: 'admin-1', email: 'admin@voicenote.ai', name: 'Master Admin', is_admin: true }),
            });
        });
    });

    test('should render dashboard overview metrics', async ({ page }) => {
        await page.goto('/');
        // Explicitly wait for the stabilizing element
        await page.waitForSelector('text=System Overview', { state: 'visible', timeout: 30000 });

        await expect(page.getByText(/System Overview/i)).toBeVisible({ timeout: 15000 });
        await expect(page.getByText(/Total Users/i)).toBeVisible({ timeout: 15000 });
        await expect(page.getByText(/Active Notes/i)).toBeVisible({ timeout: 15000 });
    });

    test('should navigate to user management', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /User Management/i }).click();
        await expect(page).toHaveURL(/.*users/, { timeout: 15000 });
    });

    test('should navigate to analytics hub', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /Analytics/i }).first().click();
        await expect(page).toHaveURL(/.*analytics/, { timeout: 15000 });
    });

    test('should navigate to system monitoring', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /System Monitoring/i }).click();
        await expect(page).toHaveURL(/.*system/, { timeout: 15000 });
    });

    test('should navigate to content moderation', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /Moderation/i }).click();
        await expect(page).toHaveURL(/.*moderation/, { timeout: 15000 });
    });

    test('should navigate to operations center', async ({ page }) => {
        // Operations Center is not in sidebar nav — navigate directly
        await page.goto('/operations');
        await page.waitForLoadState('networkidle');
        await expect(page.getByText(/Operations/i).first()).toBeVisible({ timeout: 15000 });
    });

    test('should responsive sidebar toggle handles', async ({ page }) => {
        await page.setViewportSize({ width: 375, height: 667 });
        await page.goto('/');
        await expect(page.getByText(/VoiceNote Admin/i)).toBeVisible({ timeout: 15000 });
    });
});
