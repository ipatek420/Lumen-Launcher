"""Frame rate while scrolling, the way Lumen measured it: 6x CPU throttle, an arrow every 100 ms, 30 moves.
Scenarios: living sky, app colours, slow animation, a photo backdrop (Bing routed to a local photo), and Lite.
Headless numbers drift with machine load: compare builds run back to back, and look at the >25 ms frame count."""
import asyncio, json
from playwright.async_api import async_playwright
from tvmock import opts, settings_script, PAGE, FIX

PHOTO = open(FIX/'photos'/'a.jpg', 'rb').read()
BING = {"images": [{"urlbase": "/th?id=OHR.Test", "title": "A test photo", "copyright": "Somewhere (© Someone)"}]}

async def route(r):
    u = r.request.url
    if 'HPImageArchive' in u:
        return await r.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*'}, content_type='application/json', body=json.dumps(BING))
    if 'bing.com/th' in u:
        return await r.fulfill(status=200, content_type='image/jpeg', body=PHOTO)
    if u.startswith('http'):
        return await r.abort()
    return await r.continue_()

async def run(p, label, st):
    b = await p.chromium.launch(**opts())
    ctx = await b.new_context(viewport={'width': 1920, 'height': 1080}); await ctx.route('**/*', route)
    pg = await ctx.new_page()
    await pg.add_init_script(settings_script(st))
    await pg.goto(PAGE); await pg.wait_for_timeout(2500)
    cdp = await ctx.new_cdp_session(pg); await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 6})
    await pg.keyboard.press('ArrowUp'); await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('ArrowDown')   # All apps: the longest shelf
    await pg.wait_for_timeout(800)
    await pg.evaluate("window.__f=[];(function l(t){window.__f.push(t);requestAnimationFrame(l)})(performance.now())")
    for i in range(30):
        await pg.keyboard.press('ArrowRight' if i % 10 < 6 else 'ArrowLeft'); await pg.wait_for_timeout(100)
    f = await pg.evaluate("window.__f"); d = [f[i+1]-f[i] for i in range(len(f)-1)]
    fps = len(d)/((f[-1]-f[0])/1000)
    print(f"{label:28s} fps {fps:5.1f}  >25ms {sum(1 for x in d if x > 25):3d}  >50ms {sum(1 for x in d if x > 50):3d}")
    await b.close()
    return fps

async def main():
    async with async_playwright() as p:
        res = [await run(p, 'Living sky (Full)', {}),
               await run(p, 'Living sky, Slow (Full)', {'speed': 'relaxed'}),
               await run(p, 'App colours (Full)', {'backdrop': 'app'}),
               await run(p, 'Bing photo (Full)', {'backdrop': 'bing'}),
               await run(p, 'Living sky (Lite)', {'quality': 'lite'})]
    assert min(res) > 35, 'frame rate regression: keep every scenario above ~35 fps at 6x throttle'
asyncio.run(main())
