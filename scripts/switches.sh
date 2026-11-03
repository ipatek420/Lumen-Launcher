#!/bin/sh
# Home-button override and start-on-boot. Missing flag file means on.
export PATH=/usr/bin:/usr/sbin:/bin:/sbin:$PATH
L=/media/developer/lumen-home
V=/var/lib/lumen-home/overlay
H=/usr/palm/applications/com.webos.app.home

home_on() { [ ! -e "$L/DISABLE-HOME" ] && [ ! -e "$L/DISABLE" ]; }
boot_on() { [ ! -e "$L/DISABLE-BOOT" ] && [ ! -e "$L/DISABLE" ]; }

set_marker() {
  python3 - "$1" << 'PY'
import sys, pathlib, re
val = sys.argv[1]
pat = re.compile(r'var LUMEN_BOOT = "(on|off)";')
for p in (pathlib.Path("/media/developer/lumen-home/overlay/index.html"), pathlib.Path("/var/lib/lumen-home/overlay/index.html")):
    if not p.exists():
        continue
    text = p.read_text()
    new, n = pat.subn('var LUMEN_BOOT = "%s";' % val, text, count=1)
    if n:
        p.write_text(new)
PY
}

copy_overlay() {
  mkdir -p "$V"
  cp -f "$L/overlay/appinfo.json" "$L/overlay/index.html" "$V/" 2>/dev/null || true
}

mount_home() {
  copy_overlay
  grep -q " $H " /proc/mounts || mount --bind "$V" "$H"
}

unmount_home() {
  if grep -q " $H " /proc/mounts; then
    umount "$H" || umount -l "$H" || true
  fi
}

# Restarting the app manager is what makes Home pick up the stand-in. It blanks the picture for a moment.
relaunch() {
  (
    systemctl restart sam
    i=0
    while [ "$i" -lt 40 ]; do
      systemctl is-active sam >/dev/null && break
      i=$((i+1))
      sleep 1
    done
    /usr/bin/luna-send -n 1 -w 10000 luna://com.webos.applicationManager/launch '{"id":"org.webosbrew.lumen","noSplash":true}' >/dev/null 2>&1
  ) >/tmp/lumen-switch.log 2>&1 &
}

case "$1" in
  status)
    if home_on; then printf 'home=1'; else printf 'home=0'; fi
    if boot_on; then echo ' boot=1'; else echo ' boot=0'; fi
    ;;
  home)
    if [ "$2" = on ]; then rm -f "$L/DISABLE-HOME"; else : > "$L/DISABLE-HOME"; fi
    if boot_on; then set_marker on; else set_marker off; fi
    if home_on; then mount_home; else unmount_home; fi
    relaunch
    echo ok
    ;;
  boot)
    if [ "$2" = on ]; then rm -f "$L/DISABLE-BOOT"; else : > "$L/DISABLE-BOOT"; fi
    if boot_on; then set_marker on; else set_marker off; fi
    copy_overlay
    echo ok
    ;;
  *)
    echo 'usage: switches.sh status|home on|off|boot on|off' >&2
    exit 1
    ;;
esac
