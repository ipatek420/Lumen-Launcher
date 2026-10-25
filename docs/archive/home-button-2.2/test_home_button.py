"""Home button and power-on (2.2): the settings switches run service/lumen-home.js as root through the
Homebrew Channel, show its state, and Lumen puts the saved choice back at start.
The root side (lumen-home.js, lumen-init) is tested against a fake TV in tests/test_home_service.sh."""
from pwlaunch import opts
import pathlib, asyncio, json
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=str(ROOT/'tests'/'shots')+'/'
MOCK="""
window.__calls=[]; window.__homeReply=REPLY;
window.PalmServiceBridge=function(){ var self=this; this.call=function(uri,p){ window.__calls.push(uri+' '+p);
  var reply, P=JSON.parse(p);
  if(/hbchannel.service\\/exec$/.test(uri)){
    if(/lumen-home\\.js/.test(P.command)) reply={returnValue:true,stdoutString:JSON.stringify(window.__homeReply)+'\\n'};
    else reply={returnValue:true,stdoutString:JSON.stringify({returnValue:true,launchPoints:[{id:'app.one',title:'App One'}],devices:[]})};
  } else reply={returnValue:false,errorText:'Denied'};
  setTimeout(function(){ self.onservicecallback(JSON.stringify(reply)); },40); }; };
"""
def home_cmds(calls): return [json.loads(c.split(' ',1)[1])['command'] for c in calls if 'lumen-home.js' in c]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(**opts()); pg=await b.new_page(viewport={'width':1920,'height':1080})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.add_init_script(MOCK.replace('REPLY',json.dumps({'ok':True,'home':'active','powerOn':True})))
        await pg.goto((ROOT/'webos'/'index.html').as_uri()); await pg.wait_for_timeout(1200)
        await pg.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:403,bubbles:true}))"); await pg.wait_for_timeout(500)
        labels=await pg.evaluate("Array.prototype.map.call(document.querySelectorAll('#s-list .si span:first-child'),function(e){return e.textContent})")
        assert 'Home button opens Lumen' in labels and 'Open Lumen when the TV turns on' in labels, labels
        async def click(label):
            await pg.evaluate("(function(l){var r=Array.prototype.filter.call(document.querySelectorAll('#s-list .si'),function(e){return e.firstChild.textContent===l})[0]; r.click();})(%s)"%json.dumps(label))
        await click('Home button opens Lumen'); await pg.wait_for_timeout(150); await click('Open Lumen when the TV turns on')
        await pg.wait_for_timeout(1500)
        cmds=home_cmds(await pg.evaluate('window.__calls')); print('commands', cmds)
        assert len(cmds)==1 and cmds[0].endswith("lumen-home.js' apply 1 1") and cmds[0].startswith('/usr/bin/node '), cmds
        status=await pg.evaluate("(function(){var r=Array.prototype.filter.call(document.querySelectorAll('#s-list .si'),function(e){return e.firstChild.textContent==='Status'})[0]; return r&&r.querySelector('.v').textContent})()")
        print('status', status, '| toast', await pg.evaluate("document.getElementById('toast').textContent")); assert status=='On'
        await pg.screenshot(path=OUT+'home_settings.png')
        # a fresh start with the switches on: Lumen puts the choice back
        await pg.evaluate('window.__calls=[]'); await pg.reload(); await pg.wait_for_timeout(5000)
        cmds=home_cmds(await pg.evaluate('window.__calls')); print('at start', cmds); assert any(c.endswith(' ensure') for c in cmds)
        # GlassHouse missing
        await pg.evaluate("window.__homeReply={ok:true,home:'noglasshouse',powerOn:true}")
        await pg.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:403,bubbles:true}))"); await pg.wait_for_timeout(400)
        await click('Status'); await pg.wait_for_timeout(800)
        print('no GlassHouse:', await pg.evaluate("document.getElementById('toast').textContent"))
        # both off
        await pg.evaluate("window.__homeReply={ok:true,home:'off',powerOn:false}; window.__calls=[]")
        await click('Home button opens Lumen'); await pg.wait_for_timeout(150); await click('Open Lumen when the TV turns on'); await pg.wait_for_timeout(1500)
        cmds=home_cmds(await pg.evaluate('window.__calls')); print('off', cmds, '|', await pg.evaluate("document.getElementById('toast').textContent"))
        assert cmds and cmds[-1].endswith(' apply 0 0')
        print('errors',errs); assert not errs
        await b.close()
asyncio.run(main())
