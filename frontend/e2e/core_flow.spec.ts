import { test, expect } from '@playwright/test';

test.describe('OpsPulse Core Dashboard Navigation & Triage Flow', () => {
  test('navigates seamlessly across overview, infrastructure, incidents, and alert rules', async ({ page }) => {
    // 1. Load System Overview
    await page.goto('http://localhost:4173/');
    await expect(page).toHaveTitle(/OpsPulse/i);
    await expect(page.locator('h2')).toContainText('System Overview');

    // 2. Navigate to Infrastructure Fleet View
    await page.click('a[href="/infrastructure"]');
    await expect(page).toHaveURL(/.*\/infrastructure/);
    await expect(page.locator('h2')).toContainText('Infrastructure');

    // 3. Navigate to Incidents Management & Triage
    await page.click('a[href="/incidents"]');
    await expect(page).toHaveURL(/.*\/incidents/);
    await expect(page.locator('h2')).toContainText('Incidents');

    // 4. Navigate to Alert Rules Config
    await page.click('a[href="/alerts"]');
    await expect(page).toHaveURL(/.*\/alerts/);
    await expect(page.locator('h2')).toContainText('Alert Rules');
  });
});

