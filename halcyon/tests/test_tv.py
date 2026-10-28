"""Halcyon on a simulated rooted TV: every direct Luna call is denied, so apps, sources, icons, launching and
TV settings must all work through the Homebrew Channel's root service. Also covers the shelf, tabs, dock and
top-button navigation, Recent, the options menu, relaunch, and that no package ids reach the screen."""
import asyncio, json
from playwright.async_api import async_playwright
from tvmock import opts, tv_mock, root_cmds, b64, settings_script, PAGE, SHOTS, FIX

I = str(FIX/'icons')+'/'
LPS = [{"id":"stream.dark","title":"StreamFlix","largeIcon":"/blocked/dark.png"},
       {"id":"tube.white","title":"TubeView","largeIcon":I+"white.png"},
       {"id":"orb.clear","title":"Orb Music","largeIcon":I+"clear.png"},
       {"id":"photo.tile","title":"Gallery TV","largeIcon":I+"photo.png"},
       {"id":"blue.app","title":"Blue Plus","largeIcon":I+"blue.png"},
       {"id":"no.icon","title":"Plain App"},
       {"id":"works.partridge.webos-launcher","title":"Partridge Launcher"},
       {"id":"com.webos.app.hdmi1","title":"HDMI 1"},
       {"id":"org.webosbrew.halcyon","title":"Halcyon"}]
DEVS = [{"id":"HDMI_1","label":"PS5","appId":"com.webos.app.hdmi1","connected":True},
        {"id":"HDMI_2","label":"HDMI2","appId":"com.webos.app.hdmi2","connected":False},
        {"id":"HDMI_3","label":"Apple TV","connected":True},
        {"id":"AV_1","label":"AV","appId":"com.webos.app.externalinput.av1","connected":True}]
# root cat serves every icon: on file:// pages the canvas is tainted, so colours are read from the root copy (as on the TV)
FILES = {I+n: b64(I+n) for n in ('white.png','clear.png','photo.png','blue.png')}
FILES["/blocked/dark.png"] = b64(I+'dark.png')

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**opts())
        pg = await b.new_page(viewport={'width':1920,'height':1080})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.add_init_script(tv_mock(LPS, DEVS, FILES))
        await pg.add_init_script(settings_script({'name':'Sam'}))
        await pg.add_init_script("window.webOSSystem={activate:function(){ window.__activated=(window.__activated||0)+1; }};")
        await pg.goto(PAGE); await pg.wait_for_timeout(2500)
        ev = lambda js: pg.evaluate(js)

        # apps come from launch points through root; inputs from the input manager, connected HDMI only
        calls = await ev('window.__calls')
        cmds = root_cmds(calls)
        assert any('listLaunchPoints' in c for c in cmds), cmds
        assert any('getAllInputStatus' in c for c in cmds), cmds
        tabs = await ev("window.__halcyon.TABS().map(function(t){return t.key+':'+t.ids.length})")
        print('tabs', tabs)
        all_ids = await ev("window.__halcyon.TABS().filter(function(t){return t.key==='all'})[0].ids")
        assert 'org.webosbrew.halcyon' not in all_ids, 'Halcyon lists itself'
        assert 'com.webos.app.hdmi1' not in all_ids, 'an input leaked into All apps'
        assert 'works.partridge.webos-launcher' not in all_ids, 'Partridge should be hidden by default'
        dock = await ev("Array.prototype.map.call(document.querySelectorAll('#dock .pill'),function(e){return e.textContent})")
        print('dock', dock); assert dock == ['PS5', 'Apple TV'], dock

        # icons: readable files are analysed for their edge colour; a blocked file is read as root with cat
        assert any(c.startswith("cat '/blocked/dark.png'") for c in cmds), 'blocked icon was not read as root'
        modes = await ev("JSON.parse(localStorage.getItem('halcyon.colors.v1')||'{}')")
        print('icon modes', {k:v['mode'] for k,v in modes.items()})
        assert modes['stream.dark']['mode'] == 'seam' and modes['photo.tile']['mode'] == 'tile' and modes['orb.clear']['mode'] == 'clear'
        await pg.screenshot(path=str(SHOTS/'tv_home.png'))

        # nothing developer-facing on screen
        text = await ev("document.getElementById('stage').innerText")
        assert 'stream.dark' not in text and 'webosbrew' not in text, 'package id on screen'

        # navigation: Right moves along the shelf, Up reaches the tabs, Right switches tab, Up again the top buttons
        await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(300)
        assert await ev("window.__halcyon.F.cols.fav") == 1
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(300)
        assert await ev("window.__halcyon.F.zone") == 'tabs'
        await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(500)
        assert await ev("window.__halcyon.F.tab") == 'all'
        assert await ev("document.getElementById('title').textContent") == 'All apps'
        await pg.screenshot(path=str(SHOTS/'tv_tabs.png'))
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(500)
        assert await ev("window.__halcyon.F.zone") == 'top'
        assert await ev("document.querySelector('.tbtn.focus').id") == 'gear'
        await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(500)
        await pg.screenshot(path=str(SHOTS/'tv_top.png'))
        await ev('window.__calls=[]')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(800)
        cmds = root_cmds(await ev('window.__calls'))
        print('TV settings', cmds); assert any('com.palm.app.settings' in c for c in cmds)

        # Down, Down: back to the shelf on the All apps tab; launch the focused app (direct denied -> root)
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(200)
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(400)
        assert await ev("window.__halcyon.F.zone") == 'shelf'
        first = await ev("window.__halcyon.TABS().filter(function(t){return t.key==='all'})[0].ids[0]")
        await ev('window.__calls=[]')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1200)
        cmds = root_cmds(await ev('window.__calls'))
        print('launch', cmds); assert any('applicationManager/launch' in c and first in c for c in cmds)

        # Recent: coming back to Halcyon (relaunch), the launched app is in a Recent tab and the hero says when it was opened
        await ev("document.dispatchEvent(new Event('webOSRelaunch'))"); await pg.wait_for_timeout(800)
        assert await ev('window.__activated') == 1, 'relaunch must call webOSSystem.activate()'
        assert 'recent' in await ev("window.__halcyon.TABS().map(function(t){return t.key})")
        # tabs are Favorites, Recent, All apps: Up from All apps, Left to Recent, Down into it
        assert await ev("window.__halcyon.TABS().map(function(t){return t.key}).join()") == 'fav,recent,all'
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(200)
        await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(200)
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(600)
        tab, desc = await ev("[window.__halcyon.F.tab, document.getElementById('desc').textContent]")
        print('recent hero', tab, repr(desc)); assert tab == 'recent' and desc.startswith('Last opened just now')

        # the dock: Down from the shelf, OK switches input through root
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(500)
        assert await ev("window.__halcyon.F.zone") == 'dock'
        assert await ev("document.getElementById('title').textContent") == 'PS5'
        await ev('window.__calls=[]')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(800)
        cmds = root_cmds(await ev('window.__calls'))
        assert any('com.webos.app.hdmi1' in c for c in cmds), cmds
        await pg.screenshot(path=str(SHOTS/'tv_dock.png'))

        # options menu: Up to the shelf, hold OK, Hide removes the app from the shelf
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(300)
        await pg.keyboard.down('Enter'); await pg.wait_for_timeout(700); await pg.keyboard.up('Enter'); await pg.wait_for_timeout(300)
        items = await ev("Array.prototype.map.call(document.querySelectorAll('#menu .mi'),function(e){return e.textContent})")
        print('menu', items); assert 'Remove from Recent' in items and 'Hide' in items
        await pg.screenshot(path=str(SHOTS/'tv_menu.png'))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        assert await ev("window.__halcyon.F.zone") == 'shelf'

        # debug log opens with 0 and shows the root fallback
        await pg.keyboard.press('0'); await pg.wait_for_timeout(200)
        log = await ev("document.querySelector('#debug pre').textContent")
        assert 'direct call failed' in log and 'root call OK' in log
        await pg.keyboard.press('0')

        print('errors', errs); assert not errs
        await b.close()
    print('test_tv: OK')
asyncio.run(main())
