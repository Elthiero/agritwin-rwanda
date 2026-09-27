#!/usr/bin/env node
/**
 * Take screenshots of AgriTwin Rwanda web app for submission.
 */

import puppeteer from 'puppeteer';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SCREENSHOTS_DIR = path.join(__dirname, '../screenshots/web');
const BASE_URL = 'http://localhost:5173';

const SCREENSHOTS = [
  {
    name: '01-home-hero.png',
    url: '/',
    description: 'Home page with hero section',
    viewport: { width: 1920, height: 1080 },
  },
  {
    name: '02-map-overview.png',
    url: '/map',
    description: 'Map page with yield gap heatmap',
    viewport: { width: 1920, height: 1080 },
    waitFor: '.map',
    delay: 2000,
  },
  {
    name: '03-map-mobile.png',
    url: '/map',
    description: 'Map page on mobile (375px width)',
    viewport: { width: 375, height: 812 },
    waitFor: '.map',
    delay: 2000,
  },
  {
    name: '04-home-features.png',
    url: '/',
    description: 'Home page feature cards (scrolled)',
    viewport: { width: 1920, height: 1080 },
    delay: 500,
    scroll: 400,
  },
  {
    name: '05-early-estimate.png',
    url: '/early-estimate',
    description: 'Early estimate (nowcast) page',
    viewport: { width: 1920, height: 1080 },
    waitFor: '.page-content',
    delay: 2000,
  },
  {
    name: '06-scenario-explorer.png',
    url: '/scenario',
    description: 'Scenario explorer page',
    viewport: { width: 1920, height: 1080 },
    waitFor: '.page-content',
    delay: 2000,
  },
  {
    name: '07-methodology.png',
    url: '/methodology',
    description: 'Methodology page',
    viewport: { width: 1920, height: 1080 },
    waitFor: '.page-content',
    delay: 1000,
  },
  {
    name: '08-about.png',
    url: '/about',
    description: 'About page',
    viewport: { width: 1920, height: 1080 },
    waitFor: '.page-content',
    delay: 1000,
  },
];

async function takeScreenshots() {
  // Create screenshots directory
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
  }

  let browser;
  try {
    // Launch browser with specific executable path
    browser = await puppeteer.launch({
      headless: true,
      executablePath: '/usr/bin/chromium-browser',
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    for (const config of SCREENSHOTS) {
      console.log(`📸 Taking screenshot: ${config.name}`);
      console.log(`   URL: ${config.url}`);
      console.log(`   Description: ${config.description}`);

      const page = await browser.newPage();
      try {
        await page.setViewport(config.viewport);

        // Navigate to page
        await page.goto(`${BASE_URL}${config.url}`, {
          waitUntil: 'networkidle0',
          timeout: 10000,
        });

        // Wait for element if specified
        if (config.waitFor) {
          try {
            await page.waitForSelector(config.waitFor, { timeout: 5000 });
          } catch {
            console.log(`   ⚠️  Element not found, continuing anyway`);
          }
        }

        // Extra delay for animations
        if (config.delay) {
          await new Promise(r => setTimeout(r, config.delay));
        }

        // Scroll if specified
        if (config.scroll) {
          await page.evaluate((scrollAmount) => {
            window.scrollBy(0, scrollAmount);
          }, config.scroll);
          await new Promise(r => setTimeout(r, 500));
        }

        // Take screenshot
        const screenshotPath = path.join(SCREENSHOTS_DIR, config.name);
        await page.screenshot({ path: screenshotPath });
        console.log(`   ✓ Saved to ${screenshotPath}\n`);
      } catch (error) {
        console.log(`   ✗ Error: ${error.message}\n`);
      } finally {
        await page.close();
      }
    }

    console.log('✅ All screenshots captured!');
    console.log(`Screenshots saved to: ${SCREENSHOTS_DIR}`);
  } catch (error) {
    console.error('Fatal error:', error);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

takeScreenshots();
