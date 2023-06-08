import sys
import os
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
from urllib.parse import urlparse
from urllib.parse import parse_qsl
from uuid import getnode as get_mac
import resources.lib.cls4katv_v2 as C_4KATV
import resources.lib.logger as logger
from resources.lib.functions import *
import routing
from urllib.parse import quote, quote_plus, unquote_plus
import json
import datetime
import unicodedata
import subprocess
#CAHCE
try:
   import StorageServer
except:
   import storageserverdummy as StorageServer

cache = StorageServer.StorageServer("plugin.video.4ka.tv", 1) 
#cache.dbg = True

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
_datapath_ = xbmcvfs.translatePath( _addon.getAddonInfo('profile'))

if not _username_ or not _password_:
    not_usr_pwd_notice = xbmcgui.Dialog()
    not_usr_pwd_notice.ok(_addon.getLocalizedString(30601),_addon.getLocalizedString(30065))
    _addon.openSettings()

if not _device_token_:
    notify(_addon.getLocalizedString(30066),True)
    _addon.openSettings()


def get_content(id,isSeries=False,q=None):
    logger.log("Reading content ..."+str(_handle))
    try:
        if isSeries==True:
            cont= cache.cacheFunction(_4katv.get_content,id,True,q)
            #cont= _4katv.get_content(id,True,q)
        else:
            cont= cache.cacheFunction(_4katv.get_content,id,False,q)
            #cont= _4katv.get_content(id,False,q)
        for subcat in cont:
            list_item = xbmcgui.ListItem(label=subcat['name'])
            art={'icon': subcat['img'],
                'thumb': subcat['img'],
                'poster': subcat['img'],
                'fanart': subcat['img']}
            list_item.setArt(art)
            info={'title': subcat['name'],
                 'genre': subcat['genre'],
                  'plot':subcat['info'],
                  'year':subcat['year'],
                 'dateadded':subcat['date']}
            list_item.setInfo('video', info)
       
            if subcat['series']==0 or isSeries:
                isFolder=False 
                url = router.url_for(play4kaarchive,id=subcat['ch_id'],start=subcat['start'],end=subcat['end'])
            else:
               isFolder=True
               url = router.url_for(getepisodes,id=subcat['br_id'])
            list_item.setProperty('IsPlayable', 'true')
            commands=[]
           # rs='XBMC.RunScript('+_addon.getAddonInfo('id')+", get_detail_info"+', '+str(subcat['broadcast_id'])+")"
           # commands.append(('Info', rs))
           # list_item.addContextMenuItems(commands,False)
            if isFolder==False:
                data={}
                data['info']=info
                data['art']=art
                fname_base=sanitize_filename(subcat['name'])
                logDbg('Create fname_base type: %s' %(type(fname_base)))
                #fname_base=unicodedata.normalize('NFKD', fname_base).encode('ascii','ignore').decode() 
                urlrec=router.url_for(recw,id=subcat['ch_id'],start=subcat['start'],end=subcat['end'],fname_base=fname_base,jsoninfo=json.dumps(data))
                list_item.addContextMenuItems([(_addon.getLocalizedString(30074),'RunPlugin(%s)'% (urlrec))])
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
        for channel in _4katv.get_channels_live(type):
            list_item = xbmcgui.ListItem(label=channel['name'],)
            art={'icon': "DefaultVideo.png",
                'thumb': channel['tvg-logo'],
                'poster':channel['img'],
                'fanart':channel['img']}
            list_item.setArt(art)
            plot=channel['start']+' - '+channel['end'] + '[CR]'
            plot+=channel['plot']+'[CR]'+'[CR]'
            plot+='[COLOR blue][B]'+_addon.getLocalizedString(30067)+'[/B][/COLOR] '+channel['next_prg_name']+' '+channel['next_prg_start']+' - '+channel['next_prg_end']+'[CR]'
            title= channel['name']+': [B]'+channel['prg_name']+'[/B] '+channel['start']+' - '+channel['end'] + '[CR]'
            info= {'title':title,
                   'genre': channel['genre'],
                   'year': channel['year'],
                   'plot':plot}
            list_item.setInfo('video',info)
            url = router.url_for(playitem, channel['content_source'].replace('?','%')) #need replace ? cause router plugin
      
            list_item.setProperty('IsPlayable', 'true')
            data={}
            data['info'] =info
            data['art'] =art
            name=channel['prg_name']+' - '+channel['name']+'- '+channel['start']+' - '+str(datetime.timedelta(seconds=(int(channel['timestamp_end'])-int(channel['timestamp_start']))))
            data['info']['title']=name
            fname_base=sanitize_filename(name)
            #fname_base=unicodedata.normalize('NFKD', fname_base).encode('ascii','ignore').decode() 
            urlrec=router.url_for(recw,id=channel['ch_id'],start=channel['timestamp_start'],end=channel['timestamp_end'],fname_base=fname_base,jsoninfo=json.dumps(data))
            list_item.addContextMenuItems([(_addon.getLocalizedString(30074),'RunPlugin(%s)'% (urlrec))])
            
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

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30061))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(listchannelstv)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30062))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(listchannelradio)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30063))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(listsubcategories)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30075))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(recordings)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_NONE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

@router.route('/listsubcategories')   
def listsubcategories():
    logger.log("Reading subcategories ..."+str(_handle))
    try:
        list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30064))
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
                                        'genre': subcat['name']})
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
    keyboard = xbmc.Keyboard('', _addon.getLocalizedString(30064))
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        txt = keyboard.getText()
        get_content(0,False,txt)
    else:
        listsubcategories()

@router.route('/play4kaarchive/<id>/<start>/<end>')
def play4kaarchive(id,start,end):
    try:
       url=_4katv.get_4KATV_stream(int(id),start,end)
    except C_4KATV.DeviceNotAuthorizedToPlayException as e:
        notify(e.detail,True)
        logger.logErr(e.detail)
    playitem(url)
    listcategories()
         
         
@router.route('/playitem/<path:url>')
def playitem(url):

    """
    Play a video by the provided path.
    :param path: Fully-qualified video URL
    :type path: str
    """
    url=url.replace('%','?')
    # Create a playable item with a path to play.
    logger.logDbg("Playing channel ...   playitem: "+url)

    play_item = xbmcgui.ListItem(path=url)

    # based on example from https://forum.kodi.tv/showthread.php?tid=330507
    
    # play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
    # play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    # play_item.setMimeType('application/dash+xml')
    # play_item.setContentLookup(False)

    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)


    

@router.route('/recw/<id>/<start>/<end>/<fname_base>')
def recw(id,start,end,fname_base=None):
    jsoninfo=router.args['jsoninfo'][0]

    try:
       url=quote(_4katv.get_4KATV_stream(int(id),start,end))
    except C_4KATV.DeviceNotAuthorizedToPlayException as e:
        notify(e.detail,True)
        logger.logErr(e.detail)

    ffmpeg_path=ffmpeg_location()
    save_path=_addon.getSettingString('save_path')
    fname_ext="."+_addon.getSettingString('fname_ext')
    ffmpeg_additional_settings=_addon.getSettingString('ffmpeg_additional_settings')
    jsonf=xbmcvfs.File(save_path+fname_base+'.json','w')
    jsonf.write(jsoninfo)
    jsonf.close()
    duration=int(end)-int(start)
    record_script = xbmcvfs.translatePath("special://home/addons/plugin.video.4ka.tv/resources/script/recording.py")
    cmd = 'RunScript(%s,%d,%s,%s,%s,%s,%s,%s)' % (record_script,duration,fname_base,fname_ext,ffmpeg_additional_settings,save_path,ffmpeg_path,url)
    logDbg('Execute script: '+cmd)
    xbmc.executebuiltin(cmd)
    listcategories()

@router.route('/recordings')
def recordings():
    rec_path=_addon.getSettingString('save_path')
    fname_ext="."+_addon.getSettingString('fname_ext')
    dirs, files = xbmcvfs.listdir(rec_path)
    info={}
    art={}
    for file in files:
        data={}
        filename, file_extension = os.path.splitext(file)
        if file_extension in ['.avi','.mp4','.ts',fname_ext]:
            contextmenu=[];
            list_item = xbmcgui.ListItem(label='')
            url=rec_path+file
            if xbmcvfs.exists(rec_path+filename+'.json'):
                jsonf=xbmcvfs.File(rec_path+filename+'.json','r')
                data=json.loads(jsonf.read())
                jsonf.close()
                art=data['art']
                info=data['info']
            else:
                info={}
                art={}
            title=data['info']['title'] if 'info' in data and  'title' in data['info'] else filename
            if xbmcvfs.exists(rec_path+filename+'.pid'):
                label="[COLOR yellow]"+title+"[/COLOR] [COLOR red]"+_addon.getLocalizedString(30076)+"[/COLOR]"
                isPlayable='false'
                url=""
                cancelrecurl=router.url_for(cancelrecord,f=filename)
                contextmenu.append((_addon.getLocalizedString(30085),'RunPlugin(%s)'% (cancelrecurl)))
            else:
                label=title
                isPlayable='true'
                #url = router.url_for(playitem,rec_path+file)
                url=rec_path+file
                list_item.setPath(rec_path+file)
            if 'info' in data and  'title' in data['info']:
                data['info']['title']=label

            list_item.setInfo('video', info)
            list_item.setArt(art)
            list_item.setLabel(label)
            delurl=router.url_for(del_record,f=file)
            contextmenu.append((_addon.getLocalizedString(30077),'RunPlugin(%s)'% (delurl)))
            list_item.addContextMenuItems(contextmenu)
            list_item.setProperty('IsPlayable', isPlayable)
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
            

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_DATEADDED )
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_UNSORTED )
    xbmcplugin.endOfDirectory(_handle)

@router.route('/del_record/<f>')
def del_record(f):
    runDelete = xbmcgui.Dialog().yesno(_addon.getLocalizedString(30078),_addon.getLocalizedString(30079)+"\n"+f)
    if(not runDelete):
        recordings()
        return
    rec_path=_addon.getSettingString('save_path')
    if xbmcvfs.delete(rec_path+f):
        filename, file_extension = os.path.splitext(f)
        xbmcvfs.delete(rec_path+filename+".json")
        xbmcvfs.delete(rec_path+filename+".")
        xbmcvfs.delete(rec_path+f+".cmd.txt")
        xbmcvfs.delete(rec_path+f+".stderr.txt")
        xbmcvfs.delete(rec_path+f+".stdout.txt")
        xbmcvfs.delete(rec_path+filename+".pid")
    else:
        xbmcgui.Dialog().ok(_addon.getLocalizedString(30080),_addon.getLocalizedString(30081)+f)
    url=router.url_for(recordings)
    xbmc.executebuiltin("Container.Refresh(%s)" % url)
    
@router.route('/cancelrecord/<f>')
def cancelrecord(f):
    runCancel = xbmcgui.Dialog().yesno(_addon.getLocalizedString(30086),_addon.getLocalizedString(30087)+"\n"+f)
    if(not runCancel):
        recordings()
        return
    
    rec_path=_addon.getSettingString('save_path')
    pidf=xbmcvfs.File(rec_path+f+".pid",'r')
    pid=pidf.read()
    pidf.close()
    logDbg("Kill PID: "+pid)
    if xbmc.getCondVisibility("system.platform.windows"):
        subprocess.Popen(["taskkill", "/im", pid], shell=True)
    else:
        subprocess.Popen(['kill','-9',pid])
    logDbg("Delete PID: "+rec_path+f+".pid")
    xbmcvfs.delete(rec_path+f+".pid")
    url=router.url_for(recordings)
    xbmc.executebuiltin("Container.Refresh(%s)" % url)


@router.route('/iptvmanager/channels')
def iptvmanager_channels():
    """Return JSON-STREAMS formatted data for all live channels"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(router.args.get('port')[0])
    logDbg('iptvmanager_channels port: %d' %(port))
    IPTVManager(port).send_channels()


@router.route('/iptvmanager/epg')
def iptvmanager_epg():
    """Return JSON-EPG formatted data for all live channel EPG data"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(router.args.get('port')[0])
    logDbg('iptvmanager_epg port: %d' %(port))
    IPTVManager(port).send_epg()

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    
    _4katv=C_4KATV.C_4KATV(_username_, _password_,_device_token_,_device_type_code_,_device_model_,_device_name_,_device_serial_number_,_datapath_,_epg_lang_)
    router.run()

