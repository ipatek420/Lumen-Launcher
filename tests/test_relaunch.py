from pwlaunch import opts
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(**opts()); pg=await b.new_page(viewport={'width':1920,'height':1080})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.add_init_script("window.__act=0; window.webOSSystem={activate:function(){window.__act++;}};")
        await pg.goto((ROOT/'webos'/'index.html').as_uri()); await pg.wait_for_timeout(800)
        await pg.evaluate("document.dispatchEvent(new Event('webOSRelaunch'))"); await pg.wait_for_timeout(200)
        print('activate calls (webOSSystem):', await pg.evaluate('window.__act'))
        await pg.add_init_script("delete window.webOSSystem; window.PalmSystem={activate:function(){window.__act++;}};")
        await pg.reload(); await pg.wait_for_timeout(800)
        await pg.evaluate("document.dispatchEvent(new Event('webOSRelaunch'))"); await pg.wait_for_timeout(200)
        print('activate calls (PalmSystem):', await pg.evaluate('window.__act'))
        print('errors',errs); await b.close()
asyncio.run(main())
