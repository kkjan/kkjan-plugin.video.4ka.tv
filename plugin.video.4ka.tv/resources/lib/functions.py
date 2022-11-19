import sys
import os
import resources.lib.cls4katv as cls4katv
from resources.lib.logger import *
import xbmc
import xbmcaddon
import xbmcvfs
from contextlib import contextmanager

ADDON = xbmcaddon.Addon()


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
    _addon = xbmcaddon.Addon('plugin.video.4ka.tv')
    _addon.openSettings()
    #xbmc.executebuiltin( "Dialog.Close(busydialognocancel)" )
    log('Update ended-from settings')
    ADDON.openSettings()






