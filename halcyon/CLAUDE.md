# Halcyon: notes for contributors (and coding agents)

A redesign of Lumen Launcher for **rooted LG webOS TVs**, app id `org.webosbrew.halcyon`. Version **1.3.0**. Same platform, same hard-won rules; different layout, type and personality. Read `../CLAUDE.md` first: its "webOS rules learned the hard way" all apply here.

## Design

- **Mood:** calm, editorial, time-aware. A greeting in a serif ("Good evening, *Sam*"), a weather sentence ("59° and partly cloudy · High 68°, low 41°"), a sky that follows the real time of day.
- **Type:** Fraunces (300, 300 italic, 400) for the greeting, clock, titles, card names; Manrope (400–700) for everything else. Bundled by `build.py` from `@fontsource`.
- **Palette:** warm ink `#f4f1ea` on near-black `#05070d`; default accent Sunlit `#f2c47e`; Auto accent follows the focused app (Lumen's `readableAccent`, clamped l .68–.78).
- **Layout, bottom up** (`layout()`): dock (bottom 60 px), card track with labels, tabs 80 px above the track, hero anchored by its *bottom* 44 px above the tabs, so it never collides with tall cards. Greeting top left, clock and two buttons top right, hints right-aligned on the tab line.
- **One shelf under tabs** instead of Lumen's stacked rows: Recent (when non-empty), Favorites, All apps (user's order, 1.1). Halcyon opens on Favorites; Back on the shelf returns there. Only one track is in the DOM at a time.
- **Dock:** inputs ("Sources") and Home Assistant tiles (titled by the tile file's `title`) as pills. Hold OK on a pill: switch/run, or hide it (`S.hidden`, unhidden from Apps → Hidden apps & sources).
- **Categories (1.2):** no pill behind the focused tab (tried in 1.0–1.1, user preferred the line): the accent underline `#tabbar` marks the open category, full strength while the tabs have focus. Sized in px and moved with `transform`. With the tabs focused the hero shows the count in the accent line ("6 APPS") and the name; no "Shelf" label or description (user: it over-described).
- **One continuous shelf (1.2):** Right past the last card runs into the next category's first card, Left before the first into the previous category's last (`crossTab()`). The track snaps (transition off for one frame) rather than rewinding across the old category, and `#trackWrap` slides in 60 px from the side it was entered (`enterR`/`enterL`, transform + opacity; not the separate `translate` property, which old webOS browsers lack).
- **Scene press (1.2):** no toast on success and no lingering dot (user's request); an accent ring on `.pill::after` pulses out and fades in .55 s (`pressPulse()`, on press, before Home Assistant answers). Failures still toast.
- **Recent:** `noteUse()` on launch keeps `S.recent` (14, newest first). The shelf re-renders on return (`onReturn`), not at launch, so nothing re-lays out under the zoom. A "Last opened …" hero line was tried in 1.0 and removed in 1.1 (user: unnecessary); apps without a description show none.

## The sky (`skyNow()`, `paintSky()`)

Keyframes around sunrise/sunset (from the Open-Meteo `daily=sunrise,sunset`, default 06:45/18:15): night → dawn (rise−10) → day (rise+80) → day (set−110) → golden (set−35) → dusk (set+15) → night (set+75), smoothstep between them, wrapping midnight. Each phase has three gradient stops, a sun/moon glow colour, strength and position, and a star amount (170 seeded stars). The sky base is cached per 5-minute slot (`skyCache`), the dim+shade+grain overlay per size and dim (`overCache`); a focus change paints `drawImage(base)` + the app tint blob + `drawImage(overlay)`. A new forecast clears `skyCache`.

## Performance (measured, keep it)

`tests/test_performance.py` (6× throttle, arrow every 100 ms) back to back with Lumen 2.4 on the same machine: sky Full ≈ 57–59 fps (Lumen dynamic 56.5), Bing photo ≈ 55–57 (Lumen photo 51.6), Lite ≈ 58–59. Trace (30 moves): raster ≈ 60 ms (Lumen 64), 2 layouts.

Findings from getting there:
1. **Don't fade cards that scroll past.** An opacity transition on each card leaving the left edge promoted it to a layer and then folded it back into the track, re-rastering the whole track every step (26 layouts, raster 174 ms). The track now sits in a clip window (`#trackWrap`, left 96 px, overflow hidden) so earlier cards slide out of view for free.
2. **One glow, not one per card.** A per-card accent glow meant every Auto-accent change repainted every card's glow layer. `#glow` is a single element in the track, moved with `transform` to the focused card.
3. **Cache the sky.** Redrawing 170 star paths + shade + grain on every settle cost ~4 fps at 6× throttle.
4. Everything else as in Lumen: transform/opacity only, glide mode on held arrows (`stepped()`), hero text deferred while gliding, backdrop repainted only after the focus settles (200/320 ms), key repeat capped (110 ms, 70 in Lite).

## Zones and keys

`F.zone`: `shelf` · `tabs` · `peek` · `top` · `dock` · `menu` · `settings`. Up: shelf → tabs → peek → top. Down: top → peek → tabs → shelf → dock. **Peek** (Lumen's two-step Up, restored in 1.1 at the user's request): `#stage.z-peek` slides the shelf down 170 px and fades it to .16, hides hero/hints/dock and lightens the photo shade, so the sky or photo shows; OK or Back returns to the cards. `z-top` keeps the shelf aside and the hero describes the focused button. Left/Right on tabs switches the shelf immediately. Back: dock/tabs/top → shelf; on the shelf, first card, then the first card of Favorites. An empty shelf (apps still loading) parks focus on the dock or top (`F.parked`) and returns it when apps arrive (first-boot bug caught by `test_tv.py`). Hold OK/Yellow: options menu; Red: settings; Green: next photo; 0/Blue: debug log.

## Storage

`halcyon.settings.v1` (S), `halcyon.apps.v1` (last app list, instant start), `halcyon.colors.v1` (icon edge analysis), `halcyon.icons.v1` (root-read icons, capped ~3.5 MB), `halcyon.wx.v1` (forecast incl. sunrise/sunset), `halcyon.ha.v1` (tiles), `halcyon.wp.<source>` (photo lists). All access wrapped in try/catch.

## Inputs

Rule 2 of `../CLAUDE.md`: connected HDMI only, and a port whose connection the TV doesn't report is shown. Every load logs what the TV said per port (`inputs: N shown; TV reports HDMI_1 connected=true … | …`). If the input list can't be read, the last list is kept and a manual reload says so (1.0 claimed "sources loaded" with the old list). A user reported (1.0, real TV) a removed HDMI source that stayed after reload and reboot: not reproduced on the simulated TV, where an unplugged port leaves the dock on the next load; the log line will tell whether the TV still reports it connected. Workaround: hide the pill.

## Restart TV (1.3)

LG's settings have no reboot. Settings → Advanced → Restart TV: OK arms it ("Press OK again to restart"), a second OK within 3.5 s calls `rebootTv()`: `luna://org.webosbrew.hbchannel.service/reboot` (what the Homebrew Channel's own Reboot button uses), then root `reboot` if that is refused. Moving away or 3.5 s cancels (`disarm()`, shared with Reset all settings, redraws the armed row). Unverified on a real TV.

## Home Assistant

Lumen's protocol unchanged (`../docs/home-assistant.md`): `GET /local/halcyon.json`, on 404 `GET /local/lumen.json`; `POST /api/webhook/<id>`; both through root curl on the TV, never XHR; ids `^[A-Za-z0-9_-]{1,100}$`, max 20 tiles. The browser preview shows a demo "Living room" set.

## Build, test

```sh
npm install && python3 build.py [--package]
HALCYON_CHROMIUM=/path/to/chrome python3 tests/test_tv.py   # and test_scenes, test_sky_settings, test_wallpapers, test_reboot, test_performance
```

`tests/tvmock.py` is the simulated TV (direct calls denied; root exec answers luna-send, cat, curl). Look at `tests/shots/` after every change.

## Open items

- **Never run on real hardware yet.** Everything above is verified on the simulated TV only. First things to check on the TV: fonts (Fraunces italic), the clip window with Large cards, sky repaint cost on the real GPU, the `z-top` shelf slide.
- **Open (1.1):** the removed HDMI source above: ask for the `inputs:` debug log line.
- Photo topics (1.1): all of Lumen's are back (Commons topics, custom topic, subreddit via root curl RSS, Bing, NASA). Not ported: photo quality, slow drift, blur photos, the gradient wallpapers.
- Dropped from Lumen on purpose: per-app artwork (`bgImage`) on cards, the light sweep, the Android shell hooks.
