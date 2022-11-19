import json
import time
from resources.lib.logger import *


class IPTVSimple:
    def __init__(self):
        self.need_restart=False
        
    def iptv_simple_restart(self):
        #test if iptv simple running
        is_playingtv=xbmc.getCondVisibility('Pvr.IsPlayingTv')
        is_playingRadio=xbmc.getCondVisibility('Pvr.IsPlayingRadio')
        is_recording=xbmc.getCondVisibility('Pvr.IsPlayingRadio')
        if  (is_playingtv or is_playingRadio or is_recording):
            self.need_restart=True
            logDbg("IPTVSimple restart postpone")
        else:
            logDbg("IPTVSimple restart start")
            if xbmc.getCondVisibility("System.AddonIsEnabled('pvr.iptvsimple')"):
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": {"addonid": "pvr.iptvsimple", "enabled":false}, "id": 1} ')
                json_query = json.loads(json_query)
            time.sleep(5)
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": {"addonid": "pvr.iptvsimple", "enabled":true}, "id": 1} ')
            json_query = json.loads(json_query)
            logDbg("IPTVSimple restart finished")
            self.need_restart=False
            return self.need_restart
