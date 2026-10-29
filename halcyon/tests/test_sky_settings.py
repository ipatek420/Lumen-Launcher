"""The living sky, the greeting and weather, and the settings sheet (browser preview, network routed to fixtures).
- the sky phase follows the clock and the real sunrise/sunset from the forecast
- the greeting follows the hour and uses the name from settings
- typing a place geocodes it once, then the forecast fills the weather sentence
- settings pages: open, change the accent and card shape, Back to the page list, Back to close"""
import asyncio, json, datetime
from playwright.async_api import async_playwright
from tvmock import opts, settings_script, PAGE, SHOTS

GEO = {"results": [{"name": "Newark", "latitude": 40.7357, "longitude": -74.1724, "admin1": "New Jersey", "country": "United States", "country_code": "US"},
                   {"name": "Newark", "latitude": 39.6837, "longitude": -75.7497, "admin1": "Delaware", "country": "United States", "country_code": "US"}]}
FORECAST = {"current": {"temperature_2m": 58.6, "weather_code": 2, "is_day": 1},
            "daily": {"temperature_2m_max": [67.9], "temperature_2m_min": [41.2], "sunrise": ["2026-10-28T07:16"], "sunset": ["2026-10-28T18:03"]}}

async def route(r):
    u = r.request.url
    if 'geocoding-api.open-meteo.com' in u:
        return await r.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*'}, content_type='application/json', body=json.dumps(GEO))
    if 'api.open-meteo.com' in u:
        assert 'sunrise' in u and 'temperature_unit=fahrenheit' in u, u
        return await r.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*'}, content_type='application/json', body=json.dumps(FORECAST))
    return await r.continue_()

async def page_at(b, hh, mm, st=None, wx=None):
    ctx = await b.new_context(viewport={'width': 1920, 'height': 1080})
    await ctx.route('**/*', route)
    pg = await ctx.new_page()
    await pg.clock.set_system_time(datetime.datetime(2026, 10, 28, hh, mm))
    await pg.add_init_script(settings_script(st or {}))
    if wx: await pg.add_init_script("localStorage.setItem('halcyon.wx.v1',%s)" % json.dumps(json.dumps(wx)))
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(PAGE); await pg.wait_for_timeout(1200)
    return ctx, pg, errs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**opts())

        # sky phases and greetings through the day (sunrise 07:16, sunset 18:03 from a cached forecast)
        wx = {"t": 0, "sunrise": "2026-10-28T07:16", "sunset": "2026-10-28T18:03"}
        expect = [(3, 0, 'night', 'Still up'), (7, 15, 'dawn', 'Good morning'), (12, 0, 'day', 'Good afternoon'),
                  (17, 35, 'golden', 'Good evening'), (18, 25, 'dusk', 'Good evening'), (22, 30, 'night', 'Good night')]
        for hh, mm, phase, greet in expect:
            ctx, pg, errs = await page_at(b, hh, mm, {'name': 'Sam'}, wx)
            got = await pg.evaluate("window.__halcyon.sky().phase")
            text = await pg.evaluate("document.getElementById('greet').textContent")
            print('%02d:%02d' % (hh, mm), got, '|', text)
            assert got == phase, (hh, mm, got)
            assert text == greet + ', Sam', text
            if (hh, mm) in ((7, 15), (17, 35)): await pg.screenshot(path=str(SHOTS/('sky_%s.png' % phase)))
            assert not errs, errs
            await ctx.close()

        # weather: open settings from the top button, Weather page, type a place
        ctx, pg, errs = await page_at(b, 20, 10)
        ev = lambda js: pg.evaluate(js)
        for _ in range(3): await pg.keyboard.press('ArrowUp')     # tabs, peek, gear
        await pg.wait_for_timeout(300)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(600)
        pages = await ev("Array.prototype.map.call(document.querySelectorAll('#s-list .si>span:first-child'),function(e){return e.textContent})")
        print('pages', pages)
        assert pages[:5] == ['Backdrop', 'Cards', 'Focus & colour', 'Greeting & clock', 'Weather'], pages
        for _ in range(4): await pg.keyboard.press('ArrowDown')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
        assert await ev("document.querySelector('#s-head h2').textContent") == 'Weather'
        await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)   # Place
        await pg.keyboard.type('Newark, New Jersey'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1500)
        st = await ev("window.__halcyon.S()")
        print('place', st['wxPlace'], st['wxLat'], st['wxLon'])
        assert st['wxPlace'] == 'Newark, New Jersey' and abs(st['wxLat'] - 40.736) < .01
        ctxline = await ev("document.getElementById('context').textContent")
        print('context', repr(ctxline))
        assert '59° and partly cloudy' in ctxline and 'High 68°, low 41°' in ctxline
        assert await ev("window.__halcyon.sky().phase") == 'night'

        # Back to the page list, then Focus & colour: accent to Lilac
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
        assert await ev("document.querySelector('#s-head h2').textContent") == 'Halcyon'
        for _ in range(2): await pg.keyboard.press('ArrowUp')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        assert await ev("document.querySelector('#s-head h2').textContent") == 'Focus & colour'
        await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('ArrowDown')
        for _ in range(4): await pg.keyboard.press('ArrowRight')
        accent = await ev("getComputedStyle(document.getElementById('stage')).getPropertyValue('--accent').trim()")
        print('accent', accent); assert accent == '#c9a8ff'
        await pg.screenshot(path=str(SHOTS/'settings_accent.png'))

        # Cards page: shape to Square re-renders the shelf with square cards
        await pg.keyboard.press('Escape'); await pg.keyboard.press('ArrowUp'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(400)
        w, h = await ev("(function(){var f=document.querySelector('.card.focus .face')||document.querySelector('.face');return [f.offsetWidth,f.offsetHeight]})()")
        print('square card', w, h); assert w == h
        # Back twice closes settings; focus returns to the top buttons where it came from
        await pg.keyboard.press('Escape'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(500)
        assert not await ev("document.getElementById('settings').classList.contains('open')")
        assert await ev("window.__halcyon.F.zone") == 'top'
        print('errors', errs); assert not errs
        await ctx.close(); await b.close()
    print('test_sky_settings: OK')
asyncio.run(main())
