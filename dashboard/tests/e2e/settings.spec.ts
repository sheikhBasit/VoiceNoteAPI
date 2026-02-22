import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
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

            if (url.includes('/settings/ai') && route.request().method() === 'GET') {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        llm_model: 'llama-3.3-70b-versatile',
                        llm_fast_model: 'llama-3.1-8b-instant',
                        temperature: 7,
                        max_tokens: 4096,
                        top_p: 9,
                        stt_engine: 'deepgram',
                        groq_whisper_model: 'whisper-large-v3-turbo',
                        deepgram_model: 'nova-3',
                        semantic_analysis_prompt: 'Analyze this note for key themes.',
                        updated_at: Date.now(),
                        updated_by: 'admin-1'
                    }),
                });
            } else if (url.includes('/settings/ai') && route.request().method() === 'PATCH') {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ message: 'Settings updated' }),
                });
            } else if (url.includes('/api-keys')) {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify([
                        {
                            id: 'key-1',
                            service_name: 'groq',
                            api_key: 'gsk_****abcd',
                            priority: 1,
                            is_active: true,
                            notes: 'Primary Groq key',
                            created_at: Date.now()
                        },
                        {
                            id: 'key-2',
                            service_name: 'deepgram',
                            api_key: 'dg_****efgh',
                            priority: 1,
                            is_active: true,
                            notes: null,
                            created_at: Date.now()
                        }
                    ]),
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

    test('should render AI settings form', async ({ page }) => {
        await page.goto('/settings');
        await page.waitForSelector('text=Settings', { state: 'visible', timeout: 30000 });

        // AI model settings should be visible
        await expect(page.getByText(/LLM|Model|Temperature/i).first()).toBeVisible({ timeout: 15000 });
    });

    test('should display current AI settings values', async ({ page }) => {
        await page.goto('/settings');
        await page.waitForSelector('text=Settings', { state: 'visible', timeout: 30000 });

        // The temperature or model values should be rendered
        await expect(page.getByText(/Temperature|Primary Model|STT/i).first()).toBeVisible({ timeout: 15000 });
    });

    test('should render API keys table', async ({ page }) => {
        await page.goto('/settings');
        await page.waitForSelector('text=Settings', { state: 'visible', timeout: 30000 });

        // API keys section should show service names
        await expect(page.getByText(/API Key|groq|deepgram/i).first()).toBeVisible({ timeout: 15000 });
    });

    test('should have a save button for settings', async ({ page }) => {
        await page.goto('/settings');
        await page.waitForSelector('text=Settings', { state: 'visible', timeout: 30000 });

        const saveBtn = page.getByRole('button', { name: /save/i });
        await expect(saveBtn).toBeVisible({ timeout: 15000 });
    });

    test('should trigger save mutation on button click', async ({ page }) => {
        let patchCalled = false;
        await page.route('**/api/v1/admin/settings/ai', async route => {
            if (route.request().method() === 'PATCH') {
                patchCalled = true;
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ message: 'Settings updated' }),
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        llm_model: 'llama-3.3-70b-versatile',
                        llm_fast_model: 'llama-3.1-8b-instant',
                        temperature: 7, max_tokens: 4096, top_p: 9,
                        stt_engine: 'deepgram', groq_whisper_model: 'whisper-large-v3-turbo',
                        deepgram_model: 'nova-3', semantic_analysis_prompt: null,
                        updated_at: Date.now(), updated_by: null
                    }),
                });
            }
        });

        await page.goto('/settings');
        await page.waitForSelector('text=Settings', { state: 'visible', timeout: 30000 });

        // Fill in the semantic analysis prompt to pass validation
        const promptField = page.locator('textarea, input[type="text"]').last();
        if (await promptField.isVisible({ timeout: 3000 }).catch(() => false)) {
            await promptField.fill('Analyze this note for key themes.');
        }

        const saveBtn = page.getByRole('button', { name: /save/i });
        await saveBtn.click();

        // Wait for the mutation to fire
        await page.waitForTimeout(3000);
        expect(patchCalled).toBe(true);
    });
});
