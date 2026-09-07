const assert = require('node:assert/strict');
const { spawn, execFile } = require('node:child_process');
const { promisify } = require('node:util');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

async function startTestServer() {
    const server = spawn(process.env.PYTHON || 'python', ['-u', '-c',
        'from werkzeug.serving import make_server; from live_widget import app; ' +
        'server = make_server("127.0.0.1", 0, app, threaded=True); ' +
        'print("TEST_PORT=" + str(server.server_port), flush=True); server.serve_forever()'
    ], {
        cwd: path.resolve(__dirname, '..'),
        windowsHide: true,
        env: {
            ...process.env,
            PYTHONIOENCODING: 'utf-8',
            CONTROL_PASSWORD: 'browser-test-only-password',
            ALLOWED_ORIGINS: '',
            SPOTIFY_CLIENT_ID: '',
            SPOTIFY_CLIENT_SECRET: '',
            SPOTIFY_REFRESH_TOKEN: '',
            SPOTIFY_QUEUE_ON_REQUEST: '0',
            AUTO_NEXT_ON_THRESHOLD: '0',
            AUTO_RESET_SKIP_ENABLED: '0'
        }
    });
    let output = '';
    server.stderr.on('data', chunk => { output = (output + chunk).slice(-8000); });
    try {
        const port = await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => reject(new Error('Test server startup timed out: ' + output)), 30000);
            server.on('error', error => { clearTimeout(timeout); reject(error); });
            server.on('exit', code => { clearTimeout(timeout); reject(new Error('Test server exited: ' + code + '\n' + output)); });
            server.stdout.on('data', chunk => {
                output += chunk;
                const match = output.match(/TEST_PORT=(\d+)/);
                if (match) { clearTimeout(timeout); resolve(Number(match[1])); }
            });
        });
        return { server, url: 'http://127.0.0.1:' + port };
    } catch (error) {
        server.kill();
        throw error;
    }
}

async function main() {
    const { server, url } = await startTestServer();
    let browser;
    try {
        const smokeTest = await promisify(execFile)(process.env.PYTHON || 'python', [
            'test_socket_connection.py', '--url', url
        ], { cwd: path.resolve(__dirname, '..'), windowsHide: true, timeout: 20000 });
        assert.match(smokeTest.stdout, /No queue or playback changes were made/);
        browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || 'msedge', headless: true });
        const context = await browser.newContext({ viewport: { width: 375, height: 812 }, reducedMotion: 'reduce' });
        const errors = [];
        context.on('page', page => {
            page.on('pageerror', error => errors.push(error.message));
            page.on('console', message => {
                if (message.type() === 'error' && /content security policy|refused to execute/i.test(message.text())) errors.push(message.text());
            });
        });
        const overlay = await context.newPage();
        await overlay.goto(url);
        await overlay.waitForFunction(() => typeof socket !== 'undefined' && socket.connected);
        assert.equal(await overlay.locator('.mod-bar').isVisible(), false);
        assert.equal(await overlay.locator('.test-bar').isVisible(), false);
        assert.equal(await overlay.locator('#control-auth').isVisible(), false);
        await overlay.locator('.requests-panel.hidden-panel').waitFor({ state: 'attached' });
        for (const selector of ['html', 'body', '#voting-panel']) {
            assert.equal(await overlay.locator(selector).evaluate(element => getComputedStyle(element).backgroundColor), 'rgba(0, 0, 0, 0)');
        }
        assert.equal(await overlay.locator('#voting-panel').evaluate(element => getComputedStyle(element).boxShadow), 'none');
        assert.equal(await overlay.locator('#voting-panel').evaluate(element => getComputedStyle(element).backdropFilter), 'none');
        assert.equal(await overlay.locator('#voting-panel .border-glow').isVisible(), false);
        assert.equal(await overlay.locator('#voting-panel .glow-line').isVisible(), false);
        assert.equal(await overlay.locator('#particles').isVisible(), false);
        assert.notEqual(await overlay.locator('#skip-count').evaluate(element => getComputedStyle(element).textShadow), 'none');
        for (const viewport of [{ width: 200, height: 200 }, { width: 320, height: 240 }, { width: 1920, height: 1080 }]) {
            await overlay.setViewportSize(viewport);
            const panel = await overlay.locator('#voting-panel').boundingBox();
            for (const selector of ['.skip-command-hint', '#skip-meter-circle', '#skip-count']) {
                const bounds = await overlay.locator(selector).boundingBox();
                assert.ok(bounds && bounds.width > 0 && bounds.height > 0, selector + ' remains visible');
                assert.ok(bounds.x >= panel.x && bounds.x + bounds.width <= panel.x + panel.width + 1, selector + ' fits the panel');
                assert.ok(bounds.y >= 0 && bounds.y + bounds.height <= viewport.height, selector + ' fits the source height');
            }
        }
        await overlay.setViewportSize({ width: 200, height: 200 });
        await overlay.waitForFunction(() => getComputedStyle(document.getElementById('conn-banner')).opacity === '0');
        const skipScreenshot = await overlay.screenshot({
            omitBackground: true,
            ...(process.env.WIDGET_SCREENSHOT_DIR ? { path: path.join(process.env.WIDGET_SCREENSHOT_DIR, 'widget-skip-transparent.png') } : {})
        });
        const backgroundAlpha = await overlay.evaluate(async encodedImage => {
            const screenshotImage = new Image();
            screenshotImage.src = 'data:image/png;base64,' + encodedImage;
            await screenshotImage.decode();
            const canvas = document.createElement('canvas');
            canvas.width = screenshotImage.width;
            canvas.height = screenshotImage.height;
            const drawing = canvas.getContext('2d');
            drawing.drawImage(screenshotImage, 0, 0);
            const panelBounds = document.getElementById('voting-panel').getBoundingClientRect();
            return [
                drawing.getImageData(0, 0, 1, 1).data[3],
                drawing.getImageData(100, 190, 1, 1).data[3],
                drawing.getImageData(Math.floor(panelBounds.x + 2), Math.floor(panelBounds.y + panelBounds.height / 2), 1, 1).data[3]
            ];
        }, skipScreenshot.toString('base64'));
        assert.deepEqual(backgroundAlpha, [0, 0, 0], 'Rendered page and empty card areas have fully transparent pixels');
        await overlay.setViewportSize({ width: 375, height: 812 });

        const backgroundPreview = await context.newPage();
        for (const query of ['?bg=black', '?transparent=0', '?bg=transparent', '?transparent=1', '?controls=1']) {
            await backgroundPreview.goto(url + '/' + query);
            await backgroundPreview.waitForFunction(() => typeof socket !== 'undefined' && socket.connected);
            const transparent = query === '?bg=transparent' || query === '?transparent=1';
            assert.equal(await backgroundPreview.locator('body').evaluate(element => getComputedStyle(element).backgroundColor), transparent ? 'rgba(0, 0, 0, 0)' : 'rgb(0, 0, 0)');
            assert.equal(await backgroundPreview.locator('#voting-panel').evaluate(element => getComputedStyle(element).backgroundColor === 'rgba(0, 0, 0, 0)'), transparent);
        }
        await backgroundPreview.close();

        const controls = await context.newPage();
        await controls.goto(url + '/control');
        await controls.waitForFunction(() => typeof socket !== 'undefined' && socket.connected);
        assert.equal(await controls.locator('body').evaluate(element => getComputedStyle(element).backgroundColor), 'rgb(0, 0, 0)');
        assert.notEqual(await controls.locator('#voting-panel').evaluate(element => getComputedStyle(element).backgroundColor), 'rgba(0, 0, 0, 0)');
        assert.equal(await controls.getByLabel('Control password', { exact: true }).isVisible(), true);
        await controls.locator('#mod-toggle').click();
        assert.equal(await controls.locator('#mod-panel').isVisible(), false);
        assert.equal(await controls.locator('#mod-password').isVisible(), true);
        await controls.locator('#test-toggle').click();
        await controls.locator('#test-message').fill('!req Offline Test by Artist');
        await controls.locator('#test-send').click();
        await controls.waitForFunction(() => document.getElementById('control-auth-status').textContent.includes('Enter your control password'));
        assert.equal(await controls.locator('#test-message').inputValue(), '!req Offline Test by Artist');
        assert.equal(await controls.evaluate(() => document.activeElement.id), 'mod-password');

        await controls.locator('#mod-password').fill('wrong-password');
        await controls.locator('#mod-login').click();
        await controls.waitForFunction(() => document.getElementById('control-auth-status').textContent.includes('Password not accepted'));
        await controls.evaluate(() => {
            window.originalStorageSetItem = Storage.prototype.setItem;
            Storage.prototype.setItem = function() { throw new Error('Storage unavailable'); };
        });
        await controls.locator('#mod-password').fill('browser-test-only-password');
        await controls.locator('#mod-login').click();
        await controls.waitForFunction(() => document.getElementById('mod-feedback').textContent.includes('unlocked'));
        assert.equal(await controls.evaluate(() => sessionStorage.getItem('modPassword')), null);
        await controls.locator('#test-send').click();
        await controls.waitForFunction(() => document.getElementById('test-message').value === '');
        await overlay.waitForFunction(() => document.getElementById('request-count').textContent === '1');
        await controls.evaluate(() => { Storage.prototype.setItem = window.originalStorageSetItem; });
        await controls.locator('#mod-logout').click();
        await controls.locator('#test-message').fill('!skip');
        await controls.locator('#test-send').click();
        await controls.waitForFunction(() => document.activeElement.id === 'mod-password');
        assert.equal(await controls.locator('#test-message').inputValue(), '!skip');
        await controls.locator('#mod-password').fill('browser-test-only-password');
        await controls.locator('#mod-login').click();
        await controls.waitForFunction(() => document.getElementById('control-auth-status').textContent.includes('Controls unlocked'));
        await controls.locator('#test-unlock').click();
        assert.equal(await controls.evaluate(() => document.activeElement.id), 'mod-password');
        await controls.locator('#mod-toggle').click();
        await controls.locator('#vis-requests').check();
        await overlay.locator('.requests-panel').waitFor({ state: 'visible' });
        await controls.locator('#vis-skip').uncheck();
        await overlay.locator('.voting-panel').waitFor({ state: 'hidden' });
        await controls.locator('#vis-requests').uncheck();
        await controls.locator('#vis-requests').check();
        assert.equal(await overlay.locator('.voting-panel').isVisible(), false);
        await controls.locator('#vis-skip').check();

        const renderedName = await overlay.evaluate(() => {
            const items = [{ user: 'A&B <viewer>', song: '<img src=x onerror=alert(1)> by Artist' }];
            renderQueue(items);
            renderQueue(items);
            return items[0].user;
        });
        assert.equal(renderedName, 'A&B <viewer>');
        assert.equal(await overlay.locator('.request-item img').count(), 0);
        assert.match(await overlay.locator('.user-tag').textContent(), /A&B <viewer>/);
        const denial = await overlay.evaluate(() => new Promise(resolve => socket.emit('mod_clear', { moderator: 'trusted' }, resolve)));
        assert.equal(denial.error, 'unauthorized');

        const queue = await context.newPage();
        await queue.goto(url + '/queue_widget');
        await queue.waitForFunction(() => typeof socket !== 'undefined' && socket.connected);
        await queue.evaluate(() => {
            requestQueueItems = [{ user: 'Viewer', song: 'First Request by Artist' }];
            spotifyQueueStatus = { auth_ready: false };
            syncQueueSourceAndRender();
        });
        assert.match(await queue.locator('#queue-list').textContent(), /First Request/);
        await queue.evaluate(() => {
            spotifyQueueStatus = { auth_ready: true, last_error: 'test error' };
            spotifyQueueItems = [];
            syncQueueSourceAndRender();
        });
        assert.match(await queue.locator('#queue-list').textContent(), /No queued songs/);
        assert.match(await queue.locator('#queue-status').textContent(), /sync unavailable/);
        const elapsed = await queue.evaluate(() => {
            handleNow({ available: true, title: 'Test Song', artist: 'Artist', elapsed: 30, duration: 200, playing: false });
            nowAnchorMs = Date.now() - 90000;
            handleNow({ available: true, title: 'Test Song', artist: 'Artist', elapsed: 30, duration: 200, playing: true });
            return currentElapsedSec();
        });
        assert.ok(elapsed >= 30 && elapsed < 32, 'Playback must resume without jumping ahead');

        for (const page of [overlay, controls, queue]) {
            for (const width of [320, 375, 768]) {
                await page.setViewportSize({ width, height: 812 });
                assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No horizontal overflow at ' + width);
            }
            await page.setViewportSize({ width: 375, height: 812 });
        }
        if (process.env.WIDGET_SCREENSHOT_DIR) {
            await controls.evaluate(() => window.scrollTo(0, 0));
            assert.ok(await controls.locator('.control-heading').isVisible());
            await controls.screenshot({ path: path.join(process.env.WIDGET_SCREENSHOT_DIR, 'widget-controls.png'), fullPage: true });
            await queue.screenshot({ path: path.join(process.env.WIDGET_SCREENSHOT_DIR, 'widget-queue.png'), fullPage: true });
        }

        await context.setOffline(true);
        await controls.evaluate(() => socket.io.engine.close());
        await queue.evaluate(() => socket.io.engine.close());
        await controls.waitForFunction(() => document.getElementById('mod-clear').disabled);
        assert.equal(await queue.locator('#connection-status').isVisible(), true);
        const disconnectedAction = await controls.evaluate(() => new Promise(resolve => sendModeratorAction('mod_clear', {}, resolve)));
        assert.match(disconnectedAction.error, /Disconnected/);
        const frozenClock = await queue.evaluate(() => {
            const before = currentElapsedSec();
            nowAnchorMs -= 60000;
            return currentElapsedSec() === before;
        });
        assert.equal(frozenClock, true);
        await context.setOffline(false);
        await queue.waitForFunction(() => socket.connected && document.getElementById('connection-status').hidden);
        await controls.waitForFunction(() => socket.connected && !document.getElementById('mod-clear').disabled);
        assert.deepEqual(errors, [], 'No JavaScript or CSP errors');
        console.log('PASS: transparent skip background, compact source sizing, opaque control panel, background overrides, visible password entry, locked test guidance, rejected passwords, blocked-storage auth, simulated requests, overlay controls, escaping, visibility, queue states, playback resume, mobile widths, offline safety, reconnect, and CSP');
    } finally {
        if (browser) await browser.close();
        server.kill();
    }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
