# Lumen Launcher 2.4

A Projectivy / Apple TV style launcher for rooted LG webOS TVs.

## New in 2.4: Home Assistant row

A row of tiles under Inputs that run Home Assistant automations (lights, scenes, anything).
No token or login: the tile list is a file in Home Assistant's `www` folder (`lumen.json`)
and each tile triggers a webhook automation, which Home Assistant only accepts from your
home network. Lumen settings → **Home Assistant**: Address, Show the row, Reload tiles.
Full setup with examples: `docs/home-assistant.md`.

## New in 2.3

- **Weather next to the clock:** an icon and the current temperature, with today's high
  and low under it. Lumen settings → Clock & weather → **Place**: type a city ("Austin"),
  a city and state ("Austin, Minnesota") or a ZIP code. Choose °F or °C, or turn weather
  off. It comes from Open-Meteo (free, no account), refreshes every 30 minutes, and simply
  doesn't show if it can't connect.
- **Settings in pages:** the first screen lists Wallpaper, Cards, Focus & colour, Clock &
  weather, Layout, Performance, Apps and Advanced, each with a short summary. OK opens a
  page, Back goes up one level, and Lumen settings opens on the page you used last.
- **Accent colour picker:** shows the chosen colour with its neighbours either side;
  left and right go through all 14 colours plus **Auto**, which takes the colour of the
  app you're on.
- **Removed:** the experimental "Home button opens Lumen" switches from 2.2.

## New in 2.1: smoother scrolling

Ideas borrowed from Hearth (`tld.my.customlauncher`), another webOS launcher that scrolls very smoothly:

- **Glide when holding an arrow.** When moves come quickly, rows slide at a short, steady
  pace instead of restarting a slow ease-out on every step (which is what made Relaxed feel
  stuttery while holding). The light sweep pauses while gliding, and the app name and
  description at the top update once you stop, instead of on every card.
- **No scaling of the whole screen.** Lumen now renders at the TV's own 1920×1080 and only
  falls back to scaling if the window is a different size. The debug log's first line
  shows the window size.
- **Less redrawing per move:** the card's glossy top layer now sits under the light sweep
  (on top of it, it forced both to be redrawn every move), and the focus shadow is a bit
  tighter. Same look.

## New in 2.0

- **New icon:** the glowing "L" in a ring, in LG's launcher, recent apps and the
  Homebrew Channel.
- **Card spacing is back to the original** (38 px). The extra space in 1.6 was a
  misunderstanding: the "gap" asked for was the in-between step on the way to Settings
  (the wallpaper view), which stays.

## New in 1.6

- **TV settings button** at the top right, next to Lumen's gear, opens LG's own
  settings menu. The TV settings row from 1.5 and the "Open TV settings" item in
  Lumen settings are gone; this button replaces them.
- **Up works in two steps.** From the first row, press **Up** once and the cards slide
  down and fade so you can see the wallpaper. Press **Up** again to reach the gear
  (then **Left** for TV settings). **Down** goes back the same way; **OK** or **Back** from
  the wallpaper view returns to the cards.
- **Inputs:** the input's name stays on the card and the port (e.g. "HDMI 3") is now
  under the card, like the app names.
- **No more package names.** Apps without a description no longer show ids like
  `youtube.leanback.v4` or a version number under their name.
- **14 accent colours:** Ice, Blue, Teal, Mint, Lime, Gold, Peach, Coral, Red, Rose,
  Magenta, Orchid, Violet and White. The chosen colour's name shows next to the swatches.
- **Smoother scrolling:** the focused card, its shadow and the light sweep now stay on
  the graphics chip instead of being redrawn on every move. In testing this cut the
  drawing work while scrolling by more than half, which matters most with Relaxed animation.

## New in 1.5

- Inputs show their names on the card; LG's default names like "HDMI2" read as "HDMI 2".
- Hero text: the app name first, then one line with the category and Favorite.
- The settings panel is titled **Lumen settings**.
- Inputs pinned to Favorites can be moved there with hold OK → Move.

## New in 1.4: photo wallpapers

Settings → Background → **Wallpaper** now offers real, high-resolution photos:

| Wallpaper | Source |
|---|---|
| Landscapes, Astrophotography, Botanical, Nature | Wikimedia Commons *featured pictures* in that category (hand-picked by the Commons community, CC-licensed) |
| Sea & coast, Sky & clouds, Abstract & fractals | Commons featured pictures matching those subjects |
| Custom topic | Commons featured pictures matching any word you type (e.g. "waterfall", "northern lights") |
| Bing daily photos | The last ~16 Bing homepage photos, in 4K |
| NASA picture of the day | Random Astronomy Pictures of the Day (wide photos only) |
| Subreddit | Top image posts of the month from any subreddit you type. Reddit closed its anonymous API in 2026, so this uses the RSS feed and may stop working if Reddit blocks it |
| Dynamic colors | The glow built from the focused app's colours (as before) |
| Gradient: … | The five built-in gradients |

Photo options (shown when a photo wallpaper is selected): **Next wallpaper**
(or press the **green** button), **Change every** 5 min – a day, **Photo quality**
1080p / 1440p / 4K, **Show photo credit**, **Slow drift** (gentle zoom), and
**Blur photos** (frosted look using the Blur slider). **Dim** applies to photos too.

Text fields (Topic, Subreddit): press OK to open the TV keyboard, OK/Enter to
save, Back to cancel. Photo lists are cached on the TV and refreshed daily
(Bing and NASA every 6 hours); the current photo shows instantly at start-up.
If a source can't be reached, Lumen falls back to Dynamic colors and the debug
log (0 / blue) says why. Only portrait-free, wide photos are used.

## New in 1.3.1

- **Fix:** opening Lumen while it's already running in the background (from a
  script, LG's launcher, or a remote button) now brings it to the front.
  Before, nothing happened until you picked it from recent apps.

## New in 1.3

- **Background:** a smooth colour field built from the focused app's own icon
  colours, instead of a heavily blurred, stretched icon. App artwork (when an
  app provides it) is painted at twice the old resolution with a step-blur.
- **No more square inside the card:** Lumen reads each icon's edge colour and
  paints the card to match, so solid-background icons blend in. Icons with busy
  edges get rounded corners; transparent icons float on their own colour.
  Colours are worked out once per app and remembered.

## New in 1.2

- **Icons:** read from the TV's launch-point list (the same one LG's home bar
  uses). If an icon file is blocked, Lumen reads it as root through the
  Homebrew Channel and keeps a copy. App artwork is only used once it's
  confirmed to load, so cards never go blank.
- **Inputs:** a row of the HDMI ports that have something plugged in, under
  the names you set in LG's input settings. Inputs can be pinned to Favorites.
- **Choose favorites:** Settings → Apps → Choose favorites. OK adds or removes;
  the numbers are the order on the home screen. Hold OK → Move on the home
  screen still works for fine-tuning.
- **Hidden by default:** `works.partridge.webos-launcher`. Unhide it from
  Settings → Hidden apps if you ever want it back.
- **Debug log:** press **0** or the **blue** button (or Settings → Debug log)
  to see what Lumen asked the TV and what came back.

## Upgrading from 1.0

Version 1.1 has a new app ID (`org.webosbrew.lumen`), so it installs as a
separate app. Uninstall the old "Lumen Launcher" (`com.lumen.launcher`) first,
and update your boot script if you made one (see below).

## Install

**From your PC**

```sh
ares-install org.webosbrew.lumen_1.4.0_all.ipk
```

**On the TV over SSH (rooted)**: copy the .ipk to `/tmp`, then:

```sh
luna-send -n 1 'luna://com.webos.appInstallService/dev/install' \
  '{"id":"org.webosbrew.lumen","ipkUrl":"/tmp/org.webosbrew.lumen_1.4.0_all.ipk","subscribe":true}'
```

## How it reads your apps

webOS doesn't let ordinary apps list installed apps (this caused the
"Denied method call listApps" error in 1.0). Lumen now asks the Homebrew
Channel's root service to run that query instead:

```
luna://org.webosbrew.hbchannel.service/exec
```

This needs the Homebrew Channel installed with its root service working.
In the Homebrew Channel's settings, the status should show the service as
running as root. The list is saved after the first load, so later starts are
instant, and it refreshes quietly whenever you come back to the launcher.
Settings → Reload apps and inputs forces a refresh.

If it still can't read the list, the banner shows the exact error. Send that
text back for a fix.

## Start it automatically at boot

Create `/var/lib/webosbrew/init.d/lumen-launcher` (no file extension):

```sh
#!/bin/sh
sleep 15
luna-send -n 1 luna://com.webos.applicationManager/launch '{"id":"org.webosbrew.lumen"}'
```

then `chmod +x /var/lib/webosbrew/init.d/lumen-launcher`.

## If it feels slow

- Settings → Performance → **Effects: Lite** turns off the shine sweep, title
  animation, card shadows and background fade. It's the fastest mode.
- **Show frame rate** puts a counter in the corner. 50–60 fps is smooth.
  Send the number back if it's still choppy.
- Setting **Animation** to Fast also helps on older TVs.

## Remote

| Remote            | Action                                      |
|-------------------|---------------------------------------------|
| Arrows            | Move between apps and rows                  |
| OK                | Open the app                                |
| Hold OK / Yellow  | Options: Favorites, Move, Hide              |
| Up from top row   | Settings gear                               |
| Red               | Open or close Settings                      |
| Back              | Close panels, or jump back to the first app |
| Green             | Next wallpaper (photo wallpapers)           |
| 0 / Blue          | Debug log                                   |

## Rebuild

Edit `index.html`, then `ares-package <this folder> -o out`. Fonts are bundled
in `fonts/`, so the launcher looks the same with no internet connection.
