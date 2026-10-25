"""Home Assistant row (2.4) on a simulated TV: tiles from http://<ha>/local/lumen.json and webhook POSTs,
both through root curl (the mock answers curl commands like a Home Assistant would)."""
from pwlaunch import opts
import pathlib, asyncio, json
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=str(ROOT/'tests'/'shots')+'/'
TILES={'title':'Home','tiles':[{'name':'All lights','icon':'light','webhook':'lumen-alllights-Qm7xT2vK9pRz'},
  {'name':'Lamp','icon':'lamp','webhook':'lumen-lamp-H4sN8wLc2eYd'},{'name':'Stair lights','icon':'light','webhook':'lumen-stairs-Vb6kP3rJ8tGx'},
  {'name':'Bad one','icon':'light','webhook':"x'; reboot; '"}]}
MOCK="""
window.__calls=[]; window.__ha={file:FILE, up:true};
window.PalmServiceBridge=function(){ var self=this; this.call=function(uri,p){ window.__calls.push(uri+' '+p);
  var reply, P=JSON.parse(p), c=P.command||'';
  if(/hbchannel.service\\/exec$/.test(uri)){
    if(/^curl /.test(c)){
      if(!window.__ha.up) reply={returnValue:true,stdoutString:'000'};
      else if(/lumen\\.json/.test(c)) reply={returnValue:true,stdoutString:window.__ha.file===null?'404: Not Found\\n404':window.__ha.file+'\\n200'};
      else if(/-X POST/.test(c)) reply={returnValue:true,stdoutString:'200'};
    } else reply={returnValue:true,stdoutString:JSON.stringify({returnValue:true,launchPoints:[{id:'app.one',title:'App One'}],devices:[{id:'HDMI_1',label:'PS5',connected:true}]})};
  } else reply={returnValue:false,errorText:'Denied'};
  setTimeout(function(){ self.onservicecallback(JSON.stringify(reply)); },40); }; };
""".replace('FILE',json.dumps(json.dumps(TILES)))
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(**opts()); pg=await b.new_page(viewport={'width':1920,'height':1080})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.add_init_script(MOCK)
        await pg.goto((ROOT/'webos'/'index.html').as_uri()); await pg.wait_for_timeout(1200)
        key=lambda k: pg.keyboard.press(k)
        focused=lambda: pg.evaluate("document.querySelector('#s-list .si.focus').firstChild.textContent")
        async def goto(label):
            for i in range(25):
                if await focused()==label: return
                await key('ArrowDown'); await pg.wait_for_timeout(40)
            raise Exception('no row '+label)
        rowtitles=lambda: pg.evaluate("Array.prototype.map.call(document.querySelectorAll('.row-title'),function(e){return e.textContent})")
        print('rows before setup:', await rowtitles())
        # settings → Home Assistant → Address
        await pg.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:403,bubbles:true}))"); await pg.wait_for_timeout(300)
        await goto('Home Assistant'); await key('Enter'); await pg.wait_for_timeout(200); await goto('Address'); await key('Enter')
        await pg.keyboard.type('http://192.168.1.20'); await key('Enter'); await pg.wait_for_timeout(1000)
        st=await pg.evaluate("[JSON.parse(localStorage.getItem('lumen.launcher.v1')).haAddr, document.getElementById('toast').textContent]"); print('address saved, toast:', st)
        assert st[0]=='192.168.1.20:8123'
        cmd=[json.loads(c.split(' ',1)[1])['command'] for c in await pg.evaluate('window.__calls') if 'lumen.json' in c]; print('fetch:', cmd[-1])
        assert "-w '\\n%{http_code}' 'http://192.168.1.20:8123/local/lumen.json?t=" in cmd[-1]
        await pg.screenshot(path=OUT+'ha_settings.png')
        await key('Backspace'); await key('Backspace'); await pg.wait_for_timeout(400)
        t=await rowtitles(); print('rows:', t); assert t[-1]=='Home' and t[-2]=='Inputs'
        names=await pg.evaluate("Array.prototype.map.call(document.querySelectorAll('.row:last-child .art.nm'),function(e){return e.textContent})")
        print('tiles:', names); assert names==['All lights','Lamp','Stair lights'], names   # the unsafe webhook id is dropped
        # go to the row, run the second tile
        for i in range(len(t)-1): await key('ArrowDown'); await pg.wait_for_timeout(120)
        await key('ArrowRight'); await pg.wait_for_timeout(700)
        await pg.screenshot(path=OUT+'ha_row.png')
        await pg.evaluate('window.__calls=[]'); await key('Enter'); await pg.wait_for_timeout(800)
        post=[json.loads(c.split(' ',1)[1])['command'] for c in await pg.evaluate('window.__calls') if '-X POST' in c]
        toast=await pg.evaluate("document.getElementById('toast').textContent"); print('run:', post, '|', toast)
        assert len(post)==1 and "'http://192.168.1.20:8123/api/webhook/lumen-lamp-H4sN8wLc2eYd'" in post[0] and toast=='Lamp ✓'
        assert await pg.evaluate("!document.getElementById('zoom').style.opacity||document.getElementById('zoom').style.opacity==='0'")
        # Home Assistant down
        await pg.evaluate("window.__ha.up=false"); await key('Enter'); await pg.wait_for_timeout(600)
        print('down:', await pg.evaluate("document.getElementById('toast').textContent"))
        # file missing → status says so
        await pg.evaluate("window.__ha.up=true; window.__ha.file=null")
        await pg.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:403,bubbles:true}))"); await pg.wait_for_timeout(300)
        await key('Enter'); await pg.wait_for_timeout(200)   # settings reopen on the Home Assistant entry
        await goto('Reload tiles'); await key('Enter'); await pg.wait_for_timeout(800)
        print('no file:', await pg.evaluate("document.querySelector('#s-list .si.focus .v').textContent"))
        print('errors',errs); assert not errs
        await b.close()
asyncio.run(main())
