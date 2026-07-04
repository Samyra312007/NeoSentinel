import { test, expect } from '@playwright/test';

test.describe('NeoSentinel E2E Simulation & Dashboard UI Flow', () => {
  test('should render cluster overview and all core UI components', async ({ page }) => {
    await page.goto('/');

    // Verify main header and brand title
    const header = page.locator('header');
    await expect(header).toBeVisible();
    await expect(page.locator('h1')).toHaveText('NEOSENTINEL');

    // Verify cluster overview stats
    await expect(page.locator('#overview')).toHaveText('Cluster Overview');
    await expect(page.locator('h3#nodes')).toHaveText('Nodes');

    // Verify UI sections are accessible via ARIA labels
    await expect(page.locator('section[aria-labelledby="nodes"]')).toBeVisible();
    await expect(page.locator('section[aria-labelledby="flame"]')).toBeVisible();
    await expect(page.locator('section[aria-labelledby="brain"]')).toBeVisible();
    await expect(page.locator('section[aria-labelledby="healing"]')).toBeVisible();
    await expect(page.locator('section[aria-labelledby="audit"]')).toBeVisible();
    await expect(page.locator('section[aria-labelledby="stream"]')).toBeVisible();

    // Verify theme toggle functionality
    const themeButton = page.getByRole('button', { name: /Switch to (light|dark) theme/i });
    await expect(themeButton).toBeVisible();
    await themeButton.click();

    await page.keyboard.press('Tab');
    await expect(themeButton).toBeFocused();
  });
});
