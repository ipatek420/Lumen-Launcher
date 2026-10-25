#!/bin/sh
# The root side of the Home button (webos/service/lumen-home.js + lumen-init) against a fake TV:
# a fake luna-send (compiled, so its command line looks like the real binary's), a fake GlassHouse
# folder and a temporary Homebrew Channel init.d. Needs node and cc. Usage: sh tests/test_home_service.sh
set -u
SVC=$(cd "$(dirname "$0")/../webos/service" && pwd)
T=$(mktemp -d); trap 'echo stopped > /tmp/lumen-home.gen; rm -rf "$T"' EXIT
FAIL=0; check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; FAIL=1; fi; }
mkdir -p "$T/tvweb" "$T/keyfilters" "$T/initd" "$T/data" "$T/app"
echo '// fake' > "$T/tvweb/tvweb.js"; printf '#!/bin/sh\necho "tvwebctl $*" >> %s/calls.log\n' "$T" > "$T/tvweb/tvwebctl"; chmod +x "$T/tvweb/tvwebctl"
cat > "$T/impl.sh" <<EOT
#!/bin/sh
echo "luna-send \$*" >> $T/calls.log
case "\$*" in
  *-i*getPowerState*) sleep 1; echo '{"returnValue":true,"state":"Active"}'; sleep 30 ;;
  *-i*getAppLifeEvents*) sleep 3; echo '{"event":"foreground","appId":"netflix","windowType":"_WEBOS_WINDOW_TYPE_CARD"}'; sleep 1; echo '{"event":"foreground","appId":"com.webos.app.home","windowType":"_WEBOS_WINDOW_TYPE_CARD"}'; sleep 30 ;;
  *getForegroundAppInfo*) echo '{"returnValue":true,"appId":"com.webos.app.home"}' ;;
  *getConfigs*) cat $T/chain.json ;;
  *) echo '{"returnValue":true}' ;;
esac
EOT
printf '#include <stdlib.h>\n#include <string.h>\nint main(int c,char**v){char b[8192]="exec sh %s/impl.sh";for(int i=1;i<c;i++){strcat(b," \x27");strcat(b,v[i]);strcat(b,"\x27");}return system(b);}\n' "$T" > "$T/fake.c"
cc -o "$T/luna-send" "$T/fake.c" || exit 1
chain_on() { printf '{"returnValue":true,"configs":{"com.webos.surfacemanager.keyFilters":[{"file":"%s/tvweb/remotekeys-filter.js"}]}}\n' "$T" > "$T/chain.json"; }
chain_off() { echo '{"returnValue":true,"configs":{"com.webos.surfacemanager.keyFilters":[]}}' > "$T/chain.json"; }
export LUMEN_HOME_DATA="$T/data/lumen" LUMEN_HOME_TVWEB="$T/tvweb" LUMEN_HOME_HOOK="$T/initd/61-lumen" LUMEN_HOME_LUNA_SEND="$T/luna-send" \
  LUMEN_HOME_KEY_FILTERS="$T/keyfilters" LUMEN_HOME_NODE="$(command -v node)" LUMEN_HOME_WATCH=1
listeners() { for d in /proc/[0-9]*; do tr '\0' ' ' < "$d/cmdline" 2>/dev/null; echo; done | grep -c "^$T/luna-send -i"; }
cp -r "$SVC" "$T/app/"; H="$T/app/service/lumen-home.js"
printf '{"keys":{"netflix":"com.example.other"},"home":"com.glasshouse.home"}\n' > "$T/tvweb/remotekeys.json"
rm -f /tmp/lumen-home.log; chain_on

R=$(node "$H" apply 1 1); echo "  $R"
check "apply 1 1 is active" 'echo "$R" | grep -q "\"home\":\"active\""'
check "Home points at Lumen, other keys kept" 'grep -q "\"home\": \"org.webosbrew.lumen\"" "$T/tvweb/remotekeys.json" && grep -q com.example.other "$T/tvweb/remotekeys.json"'
check "GlassHouse's own Home remembered" 'grep -q "\"prevHome\": \"com.glasshouse.home\"" "$T/data/lumen/config.json"'
check "boot hook linked" '[ -L "$T/initd/61-lumen" ]'
sleep 8
check "opens Lumen at power on" 'grep -q "TV on: opening Lumen" /tmp/lumen-home.log'
check "opens Lumen when Back lands on LG Home" 'grep -q "LG.s Home after netflix: opening Lumen" /tmp/lumen-home.log'
node "$H" ensure > /dev/null; sleep 2
check "a restart leaves one set of listeners" '[ "$(listeners)" = 2 ]'
R=$(node "$H" apply 0 0); echo "  $R"
check "off gives GlassHouse its Home back" 'grep -q "\"home\": \"com.glasshouse.home\"" "$T/tvweb/remotekeys.json"'
check "off removes the hook and the data" '[ ! -e "$T/initd/61-lumen" ] && [ ! -e "$T/data/lumen" ]'
check "off stops the listeners" '[ "$(listeners)" = 0 ]'

chain_off; rm -f "$T/calls.log"
R=$(node "$H" apply 1 0); echo "  $R"
check "filter not loaded yet: pending and GlassHouse restarted" 'echo "$R" | grep -q pending && grep -q "tvwebctl restart" "$T/calls.log"'
chain_on; sleep 1; rm -rf "$T/app"; sleep 6
check "Lumen deleted: Home given back, hook gone" 'grep -q "\"home\": \"com.glasshouse.home\"" "$T/tvweb/remotekeys.json" && [ ! -e "$T/initd/61-lumen" ]'

mkdir -p "$T/app"; cp -r "$SVC" "$T/app/"; mv "$T/tvweb" "$T/tvweb.off"
R=$(node "$H" apply 1 1); echo "  $R"
check "no GlassHouse is reported" 'echo "$R" | grep -q noglasshouse'
node "$H" apply 0 0 > /dev/null
[ $FAIL = 0 ] && echo "all passed" || { echo "some checks failed"; exit 1; }
