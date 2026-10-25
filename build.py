#!/usr/bin/env python3
"""Build Lumen from src/launcher.html.

  python3 build.py            -> webos/index.html (+ appinfo version)
  python3 build.py --package  -> also dist/org.webosbrew.lumen_<ver>_all.ipk via ares-package
"""
import json, re, shutil, subprocess, sys, pathlib
VERSION = '2.4.0'
ROOT = pathlib.Path(__file__).resolve().parent

src = (ROOT/'src'/'launcher.html').read_text()
faces = ''.join("@font-face{font-family:'%s';font-weight:%s;font-style:normal;font-display:swap;src:url(fonts/%s-latin-%s-normal.woff2) format('woff2')}\n" % (fam.capitalize(), w, fam, w)
                for fam, ws in (('outfit', (300, 500)), ('figtree', (400, 500, 600))) for w in ws)
src = re.sub(r'<!--FONTS-->.*?<!--/FONTS-->', '<style>\n'+faces+'</style>', src, flags=re.S)   # Google Fonts link -> bundled fonts
i = src.index('<div id="stage"')
html = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'+src[:i]+'</head>\n<body>\n'+src[i:]+'\n</body>\n</html>\n'
(ROOT/'webos'/'index.html').write_text(html)

info = json.loads((ROOT/'webos'/'appinfo.json').read_text())
info.update({'id': 'org.webosbrew.lumen', 'version': VERSION, 'vendor': 'Lumen',
             'requiredPermissions': ['applications', 'applications.launcher']})
(ROOT/'webos'/'appinfo.json').write_text(json.dumps(info, indent=2)+'\n')
print('built webos/index.html, version', VERSION)

if '--package' in sys.argv:
    ares = shutil.which('ares-package') or str(ROOT/'node_modules'/'.bin'/'ares-package')
    subprocess.run([ares, str(ROOT/'webos'), '-o', str(ROOT/'dist'), '--no-minify', '-e', 'README.md'], check=True)
