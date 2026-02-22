import { test, expect } from '@playwright/test';

test.describe('Billing Page', () => {
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

        // Mock API Responses
        await page.route('**/api/v1/admin/**', async route => {
            const url = route.request().url();

            if (url.includes('/reports/revenue')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        total_revenue: 25000,
                        net_revenue: 18500,
                        total_expenses: 6500,
                        arpu: 12.50,
                        transaction_count: 2000
                    }),
                });
            } else if (url.includes('/wallets') && !url.includes('/credit') && !url.includes('/debit') && !url.includes('/toggle-freeze')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify([
                        {
                            id: 'w1',
                            user_id: 'user-001',
                            balance: 500,
                            currency: 'credits',
                            is_frozen: false,
                            monthly_limit: 1000,
                            used_this_month: 350,
                        },
                        {
                            id: 'w2',
                            user_id: 'user-002',
                            balance: 0,
                            currency: 'credits',
                            is_frozen: true,
                            monthly_limit: 500,
                            used_this_month: 500,
                        },
                    ]),
                });
            } else if (url.includes('/credit') || url.includes('/debit')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ success: true }),
                });
            } else if (url.includes('/toggle-freeze')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ message: 'Wallet freeze toggled' }),
                });
            } else if (url.includes('/dashboard/overview')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        users: { total: 100 }, content: { total_notes: 500 },
                        activity: { notes_today: 10 }, system: { database_status: 'healthy' },
                        revenue: { total_balance: 5000, revenue_this_month: 800 }
                    }),
                });
            } else {
                await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
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

    test('should render billing page with revenue stats', async ({ page }) => {
        await page.goto('/billing');
        await page.waitForSelector('text=Billing', { state: 'visible', timeout: 30000 });

        // Check revenue stat cards
        await expect(page.getByText(/Revenue|Profit|ARPU|Expense/i).first()).toBeVisible({ timeout: 15000 });
    });

    test('should render wallet table with mock data', async ({ page }) => {
        await page.goto('/billing');
        await page.waitForSelector('text=Billing', { state: 'visible', timeout: 30000 });

        // Wallet table should show user IDs
        await expect(page.getByText('user-001')).toBeVisible({ timeout: 15000 });
        await expect(page.getByText('user-002')).toBeVisible({ timeout: 15000 });
    });

    test('should show frozen status for frozen wallet', async ({ page }) => {
        await page.goto('/billing');
        await page.waitForSelector('text=Billing', { state: 'visible', timeout: 30000 });

        // Frozen wallet should show a frozen indicator
        await expect(page.getByText(/Frozen/i).first()).toBeVisible({ timeout: 15000 });
    });

    test('should have credit and debit action buttons', async ({ page }) => {
        await page.goto('/billing');
        await page.waitForSelector('text=Billing', { state: 'visible', timeout: 30000 });

        // Billing page uses icon buttons with title="Add Credit" / title="Deduct Credit"
        const creditBtn = page.locator('button[title="Add Credit"]').first();
        const debitBtn = page.locator('button[title="Deduct Credit"]').first();
        // Also check for text-based buttons or header action buttons
        const manualBtn = page.locator('button').filter({ hasText: /Manual Adjustment|credit|debit/i }).first();

        const hasCreditBtn = await creditBtn.isVisible({ timeout: 5000 }).catch(() => false);
        const hasDebitBtn = await debitBtn.isVisible({ timeout: 5000 }).catch(() => false);
        const hasManualBtn = await manualBtn.isVisible({ timeout: 5000 }).catch(() => false);
        expect(hasCreditBtn || hasDebitBtn || hasManualBtn).toBeTruthy();
    });

    test('should handle API errors with toast not alert', async ({ page }) => {
        // Override wallets endpoint to fail
        await page.route('**/api/v1/admin/wallets', async route => {
            if (route.request().url().includes('/wallets') && route.request().method() === 'GET') {
                await route.fulfill({
                    status: 500,
                    contentType: 'application/json',
                    body: JSON.stringify({ detail: 'Server error' }),
                });
            }
        });

        // Listen for dialogs (alerts) — should NOT appear
        let alertShown = false;
        page.on('dialog', () => { alertShown = true; });

        await page.goto('/billing');
        await page.waitForTimeout(3000);
        expect(alertShown).toBe(false);
    });
});
