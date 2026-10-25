from pwlaunch import opts
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
import asyncio, json, sys, re
from playwright.async_api import async_playwright
import os
os.makedirs(str(ROOT/'tests'/'shots'),exist_ok=True)
OUT=str(ROOT/'tests'/'shots')+'/'
IMG=str(ROOT/'tests'/'fixtures'/'photos')+'/'
seen=[]
def commons_reply(url):
    q=re.search(r'gsrsearch=([^&]+)',url).group(1)
    pages={}
    for i,(f,w,h,t) in enumerate([('a.jpg',6000,3376,'Alpine sunset over the Dolomites'),('b.jpg',5000,2800,'Night sky above the ridge'),('c.jpg',7000,4000,'Morning fog in the valley'),('p.jpg',3000,4500,'A tall portrait photo')]):
        pages[str(100+i)]={"pageid":100+i,"ns":6,"title":"File:"+t.replace(' ','_')+".jpg","imageinfo":[{"thumburl":"https://upload.wikimedia.org/thumb/"+f,"thumbwidth":2560,"thumbheight":1440,"url":"https://upload.wikimedia.org/orig/"+f,"width":w,"height":h,
            "extmetadata":{"ObjectName":{"value":t},"Artist":{"value":"<a href=\"//commons.wikimedia.org/wiki/User:X\">Jane Photographer</a>"}}}]}
    return {"batchcomplete":"","query":{"pages":pages}}
BING={"images":[{"url":"/th?id=OHR.Test1_EN-US1_1920x1080.jpg","urlbase":"/th?id=OHR.Test1_EN-US1","copyright":"Lake at dawn, Patagonia (© Someone/Getty Images)","title":"Quiet water"},
                {"url":"/th?id=OHR.Test2_EN-US2_1920x1080.jpg","urlbase":"/th?id=OHR.Test2_EN-US2","copyright":"Desert dunes, Namibia (© Other/Minden)","title":"Shifting sands"}]}
RSS='''<?xml version="1.0"?><feed><entry><title>Blue hour in Norway [OC] [4000x2250]</title><content type="html">&lt;a href=&quot;https://i.redd.it/abc123.jpeg&quot;&gt;[link]&lt;/a&gt;</content></entry>
<entry><title>Text post</title><content>no image</content></entry><entry><title>Redwoods [OC]</title><content>&lt;a href=&quot;https://i.redd.it/def456.jpg&quot;&gt;</content></entry></feed>'''
async def route(r):
    u=r.request.url; seen.append(u)
    hdr={'Access-Control-Allow-Origin':'*'}
    if 'commons.wikimedia.org/w/api.php' in u: return await r.fulfill(status=200,headers=hdr,content_type='application/json',body=json.dumps(commons_reply(u)))
    if 'bing.com/HPImageArchive' in u:
        if TVMODE: return await r.abort()          # no CORS from Bing -> must use root curl
        return await r.fulfill(status=200,headers=hdr,content_type='application/json',body=json.dumps(BING))
    if 'reddit.com' in u: return await r.abort()
    if 'upload.wikimedia.org' in u or 'bing.com/th' in u or 'i.redd.it' in u:
        f={'a.jpg':'a.jpg','b.jpg':'b.jpg','c.jpg':'c.jpg','p.jpg':'portrait.jpg'}.get(u.split('/')[-1],'d.jpg')
        return await r.fulfill(status=200,content_type='image/jpeg',body=open(IMG+f,'rb').read())
    return await r.continue_()
TVMODE=len(sys.argv)>1 and sys.argv[1]=='tv'
MOCK="""
window.PalmServiceBridge=function(){ var self=this; this.call=function(uri,p){ var P=JSON.parse(p), reply;
 if(/exec$/.test(uri)){ var c=P.command;
   if(/curl .*bing\\.com/.test(c)) reply={returnValue:true,stdoutString:JSON.stringify(BING)};
   else if(/curl .*reddit\\.com/.test(c)) reply={returnValue:true,stdoutString:RSS};
   else reply={returnValue:true,stdoutString:'{"returnValue":true,"launchPoints":[],"devices":[]}'}; }
 else reply={returnValue:false,errorText:'Denied method call'};
 setTimeout(function(){ self.onservicecallback(JSON.stringify(reply)); },80); }; };
""".replace('BING',json.dumps(BING)).replace('RSS',json.dumps(RSS))
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(**opts()); ctx=await b.new_context(viewport={'width':1920,'height':1080})
        await ctx.route('**/*',route)
        pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        if TVMODE: await pg.add_init_script(MOCK)
        await pg.add_init_script("if(!sessionStorage.getItem('x')){sessionStorage.setItem('x',1);localStorage.setItem('lumen.launcher.v1',JSON.stringify({wallpaper:'%s'}));}"%('bing' if TVMODE else 'landscapes'))
        await pg.goto((ROOT/'webos'/'index.html').as_uri()); await pg.wait_for_timeout(2500)
        tag=sys.argv[1] if len(sys.argv)>1 else 'web'
        await pg.screenshot(path=OUT+tag+'_wp1.png')
        cur1=await pg.evaluate("(document.querySelector('.ph.on')||{}).style&&document.querySelector('.ph.on').style.backgroundImage")
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(300)
        await pg.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:404,bubbles:true}))"); await pg.wait_for_timeout(2200)
        cur2=await pg.evaluate("document.querySelector('.ph.on').style.backgroundImage")
        print('photo1',cur1,'\nphoto2',cur2,'\ncredit',await pg.evaluate("document.getElementById('credit').innerText.replace(/\\n/g,' | ')"))
        await pg.screenshot(path=OUT+tag+'_wp2.png')
        if not TVMODE:
            # settings: switch to custom topic and type one
            await pg.keyboard.press('Escape'); await pg.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:403,bubbles:true}))"); await pg.wait_for_timeout(600)
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)   # open the Wallpaper page (2.3)
            for i in range(9): await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(60)   # landscapes -> ... -> topic
            await pg.wait_for_timeout(500)
            print('wallpaper now', await pg.evaluate("JSON.parse(localStorage.getItem('lumen.launcher.v1')).wallpaper"))
            await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
            await pg.keyboard.press('Control+A'); await pg.keyboard.type('northern lights'); await pg.wait_for_timeout(200)
            await pg.screenshot(path=OUT+tag+'_edit.png')
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(2500)
            print('topic saved', await pg.evaluate("JSON.parse(localStorage.getItem('lumen.launcher.v1')).wpTopic"))
            print('commons query used:', [re.search(r'gsrsearch=([^&]+)',u).group(1) for u in seen if 'gsrsearch' in u][-1])
            await pg.screenshot(path=OUT+tag+'_settings.png')
            # reddit (blocked in browser mode) -> should fall back gracefully
            await pg.keyboard.press('ArrowUp'); await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(2500)
            print('after reddit: wallpaper', await pg.evaluate("S_dbg=JSON.parse(localStorage.getItem('lumen.launcher.v1')).wallpaper"), 'photo class', await pg.evaluate("document.getElementById('stage').classList.contains('photo')"))
        else:
            # switch to subreddit via localStorage + reload: root curl RSS
            # set and reload in one step: the running page saves its settings when a photo finishes loading,
            # which used to overwrite this change before the reload (a flaky test, not an app bug)
            await pg.evaluate("var s=JSON.parse(localStorage.getItem('lumen.launcher.v1'));s.wallpaper='reddit';localStorage.setItem('lumen.launcher.v1',JSON.stringify(s));window.onbeforeunload=function(){localStorage.setItem('lumen.launcher.v1',JSON.stringify(s))};location.reload()")
            await pg.wait_for_timeout(2500)
            print('reddit photo', await pg.evaluate("(document.querySelector('.ph.on')||{style:{}}).style.backgroundImage"), await pg.evaluate("document.getElementById('credit').innerText.replace(/\\n/g,' | ')"))
            await pg.keyboard.press('Digit0'); await pg.wait_for_timeout(300); await pg.screenshot(path=OUT+tag+'_log.png')
        print('errors',errs)
        await b.close()
asyncio.run(main())
