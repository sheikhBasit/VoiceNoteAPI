import { test, expect } from '@playwright/test';

test.describe('Dashboard Content Rendering', () => {
    // Use a mock token for rendering tests to avoid backend dependency in pure UI tests
    test.beforeEach(async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('auth-storage', JSON.stringify({
                state: {
                    user: { id: 'admin-1', email: 'admin@voicenote.ai', name: 'Master Admin', is_admin: true },
                    token: 'mock-token'
                },
                version: 0
            }));
        });
    });

    test('should render metrics cards', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('text=Total Users')).toBeVisible();
        await expect(page.locator('text=Active Notes')).toBeVisible();
        await expect(page.locator('text=System Pulse')).toBeVisible();
    });

    test('should navigate to user management', async ({ page }) => {
        await page.goto('/');
        await page.click('text=User Management');
        await expect(page).toHaveURL(/.*users/);
        await expect(page.locator('h1')).toContainText('User Directory');
    });

    test('should responsive sidebar toggle handles', async ({ page }) => {
        // Test mobile view
        await page.setViewportSize({ width: 375, height: 667 });
        await page.goto('/');
        // Sidebar might be hidden or in a hamburger on mobile
        // Add specific mobile checks here
    });
});
