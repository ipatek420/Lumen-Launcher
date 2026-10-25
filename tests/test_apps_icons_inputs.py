from pwlaunch import opts
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
import asyncio, json, base64
from playwright.async_api import async_playwright
import os
os.makedirs(str(ROOT/'tests'/'shots'),exist_ok=True)
OUT=str(ROOT/'tests'/'shots')+'/'
ICON=str(ROOT/'webos'/'largeIcon.png')
import sys
FLAG=sys.argv[1]=='open'
import os
B64=base64.b64encode(open(str(ROOT/'webos'/'icon.png'),'rb').read()).decode()
FILES={T2+f:base64.b64encode(open(T2+f,'rb').read()).decode() for T2 in [str(ROOT/'tests'/'fixtures'/'icons')+'/'] for f in os.listdir(T2)}
T=str(ROOT/'tests'/'fixtures'/'icons')+'/'
lps=[{"id":"stream.dark","title":"StreamFlix","largeIcon":T+"dark.png"},{"id":"tube.white","title":"TubeView","largeIcon":T+"white.png"},{"id":"orb.clear","title":"Orb Music","largeIcon":T+"clear.png"},{"id":"photo.tile","title":"Gallery TV","largeIcon":T+"photo.png"},{"id":"blue.app","title":"Blue Plus","largeIcon":T+"blue.png"},{"id":"netflix","title":"Netflix","largeIcon":ICON,"bgColor":"#141414","bgImage":"/missing/bg.jpg"},
 {"id":"youtube.leanback.v4","title":"YouTube","largeIcon":"/blocked/yt.png","iconColor":"#e62117"},
 {"id":"works.partridge.webos-launcher","title":"Partridge Launcher","largeIcon":ICON},
 {"id":"org.webosbrew.hbchannel","title":"Homebrew Channel","largeIcon":ICON},
 {"id":"com.webos.app.browser","title":"Web Browser","largeIcon":ICON,"iconColor":"#1b8a7a"},
 {"id":"com.disney.disneyplus-prod","title":"Disney+","largeIcon":"/blocked/dp.png","iconColor":"#173584"},
 {"id":"com.webos.app.hdmi1","title":"HDMI 1","largeIcon":ICON},
 {"id":"org.webosbrew.lumen","title":"Lumen Launcher","largeIcon":ICON}]
devs=[{"id":"HDMI_1","label":"PS5","appId":"com.webos.app.hdmi1","connected":True},
      {"id":"HDMI_2","label":"HDMI2","appId":"com.webos.app.hdmi2","connected":False},
      {"id":"HDMI_3","label":"Apple TV","connected":True},
      {"id":"AV_1","label":"AV","appId":"com.webos.app.externalinput.av1","connected":True}]
MOCK="""
window.__calls=[];window.COLORS_DBG=function(){return JSON.parse(localStorage.getItem('lumen.colors.v1')||'{}')};
window.PalmServiceBridge=function(){ var self=this; this.call=function(uri,p){ window.__calls.push(uri+' '+p);
  var reply, P=JSON.parse(p);
  function ok(u){ if(/listLaunchPoints/.test(u)) return {returnValue:true,launchPoints:LPS};
                  if(/getAllInputStatus/.test(u)) return {returnValue:true,devices:DEVS};
                  if(/launch$/.test(u)) return {returnValue:true}; return {returnValue:false,errorText:'unknown'}; }
  if(/hbchannel.service\\/exec$/.test(uri)){ var c=P.command;
    if(/^cat /.test(c)){ var fp=c.slice(5,-1); reply=FILESJ[fp]?{returnValue:true,stdoutBytes:FILESJ[fp]}:(/blocked/.test(c)?{returnValue:true,stdoutString:'',stdoutBytes:'B64'}:{returnValue:false,error:'No such file'}); }
    else { var u=(c.match(/'(luna:[^']+)'/)||[])[1]; reply={returnValue:true,stdoutString:JSON.stringify(ok(u))}; } }
  else if(/launch$/.test(uri)) reply={returnValue:true};
  else reply={returnValue:false,errorText:'Denied method call "'+uri.split('/').pop()+'" for category "/"'};
  setTimeout(function(){ self.onservicecallback(JSON.stringify(reply)); },150); }; };
""".replace('LPS',json.dumps(lps)).replace('DEVS',json.dumps(devs)).replace('FILESJ','('+json.dumps(FILES)+')').replace('B64',B64)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(**opts(args=['--allow-file-access-from-files'] if FLAG else []))
        pg=await b.new_page(viewport={'width':1920,'height':1080})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.add_init_script(MOCK)
        await pg.goto((ROOT/'webos'/'index.html').as_uri()); await pg.wait_for_timeout(2500)
        await pg.screenshot(path=OUT+sys.argv[1]+'_home.png')
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(1400)
        await pg.screenshot(path=OUT+sys.argv[1]+'_all.png')
        for i in range(6): await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(250)
        await pg.wait_for_timeout(1200); await pg.screenshot(path=OUT+sys.argv[1]+'_all2.png')
        print(await pg.evaluate("JSON.stringify(Object.keys(COLORS_DBG()).map(function(k){var p=COLORS_DBG()[k];return k+':'+p.mode}))"))
        calls=await pg.evaluate('window.__calls')
        print('\n'.join(c[:140] for c in calls[-6:]))
        print('errors',errs)
        await b.close()
asyncio.run(main())
