import json
import time
from resources.lib.logger import *


class IPTVSimpleHelper:

    need_restart=False
    def __init__(self):
        """Init"""

    @classmethod
    def iptv_simple_restart(cls):
        #test if iptv simple running
        is_playingtv=xbmc.getCondVisibility('Pvr.IsPlayingTv')
        is_playingRadio=xbmc.getCondVisibility('Pvr.IsPlayingRadio')
        is_recording=xbmc.getCondVisibility('Pvr.IsPlayingRadio')
        if  (is_playingtv or is_playingRadio or is_recording):
            cls.need_restart=True
            logDbg("IPTVSimple restart postpone")
        else:
            logDbg("IPTVSimple restart start")
            ret=xbmc.getCondVisibility("System.AddonIsEnabled(pvr.iptvsimple)")
            logDbg(ret)
            if ret:
                json_query =json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": {"addonid": "pvr.iptvsimple", "enabled":false}, "id": 0} '))
                logDbg(json.dumps(json_query))
            time.sleep(5)
            json_query =json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": {"addonid": "pvr.iptvsimple", "enabled":true}, "id": 0} '))
            logDbg(json.dumps(json_query))
            logDbg("IPTVSimple restart finished")
            cls.need_restart=False
            return cls.need_restart
