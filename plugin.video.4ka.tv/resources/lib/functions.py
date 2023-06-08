import sys
import os
import resources.lib.cls4katv_v2 as cls4katv
from resources.lib.logger import *
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import stat
from contextlib import contextmanager

ADDON = xbmcaddon.Addon()
ADDON = xbmcaddon.Addon('plugin.video.4ka.tv')

@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')


def notify(text, error=False):
        icon = 'DefaultIconError.png' if error else ''
        try:
            text = text.encode("utf-8") if type(text) is unicode else text
            xbmc.executebuiltin('Notification("%s","%s",5000,%s)' % (ADDON.getAddonInfo('name').encode("utf-8"), text, icon))
        except NameError as e:
            xbmc.executebuiltin('Notification("%s","%s",5000,%s)' % (ADDON.getAddonInfo('name'), text, icon))

def refresh():
    #there is nothing because there is service and callback for event OnSettingChange is executed  and update is there
    #xbmc.executebuiltin( "ActivateWindow(busydialognocancel)" )
    log('Update started-from settings')
    #with busy_dialog():
       # update()
    #xbmc.executebuiltin( "Dialog.Close(busydialognocancel)" )
    log('Update ended-from settings')
    ADDON.openSettings()

def android_get_current_appid():
    with open("/proc/%d/cmdline" % os.getpid()) as fp:
        return fp.read().rstrip("\0")

def ffmpeg_location():
    ffmpeg_src = xbmcvfs.translatePath(ADDON.getSettingString('ffmpeg_path'))

    if xbmc.getCondVisibility('system.platform.android'):
        ffmpeg_dst = '/data/data/%s/ffmpeg' % android_get_current_appid()

        if (ADDON.getSettingString('ffmpeg_path') != ADDON.getSettingString('ffmpeg_path_last')) or (not xbmcvfs.exists(ffmpeg_dst) and ffmpeg_src != ffmpeg_dst):
            xbmcvfs.copy(ffmpeg_src, ffmpeg_dst)
            ADDON.setSettingString('ffmpeg_path_last',ADDON.getSettingString('ffmpeg_path'))

        ffmpeg = ffmpeg_dst
    else:
        ffmpeg = ffmpeg_src

    if ffmpeg:
        try:
            st = os.stat(ffmpeg)
            if not (st.st_mode & stat.S_IXUSR):
                try:
                    os.chmod(ffmpeg, st.st_mode | stat.S_IXUSR)
                except:
                    pass
        except:
            pass
    if xbmcvfs.exists(ffmpeg):
        return ffmpeg
    else:
        xbmcgui.Dialog().notification("IPTV Recorder", "ffmpeg exe not found!")

def sanitize_filename(str):
    _quote = {'"': '', '|': '', '*': '', '/': '_', '<': '', ':': '-', '\\': ' ', '?': '', '>': ''}
    for char in _quote:
        str = str.replace(char, _quote[char])
    return str