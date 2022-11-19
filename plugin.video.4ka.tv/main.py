import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
from urlparse import urlparse
from urlparse import parse_qsl
from uuid import getnode as get_mac
import  resources.lib.cls4katv as C_4KATV
import  resources.lib.logger as logger
from  resources.lib.functions import *
import routing


#CAHCE
try:
   import StorageServer
except:
   import storageserverdummy as StorageServer

cache = StorageServer.StorageServer("plugin.video.4ka.tv", 1) 


params = False
_addon = xbmcaddon.Addon('plugin.video.4ka.tv')
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])
 
router = routing.Plugin()

_username_ = _addon.getSetting("username")
_password_ = _addon.getSetting("password")
_device_token_ = _addon.getSetting("device_token")
_device_type_code_ = _addon.getSetting("device_type_code")
_device_model_ = _addon.getSetting("device_model")
_device_name_ = _addon.getSetting("device_name")
_device_serial_number_ = _addon.getSetting("device_serial_number")
_epg_lang_ = _addon.getSetting("epg_lang")
_datapath_ = xbmc.translatePath( _addon.getAddonInfo('profile'))

if not _username_ or not _password_:
    not_usr_pwd_notice = xbmcgui.Dialog()
    not_usr_pwd_notice.ok(_addon.getLocalizedString(30601),_addon.getLocalizedString(30064))
    _addon.openSettings()

if not _device_token_:
    notify(_addon.getLocalizedString(30065),True)
    _addon.openSettings()


def get_content(id,isSeries=False,q=None):
    logger.log("Reading content ..."+str(_handle))
    try:
        if isSeries==True:
            cont= cache.cacheFunction(_4katv.get_content,id,True,q)
        else:
            cont= cache.cacheFunction(_4katv.get_content,id,False,q)
        for subcat in cont:
            list_item = xbmcgui.ListItem(label=subcat['name'])
            list_item.setArt({'icon': subcat['img'],
                                'thumb': subcat['img'],
                                'poster': subcat['img'],
                                'fanart': subcat['img']})
            list_item.setInfo('video', {'title': subcat['name'],
                                        'genre': subcat['genre'],
                                        'plot':subcat['info'],
                                        'year':subcat['year'],
                                        'dateadded':subcat['date'],
                                        'mediatype': 'video'})
       
            if subcat['series']==0 or isSeries:
                isFolder=False
                url = router.url_for(play4katv,id=subcat['ch_id'],start=subcat['start'],end=subcat['end'])
            else:
               isFolder=True
               url = router.url_for(getepisodes,id=subcat['br_id'])
            list_item.setProperty('IsPlayable', 'true')
            logger.logDbg('get_content: '+subcat['name']+", url:"+url)
           
            xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder)
        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_DATEADDED )
        xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_UNSORTED )
        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(_handle)
    except C_4KATV.StreamNotResolvedException as e:
        notify(e.detail,True)
        logger.logErr(e.detail)
    return

@router.route('/')
def index():
    listcategories()


@router.route('/listchannelstv')
def listchannelstv():
    logger.log("Reading channels ..."+str(_handle))
    add_live_chanels(type='tv')

@router.route('/listchannelsradio')
def listchannelradio():
    logger.log("Reading channels ..."+str(_handle))
    add_live_chanels(type='radio')
   
def add_live_chanels(type='tv'):
    try:
        for channel in cache.cacheFunction(_4katv.get_channels_live,type):
            list_item = xbmcgui.ListItem(label=channel['name'],)
            list_item.setArt({'icon': "DefaultVideo.png",
                            'thumb': channel['tvg-logo'],
                            'poster':channel['img']})
            plot=channel['start']+' - '+channel['end'] + '[CR]'
            plot+=channel['plot']+'[CR]'+'[CR]'
            plot+='[COLOR blue][B]'+_addon.getLocalizedString(30066)+'[/B][/COLOR] '+channel['next_prg_name']+' '+channel['next_prg_start']+' - '+channel['next_prg_end']+'[CR]'
            title= channel['name']+': [B]'+channel['prg_name']+'[/B] '+channel['start']+' - '+channel['end'] + '[CR]'

            list_item.setInfo('video', {'title':title,
                                        'genre': channel['genre'],
                                        'year': channel['year'],
                                        'plot':plot,
                                        'mediatype': 'video'})
            url = router.url_for(playlive, channel['content_source'].replace('?','%')) #need replace ? cause router plugin

            logger.logDbg("list channels: "+url+' tvg-logo: '+channel['tvg-logo'])
      
            list_item.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_NONE)
        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(_handle)
    except C_4KATV.StreamNotResolvedException as e:
        notify(e.detail,True)
        logger.logErr(e.detail)
    return

@router.route('/listcategories')  
def listcategories():
    logger.log("Settings categories ..."+str(_handle))

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30060))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(listchannelstv)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30061))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(listchannelradio)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30062))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(listsubcategories)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_NONE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

@router.route('/listsubcategories')   
def listsubcategories():
    logger.log("Reading subcategories ..."+str(_handle))
    try:
        list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30063))
        list_item.setArt({'icon': "DefaultAddonsSearch.png",
                                'thumb': "DefaultAddonsSearch.png"})
        url = router.url_for(search)
        list_item.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
        
        for subcat in cache.cacheFunction(_4katv.get_4KATVtags):
            list_item = xbmcgui.ListItem(label=subcat['name'])
            list_item.setArt({'icon': "DefaultVideo.png",
                                'thumb': subcat['img']})
            list_item.setInfo('video', {'title': subcat['name'],
                                        'genre': subcat['name'],
                                        'mediatype': 'video'})
            url = router.url_for(gettagcontent,id=subcat['id_tag'],type=subcat['type'])
            list_item.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_NONE)
        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(_handle)
    except C_4KATV.StreamNotResolvedException as e:
        notify(e.detail,True)
        logger.logErr(e.detail)
    return

@router.route('/getepisodes/<id>') 
def getepisodes(id):
    get_content(id,True)

@router.route('/gettagcontent/<id>')
def gettagcontent(id):
    get_content(id,False)

@router.route('/search')
def search():
    keyboard = xbmc.Keyboard('', _addon.getLocalizedString(30063))
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        txt = keyboard.getText()
        get_content(0,False,txt)
        
@router.route('/playlive/<path:url>')
def playlive(url):
    """
    Play a video by the provided path.
    :param path: Fully-qualified video URL
    :type path: str
    """
    url=url.replace('%','?')
    # Create a playable item with a path to play.
    logger.logDbg("Playing channel ...   playlive: "+url)

    play_item = xbmcgui.ListItem(path=url)

    # based on example from https://forum.kodi.tv/showthread.php?tid=330507
    # play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
    # play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    # play_item.setMimeType('application/dash+xml')
    # play_item.setContentLookup(False)

    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

@router.route('/play4katv/<id>/<start>/<end>')
def play4katv(id,start,end):
    """
    Play a video by the provided path.
    :param path: Fully-qualified video URL
    :type path: str
    """
    # Create a playable item with a path to play.
    logger.logDbg("play_4katv "+str(id)+' start '+str(start)+' end '+str(end))
    url = _4katv.get_4KATV_stream(int(id),start,end)

    logger.log('Playing channel ... '+str(url))

    play_item = xbmcgui.ListItem(path=url)
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)


    # based on example from https://forum.kodi.tv/showthread.php?tid=330507
    # play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
    # play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    # play_item.setMimeType('application/dash+xml')
    # play_item.setContentLookup(False)

    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

@router.route('/iptvmanager/channels')
def iptvmanager_channels():
    """Return JSON-STREAMS formatted data for all live channels"""
    from  resources.lib.iptvmanager import IPTVManager
    port = int(router.args.get('port')[0])
    IPTVManager(port).send_channels()


@router.route('/iptvmanager/epg')
def iptvmanager_epg():
    """Return JSON-EPG formatted data for all live channel EPG data"""
    from  resources.lib.iptvmanager import IPTVManager
    port = int(router.args.get('port')[0])
    IPTVManager(port).send_epg()

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring

    _4katv=C_4KATV.C_4KATV(_username_, _password_,_device_token_,_device_type_code_,_device_model_,_device_name_,_device_serial_number_,_datapath_,_epg_lang_)
    router.run()

