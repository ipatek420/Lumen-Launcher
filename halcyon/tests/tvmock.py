"""Shared test setup: a simulated LG TV and a Chromium launcher.

The mock PalmServiceBridge behaves like a real rooted TV: privileged Luna calls made directly are denied
("Denied method call ... for category /"), while the same call through the Homebrew Channel's root exec service
succeeds and comes back as luna-send's stdout. Root `cat` returns files base64-encoded; root `curl` answers from
the CURL table (url substring -> [http code, body])."""
import json, os, base64, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = (ROOT/'webos'/'index.html').as_uri()
SHOTS = ROOT/'tests'/'shots'
SHOTS.mkdir(exist_ok=True)
FIX = ROOT/'tests'/'fixtures'

def opts(**kw):
    """HALCYON_CHROMIUM points the tests at a preinstalled browser (cloud sessions)."""
    exe = os.environ.get('HALCYON_CHROMIUM')
    if exe: kw['executable_path'] = exe
    return kw

def b64(path): return base64.b64encode(open(path, 'rb').read()).decode()

def tv_mock(launch_points, devices, files=None, curl=None):
    return """
window.__calls=[];
(function(){
var LPS=%s, DEVS=%s, FILES=%s, CURL=%s;
function ok(u){
  if(/listLaunchPoints/.test(u)) return {returnValue:true,launchPoints:LPS};
  if(/getAllInputStatus/.test(u)) return {returnValue:true,devices:DEVS};
  return {returnValue:true};
}
window.PalmServiceBridge=function(){ var self=this; this.call=function(uri,p){
  window.__calls.push(uri+' '+p);
  var reply, P=JSON.parse(p);
  if(/hbchannel.service\\/exec$/.test(uri)){
    var c=P.command;
    if(/^cat /.test(c)){ var fp=c.slice(5,-1); reply=FILES[fp]?{returnValue:true,stdoutBytes:FILES[fp]}:{returnValue:false,error:'No such file'}; }
    else if(/^curl /.test(c)){
      var hit=null; for(var k in CURL) if(c.indexOf(k)>-1){ hit=CURL[k]; break; }
      if(!hit) hit=[0,''];
      var post=/-X POST/.test(c);
      reply={returnValue:true,stdoutString:post?String(hit[0]):(hit[1]+'\\n'+hit[0])};
    }
    else { var u=(c.match(/'(luna:[^']+)'/)||[])[1]; reply={returnValue:true,stdoutString:JSON.stringify(ok(u))}; }
  }
  else reply={returnValue:false,errorText:'Denied method call "'+uri.split('/').pop()+'" for category "/"'};
  setTimeout(function(){ self.onservicecallback(JSON.stringify(reply)); },60);
}; };
})();
""" % (json.dumps(launch_points), json.dumps(devices), json.dumps(files or {}), json.dumps(curl or {}))

def root_cmds(calls):
    out = []
    for c in calls:
        if 'hbchannel' in c:
            out.append(json.loads(c.split(' ', 1)[1])['command'])
    return out

def settings_script(st):
    return "localStorage.setItem('halcyon.settings.v1',%s);" % json.dumps(json.dumps(st))
