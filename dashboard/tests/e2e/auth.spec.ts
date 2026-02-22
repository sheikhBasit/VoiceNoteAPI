import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
    test.slow(); // Increase timeout for this suite

    test.beforeEach(async ({ page }) => {
        page.on('console', msg => console.log(`PAGE LOG [${msg.type()}]: ${msg.text()}`));
        page.on('pageerror', err => console.log(`PAGE ERROR: ${err.message}`));
    });

    test('should redirect unauthenticated users to login', async ({ page }) => {
        await page.goto('/');
        await page.waitForURL(/.*login/, { timeout: 30000 });
        await expect(page).toHaveURL(/.*login/);
    });

    test('should show login page with all elements', async ({ page }) => {
        await page.goto('/login');
        await page.waitForSelector('text=Admin Gateway', { state: 'visible', timeout: 30000 });
        await expect(page.getByText(/Admin Gateway/i)).toBeVisible({ timeout: 15000 });
        await expect(page.locator('input[type="email"]')).toBeVisible();
        await expect(page.locator('input[type="password"]')).toBeVisible();
        await expect(page.locator('button[type="submit"]')).toBeVisible();
    });

    test('should show error on invalid login', async ({ page }) => {
        // Mock failing login with 400 (not 401, which triggers redirect interceptor)
        await page.route('**/api/v1/users/login', async route => {
            await route.fulfill({
                status: 400,
                contentType: 'application/json',
                body: JSON.stringify({ detail: 'Invalid credentials' }),
            });
        });

        await page.goto('/login');
        await page.waitForSelector('input[type="email"]', { state: 'visible', timeout: 30000 });
        await page.fill('input[type="email"]', 'invalid@voicenote.ai');
        await page.fill('input[type="password"]', 'wrongpassword');
        await page.click('button[type="submit"]');

        // Error message should show either the API detail or fallback text
        await expect(page.getByText(/Invalid credentials|Login failed/i)).toBeVisible({ timeout: 15000 });
    });

    test('should succeed and redirect on valid login', async ({ page }) => {
        // Mock successful login
        await page.route('**/api/v1/users/login', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    user: { id: 'admin-1', email: 'admin@voicenote.ai', name: 'Master Admin', is_admin: true },
                    access_token: 'mock-token'
                }),
            });
        });

        // Mock dashboard overview
        await page.route('**/api/v1/admin/dashboard/overview', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    users: { total: 0 }, content: { total_notes: 0 }, activity: { notes_today: 0 }, system: { database_status: 'healthy' }, revenue: { total_balance: 0 }
                }),
            });
        });

        await page.goto('/login');
        await page.waitForSelector('input[type="email"]', { state: 'visible', timeout: 30000 });
        await page.fill('input[type="email"]', 'admin@voicenote.ai');
        await page.fill('input[type="password"]', 'password');
        await page.click('button[type="submit"]');

        await page.waitForURL('**/', { timeout: 30000 });
        await expect(page).toHaveURL(/.*\//);
        await expect(page.getByText(/System Overview/i)).toBeVisible({ timeout: 15000 });
    });
});
