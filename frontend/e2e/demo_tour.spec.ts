import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test('record full platform demo video tour', async ({ page }) => {
  const recordingsDir = path.resolve(process.cwd(), '../demo_recordings');
  if (!fs.existsSync(recordingsDir)) {
    fs.mkdirSync(recordingsDir, { recursive: true });
  }

  // 1. Authenticate with admin account to set HttpOnly session cookie
  const loginResp = await page.request.post('http://127.0.0.1:5173/api/v1/auth/login', {
    data: {
      email: 'admin@opspulse.local',
      password: 'adminpassword',
    },
  });
  expect(loginResp.ok()).toBeTruthy();

  // 2. System Overview Dashboard
  await page.goto('http://127.0.0.1:5173/');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(recordingsDir, '01_system_overview.png') });

  // 3. Infrastructure Fleet View
  await page.click('a[href="/infrastructure"]');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(recordingsDir, '02_infrastructure.png') });

  // 4. Machine Detail Telemetry (Recharts charts)
  const hostRow = page.locator('tbody tr').first();
  await hostRow.click();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(4000);
  await page.screenshot({ path: path.join(recordingsDir, '03_machine_detail.png') });

  // 5. Incident Management & Triage
  await page.click('a[href="/incidents"]');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  // Click on the first incident row to open master-detail triage panel
  const incRow = page.locator('tbody tr').first();
  await incRow.click();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(recordingsDir, '04_incident_triage.png') });

  // Acknowledge incident if visible
  const ackBtn = page.getByRole('button', { name: 'Acknowledge', exact: true });
  if (await ackBtn.isVisible()) {
    await ackBtn.click();
    await page.waitForTimeout(1500);
  }

  // Submit investigation note
  const noteInput = page.locator('input[placeholder*="investigation note"]');
  if (await noteInput.isVisible()) {
    await noteInput.fill('Checked process tree via htop; isolated noisy worker thread.');
    await page.locator('form button[type="submit"]').click();
    await page.waitForTimeout(2500);
  }

  // 6. Alert Rules
  await page.click('a[href="/alerts"]');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(recordingsDir, '05_alert_rules.png') });

  // Open modal
  const newRuleBtn = page.getByRole('button', { name: 'New Rule' });
  if (await newRuleBtn.isVisible()) {
    await newRuleBtn.click();
    await page.waitForTimeout(1500);

    const nameInput = page.locator('div[role="dialog"] input, div.fixed input').first();
    if (await nameInput.isVisible()) {
      await nameInput.fill('Worker Disk Capacity Warning');
    }
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(recordingsDir, '06_create_rule_modal.png') });

    const cancelBtn = page.getByRole('button', { name: 'Cancel' });
    if (await cancelBtn.isVisible()) {
      await cancelBtn.click();
      await page.waitForTimeout(1000);
    }
  }

  // 7. Return to Overview
  await page.click('a[href="/"]');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);
});
