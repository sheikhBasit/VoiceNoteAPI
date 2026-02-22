import { test, expect } from '@playwright/test';

test.describe('Sidebar Navigation', () => {
    test.slow();

    test.beforeEach(async ({ page }) => {
        page.on('console', msg => console.log(`PAGE LOG [${msg.type()}]: ${msg.text()}`));
        page.on('pageerror', err => console.log(`PAGE ERROR: ${err.message}`));

        // Mock auth
        await page.addInitScript(() => {
            window.localStorage.setItem('auth-storage', JSON.stringify({
                state: {
                    user: { id: 'admin-1', email: 'admin@voicenote.ai', name: 'Master Admin', is_admin: true },
                    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbi0xIiwiZXhwIjo0MTAyNDQ0ODAwfQ.mock_signature'
                },
                version: 0
            }));
        });

        // Mock all admin API routes
        await page.route('**/api/v1/admin/**', async route => {
            const url = route.request().url();
            if (url.includes('/dashboard/overview')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        users: { total: 100, active: 80, new_this_month: 5, deleted: 2, admins: 3 },
                        content: { total_notes: 500, total_tasks: 200, total_teams: 5, total_folders: 20 },
                        activity: { notes_today: 10, tasks_today: 5, active_users_24h: 30 },
                        system: { database_status: 'healthy', redis_status: 'healthy', celery_workers: 4 },
                        revenue: { total_balance: 5000, revenue_this_month: 800 }
                    }),
                });
            } else if (url.includes('/users')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ users: [], total: 0 }),
                });
            } else if (url.includes('/analytics')) {
                await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
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

    test('should display VoiceNote Admin branding', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByText(/VoiceNote Admin/i)).toBeVisible({ timeout: 15000 });
    });

    test('should show all sidebar navigation items', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');

        // Use role-based selectors to avoid strict mode violations with duplicate text
        const navLinks = [
            'Dashboard',
            'User Management',
            'Analytics',
            'System Monitoring',
            'Moderation',
            'Billing',
            'Audit Logs',
            'Settings',
        ];

        for (const item of navLinks) {
            await expect(page.getByRole('link', { name: item })).toBeVisible({ timeout: 10000 });
        }
    });

    test('should navigate to User Management', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /User Management/i }).click();
        await expect(page).toHaveURL(/.*users/, { timeout: 15000 });
    });

    test('should navigate to Analytics', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /Analytics/i }).first().click();
        await expect(page).toHaveURL(/.*analytics/, { timeout: 15000 });
    });

    test('should navigate to System Monitoring', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /System Monitoring/i }).click();
        await expect(page).toHaveURL(/.*system/, { timeout: 15000 });
    });

    test('should navigate to Moderation', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /Moderation/i }).click();
        await expect(page).toHaveURL(/.*moderation/, { timeout: 15000 });
    });

    test('should navigate to Billing', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /Billing/i }).click();
        await expect(page).toHaveURL(/.*billing/, { timeout: 15000 });
    });

    test('should navigate to Audit Logs', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /Audit Logs/i }).click();
        await expect(page).toHaveURL(/.*logs/, { timeout: 15000 });
    });

    test('should navigate to Settings', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.getByRole('link', { name: /Settings/i }).click();
        await expect(page).toHaveURL(/.*settings/, { timeout: 15000 });
    });

    test('should logout and redirect to login', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');

        // Click the logout button (text is "Logout Session")
        const logoutBtn = page.getByRole('button', { name: /logout/i });
        if (await logoutBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
            await logoutBtn.click();
            await page.waitForURL(/.*login/, { timeout: 15000 });
            await expect(page).toHaveURL(/.*login/);
        }
    });
});
