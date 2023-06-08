import datetime
import time
import requests
import resources.lib.cls4katv_v2 as C_4KATV
from resources.lib.iptvsimplehelper import IPTVSimpleHelper
import resources.lib.progress as progressdialogBG
import resources.lib.logger as logger
import xbmc
import xbmcaddon
from resources.lib.functions import *



class cls4katvMonitor(xbmc.Monitor):
    _addon = None
    _next_update = 0
    _scriptname = None

    def __init__(self):
        xbmc.Monitor.__init__(self)
        self._addon = xbmcaddon.Addon()
        self._scriptname = self._addon.getAddonInfo('name')
        ts = self._addon.getSetting('next_update')
        self._next_update = datetime.datetime.now() if ts == '' else datetime.datetime.fromtimestamp(float(ts))
        logger.logDbg("Get settings next_update: "+self._next_update.strftime("%m/%d/%Y, %H:%M:%S"))
        self._updt_interval=int(self._addon.getSetting('update_interval'))
        self._iptv_simple_restart_ = 'true' == self._addon.getSetting("iptv_simple_restart")



    def __del__(self):
        logger.log('service destroyed')

    def update(self):
        
        result =-1
        pDialog=None
        try:
            log('Update started')
            _generate_playlist = 'true' == self._addon.getSetting("generate_playlist")
            _generate_epg = 'true' == self._addon.getSetting("generate_epg")          
            self._iptv_simple_restart_ = 'true' == self._addon.getSetting("iptv_simple_restart")                 
            _username_ = self._addon.getSetting("username")
            _password_ = self._addon.getSetting("password")
            _device_token_ = self._addon.getSetting("device_token")
            _device_type_code_ = self._addon.getSetting("device_type_code")
            _device_model_ = self._addon.getSetting("device_model")
            _device_name_ = self._addon.getSetting("device_name")
            _device_serial_number_ = self._addon.getSetting("device_serial_number")
            _epghourspast_ = 24* int(self._addon.getSetting("epgdays.past"))
      
            if _epghourspast_<24:
                _epghourspast_=24
            _epghourssfuture_ = 24*int(self._addon.getSetting("epgdays.future"))
            if _epghourssfuture_<24:
                _epghourssfuture_=24
            _epgpath_ = os.path.join(self._addon.getSetting("epgpath"),self._addon.getSetting("epgfile"))
            _playlistpath_ = os.path.join(self._addon.getSetting("playlistpath"),self._addon.getSetting("playlistfile"))
            _datapath_ = xbmcvfs.translatePath(self._addon.getAddonInfo('profile')) 
            _epg_lang_ = self._addon.getSetting("epg_lang")
            _4katv_=C_4KATV.C_4KATV(username=_username_, password=_password_,device_token=_device_token_,device_type_code=_device_type_code_,model=_device_model_,name=_device_name_,serial_number=_device_serial_number_,datapath=_datapath_,epg_lang=_epg_lang_)
            
            if _4katv_.logdevicestartup() ==True:
                pDialog = progressdialogBG.progressdialogBG(self._addon.getLocalizedString(30068),self._addon.getLocalizedString(30068))
                if pDialog is not None:
                    _4katv_.progress = pDialog
                    pDialog.setpercentrange(0,15)
                #_4katv_.save_4KATV_jsons(hourspast=_epghourspast_,hoursfuture=_epghourssfuture_)
                if _generate_playlist:
                    if pDialog is not None:
                        pDialog.setpercentrange(15,40)
                        pDialog.setpozition(0,message=self._addon.getLocalizedString(30069))
                    _4katv_.generateplaylist(playlistpath=_playlistpath_)
                if _generate_epg:
                    if pDialog is not None:
                        pDialog.setpercentrange(40,70)
                        pDialog.setpozition(0,message=self._addon.getLocalizedString(30070))
                    _4katv_.generateepg(epgpath=_epgpath_,hourspast=_epghourspast_,hoursfuture=_epghourssfuture_)
                if self._iptv_simple_restart_ and(_generate_epg or _generate_playlist):
                    if pDialog is not None:
                        pDialog.setpercentrange(70,100)
                        pDialog.setpozition(0,message=self._addon.getLocalizedString(30071))
                    IPTVSimpleHelper.iptv_simple_restart() 
                result=1
                if pDialog is not None:
                    pDialog.setpozition(100, message=self._addon.getLocalizedString(30072))
                    pDialog.close()

            else:
                logDbg('Pairing device:')
                _4katv_.device_token=_4katv_.pairingdevice()
                logDbg("Device token: " +_4katv_.device_token)
                self._addon.setSetting("device_token",_4katv_.device_token)
                if _4katv_.logdevicestartup() ==True:
                    self._addon.setSetting("device_token",_4katv_.device_token)
                    if _generate_playlist:
                        _4katv_.generateplaylist(playlistpath=_playlistpath_)
                    if _generate_epg:
                        _4katv_.generateepg(epgpath=_epgpath_,hourspast=_epghourspast_,hoursfuture=_epghourssfuture_)
                    if self._iptv_simple_restart_ and(_generate_epg or _generate_playlist):
                        IPTVSimpleHelper.iptv_simple_restart() 
                    result=1
            

        except C_4KATV.UserNotDefinedException as e:
            logErr(self._addon.getLocalizedString(e.id))
            notify(self._addon.getLocalizedString(e.id), True)
        except C_4KATV.UserInvalidException as e:
            logErr(self._addon.getLocalizedString(e.id))
            notify(self._addon.getLocalizedString(e.id), True)
        except C_4KATV.TooManyDevicesException as e:
            logErr(self._addon.getLocalizedString(e.id))
            notify(self._addon.getLocalizedString(e.id), True)
        except C_4KATV.PairingException as e:
            logErr(self._addon.getLocalizedString(e.id))
            notify(self._addon.getLocalizedString(e.id), True)
        except C_4KATV._4KATVException as e:
            logErr(self._addon.getLocalizedString(e.id))
            notify(self._addon.getLocalizedString(e.id), True)
        finally:
            if pDialog is not None:
                pDialog.close()

        log('Update ended')
        return result
        
    def onSettingsChanged(self):
        self._addon = xbmcaddon.Addon()  # refresh for updated settings!
        notify(self._addon.getLocalizedString(30703),False)
        if not self.abortRequested():
            try:
                logger.logDbg("Update started onSettingsChanged")
                self._updt_interval=int(self._addon.getSetting('update_interval'))
                
    
                res = self.update()
                if res == 1:
                    notify(self._addon.getLocalizedString(30701),False)
                    self.schedule_next(self._updt_interval * 60 * 60)
                    logger.logDbg("Update finished onSettingsChanged")
                else:
                    self._addon.openSettings();
            except C_4KATV._4KATVException as e:
                logger.logErr(e.detail)
                notify(self._addon.getLocalizedString(e.id), True)

    def schedule_next(self, seconds):
        dt = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        logger.log('Next update %s' % dt)
        self._next_update = dt

   

    def tick(self):
        if  IPTVSimpleHelper.need_restart and self._iptv_simple_restart_ :
            IPTVSimpleHelper.iptv_simple_restart() 

    
        if datetime.datetime.now() > self._next_update:
            try:
                logger.logDbg("Update started from auto scheduller")
                notify(self._addon.getLocalizedString(30703),False)
                self.schedule_next(self._updt_interval * 60 * 60)
                res=self.update()
                logger.logDbg("Update ended from auto scheduller")
                if res==1:
                    notify(self._addon.getLocalizedString(30702),False)
                else:
                    self._addon.openSettings()
            except requests.exceptions.ConnectionError:
                self.schedule_next(60)
                logger.log('Can''t update, no internet connection')
                pass
            except C_4KATV._4KATVException as e:
                logger.logErr(e.detail)
                notify("Unexpected error", True)

    def save(self):
        self._addon.setSetting('next_update', str(time.mktime(self._next_update.timetuple())))
        logger.log('Saving next update %s' % self._next_update)


if __name__ == '__main__':
    monitor = cls4katvMonitor()
    
    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            monitor.save()
            break
        monitor.tick()
