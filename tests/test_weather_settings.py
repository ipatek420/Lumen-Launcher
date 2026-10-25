"""2.3: settings pages, weather next to the clock (Open-Meteo, routed to fixtures here) and the accent picker with Auto."""
from pwlaunch import opts
import pathlib, asyncio, json
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=str(ROOT/'tests'/'shots')+'/'
GEO={'results':[{'name':'Austin','latitude':30.26715,'longitude':-97.74306,'country_code':'US','country':'United States','admin1':'Texas'},
                {'name':'Austin','latitude':43.66663,'longitude':-92.97464,'country_code':'US','country':'United States','admin1':'Minnesota'}]}
FC={'current':{'temperature_2m':72.4,'weather_code':2,'is_day':1},'daily':{'temperature_2m_max':[81.2],'temperature_2m_min':[60.6]}}
seen=[]
async def route(r):
    u=r.request.url; seen.append(u)
    h={'Access-Control-Allow-Origin':'*'}
    if 'geocoding-api.open-meteo.com' in u: return await r.fulfill(status=200,headers=h,content_type='application/json',body=json.dumps(GEO if 'name=Austin' in u else {}))
    if 'api.open-meteo.com' in u: return await r.fulfill(status=200,headers=h,content_type='application/json',body=json.dumps(FC))
    return await r.continue_()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(**opts()); ctx=await b.new_context(viewport={'width':1920,'height':1080}); await ctx.route('**/*',route)
        pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto((ROOT/'webos'/'index.html').as_uri()); await pg.wait_for_timeout(1200)
        key=lambda k: pg.keyboard.press(k)
        rows=lambda: pg.evaluate("Array.prototype.map.call(document.querySelectorAll('#s-list .si'),function(e){return e.firstChild.textContent+' | '+e.querySelector('.v').textContent})")
        focused=lambda: pg.evaluate("document.querySelector('#s-list .si.focus').firstChild.textContent")
        async def goto(label):
            for i in range(25):
                if await focused()==label: return
                await key('ArrowDown'); await pg.wait_for_timeout(40)
            raise Exception('no row '+label)
        await pg.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:403,bubbles:true}))"); await pg.wait_for_timeout(500)
        r=await rows(); print('root:', r); assert [x.split(' | ')[0] for x in r]==['Wallpaper','Cards','Focus & colour','Clock & weather','Layout','Performance','Apps','Home Assistant','Advanced'], r
        await pg.screenshot(path=OUT+'settings_root.png')
        # Clock & weather page: type a place with the TV keyboard
        await goto('Clock & weather'); await key('Enter'); await pg.wait_for_timeout(300)
        print('page:', await pg.evaluate("document.querySelector('#s-head h2').textContent"), await rows())
        await goto('Place'); await key('Enter'); await pg.wait_for_timeout(200)
        await pg.keyboard.type('Austin, Minnesota'); await key('Enter'); await pg.wait_for_timeout(1500)
        print('place saved:', await pg.evaluate("JSON.parse(localStorage.getItem('lumen.launcher.v1')).wxPlace"))
        fc=[u for u in seen if 'api.open-meteo.com/v1/forecast' in u]; print('forecast:', fc[-1] if fc else None)
        assert fc and 'latitude=43.667' in fc[-1] and 'temperature_unit=fahrenheit' in fc[-1]
        wx=await pg.evaluate("[document.getElementById('wx').hidden, document.getElementById('wx-temp').textContent, document.getElementById('wx-range').textContent]")
        print('weather shown:', wx); assert wx==[False,'72°','H 81°   L 61°'], wx
        await pg.screenshot(path=OUT+'settings_weather.png')
        # Units to °C: refetches without the fahrenheit flag
        await goto('Units'); await key('ArrowRight'); await pg.wait_for_timeout(800)
        assert 'temperature_unit' not in [u for u in seen if 'forecast' in u][-1]
        await key('ArrowLeft'); await pg.wait_for_timeout(800)
        # Back: to the root with this page focused, Back again closes
        await key('Backspace'); await pg.wait_for_timeout(300)
        print('back to root, focus on:', await focused()); assert await focused()=='Clock & weather'
        # Focus & colour: accent carousel, Auto
        await key('ArrowUp'); await key('Enter'); await pg.wait_for_timeout(300); await goto('Accent')
        for i in range(14): await key('ArrowRight'); await pg.wait_for_timeout(30)   # wraps round to Auto
        await pg.wait_for_timeout(400)
        acc=await pg.evaluate("[document.querySelectorAll('#s-list .si.focus .sw').length, document.querySelector('#s-list .si.focus .swn').textContent, JSON.parse(localStorage.getItem('lumen.launcher.v1')).accent]")
        print('accent row:', acc); assert acc==[3,'Auto','auto'], acc
        await pg.screenshot(path=OUT+'settings_accent.png')
        await key('Backspace'); await key('Backspace'); await pg.wait_for_timeout(500)
        a1=await pg.evaluate("getComputedStyle(document.getElementById('stage')).getPropertyValue('--accent')")
        await key('ArrowRight'); await pg.wait_for_timeout(900)
        a2=await pg.evaluate("getComputedStyle(document.getElementById('stage')).getPropertyValue('--accent')")
        print('auto accent follows the app:', a1, '->', a2); assert a1!=a2
        await pg.screenshot(path=OUT+'home_weather.png')
        # a place that doesn't exist
        await pg.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:403,bubbles:true}))"); await pg.wait_for_timeout(300)
        await goto('Clock & weather'); await key('Enter'); await pg.wait_for_timeout(200); await goto('Place'); await key('Enter')
        await pg.keyboard.press('Control+A'); await pg.keyboard.type('Nowhereville'); await key('Enter'); await pg.wait_for_timeout(800)
        t=await pg.evaluate("document.getElementById('toast').textContent"); print('unknown place:', t, '| kept:', await pg.evaluate("document.getElementById('in-wxPlace').value"))
        assert 'find' in t
        print('errors', errs); assert not errs
        await b.close()
asyncio.run(main())
