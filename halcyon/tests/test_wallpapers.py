"""Photo backdrops, network routed to local fixtures.
- every Commons topic sends its own featured-picture queries and shows a wide photo with its credit
- Custom topic: typing a topic in settings reloads photos for it
- Subreddit on a simulated TV: the RSS feed is read through root curl, image posts become photos"""
import asyncio, json, urllib.parse
from playwright.async_api import async_playwright
from tvmock import opts, tv_mock, settings_script, PAGE, SHOTS, FIX

PHOTO = open(FIX/'photos'/'a.jpg', 'rb').read()
TOPICS = {'landscapes': ['Featured_pictures_of_landscapes'], 'astro': ['Featured_pictures_of_astronomy'],
          'botanical': ['Featured_pictures_of_plants'], 'nature': ['Featured_pictures_of_nature'],
          'sea': ['sea', 'coast', 'ocean', 'waves'], 'clouds': ['clouds', 'sunset', 'aurora', 'sky'],
          'abstract': ['fractal', 'abstract', 'long exposure', 'bokeh']}

def commons_reply(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)['gsrsearch'][0]
    name = q.split(' filetype')[0].split()[-1].strip('"')
    return {"query": {"pages": {"1": {"title": "File:%s.jpg" % name, "imageinfo": [{"url": "https://upload.wikimedia.org/x/%s.jpg" % name,
            "thumburl": "https://upload.wikimedia.org/x/%s.jpg" % name, "width": 4000, "height": 2250,
            "extmetadata": {"ObjectName": {"value": "Photo of " + name}, "Artist": {"value": "<a href='#'>A. Photographer</a>"}}}]}}}}

def router(seen):
    async def route(r):
        u = r.request.url
        if 'commons.wikimedia.org/w/api.php' in u:
            seen.append(urllib.parse.parse_qs(urllib.parse.urlparse(u).query)['gsrsearch'][0])
            return await r.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*'}, content_type='application/json', body=json.dumps(commons_reply(u)))
        if 'upload.wikimedia.org' in u or 'i.redd.it' in u:
            return await r.fulfill(status=200, content_type='image/jpeg', body=PHOTO)
        if u.startswith('http'): return await r.abort()
        return await r.continue_()
    return route

async def open_page(b, st, init=None):
    seen = []
    ctx = await b.new_context(viewport={'width': 1920, 'height': 1080}); await ctx.route('**/*', router(seen))
    pg = await ctx.new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    if init: await pg.add_init_script(init)
    await pg.add_init_script(settings_script(st))
    await pg.goto(PAGE); await pg.wait_for_timeout(2500)
    return ctx, pg, seen, errs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**opts())
        for topic, words in TOPICS.items():
            ctx, pg, seen, errs = await open_page(b, {'backdrop': topic})
            shown = await pg.evaluate("document.getElementById('stage').classList.contains('photo')")
            credit = await pg.evaluate("document.getElementById('credit').textContent")
            print('%-11s queries %d, photo %s, credit %r' % (topic, len(set(seen)), shown, credit))
            assert shown and credit.startswith('Photo of') and 'A. Photographer' in credit, (topic, credit)
            for w in words: assert any(w in q for q in seen), (topic, w, seen)
            if topic == 'clouds': await pg.screenshot(path=str(SHOTS/'wallpaper_clouds.png'))
            assert not errs, errs
            await ctx.close()

        # Custom topic: Backdrop page shows a Topic field; typing one reloads photos for it
        ctx, pg, seen, errs = await open_page(b, {'backdrop': 'topic', 'wpTopic': 'waterfall'})
        assert any('waterfall' in q for q in seen), seen
        await pg.keyboard.press('ArrowUp'); await pg.keyboard.press('ArrowUp'); await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(300)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(400)                        # settings
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)                        # Backdrop page
        labels = await pg.evaluate("Array.prototype.map.call(document.querySelectorAll('#s-list .si>span:first-child'),function(e){return e.textContent})")
        print('backdrop page', labels); assert labels[:2] == ['Backdrop', 'Topic'], labels
        await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        await pg.keyboard.type('lighthouse'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1500)
        assert any('lighthouse' in q for q in seen), seen
        assert 'lighthouse' in await pg.evaluate("document.getElementById('credit').textContent")
        assert not errs, errs
        await ctx.close()

        # Subreddit on the TV: RSS through root curl
        rss = '<feed><entry><title>Misty valley at dawn [4000x2250]</title><content>&lt;a href=&quot;https://i.redd.it/abc123.jpg&quot;&gt;</content></entry></feed>'
        mock = tv_mock([{"id": "app.one", "title": "App One"}], [], curl={'reddit.com/r/EarthPorn': [200, rss]})
        ctx, pg, seen, errs = await open_page(b, {'backdrop': 'reddit'}, init=mock)
        cmds = [json.loads(c.split(' ', 1)[1])['command'] for c in await pg.evaluate('window.__calls') if 'hbchannel' in c]
        assert any(c.startswith('curl') and 'reddit.com/r/EarthPorn/top/.rss' in c for c in cmds), cmds
        credit = await pg.evaluate("document.getElementById('credit').textContent")
        print('reddit credit', repr(credit)); assert 'Misty valley' in credit and 'r/EarthPorn' in credit
        assert not errs, errs
        await ctx.close(); await b.close()
    print('test_wallpapers: OK')
asyncio.run(main())
