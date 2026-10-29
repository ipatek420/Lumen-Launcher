#!/usr/bin/env python3
"""Build Halcyon from src/halcyon.html.

  python3 build.py            -> webos/index.html with bundled fonts (+ appinfo version)
  python3 build.py --package  -> also dist/org.webosbrew.halcyon_<ver>_all.ipk via ares-package
"""
import json, re, shutil, subprocess, sys, pathlib
VERSION = '1.1.0'
ROOT = pathlib.Path(__file__).resolve().parent
FONTS = [('fraunces', 300, 'normal'), ('fraunces', 300, 'italic'), ('fraunces', 400, 'normal'),
         ('manrope', 400, 'normal'), ('manrope', 500, 'normal'), ('manrope', 600, 'normal'), ('manrope', 700, 'normal')]

out = ROOT/'webos'/'fonts'
out.mkdir(parents=True, exist_ok=True)
faces = ''
for fam, w, style in FONTS:
    name = '%s-latin-%d-%s.woff2' % (fam, w, style)
    src = ROOT/'node_modules'/'@fontsource'/fam/'files'/name
    if src.exists():
        shutil.copyfile(src, out/name)
    elif not (out/name).exists():
        sys.exit('missing font %s: run npm install first' % name)
    faces += "@font-face{font-family:'%s';font-weight:%d;font-style:%s;font-display:swap;src:url(fonts/%s) format('woff2')}\n" % (fam.capitalize(), w, style, name)

src = (ROOT/'src'/'halcyon.html').read_text()
src = re.sub(r'<!--FONTS-->.*?<!--/FONTS-->', '<style>\n'+faces+'</style>', src, flags=re.S)   # Google Fonts link -> bundled fonts
i = src.index('<div id="stage"')
html = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'+src[:i]+'</head>\n<body>\n'+src[i:]+'\n</body>\n</html>\n'
(ROOT/'webos'/'index.html').write_text(html)

info_path = ROOT/'webos'/'appinfo.json'
info = json.loads(info_path.read_text()) if info_path.exists() else {}
info.update({'id': 'org.webosbrew.halcyon', 'version': VERSION, 'vendor': 'Halcyon', 'type': 'web', 'main': 'index.html',
             'title': 'Halcyon', 'icon': 'icon.png', 'largeIcon': 'largeIcon.png', 'bgColor': '#05070d', 'iconColor': '#1a1d44',
             'resolution': '1920x1080', 'disableBackHistoryAPI': True, 'handlesRelaunch': True, 'transparent': False,
             'requiredPermissions': ['applications', 'applications.launcher']})
info_path.write_text(json.dumps(info, indent=2)+'\n')
print('built webos/index.html, version', VERSION)

if '--package' in sys.argv:
    ares = shutil.which('ares-package') or str(ROOT/'node_modules'/'.bin'/'ares-package')
    subprocess.run([ares, str(ROOT/'webos'), '-o', str(ROOT/'dist'), '--no-minify', '-e', 'README.md'], check=True)
