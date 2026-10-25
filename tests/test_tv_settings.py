"""TV settings button and the Up path (1.6): Up from the first row peeks at the background, Up again
reaches the top buttons; the TV settings button opens LG's settings (simulated TV: direct call denied, root works)."""
from pwlaunch import opts
import pathlib, asyncio, json
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=str(ROOT/'tests'/'shots')+'/'
LPS=[{"id":"app.one","title":"App One"},{"id":"app.two","title":"App Two"}]
DEVS=[{"id":"HDMI_1","label":"PS5","appId":"com.webos.app.hdmi1","connected":True},{"id":"HDMI_2","label":"HDMI2","connected":True}]
MOCK="""
window.__calls=[];
window.PalmServiceBridge=function(){ var self=this; this.call=function(uri,p){ window.__calls.push(uri+' '+p);
  var reply, P=JSON.parse(p);
  function ok(u,c){ if(/listLaunchPoints/.test(u)) return {returnValue:true,launchPoints:LPS};
                    if(/getAllInputStatus/.test(u)) return {returnValue:true,devices:DEVS};
                    if(/Bluetooth/.test(c)) return {returnValue:false,errorText:'unknown target'};
                    return {returnValue:true}; }
  if(/hbchannel.service\\/exec$/.test(uri)){ var u=(P.command.match(/'(luna:[^']+)'/)||[])[1]; reply={returnValue:true,stdoutString:JSON.stringify(ok(u,P.command))}; }
  else reply={returnValue:false,errorText:'Denied method call "'+uri.split('/').pop()+'" for category "/"'};
  setTimeout(function(){ self.onservicecallback(JSON.stringify(reply)); },60); }; };
""".replace('LPS',json.dumps(LPS)).replace('DEVS',json.dumps(DEVS))
def root_cmds(calls): return [json.loads(c.split(' ',1)[1])['command'] for c in calls if 'hbchannel' in c and 'luna-send' in c and 'list' not in c and 'getAll' not in c]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(**opts()); pg=await b.new_page(viewport={'width':1920,'height':1080})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.add_init_script(MOCK)
        await pg.goto((ROOT/'webos'/'index.html').as_uri()); await pg.wait_for_timeout(1500)
        titles=await pg.evaluate("Array.prototype.map.call(document.querySelectorAll('.row-title'),function(e){return e.textContent})")
        print('rows', titles); assert 'TV settings' not in titles, titles
        print('input cards', await pg.evaluate("Array.prototype.map.call(document.querySelectorAll('.art.nm'),function(e){return e.textContent+' / '+e.closest('.card').querySelector('.label').textContent})"))
        hero=await pg.evaluate("document.getElementById('desc').textContent")
        print('hero desc', repr(hero)); assert 'app.one' not in hero
        cls=lambda: pg.evaluate("document.getElementById('stage').className")
        # Up once: peek (cards aside, nothing focused); Up again: the Lumen gear; Left: TV settings
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(800)
        c=await cls(); print('after Up:', c); assert 'peek-bg' in c and not await pg.evaluate("!!document.querySelector('.tbtn.focus')")
        await pg.screenshot(path=OUT+'tvset_peek.png')
        await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(300)
        print('top focus', await pg.evaluate("document.querySelector('.tbtn.focus').id"))
        await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(600)
        await pg.screenshot(path=OUT+'tvset_top.png')
        await pg.evaluate('window.__calls=[]'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1500)
        cmds=root_cmds(await pg.evaluate('window.__calls')); print('TV settings button', cmds)
        assert any('com.palm.app.settings' in x for x in cmds)
        # Down twice: back through peek to the cards
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(200)
        assert 'peek-bg' in await cls()
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(400)
        assert 'peek' not in await cls() and await pg.evaluate("!!document.querySelector('.card.focus')")
        print('errors',errs); assert not errs
        await b.close()
asyncio.run(main())
