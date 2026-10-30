"""Restart TV in Halcyon settings (Advanced), on a simulated TV.
- one OK only arms it ("Press OK again to restart"); moving away cancels; nothing is sent
- a second OK asks the Homebrew Channel's reboot service; when that is refused, `reboot` runs as root"""
import asyncio, json
from playwright.async_api import async_playwright
from tvmock import opts, tv_mock, root_cmds, PAGE, SHOTS

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**opts())
        pg = await b.new_page(viewport={'width': 1920, 'height': 1080})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.add_init_script(tv_mock([{"id": "app.one", "title": "App One"}], []))
        await pg.goto(PAGE); await pg.wait_for_timeout(2000)
        ev = lambda js: pg.evaluate(js)
        reboots = lambda: ev("window.__calls.filter(function(c){return /reboot/.test(c)})")

        for _ in range(3): await pg.keyboard.press('ArrowUp')          # tabs, peek, gear
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(500)
        for _ in range(12): await pg.keyboard.press('ArrowDown')       # the last page: Advanced
        summary = await ev("document.querySelector('#s-list .si.focus').textContent")
        print('page', repr(summary)); assert summary.startswith('Advanced') and 'Restart TV' in summary
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
        row = lambda: ev("document.querySelector('#s-list .si.focus').textContent")
        assert (await row()).startswith('Restart TV'), await row()

        # one OK arms it; moving away cancels; nothing sent
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        print('armed', repr(await row())); assert 'Press OK again to restart' in await row()
        await pg.screenshot(path=str(SHOTS/'reboot_armed.png'))
        await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(200)
        assert 'Press OK again' not in await ev("document.getElementById('s-list').textContent"), 'moving away should cancel'
        assert await reboots() == []

        # OK, OK: the Homebrew Channel's reboot service first (the mock refuses it, as a TV without it would), then root
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(600)
        calls = await reboots()
        print('reboot calls', calls)
        assert calls[0].startswith('luna://org.webosbrew.hbchannel.service/reboot'), calls
        assert any(json.loads(c.split(' ', 1)[1]).get('command') == 'reboot' for c in calls[1:]), calls
        assert (await ev("document.getElementById('toast').textContent")).startswith('Restarting the TV')
        print('errors', errs); assert not errs
        await b.close()
    print('test_reboot: OK')
asyncio.run(main())
