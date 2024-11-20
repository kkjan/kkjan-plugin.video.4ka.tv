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
import time
import requests

dayBefore=10
#CAHCE
dbg = False
try:
   import StorageServer
except:
   import resources.lib.storageserverdummy as StorageServer

cache = StorageServer.StorageServer("plugin_video_4ka_tv", 1) 


params = False
_addon = xbmcaddon.Addon('plugin.video.4ka.tv')
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])
logDbg(', '.join(sys.argv))

router = routing.Plugin()

_username_ = _addon.getSetting("username")
_password_ = _addon.getSetting("password")
_device_token_ = _addon.getSetting("device_token")
_device_type_code_ = _addon.getSetting("device_type_code")
_device_model_ = _addon.getSetting("device_model")
_device_name_ = _addon.getSetting("device_name")
_device_serial_number_ = _addon.getSetting("device_serial_number")
_all_tags_ = _addon.getSettingBool("all_tags")
_epg_lang_ = _addon.getSetting("epg_lang")
_datapath_ = xbmcvfs.translatePath( _addon.getAddonInfo('profile'))


if not _username_ or not _password_:
    not_usr_pwd_notice = xbmcgui.Dialog()
    not_usr_pwd_notice.ok(_addon.getLocalizedString(30601),_addon.getLocalizedString(30065))
    _addon.openSettings()

if not _device_token_:
    notify(_addon.getLocalizedString(30066),True)
    _addon.openSettings()

def display_content(content):
    logger.log("Reading content ..."+str(_handle))
    datetimeformat=xbmc.getRegion('dateshort').replace('%-', '%').replace('%#', '%') +" "+xbmc.getRegion('time')
    try:
        list_items=[]
        for subcat in content:
            contextMenu=[]
            list_item=createlistitem(subcat)
            if subcat['programme']['series']==0 or subcat['programme']['playable']:
                isFolder=False
                start=datetime.datetime.fromtimestamp(int(subcat['programme']['start'])).strftime(datetimeformat)           
                subtitle=": "+subcat['programme']['sub_title']+" " if subcat['programme']['sub_title'] else ""
                title=subcat['programme']['title']+subtitle+' - '+subcat['channel']['channelname']+'- '+start+' - '+str(datetime.timedelta(seconds=subcat['programme']['duration']))
                url = router.url_for(play4kaarchive,id=subcat['programme']['channelid'],start=subcat['programme']['start'],stop=subcat['programme']['stop'])
                list_item.setProperty('IsPlayable', 'true')
            else:
                isFolder=True
                url = router.url_for(getepisodes,id=subcat['programme']['broadcast_id'])
                title="[I]"+subcat['programme']['title']+' - '+subcat['channel']['channelname']+"[/I]"
                list_item.setProperty('IsPlayable', 'false')

            list_item.setLabel(title)
            vt=list_item.getVideoInfoTag()
            vt.setTitle(title)
           # rs='XBMC.RunScript('+_addon.getAddonInfo('id')+", get_detail_info"+', '+str(subcat['broadcast_id'])+")"
           # commands.append(('Info', rs))
           # list_item.addContextMenuItems(commands,False)
            if isFolder==False:
                #fname_base=unicodedata.normalize('NFKD', fname_base).encode('ascii','ignore').decode()
                urlrec=router.url_for(recw,id=subcat['programme']['broadcast_id'])
                contextMenu.append((_addon.getLocalizedString(30074),'RunPlugin({})'.format(urlrec)))
            
            urlinfo=router.url_for(iteminfo,id=subcat['programme']['broadcast_id'],isFolder=isFolder)
            
            contextMenu.append(('Info','RunPlugin({})'.format(urlinfo)))
            list_item.addContextMenuItems(contextMenu)
            list_items.append((url,list_item,isFolder),)
        
        xbmcplugin.addDirectoryItems(_handle, list_items)

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

@router.route('/refresh')
def refresh():
    _addon.openSettings()

@router.route('/listchannelstv')
def listchannelstv():
    logger.log("Reading channels ..."+str(_handle))
    add_live_chanels(type='tv')

@router.route('/listchannelsradio')
def listchannelradio():
    logger.log("Reading channels ..."+str(_handle))
    add_live_chanels(type='radio')
   
def add_live_chanels(type='tv'):
    datetimeformat=xbmc.getRegion('dateshort').replace('%-', '%').replace('%#', '%') +" "+xbmc.getRegion('time')
    list_items=[]
    try:
        for channel in _4katv.get_channels_live(type):
            contextMenu=[]
            start=datetime.datetime.fromtimestamp(int(channel['programme']['start'])).strftime(datetimeformat)
            stop=datetime.datetime.fromtimestamp(int(channel['programme']['stop'])).strftime(datetimeformat)
            next_start=datetime.datetime.fromtimestamp(int(channel['programme']['next_prg_start'])).strftime(datetimeformat)
            next_stop=datetime.datetime.fromtimestamp(int(channel['programme']['next_prg_stop'])).strftime(datetimeformat)
            plot=start+' - '+stop + '[CR]'
            plot+=channel['programme']['plot']+'[CR]'+'[CR]'
            plot+='[COLOR blue][B]'+_addon.getLocalizedString(30067)+'[/B][/COLOR] '+channel['programme']['next_prg_name']+' '+next_start+' - '+next_stop+'[CR]'
            subtitle=" "+channel['programme']['sub_title']+" " if channel['programme']['sub_title'] else " "
            title= channel['channel']['channelname']+': [B]'+channel['programme']['title']+'[/B]:'+subtitle+start+' - '+stop + '[CR]'

            url = router.url_for(playitem, channel['programme']['content_source'].replace('?','%')) #need replace ? cause router plugin
      
            if type=='tv':
                urlrec=router.url_for(recw,id=channel['programme']['broadcast_id'])
                contextMenu.append((_addon.getLocalizedString(30074),'RunPlugin({})'.format(urlrec)))

            urlinfo=router.url_for(iteminfo,id=channel['programme']['broadcast_id'],isFolder=False)
            contextMenu.append(('Info','RunPlugin({})'.format(urlinfo)))

            channel['programme']['title']=title
            channel['programme']['plot']=plot
            list_item = createlistitem(channel)
            list_item.setProperty('IsPlayable', 'true')
            list_item.addContextMenuItems(contextMenu)
            list_items.append((url,list_item,False),)
            
        xbmcplugin.addDirectoryItems(_handle,list_items)
        
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

@router.route('/recordings')  
def recordings():

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30090))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(allrecordings)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30091))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(dirrecodingsview,dir=None)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30093))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(recordingutility)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30092))
    list_item.setArt({'icon': 'DefaultFolder.png'});
    url = router.url_for(maintenancerecordings)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_NONE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


@router.route('/listsubcategories')   
def listsubcategories():
    logger.log("Reading subcategories ..."+str(_handle))
    try:
        list_items=[]
        list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30064))
        list_item.setArt({'icon': "DefaultAddonsSearch.png",
                                'thumb': "DefaultAddonsSearch.png"})
        url = router.url_for(search)
        list_item.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

        list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30109))
        list_item.setArt({'icon': "DefaultAddonsSearch.png",
                                'thumb': "DefaultAddonsSearch.png"})
        url = router.url_for(browseEPGArchivechannels)
        list_item.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

        
        for subcat in cache.cacheFunction(_4katv.get_4KATVtags,_all_tags_):    
            list_item = xbmcgui.ListItem(label=subcat['name'])
            list_item.setArt({'icon': "DefaultVideo.png",
                                'thumb': subcat['img']})
        
            vt=list_item.getVideoInfoTag()
            vt.setTitle(subcat['name'])
   


            url = router.url_for(gettagcontent,id=subcat['id_tag'],type=subcat['type'])
            list_item.setProperty('IsPlayable', 'true')
            list_items.append((url,list_item,True),)
        xbmcplugin.addDirectoryItems(_handle, list_items)
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
    content= cache.cacheFunction(_4katv.get_episodesdes,id)
    #content= _4katv.get_episodesdes(id)
    display_content(content)

@router.route('/gettagcontent/<id>')
def gettagcontent(id):
    content=cache.cacheFunction(_4katv.get_tagcontent,id)
    #content=_4katv.get_tagcontent(id)
    display_content(content)

@router.route('/search')
def search():
    keyboard = xbmc.Keyboard('', _addon.getLocalizedString(30064))
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        q = keyboard.getText()
        content=_4katv.get_search_result(q)
        display_content(content)
    else:
        listsubcategories()

@router.route('/iteminfo/<id>/<isFolder>')  
def iteminfo(id,isFolder):
    info=_4katv.get_broadcastdetail(id)
    logDbg("isFolder: {}".format(isFolder))
    logDbg("PLOT1:{}".format(info['programme']['plot']))
    if isFolder=='True':
        url = router.url_for(getepisodes,id=id)
        info['programme']['plot']=info['programme']['description_show']
        IsPlayable="false"
    else:
        url = router.url_for(play4kaarchive,id=info['channel']['channelid'],start=info['programme']['start'],stop=info['programme']['stop'])
        IsPlayable="true"

    logDbg("PLOT2:{}".format(info['programme']['plot']))
    li=createlistitem(info)
    li.setPath(url)
    li.setProperty('IsPlayable',IsPlayable)
    dialog=xbmcgui.Dialog()
    dialog.info(li)
    
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


@router.route('/play4kaarchive/<id>/<start>/<stop>')
def play4kaarchive(id,start,stop):
    try:
       url=_4katv.get_4KATV_stream(int(id),start,stop)
       logger.logDbg(url)
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


    

@router.route('/recw/<id>')
def recw(id):
    data =_4katv.get_broadcastdetail(id)
    start=int(data['programme']['start'])
    stop=int(data['programme']['stop'])
    id=data['channel']['channelid']
    try:
       url=quote(_4katv.get_4KATV_stream(int(id),start,stop))
    except C_4KATV.DeviceNotAuthorizedToPlayException as e:
        notify(e.detail,True)
        logger.logErr(e.detail)

    ffmpeg_path=ffmpeg_location()
    save_path=_addon.getSettingString('save_path')
    year=" ({})".format(data['programme']['year']) if data['programme']['year'] else ""
    if 'programme' in data:
        fname_base=createfilename(data)
    if data['programme']['series']==True:
        #Series
        save_path=os.path.join(save_path,"Series",sanitize_str_for_path(data['programme']['title']+year))
        if(data['programme']['series_number']):
            save_path=os.path.join(save_path,"Session {:02d}".format(data['programme']['series_number']))
        xbmcvfs.mkdirs(save_path)
    elif data['programme']['movie']:
        save_path=os.path.join(save_path,"Movies") #,fname_base
        xbmcvfs.mkdir(save_path)
    else:
        save_path=os.path.join(save_path,"Others",fname_base)
        xbmcvfs.mkdir(save_path)


   
    fname_ext="."+_addon.getSettingString('fname_ext')
    ffmpeg_additional_settings=_addon.getSettingString('ffmpeg_additional_settings')
    jsonf=xbmcvfs.File(os.path.join(save_path,fname_base+'.json'),'w')
    jsonf.write(json.dumps(data))
    jsonf.close()

    #Download artwork
    if(data['programme']['img']):
        response = requests.get(data['programme']['img'])
        imgf=xbmcvfs.File(os.path.join(save_path,fname_base+'-fanart.jpg'),'w')
        imgf.write(response.content)
        imgf.close()
    if(data['programme']['photo']):
        response = requests.get(data['programme']['photo'])
        imgf=xbmcvfs.File(os.path.join(save_path,fname_base+'-banner.jpg'),'w')
        imgf.write(response.content)
        imgf.close()
    if(data['programme']['poster']):
        response = requests.get(data['programme']['poster'])
        imgf=xbmcvfs.File(os.path.join(save_path,fname_base+'-poster.jpg'),'w')
        imgf.write(response.content)
        imgf.close()
    duration=stop-start
    record_script = xbmcvfs.translatePath("special://home/addons/plugin.video.4ka.tv/resources/script/recording.py")
    cmd = 'RunScript({},{},{},{},{},{},{},{})'.format(record_script,duration,fname_base,fname_ext,ffmpeg_additional_settings,save_path,ffmpeg_path,url)
    logDbg('Execute script: '+cmd)
    xbmc.executebuiltin(cmd)
    listcategories()

def createlistitemsforfiles(_addon,files,retpath=None):
    list_items=[]
    art={}
    datetimeformat=xbmc.getRegion('dateshort').replace('%-', '%').replace('%#', '%') +" "+xbmc.getRegion('time')
    channels=_4katv.get_channels_live() # needed for convert
    for file in files:
        logDbg(file)
        data={}
        dir=os.path.dirname(file)
        full_file_name=os.path.basename(file)
        filename = os.path.splitext(full_file_name)[0]
        
        contextmenu=[];
        st = xbmcvfs.Stat(file)

        list_item = xbmcgui.ListItem(label='')
        url=file

        art={}
        label=filename
        isPlayable='true'
        vt=list_item.getVideoInfoTag()
        if xbmcvfs.exists(os.path.join(dir,filename+'.json')):
            jsonf=xbmcvfs.File(os.path.join(dir,filename+'.json'),'r')
            data=json.loads(jsonf.read())
            jsonf.close()
            label=filename
            if 'programme' in data:
                
                start_local=datetime.datetime.fromtimestamp(int(data['programme']['start'])).strftime(datetimeformat)
                subtitle=": "+data['programme']['sub_title'] if data['programme']['sub_title'] else ""
                name=data['programme']['title']+subtitle+' - '+data['channel']['channelname']+': '+start_local+' - '+str(datetime.timedelta(seconds=data['programme']['duration']))
                if xbmcvfs.exists(os.path.join(dir,filename+'.pid')):
                    label="[COLOR yellow]"+name+"[/COLOR] [COLOR red]"+_addon.getLocalizedString(30076)+"[/COLOR]"
                    isPlayable='false'
                    url=""
                    encf=quote_plus(file)
                    if(retpath):
                        cancelrecurl=router.url_for(cancelrecord,retpath=retpath,encfp=encf)
                        contextmenu.append((_addon.getLocalizedString(30085),'RunPlugin({})'.format(cancelrecurl)))
                else:
                    label=name
                    isPlayable='true'
                    #url = router.url_for(playitem,rec_path+file)
                    url=file
                    list_item.setPath(file)
                
                art['icon']=data['programme']['img']
                art['thumb']=data['programme']['img']
                art['poster']=data['programme']['poster'] if 'poster' in data['programme'] and data['programme']['poster'] else data['programme']['img']
                art['fanart']=data['programme']['photo'] if 'photo' in data['programme'] and  data['programme']['photo'] else data['programme']['img']

            else: #OLD FORMAT START
                art= data['art'] if 'art' in data else art
                title=data['info']['title'] if 'info' in data and  'title' in data['info'] else filename
                if xbmcvfs.exists(os.path.join(dir,filename+'.pid')):
                    label="[COLOR yellow]"+title+"[/COLOR] [COLOR red]"+_addon.getLocalizedString(30076)+"[/COLOR]"
                    isPlayable='false'
                    url=""
                    
                    encf=quote_plus(file)
                    if(retpath):
                        cancelrecurl=router.url_for(cancelrecord,retpath=retpath,encfp=encf)
                        contextmenu.append((_addon.getLocalizedString(30085),'RunPlugin({})'.format(cancelrecurl)))
                else:
                    label=title
                    isPlayable='true'
                    #url = router.url_for(playitem,rec_path+file)
                    url=file
                    list_item.setPath(file)
                
                data['info']['title'] =title
                data=convertjsininfofromoldformat(data,channels)
                '''
                #convert to new format
                
                jsonf=xbmcvfs.File(os.path.join(dir,filename+'.json'),'w')
                json.dump(data,jsonf)
                jsonf.close()
                # end k=convert to new format
                '''
             
                #END OLD FORMAT 
            if(data['programme']['episode_number']):
                vt.setEpisode(data['programme']['episode_number'])
            if(data['programme']['series_number']):
                vt.setSeason(data['programme']['series_number'])
            vt.setGenres(data['programme']['genres'])
            vt.setPlot(data['programme']['plot'])
            if(data['programme']['year']):
                vt.setYear(data['programme']['year'])
            vt.setDateAdded(data['programme']['dateadded'])

            if 'actors' in data['programme'] and data['programme']['actors']:
                actors=[]
                for actor in data['programme']['actors']:
                    act=xbmc.Actor(actor)
                    actors.append(act)
                vt.setCast(actors)

            if 'directors' in data['programme'] and data['programme']['directors']:
                vt.setDirectors(data['programme']['directors'])
                

        file_size=get_hr_filesize(st.st_size())
        label=label+' [I]'+_addon.getLocalizedString(30089)+': '+file_size+'[/I]'
                
        vt.setTitle(label)
        
        list_item.setArt(art)
        list_item.setLabel(label)
        #delurl=router.url_for_path('/del_record?ret_path='+ret_path+'&f='+file)
        encf=quote_plus(file)
        if(retpath):
            delurl=router.url_for(del_record,retpath=retpath,encfp=encf)
            logDbg('delurl: '+delurl)
            contextmenu.append((_addon.getLocalizedString(30077),'RunPlugin({})'.format(delurl)))
            ecp2liburl=router.url_for(exportrecordtolibrary,f=encf)
            contextmenu.append((_addon.getLocalizedString(30108),'RunPlugin({})'.format(ecp2liburl)))
            list_item.addContextMenuItems(contextmenu)

        list_item.setProperty('IsPlayable', isPlayable)
        list_items.append((url,list_item,False),)
        
    return list_items

@router.route('/allrecordings')
def allrecordings():
    rec_path=_addon.getSettingString('save_path')
    fname_ext="."+_addon.getSettingString('fname_ext')
    #dirs, files = xbmcvfs.listdir(rec_path)
    files=find_files(rec_path,['.avi','.mp4','.ts',fname_ext])
    list_items=createlistitemsforfiles(_addon,files,'allrecordings')  
    xbmcplugin.addDirectoryItems(_handle,list_items)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_DATEADDED )
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_UNSORTED )
    xbmcplugin.endOfDirectory(_handle)

@router.route('/dirrecodingsview/<path:dir>')
def dirrecodingsview(dir):  
    logDbg('dirrecodingsview dir: '+dir) 
    if(dir == 'None' ):
        path=_addon.getSettingString('save_path')   
    else:
        path=dir
    logDbg('dirrecodingsview path: '+path) 
    dirs, files = xbmcvfs.listdir(path)
    for dir in dirs: 
        logDbg('dirrecodingsview: '+dir) 
        list_item = xbmcgui.ListItem(label=dir)
        list_item.setArt({'icon': "DefaultFolder.png"})
        vt=list_item.getVideoInfoTag()
        vt.setTitle(dir)
        url = router.url_for(dirrecodingsview,dir=os.path.join(path,dir))
        list_item.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
        
    
    fname_ext="."+_addon.getSettingString('fname_ext')
    files= [os.path.join(path,f) for f in files ]
    fs= [f for f in files if os.path.splitext(f)[1] in ['.avi','.mp4','.ts',fname_ext]]
    list_items=createlistitemsforfiles(_addon,fs,'dirrecodingsview')
    xbmcplugin.addDirectoryItems(_handle,list_items)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_DATEADDED )
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_UNSORTED )
    xbmcplugin.endOfDirectory(_handle)
    return

    
@router.route('/del_record/<retpath>/<encfp>')
def del_record(retpath,encfp):
    f=unquote_plus(encfp)
    logDbg('del arguments: '+f+', '+retpath)
    dir=os.path.dirname(f)
    full_file_name=os.path.basename(f)
    filename = os.path.splitext(full_file_name)[0]

    runDelete = xbmcgui.Dialog().yesno(_addon.getLocalizedString(30078),_addon.getLocalizedString(30079)+"\n"+f)
    if(not runDelete):
        return
 
    logDbg("test recording: "+os.path.join(dir,filename+".pid"))
    if(xbmcvfs.exists(os.path.join(dir,filename+".pid"))):
        killrecord(f)
    if xbmcvfs.delete(f):
        xbmcvfs.delete(os.path.join(dir,filename+".json"))
        xbmcvfs.delete(f+".cmd.txt")
        xbmcvfs.delete(f+".stderr.txt")
        xbmcvfs.delete(f+".stdout.txt")
        xbmcvfs.delete(os.path.join(dir,filename+".pid"))
        xbmcvfs.delete(os.path.join(dir,filename+"-fanart.jpg"))
        xbmcvfs.delete(os.path.join(dir,filename+"-poster.jpg"))
        xbmcvfs.delete(os.path.join(dir,filename+"-banner.jpg"))
        dir=deletedirifempty(dir)
           
    else:
        xbmcgui.Dialog().ok(_addon.getLocalizedString(30080),_addon.getLocalizedString(30081)+f)
   
    if(retpath == 'allrecordings'):
        url=router.url_for(globals()[retpath]) #globasls()-variable as function name
    elif(retpath == 'dirrecodingsview'):
        logDbg(dir)
        if(not xbmcvfs.exists(dir+os.path.sep)):
            dir=os.path.dirname(dir)
        url=router.url_for(globals()[retpath],dir) #globasls()-variable as function name
    xbmc.executebuiltin("Container.Refresh({})".format(url))
    
@router.route('/cancelrecord/<retpath>/<encfp>')
def cancelrecord(retpath,encfp):
    f=unquote_plus(encfp)
    runCancel = xbmcgui.Dialog().yesno(_addon.getLocalizedString(30086),_addon.getLocalizedString(30087)+"\n"+f)
    dir=os.path.dirname(f)
    if(not runCancel):
        return
    killrecord(f)
    if(retpath == 'allrecordings'):
        url=router.url_for(globals()[retpath]) #globasls()-variable as function name
    elif(retpath == 'dirrecodingsview'):
        if(not xbmcvfs.exists(dir+os.path.sep)):
            dir=os.path.dirname(dir)
        url=router.url_for(globals()[retpath],dir) #globasls()-variable as function name
    xbmc.executebuiltin("Container.Refresh({})".format(url))

    

@router.route('/iptvmanager/channels')
def iptvmanager_channels():
    """Return JSON-STREAMS formatted data for all live channels"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(router.args.get('port')[0])
    logDbg('iptvmanager_channels port: {}'.format(port))
    IPTVManager(port).send_channels()


@router.route('/iptvmanager/epg')
def iptvmanager_epg():
    """Return JSON-EPG formatted data for all live channel EPG data"""
    from resources.lib.iptvmanager import IPTVManager
    port = int(router.args.get('port')[0])
    logDbg('iptvmanager_epg port: {}'.format(port))
    IPTVManager(port).send_epg()

@router.route('/recordingutility')
def recordingutility():  
    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30097))
    list_item.setArt({'icon': "DefaultFile.png",
                                'thumb': "DefaultFile.png"})
    url = router.url_for(exportrecordstolibrary)
    list_item.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    
    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30094))
    list_item.setArt({'icon': "DefaultFile.png",
                                'thumb': "DefaultFile.png"})
    url = router.url_for(importrecord)
    list_item.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)
    return


@router.route('/exportrecordtolibrary/<f>')
def exportrecordtolibrary(f):
    rec=(unquote_plus(f),)
    export_script = xbmcvfs.translatePath("special://home/addons/plugin.video.4ka.tv/resources/script/exportrecordings.py")
    cmd = 'RunScript({},{})'.format(export_script,";".join(rec))
    logDbg('Execute script: '+cmd)
    xbmc.executebuiltin(cmd)

@router.route('/exportrecordstolibrary')
def exportrecordstolibrary():
    rec_path=_addon.getSettingString('save_path')
    fname_ext="."+_addon.getSettingString('fname_ext')
    #dirs, files = xbmcvfs.listdir(rec_path)
    vfiles=find_files(rec_path,['.avi','.mp4','.ts',fname_ext])
    #exclude current recording
    files=()
    for f in vfiles:
        dir=os.path.dirname(f)
        full_file_name=os.path.basename(f)
        filename = os.path.splitext(full_file_name)[0]
        if not xbmcvfs.exists(os.path.join(dir,filename+'.pid')):
            files+=(f,)
    
    list_items=createlistitemsforfiles(_addon,files)  
    selitems=[]
    for list_item in list_items:
        logDbg("LIST ITEM: "+repr(list_item[1]))
        selitems.append(list_item[1])
    dialog = xbmcgui.Dialog()
    ret = dialog.multiselect(_addon.getLocalizedString(30100), selitems)
    recordings=()
    if ret:
        for rec in ret:
            recordings+=(list_items[rec][0],)

        export_script = xbmcvfs.translatePath("special://home/addons/plugin.video.4ka.tv/resources/script/exportrecordings.py")
        cmd = 'RunScript({},{})'.format(export_script,";".join(recordings))
        logDbg('Execute script: '+cmd)
        xbmc.executebuiltin(cmd)
    url="plugin://" + xbmcaddon.Addon().getAddonInfo('id')+'/recordingutility'
    xbmc.executebuiltin("Container.Refresh(%s)" % url)
    return

@router.route("/importrecord")
def importrecord():
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_NONE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)
    logDbg('curr directory: '+os.getcwd())
    relPath = xbmcvfs.translatePath('special://home/addons/{}/resources/lib/importers'.format(_addon.getAddonInfo('id'))) # This has to be relative to the working directory
    importersModules=loadimporters(relPath)
    
    dialogSrc=xbmcgui.Dialog()
    ImportersNames=()

    for importer in importersModules:
        ImportersNames+=(importer.getImporterName()),
    selected_importer=dialogSrc.select(_addon.getLocalizedString(30106), ImportersNames)
    if(selected_importer==-1):
        url=router.url_for(recordingutility)
        xbmc.executebuiltin("Container.Refresh({})".format(url))
        return
    rec_path=importersModules[selected_importer].getRecordPath()
    logDbg('Addon record path: '+rec_path)
    
    fname_ext="."+_addon.getSettingString('fname_ext')
    filter="|".join(['.avi','.mp4','.ts',fname_ext])
    #filesdialog=xbmcgui.Dialog()
    #recordings = filesdialog.browseMultiple(1, _addon.getLocalizedString(30100), '', filter, False, False, rec_path)
    list_items_vfiles=importer.getallrecordings(filter)

    selitems=[]
    for list_item in list_items_vfiles:
        logDbg("LIST ITEM: "+repr(list_item))
        selitems.append(list_item[1])
    dialog = xbmcgui.Dialog()
    ret = dialog.multiselect(_addon.getLocalizedString(30100), selitems)
    recordings=()
    if ret:
        for rec in ret:
            logDbg("RET ITEM: "+repr(rec))
            recordings+=(list_items_vfiles[rec][0],)
    logDbg("RECODINGS: "+repr(recordings))
    if(recordings):
        message=""
        for record in recordings:
            message=message+'\u25CF'+record+"\n"
        dialog = xbmcgui.Dialog()    
        yes = dialog.yesno(_addon.getLocalizedString(30098)+'?', message) 
        if(not yes):
            url=router.url_for(recordingutility)
            xbmc.executebuiltin("Container.Refresh({})".format(url))
            return
        
        import_script = xbmcvfs.translatePath("special://home/addons/plugin.video.4ka.tv/resources/script/importrecordingtask.py")
        cmd = 'RunScript({},{},{})'.format(import_script,";".join(recordings),importersModules[selected_importer].getPyFile())
        logDbg('Execute script: '+cmd)
        xbmc.executebuiltin(cmd)
        url="plugin://" + xbmcaddon.Addon().getAddonInfo('id')+'/recordingutility'
        xbmc.executebuiltin("Container.Refresh(%s)" % url)

@router.route('/maintenancerecordings')
def maintenancerecordings():  
    list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30095))
    list_item.setArt({'icon': "DefaultFile.png",
                                'thumb': "DefaultFile.png"})
    url = router.url_for(removedebugorphanedfiles)
    list_item.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)
    return

@router.route('/removedebugorphanedfiles')
def removedebugorphanedfiles():  
    path=_addon.getSettingString('save_path') 
    fname_ext="."+_addon.getSettingString('fname_ext')
    #dirs, files = xbmcvfs.listdir(rec_path)
    filesvid=find_files(path,['.avi','.mp4','.ts',fname_ext])
    files=find_files(path,['.json','.jpg'])

    for f in filesvid:
        dir=os.path.dirname(f)
        full_file_name=os.path.basename(f)
        fvideobasename = os.path.splitext(f)[0]
        logDbg("TESTING VIDEO NAME: {}".format(fvideobasename))
        for file in files[:]:
            if fvideobasename in file:
                logDbg("FILE EXIST {} -------- {}".format(fvideobasename,file))
                files.remove(file)
    

    files+=find_files(path,['.txt'])
    dialog = xbmcgui.Dialog()
    ret = dialog.multiselect(_addon.getLocalizedString(30095), files)
    if (not ret):
        return
    dialog = xbmcgui.Dialog()
    f2rem=()
    for i in ret:
        f2rem+=(files[i],)

    message=""
    for f in f2rem:
        message=message+'\u25CF'+f+"\n"
    ret = dialog.yesno(_addon.getLocalizedString(30096)+'?', message)
    if (not ret):
        return
    for f in f2rem:
        dir=os.path.dirname(f)
        xbmcvfs.delete(f)
        deletedirifempty(dir)
    return

@router.route('/browseEPGArchivechannels')
def browseEPGArchivechannels():
    list_items=[]

    try:
        for channel in cache.cacheFunction(_4katv.get_channels):
            if channel['type']=='tv' and "catchup_length" in channel and channel["catchup_length"]!=None  and channel["catchup_length"]>0:
                list_item = xbmcgui.ListItem(label=channel['name'])
                art={'icon': "DefaultVideo.png",
                    'thumb': channel['tvg-logo'],
                    'poster':channel['tvg-logo'],
                    'fanart':channel['tvg-logo']}
                list_item.setArt(art)
                url = router.url_for(get_epg_date_for_channel, id=channel['id'],id_epg=channel['id_epg'],chname=channel['name']) #need replace ? cause router plugin
        
                list_item.setProperty('IsPlayable', 'false')

                list_items.append((url,list_item,True),)
                
        xbmcplugin.addDirectoryItems(_handle,list_items)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(_handle)
    except C_4KATV.StreamNotResolvedException as e:
        notify(e.detail,True)
        logger.logErr(e.detail)
    return

@router.route('/get_epg_date_for_channel/<id>/<id_epg>/<chname>')
def get_epg_date_for_channel(id,id_epg,chname):
    list_items=[]
    #datetimeformat=xbmc.getRegion('datelong').replace('%-', '%').replace('%#', '%') +" "+xbmc.getRegion('time')
    datetimeformat="%d %A"
    for i in range(0, dayBefore):
        prevDate=(datetime.datetime.now()-datetime.timedelta(days=i))
        ts=int(prevDate.timestamp())
        list_item = xbmcgui.ListItem(label=prevDate.strftime(datetimeformat+" - " +chname))
        list_item.setArt({'icon': "DefaultFolder.png",
                                'thumb': "DefaultFolder.png"})
        url = router.url_for(get_epg_for_channel,id=id,id_epg=id_epg,timestamp=ts)
        list_item.setProperty('IsPlayable', 'false')
       # xbmcplugin.addDirectoryItem(_handle,url, list_items,True)
        list_items.append((url,list_item,True),)
    
    xbmcplugin.addDirectoryItems(_handle, list_items)
    xbmcplugin.endOfDirectory(_handle)



@router.route('/get_epg_for_channel/<id>/<id_epg>/<timestamp>')
def get_epg_for_channel(id,id_epg,timestamp):
    list_items=[]
    dt=datetime.datetime.fromtimestamp(int(timestamp))
    fr=int(round(datetime.datetime.combine(dt, datetime.time.min).timestamp()))
    to=int(round(datetime.datetime.combine(dt, datetime.time.max).timestamp()-1))
    now=datetime.datetime.now().timestamp()
    if now < to:
        to=int(round(now))
    starte = time.time()
    broadcasts=cache.cacheFunction(_4katv.get_archive_epg,id_epg,fr,to)
    #broadcasts=_4katv.get_archive_epg(id_epg,fr,to)
    ende = time.time()
    logDbg("get_archive_epg exec time: "+str(ende-starte))

    for brd in broadcasts:
        subtitle=": "+brd['programme']['sub_title']+" " if brd['programme']['sub_title'] else ""
        title=datetime.datetime.fromtimestamp(brd['programme']['start']).strftime("%H:%M")+"  "+brd['programme']['title']+subtitle
        contextMenu=[]
        if (brd['programme']['stop']<(now-1201)):
            urlrec=router.url_for(recw,id=brd['programme']['broadcast_id'])
            contextMenu.append((_addon.getLocalizedString(30074),'RunPlugin({})'.format(urlrec)))
        else:
            title="[COLOR dimgray]%s[/COLOR]" % title
        list_item=createlistitem(brd)
        list_item.setLabel(title)
        vt=list_item.getVideoInfoTag()
        vt.setTitle(title)
        url = router.url_for(play4kaarchive,id=id,start=brd['programme']['start'],stop=brd['programme']['stop'])
      
        list_item.setProperty('IsPlayable', 'true')

        #if type=='tv':
        urlinfo=router.url_for(iteminfo,id=brd['programme']['broadcast_id'],isFolder=False)
        contextMenu.append(('Info','RunPlugin({})'.format(urlinfo)))
        #list_item = 
        list_item.addContextMenuItems(contextMenu)
    

        list_items.append((url,list_item,False),)   

    xbmcplugin.addDirectoryItems(_handle,list_items)
        # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)



if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    logDbg('Main start router')
    _4katv=C_4KATV.C_4KATV(_username_, _password_,_device_token_,_device_type_code_,_device_model_,_device_name_,_device_serial_number_,_datapath_,_epg_lang_)
    router.run()

