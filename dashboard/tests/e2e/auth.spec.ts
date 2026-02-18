import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
    test('should redirect unauthenticated users to login', async ({ page }) => {
        await page.goto('/');
        await expect(page).toHaveURL(/.*login/);
    });

    test('should show login page with all elements', async ({ page }) => {
        await page.goto('/login');
        await expect(page.locator('h1')).toContainText('Admin Gateway');
        await expect(page.locator('input[type="email"]')).toBeVisible();
        await expect(page.locator('input[type="password"]')).toBeVisible();
        await expect(page.locator('button[type="submit"]')).toBeVisible();
    });

    test('should show error on invalid login', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[type="email"]', 'invalid@voicenote.ai');
        await page.fill('input[type="password"]', 'wrongpassword');
        await page.click('button[type="submit"]');

        // Check for error message (this depends on your actual Error state in LoginForm)
        await expect(page.locator('text=Login failed')).toBeVisible();
    });
});
