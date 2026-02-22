import { test, expect } from '@playwright/test';

test.describe('User Management Page', () => {
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

            if (url.includes('/admin/users') && !url.includes('/make-admin') && !url.includes('/remove-admin')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        users: [
                            {
                                id: 'user-001',
                                name: 'Alice Johnson',
                                email: 'alice@example.com',
                                is_admin: false,
                                plan_name: 'PREMIUM',
                                balance: 250,
                                usage_stats: {},
                                is_deleted: false,
                                last_login: Date.now()
                            },
                            {
                                id: 'user-002',
                                name: 'Bob Smith',
                                email: 'bob@example.com',
                                is_admin: true,
                                plan_name: 'ENTERPRISE',
                                balance: 1000,
                                usage_stats: {},
                                is_deleted: false,
                                last_login: Date.now()
                            },
                            {
                                id: 'user-003',
                                name: 'Carol Davis',
                                email: 'carol@example.com',
                                is_admin: false,
                                plan_name: 'FREE',
                                balance: 0,
                                usage_stats: {},
                                is_deleted: false,
                                last_login: Date.now() - 86400000
                            }
                        ],
                        total: 3
                    }),
                });
            } else if (url.includes('/make-admin')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ message: 'User promoted to admin' }),
                });
            } else if (url.includes('/remove-admin')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ message: 'Admin privileges revoked' }),
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

    test('should render user table with mock data', async ({ page }) => {
        await page.goto('/users');
        await page.waitForSelector('text=User Management', { state: 'visible', timeout: 30000 });

        // User names should be visible
        await expect(page.getByText('Alice Johnson')).toBeVisible({ timeout: 15000 });
        await expect(page.getByText('Bob Smith')).toBeVisible({ timeout: 15000 });
        await expect(page.getByText('Carol Davis')).toBeVisible({ timeout: 15000 });
    });

    test('should show user emails', async ({ page }) => {
        await page.goto('/users');
        await page.waitForSelector('text=User Management', { state: 'visible', timeout: 30000 });

        await expect(page.getByText('alice@example.com')).toBeVisible({ timeout: 15000 });
    });

    test('should display tier/plan information', async ({ page }) => {
        await page.goto('/users');
        await page.waitForSelector('text=User Management', { state: 'visible', timeout: 30000 });

        await expect(page.getByText(/PREMIUM/i).first()).toBeVisible({ timeout: 15000 });
    });

    test('should have action buttons for users', async ({ page }) => {
        await page.goto('/users');
        await page.waitForSelector('text=User Management', { state: 'visible', timeout: 30000 });

        // Buttons use accessible names (title/aria-label), not visible text
        const adminBtn = page.getByRole('button', { name: /Make Admin|Revoke Admin/i }).first();
        await expect(adminBtn).toBeVisible({ timeout: 10000 });
    });

    test('should have search input', async ({ page }) => {
        await page.goto('/users');
        await page.waitForSelector('text=User Management', { state: 'visible', timeout: 30000 });

        const searchInput = page.locator('input[placeholder*="earch"], input[type="search"], input[placeholder*="filter"]').first();
        await expect(searchInput).toBeVisible({ timeout: 15000 });
    });

    test('should show pagination controls', async ({ page }) => {
        await page.goto('/users');
        await page.waitForSelector('text=User Management', { state: 'visible', timeout: 30000 });

        // Look for pagination text (showing X of Y)
        const paginationText = page.getByText(/showing|of \d+ user/i).first();
        const hasPagination = await paginationText.isVisible({ timeout: 5000 }).catch(() => false);

        // Or look for prev/next buttons
        const prevBtn = page.getByRole('button', { name: /previous|prev/i });
        const hasPrev = await prevBtn.isVisible({ timeout: 5000 }).catch(() => false);

        expect(hasPagination || hasPrev).toBeTruthy();
    });
});
