# Lumen Launcher: notes for contributors (and coding agents)

A Projectivy Launcher / Apple TV–style home screen for **rooted LG webOS TVs**. Built over many rounds of feedback on a real TV; these notes are the hand-off. Read them before changing anything.

Current version: **2.4.0**.

## Target setup

- LG TV on webOS 4+ (developed on webOS 10), **rooted**, with the **webOS Homebrew Channel** and its root service. App id `org.webosbrew.lumen`.
- Lumen can be opened from LG's launcher, recent apps, or anything that calls `system.launcher/launch` with `{"id":"org.webosbrew.lumen"}` (for example a Home Assistant `webostv` script).

### Design direction

- Projectivy / Apple TV: big title for the focused app, ambient backdrop, rows of cards that lift on focus, light sweep, smooth scrolling.
- Avoid: lag; icons sitting as a hard square inside the card ("box in a box"); backgrounds that look compressed or too plain; developer details (package ids, versions) in the UI.

## Layout

```
src/launcher.html     THE source: one file, inline CSS + JS (ES5, no framework, no build step)
build.py              src → webos/index.html (bundled fonts); --package builds the .ipk
webos/                LG app folder: appinfo.json, index.html (generated), icons, fonts/, README.md (user-facing)
dist/                 latest installable builds
tests/                Playwright tests with a simulated TV (see Testing); fixtures/ has stand-in icons and photos
docs/                 home-assistant.md (user guide), icon-source.png (1024 px app icon), screenshots/, archive/
```

The same `index.html` serves three environments, detected at runtime:
- `window.PalmServiceBridge` → webOS TV (`ON_TV`)
- `window.LumenAndroid` → an Android TV shell (`ON_ANDROID`; the shell isn't part of this repo, the code paths are dormant)
- neither → browser preview with sample apps

## Build, package, install

```sh
npm install                      # @webos-tools/cli (ares-*), @fontsource fonts
python3 build.py                 # regenerate webos/index.html
python3 build.py --package       # + dist/org.webosbrew.lumen_<ver>_all.ipk
```

Bump `VERSION` in `build.py` and `LUMEN_VERSION` in `src/launcher.html` (used in the debug log and the hero). Update `webos/README.md` with a "New in x.y" section each release.

**Installing on the TV:**
- Developer-mode route: `ares-setup-device` once, then `ares-install dist/<ipk>`.
- Rooted route: enable SSH in Homebrew Channel settings, copy the ipk to `/tmp`, then `luna-send -n 1 'luna://com.webos.appInstallService/dev/install' '{"id":"org.webosbrew.lumen","ipkUrl":"/tmp/<ipk>","subscribe":true}'`.


## Testing (do this before every delivery)

`pip install playwright` (Chromium), then from the repo root. If Playwright's own browser isn't installed (cloud sessions), point the tests at a preinstalled Chromium with `LUMEN_CHROMIUM=/path/to/chrome` (see `tests/pwlaunch.py`).

```sh
python3 tests/test_home_assistant.py             # HA row on a simulated TV: address, lumen.json via root curl, webhook POST, unsafe ids dropped, errors
python3 tests/test_weather_settings.py           # settings pages, weather (Open-Meteo routed to fixtures), accent carousel + Auto
python3 tests/test_tv_settings.py                # Up path (rows -> peek -> top buttons), TV settings button via root, no package ids in the hero, input labels
python3 tests/test_apps_icons_inputs.py strict   # simulated TV: direct calls denied, root fallback, icons, inputs, favorites, debug log
python3 tests/test_apps_icons_inputs.py open     # same, with readable image pixels
python3 tests/test_wallpapers.py web             # Commons wallpapers, next photo, custom topic edit, Reddit failure → fallback
python3 tests/test_wallpapers.py tv              # Bing + Reddit through root curl
python3 tests/test_relaunch.py                   # webOSRelaunch calls webOSSystem/PalmSystem.activate
python3 tests/test_performance.py                # fps under 6x CPU throttle: dynamic, relaxed, photo, photo+drift, Lite
```

Screenshots go to `tests/shots/`. **Look at them**: most past bugs were visual. The tests mock `PalmServiceBridge` and route network requests to local fixtures; the real services (Commons, Bing, NASA, Reddit) have never been called from the test environment.

Performance baselines (headless, 6× throttle, arrow every 100 ms): dynamic ≈ 58 fps, photo ≈ 56, photo + drift ≈ 45–50, Lite ≈ 58. Don't ship regressions below about 35 at Full.

## webOS rules learned the hard way (don't regress these)

1. **Privileged calls are denied** to normal apps (`listApps`, `listLaunchPoints`, `getAllInputStatus`: "Denied method call … for category /"). `lunaQuery()` tries direct, then root via `luna://org.webosbrew.hbchannel.service/exec` running `luna-send -n 1 -w 8000 '<uri>' '<json>'` and parsing stdout. Reply fields: `stdoutString`, `stdoutBytes` (base64).
2. **Apps come from `listLaunchPoints`**, the same list LG's home bar uses; `listApps` is only a fallback. Inputs are excluded from it and come from `com.webos.service.eim/getAllInputStatus`: `devices[]`, `id` like `HDMI_3`, `label` = the user's name for it, show `connected===true` only, and if `appId` is missing use `com.webos.app.hdmiN`.
3. **Relaunch:** with `handlesRelaunch:true`, the app must call `webOSSystem.activate()` (or `PalmSystem.activate()` on older firmware) in the `webOSRelaunch` handler, or it stays hidden. This was the 1.3.1 bug.
4. **Icons:** probe `largeIcon`, then `icon`, then root `cat` → data URI (cached). App artwork (`bgImage`) is used only after it's confirmed to load; skipping that check caused blank cards in 1.1.
5. **No box in a box:** `analyzeIcon()` samples a 40×40 canvas (edge ring, skipping 12 px corners). A solid edge (`seam`) sets the card to the exact edge colour; otherwise `tile` (rounded) or `clear`. A tainted canvas triggers a root re-read. Results are cached in `lumen.colors.v1`.
6. **Performance:**
   - Never use CSS `filter: blur` or `backdrop-filter` on big layers.
   - Animate only `transform` and `opacity`; the focus shadow is a separate `.halo` whose opacity fades.
   - Measure layout once per render; throttle key repeat (110 ms, or 70 in Lite).
   - Repaint the backdrop only after navigation settles (200/320 ms).
   - The dynamic backdrop is painted on 480×270 canvases (960 for artwork) and cross-faded by the compositor (two layers, opacity).
   - Grain only at 960 px; at 480 it shows as a grid.
7. **Code style:** ES5 only (old TV browsers): no arrow functions, `let`, classes or async. Wrap every `localStorage` access in try/catch.
8. **Wallpapers (1.4):**
   - Commons featured pictures via `generator=search` with `incategory:` plus `filetype:bitmap filew:>1900`, `gsrsort=random` (with a retry without it), and `iiurlwidth` set by the Photo quality setting.
   - Bing `HPImageArchive` (`urlbase` + `_UHD.jpg`) and NASA APOD (`DEMO_KEY`).
   - Reddit: anonymous JSON was **shut down in 2026**, so Lumen uses RSS through root curl (fragile; it falls back to Dynamic colors with a toast).
   - `getText()` tries direct XHR, then root `curl || wget`.
   - Photos show on `.ph` layers with the `#phShade` overlay; Blur photos paints through the canvas path instead.

9. **TV settings button (1.5, trimmed in 1.6):** a settings row and an "Open TV settings" item proved redundant; only the top-bar button remains. It launches `com.palm.app.settings` through `lunaDo()` (direct, then root `luna-send`, reading `returnValue:false` from the output). Top bar: `F.top` 0 = TV settings, 1 = Lumen gear.
10. **Up path (1.6):** rows → `peek` (cards slide down 170 px and fade on `#rowsWrap`, hero/hints hidden, photo shade lightened) → `top` (buttons; cards stay aside, hero describes the focused button). Down retraces; OK/Back from peek returns to the cards. Stage classes `peek` / `peek-bg` are set in `applyFocus()` and `applySettings()`.
11. **Inputs:** name on the card face (`.art.nm`), port under the card as its label (`labelText()`); skipped by icon resolution. The hero never shows package ids or versions (user feedback: that's developer detail).
12. **Layers (1.6):** `.lift`, `.halo` and `.sheen` have `will-change`. Without it the 56 px focus shadow was re-rasterized on every move (Chrome trace: ~360 ms raster per 30 moves → ~145 ms). Measure with a `devtools.timeline` trace (RasterTask/Paint) rather than fps alone; headless fps barely moves, and run each build several times in a row (results drift with machine load).
13. **Smoothness (2.1, from studying Hearth `tld.my.customlauncher`):**
   - **Glide:** a move < 280 ms after the previous adds `#stage.glide` (removed 300 ms after the last move): track/rows transitions become .15 s linear, lift/halo/label .15 s, sheen off. Restarting a .5 s ease-out every 110 ms was the stutter with Relaxed.
   - **Hero text** is deferred while gliding (`heroT`, 170 ms) so 96 px type isn't laid out per step; `topHero()` clears it.
   - **Native viewport:** `<meta viewport width=1920>`; `fit()` sets no transform when the window is 1920×1080 (debug log prints the window size at start).
   - **Gloss under sheen:** `.face::after` z-index 0, `.sheen` z-index 1. With the gloss above the promoted sheen, Chrome had to give the gloss its own layer and re-raster both every move (trace: removing either cut raster ~60%).
   - Focus shadow 0 24px 42px (was 0 30px 56px).
   - Hearth itself is larger because it bundles five font families and ~50 hand-made app/input icon PNGs, not because of its engine (Preact). Its tiles are 144 px squares with a hard ring focus, which is inherently cheaper than Lumen's landscape cards with shadow and sweep.
14. **Home button (2.2, removed in 2.3):** Lightkeeper's approach (GlassHouse `glasshouse.remoteKeys` `home` entry + a Homebrew Channel boot hook in `/var/lib/webosbrew/init.d`) worked on a webOS 10.3.1 TV but fought LG's launcher (Home needed several presses), so it was removed. The 2.2 code (`lumen-home.js`, `lumen-init` and its two tests) is kept in `docs/archive/home-button-2.2/` if it is ever revisited.
15. **Settings pages (2.3):** `OPTIONS` headers (`{h, sum}`) are pages; the root lists them with `sum()`; `F.page` (-1 = root), `F.lastPage` reopens on the last page; Back: favorites picker → page → root → close. `valName(key)` gives an option's display name.
16. **Weather (2.3):** Open-Meteo geocoding (`name=`, first part before a comma; the part after a comma picks among results by state/country) and forecast (`current=temperature_2m,weather_code,is_day`, `daily=…max,min`, `timezone=auto`, `temperature_unit=fahrenheit` for °F) via `getJSON` (XHR, root curl fallback). `S.wxPlace/wxLat/wxLon/wxUnits/weather`; cache `lumen.wx.v1`, refresh 30 min, retry 10 min on failure, hidden if older than 3 h. `#wx` sits left of `#clock` with the same two-line rhythm.
17. **Accent (2.3):** `ACCENTS[0]` is `auto`: `updateAutoAccent()` runs when the hero text settles (never per step while gliding), `readableAccent()` clamps HSL to s .55–.9, l .66–.78, greys → Ice. The settings row shows 3 swatches + name.
18. **Home Assistant row (2.4):** tiles from `http://<addr>/local/lumen.json` (`{title, tiles:[{name, icon, webhook, description?}]}`), each `POST /api/webhook/<id>`. No token: `/local/` is served without auth and webhook triggers are `local_only` by default. On the TV both requests go through root `curl` (never XHR: a CORS-blocked POST still reaches HA, so an XHR-then-curl fallback would toggle twice). Webhook ids must match `^[A-Za-z0-9_-]{1,100}$` (they go into a URL and a shell command); max 30 tiles. Tiles are pseudo-apps `ha:<webhook>` (`a.ha`), merged by `haMerge()` in `setApps()`, named cards, no zoom on OK, row key `ha` after Inputs, cache `lumen.ha.v1`, reload at start / on return (once a minute) / from settings. HA answers 200 even for an unknown webhook id, so ✓ means "HA received it". User guide: `docs/home-assistant.md`.

## Version history

- **1.0** First design. App list denied and slow on the TV.
- **1.1** Root app list via Homebrew Channel; performance rewrite (canvas backdrop, transform/opacity only); local fonts; Lite mode; frame-rate counter.
- **1.2** `listLaunchPoints`, verified artwork, root icon fallback, initials placeholder, connected-HDMI Inputs row, Choose favorites screen, Partridge hidden, debug log (0 / blue).
- **1.3** Icon edge-colour matching (`seam`/`tile`/`clear`); smooth colour-field backdrop from icon colours; compositor cross-fade.
- **1.3.1** Relaunch brings Lumen to the front.
- **1.4** Photo wallpapers: Landscapes, Astrophotography, Botanical, Nature, Sea, Sky, Abstract, Custom topic, Bing, NASA, Subreddit. Rotation timer, green = next, credit, quality, slow drift, blur photos, text fields that open the TV keyboard.
- **1.5** TV settings row and top button (LG settings without the remote shortcut), named input cards, hero meta line under the title, "Lumen settings" panel title, small accessibility fixes (status regions, decorative SVGs hidden).
- **1.6** Feedback on 1.5: settings row and panel item removed (button only); Up peeks at the wallpaper before reaching the buttons; 60 px card gap (reverted in 2.0); input port under the card; no package ids in the hero; 14 accents; layer promotion for smoother scrolling.
- **2.0** New icon (source: `docs/icon-source.png`, 1024 px; `webos/icon.png` 80, `largeIcon.png` 130, `iconColor` #0a0626). Card gap back to 38 px: when the user asked for "a gap between the cards and settings" they meant the peek step, not card spacing. Scrolling reported much smoother in 1.6, especially Icon cards; Landscape still slightly choppy (larger layers).
- **2.1** Smoothness pass after comparing Lumen with Hearth: glide mode for held arrows, deferred hero text, native 1920 viewport, gloss below the sweep, tighter shadow. Trace on Relaxed + Landscape vs 2.0: layouts 30 → 10, raster tasks ~410 → ~295 per 30 moves.
- **2.2** Home button opens Lumen and open at power on (GlassHouse + Homebrew Channel boot hook), after analysing Lightkeeper. Fought LG's launcher; removed in 2.3.
- **2.3** Weather next to the clock (with high/low), settings split into pages, accent carousel with Auto, Home button feature removed. Ambient mode, number-key shortcuts and custom app artwork were considered and dropped.
- **2.4** Home Assistant row (webhooks + `www/lumen.json`, no token), new Home Assistant settings page.

## Open items

- Confirmed on a real webOS 10 TV: weather, settings pages, Auto accent, the Home Assistant row (2.3–2.4).
- **Unverified on real hardware:** the TV settings button on other webOS versions; photo wallpapers from Commons/Bing/NASA and the Reddit RSS route (debug log lines start with `wallpaper:`); scrolling with Relaxed animation + Landscape cards (debug log line 1 shows the window size).
