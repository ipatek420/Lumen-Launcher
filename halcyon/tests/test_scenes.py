"""Home Assistant scenes in the dock, on a simulated TV.
- halcyon.json missing (404) -> falls back to an existing Lumen setup's lumen.json
- both requests go through root curl, never XHR (a CORS-blocked POST would still run the automation)
- webhook ids that could break the URL or the shell command are dropped
- pressing a scene POSTs /api/webhook/<id> once and confirms with a toast"""
import asyncio, json
from playwright.async_api import async_playwright
from tvmock import opts, tv_mock, root_cmds, settings_script, PAGE, SHOTS

TILES = {"title": "Living room", "tiles": [
    {"name": "Movie time", "icon": "movie", "webhook": "lumen-movie-x1", "description": "Dims the lights."},
    {"name": "Lamp", "icon": "lamp", "webhook": "lumen-lamp-x2"},
    {"name": "Bad", "icon": "fan", "webhook": "x'; rm -rf / #"},
    {"name": "Also bad", "webhook": "a/b"}]}
CURL = {"/local/halcyon.json": [404, "Not found"], "/local/lumen.json": [200, json.dumps(TILES)], "/api/webhook/": [200, ""]}
LPS = [{"id": "app.one", "title": "App One"}]
DEVS = [{"id": "HDMI_1", "label": "PS5", "appId": "com.webos.app.hdmi1", "connected": True}]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**opts())
        pg = await b.new_page(viewport={'width': 1920, 'height': 1080})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        xhr = []; pg.on('request', lambda r: '8123' in r.url and xhr.append(r.url))
        await pg.add_init_script(tv_mock(LPS, DEVS, curl=CURL))
        await pg.add_init_script(settings_script({'haAddr': '192.168.1.20'}))
        await pg.goto(PAGE); await pg.wait_for_timeout(2500)
        ev = lambda js: pg.evaluate(js)

        gets = [c for c in root_cmds(await ev('window.__calls')) if c.startswith('curl') and '/local/' in c]
        assert any('halcyon.json' in c for c in gets) and any('lumen.json' in c for c in gets), gets
        dock = await ev("Array.prototype.map.call(document.querySelectorAll('#dock .pill'),function(e){return e.textContent})")
        print('dock', dock); assert dock == ['PS5', 'Movie time', 'Lamp'], dock
        assert 'Living room' in await ev("document.getElementById('dock').textContent")
        await pg.screenshot(path=str(SHOTS/'scenes_dock.png'))

        # Down to the dock, Right to Movie time, OK
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(300)
        await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(500)
        assert await ev("document.getElementById('title').textContent") == 'Movie time'
        assert 'Scene' in await ev("document.getElementById('eyebrow').textContent")
        await ev('window.__calls=[]')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(800)
        posts = [c for c in root_cmds(await ev('window.__calls')) if '-X POST' in c]
        print('posts', posts)
        assert len(posts) == 1 and "'http://192.168.1.20:8123/api/webhook/lumen-movie-x1'" in posts[0]
        toast = await ev("document.getElementById('toast').textContent")
        print('toast', toast); assert toast.startswith('Movie time')
        assert await ev("document.querySelector('#dock .pill.focus').classList.contains('ok')")
        await pg.screenshot(path=str(SHOTS/'scenes_run.png'))

        print('xhr to Home Assistant', xhr); assert not xhr, 'Home Assistant must only be reached through root curl on the TV'
        print('errors', errs); assert not errs
        await b.close()
    print('test_scenes: OK')
asyncio.run(main())
