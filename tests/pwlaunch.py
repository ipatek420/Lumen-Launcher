"""Shared Chromium launch options: set LUMEN_CHROMIUM to use a preinstalled browser instead of Playwright's own."""
import os
def opts(**kw):
    exe=os.environ.get('LUMEN_CHROMIUM')
    if exe: kw['executable_path']=exe
    return kw
