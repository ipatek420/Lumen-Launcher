from pwlaunch import opts
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
import asyncio, json, re
from playwright.async_api import async_playwright
exec(open(pathlib.Path(__file__).with_name('test_wallpapers.py')).read().split('TVMODE=len')[0].split('seen=[]')[1].replace('async def route','async def _unused'))  # reuse commons_reply
IMG=str(ROOT/'tests'/'fixtures'/'photos')+'/'
async def route(r):
    u=r.request.url
    if 'api.php' in u: return await r.fulfill(status=200,headers={'Access-Control-Allow-Origin':'*'},content_type='application/json',body=json.dumps(commons_reply(u)))
    if 'upload.wikimedia.org' in u: return await r.fulfill(status=200,content_type='image/jpeg',body=open(IMG+{'p.jpg':'portrait.jpg'}.get(u.split('/')[-1],u.split('/')[-1]),'rb').read())
    return await r.continue_()
async def run(p,label,st):
    b=await p.chromium.launch(**opts()); ctx=await b.new_context(viewport={'width':1920,'height':1080}); await ctx.route('**/*',route)
    pg=await ctx.new_page()
    await pg.add_init_script("localStorage.setItem('lumen.launcher.v1',JSON.stringify(%s))"%json.dumps(st))
    await pg.goto((ROOT/'webos'/'index.html').as_uri()); await pg.wait_for_timeout(2500)
    cdp=await ctx.new_cdp_session(pg); await cdp.send('Emulation.setCPUThrottlingRate',{'rate':6})
    await pg.evaluate("window.__f=[];(function l(t){window.__f.push(t);requestAnimationFrame(l)})(performance.now())")
    for i in range(30):
        await pg.keyboard.press('ArrowRight' if i%10<6 else 'ArrowLeft'); await pg.wait_for_timeout(100)
    f=await pg.evaluate("window.__f"); d=[f[i+1]-f[i] for i in range(len(f)-1)]
    print(f"{label:30s} fps {len(d)/((f[-1]-f[0])/1000):5.1f}  >25ms {sum(1 for x in d if x>25):3d}  >50ms {sum(1 for x in d if x>50):3d}")
    await b.close()
async def main():
    async with async_playwright() as p:
        await run(p,'Dynamic colors (Full)',{})
        await run(p,'Dynamic, Relaxed (Full)',{'speed':'relaxed'})
        await run(p,'Photo wallpaper (Full)',{'wallpaper':'landscapes'})
        await run(p,'Photo, Relaxed (Full)',{'wallpaper':'landscapes','speed':'relaxed'})
        await run(p,'Photo + slow drift (Full)',{'wallpaper':'landscapes','wpZoom':True})
        await run(p,'Photo wallpaper (Lite)',{'wallpaper':'landscapes','quality':'lite'})
asyncio.run(main())
