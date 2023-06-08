# -*- coding: utf-8 -*-
"""IPTV Manager Integration module"""

import json
import socket
import xbmcvfs
import xbmcaddon
import xbmc
import resources.lib.cls4katv_v2 as C_4KATV
import resources.lib.logger as logger

class IPTVManager:
    """Interface to IPTV Manager"""

    def __init__(self, port):
        """Initialize IPTV Manager object"""
        self.port = port
        self._addon = xbmcaddon.Addon()
        self.username = self._addon.getSetting("username")
        self.password = self._addon.getSetting("password")
        self.device_token = self._addon.getSetting("device_token")
        self.device_type_code = self._addon.getSetting("device_type_code")
        self.device_model = self._addon.getSetting("device_model")
        self.device_name = self._addon.getSetting("device_name")
        self.device_serial_number = self._addon.getSetting("device_serial_number")
        self.datapath = xbmcvfs.translatePath(self._addon.getAddonInfo('profile')) 
        self.epg_lang = self._addon.getSetting("epg_lang")
        iptvsimpleaddon = xbmcaddon.Addon('pvr.iptvsimple')
        iptvsimpleaddon.getSetting('musiclibrary.artistsfolder')

        #get Kodi GUI settings for epg days past/future
        json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"epg.pastdaystodisplay"}, "id":1}')
        json_query = json.loads(json_query)
        if 'result' in json_query and 'value' in json_query['result']:
            self.epgdayspast = 24*json_query['result']['value']
        else:
            self.epgdayspast  = 24

        json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":"epg.futuredaystodisplay"}, "id":1}')
        json_query = json.loads(json_query)
        if 'result' in json_query and 'value' in json_query['result']:
            self.epgdaysfuture  = 24*json_query['result']['value']
        else:
            self.epgdaysfuture  = 24

    def via_socket(func):
        """Send the output of the wrapped function to socket"""

        def send(self):
            """Decorator to send over a socket"""
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', self.port))  
            self._4katv=C_4KATV.C_4KATV(self.username, self.password,self.device_token,self.device_type_code,self.device_model,self.device_name,self.device_serial_number,self.datapath,self.epg_lang)          
            try:
                sock.sendall(json.dumps(func(self)).encode())
            finally:
                sock.close()

        return send

    @via_socket
    def send_channels(self):
        """Return JSON-STREAMS formatted python datastructure to IPTV Manager"""
        logger.logDbg('send channel iptvmanager')
        return dict(version=1, streams=self._4katv.get_iptvm_channels())

    @via_socket
    def send_epg(self):
        """Return JSON-EPG formatted python data structure to IPTV Manager"""
        logger.logDbg('send epg iptvmanager')
        return dict(version=1, epg=self._4katv.get_iptvm_epg(self.epgdayspast,self.epgdaysfuture))