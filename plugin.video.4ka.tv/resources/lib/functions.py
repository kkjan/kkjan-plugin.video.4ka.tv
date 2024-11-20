import os
from resources.lib.logger import *
from resources.lib.importdialog import *
import resources.lib.importdialog as importdialog
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import time
import subprocess
import stat
import importlib
from xml.dom import minidom 
from contextlib import contextmanager
from urllib import request

import datetime
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
            xbmc.executebuiltin('Notification("{}","{}",5000,{})'.format(ADDON.getAddonInfo('name').encode("utf-8"), text, icon))
        except NameError as e:
            xbmc.executebuiltin('Notification("{}","{}",5000,{})'.format(ADDON.getAddonInfo('name'), text, icon))


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

def sanitize_str_for_path(str):
    _quote = {'"': '', '|': '', '*': '', '/': '_', '<': '', ':': '-', '\\': ' ', '?': '', '>': '', ',': ''}
    for char in _quote:
        str = str.replace(char, _quote[char])
    return str



def get_hr_filesize(size_in_bytes):
    """ Convert the size from bytes to other units like KB, MB or GB"""
    
    if(size_in_bytes>(1024*1024*1024)):
         return '{:.2f} GB'.format(size_in_bytes/(1024 * 1024 * 1024))
    elif(size_in_bytes>(1024*1024)):
         return '{:.2f}MB'.format(size_in_bytes/(1024 * 1024))
    elif(size_in_bytes>1024):
       return '{:.2f}KB'.format(size_in_bytes/1024)
    else:
        return '{:.2f}B'.format(size_in_bytes)
    
def find_files(path,ext):
    retfiles=[]
    dirs, files = xbmcvfs.listdir(path)
    for dir in dirs:
        dpath = os.path.join(xbmcvfs.translatePath(path), dir)
        retfiles=retfiles+find_files(dpath,ext)
    for file in files:
        file_extension = os.path.splitext(file)[1]
        if file_extension in ext:
            retfiles.append(os.path.join(xbmcvfs.translatePath(path),file))

    return retfiles


def loadimporters(relPath):
       importersModules=[]
       for pyFile in os.listdir(relPath):
        # just load python (.py) files except for __init__.py or similars
        if pyFile.endswith('.py') and not pyFile.startswith('__'):
            importersModules.append(loadimporter(pyFile))
            
        
        return importersModules
       

def loadimporter(pyFile):
    module = importlib.import_module('resources.lib.importers.{}'.format(pyFile[:-3]))
    try:
        moduleInstance = module.Importer()
        
    except (AttributeError) as e:
        # NOTE: This will be fired if there is ANY AttributeError exception, including those that are related to a typo, so you should print or raise something here for diagnosting
        logWarn('WARN:'+ pyFile + 'doesn\'t has GenericModule class or there was a typo in its content')

    return moduleInstance

def killrecord(file):
    dir=os.path.dirname(file)
    full_file_name=os.path.basename(file)
    filename = os.path.splitext(full_file_name)[0]

    pidf=xbmcvfs.File(os.path.join(dir,filename+".pid"),'r')
    pid=pidf.read()
    pidf.close()
    logDbg("Kill PID: "+pid)
    if xbmc.getCondVisibility("system.platform.windows"):
        p=subprocess.Popen(["taskkill", "/im", pid], shell=True)
    else:
        p=subprocess.Popen(['kill','-9',pid])
    p.wait()
    time.sleep(3)
    logDbg("Delete PID: "+os.path.join(dir,filename+".pid")+".pid")
    xbmcvfs.delete(os.path.join(dir,filename+".pid"))

def deletedirifempty(dir):
    tf,td=xbmcvfs.listdir(dir)
    i=0
    while (len(td)==0 and len(tf)==0 and i<3):
        xbmcvfs.rmdir(dir)
        dir=os.path.dirname(dir)
        tf,td=xbmcvfs.listdir(dir)
        i+=1
    return dir #return firs no empty dir in dir tree

def convertjsininfofromoldformat(data,channels=None):
    datetimeformat=xbmc.getRegion('dateshort').replace('%-', '%').replace('%#', '%') +" "+xbmc.getRegion('time')  
    art= data['art'] if 'art' in data else art
    info=data['info']
    data.clear()
    data['programme']={
    'genres':info['genre'],
    'plot':info['plot'],
    'year':info['year'] if(info['year']) else 0,
    'dateadded':info['dateadded'],
    'img':art['poster'],
    'poster':art['poster'],
    'fanart':art['poster'],
    'episode_number' : None,
    'series_number' : None,
    'series' : None,
    'movies' : None
    }
    tit=info['title'].split(' - ')
    data['programme']['title']=tit[0]
    
    
    sub_title=tit[1] if tit[1] !=tit[-2] else ""
    
    starts=tit[-2].split(': ')[-1]
    duration=tit[-1]
    channelname=tit[-2].split(': ')[0]
    log("sub_title (tit[1]): "+sub_title+ " tit[-2]: "+tit[-2]+' channelname: '+channelname)

    channelid=''
    chthumbnail=''
    if channels:
        for ch in channels:
            if ch['channel']['channelname']==channelname:
                channelid=ch['channel']['channelid']
                chthumbnail=ch['channel']['thumbnail']
                break

    logDbg('datetimeformat: '+datetimeformat)
    logDbg('starts: '+starts)
    
    start=int(datetime.datetime(*(time.strptime(starts, datetimeformat)[0:6])).timestamp())
    dur=time.strptime(tit[-1], xbmc.getRegion('time'))
    duration=dur.tm_sec+dur.tm_min*60+dur.tm_hour*3600
    logDbg('duration format: '+xbmc.getRegion('time'))
    logDbg('duration: '+str(duration))

    stop= int(datetime.datetime(*(time.strptime(starts, datetimeformat)[0:6])).timestamp() + duration)
    
    data['programme']['sub_title']=sub_title
    data['programme']['channelid']=channelid
    data['programme']['start']=start
    data['programme']['stop']=stop
    data['programme']['duration']=duration
    
    
    data['channel']={
        'channelname':channelname,
        'channelid':channelid, 
        'thumbnail':chthumbnail,
    }
    
    
    return data


def updateprogressdialog(_addon,pDialog,dstfile,filesize,cnt,transfered,totalsize,totalcnt,stop):
    logDbg("thread updateprogressdialog START")
    currsize=0
    logDbg("importing progress dialog currsize: {} dstSize {} cnt: {} totalsize {} totalcnt {}".format(currsize,filesize,cnt,totalsize,totalcnt,))
    basedstfname=os.path.basename(dstfile)
    while currsize < filesize:
        if(xbmcvfs.exists(dstfile)):
            currsize=xbmcvfs.Stat(dstfile).st_size()
            position=int((currsize+transfered)/totalsize*100)
            pDialog.update(position,message=_addon.getLocalizedString(30102).format(cnt,totalcnt)+"\n{}".format(basedstfname))
            #logDbg("importing progress dialog position:{} currsize: {} dstSize {} cnt: {} totalsize {} totalcnt {}".format(position,currsize,filesize,cnt,totalsize,totalcnt))
        time.sleep(.5)
        if stop():
            break
    logDbg("thread updateprogressdialog EXITING")

def createfilename(data):
    start=int(data['programme']['start'])
    
    datetimeformat=(xbmc.getRegion('dateshort').replace('%-', '%').replace('%#', '%').replace('Y','y') +" "+xbmc.getRegion('time')).replace(':%S','')
    #datetimeformat="%y-%m-%d"
    logDbg("date time format: {}".format(datetimeformat))
    year=" ({})".format(data['programme']['year']) if data['programme']['year'] else ""
    subtitle=" {}".format(data['programme']['sub_title']) if data['programme']['sub_title'] else ""
    hours, remainder = divmod(data['programme']['duration'], 3600)
    minutes, seconds = divmod(remainder, 60)
    if data['programme']['series']==True:
        #Series
        episode=''
        if(data['programme']['series_number'] and data['programme']['episode_number'] ):
            episode="S{:02d}E{:02d}".format(data['programme']['series_number'],data['programme']['episode_number'])
        elif(data['programme']['series_number']):
            episode="S{:02d}".format(data['programme']['series_number'])
        elif(data['programme']['episode_number']):
            episode="E{:02d}".format(data['programme']['episode_number'])
        name=data['programme']['title']+year+" "+episode+subtitle+' ['+data['channel']['channelname']+'] ['+datetime.datetime.fromtimestamp(start).strftime(datetimeformat)+' {}-{}-{}]'.format(hours,minutes,seconds)
    else:
        name=data['programme']['title']+year+subtitle+' ['+data['channel']['channelname']+'] ['+datetime.datetime.fromtimestamp(start).strftime(datetimeformat)+' {}-{}-{}]'.format(hours,minutes,seconds)

    return sanitize_str_for_path(name)



def createnfo(data,type='movie'):
    nfo = minidom.Document() 

    tit=data['programme']['sub_title'] if data['programme']['sub_title'] else data['programme']['title']
    if type =="tvshow":
        tit=data['programme']['title']
    top=nfo.createElement(type)
    title=nfo.createElement('title')
    title.appendChild(nfo.createTextNode(tit))
    top.appendChild(title)

    if type =="episodedetails":
        if data['programme']['series_number']:
            season=nfo.createElement('season')
            season.appendChild(nfo.createTextNode("{}".format(data['programme']['series_number'])))
            top.appendChild(season)
        if data['programme']['episode_number']:
            episode=nfo.createElement('episode')
            episode.appendChild(nfo.createTextNode("{}".format(data['programme']['episode_number'])))
            top.appendChild(episode)

    if type =="tvshow" and 'description_show' in data['programme'] and data['programme']['description_show']:
        plot=nfo.createElement('plot')
        plot.appendChild(nfo.createTextNode(data['programme']['description_show']))
        top.appendChild(plot)

    elif data['programme']['plot']:
        plot=nfo.createElement('plot')
        plot.appendChild(nfo.createTextNode(data['programme']['plot']))
        top.appendChild(plot)

    if data['programme']['genres']:
        genre=nfo.createElement('genre')
        genre.appendChild(nfo.createTextNode("/".join(data['programme']['genres'])))
        top.appendChild(genre)

    if data['programme']['year']:
        premiered=nfo.createElement('premiered')
        premiered.appendChild(nfo.createTextNode("{}-01-01".format(data['programme']['year'])))
        top.appendChild(premiered)
    
    if 'actors' in data['programme'] and data['programme']['actors']:
        for actor in data['programme']['actors']:
            act=nfo.createElement('actor')
            actname=nfo.createElement('name')
            actname.appendChild(nfo.createTextNode(actor))
            act.appendChild(actname)
            top.appendChild(act)
    
    if not type =="tvshow" and 'directors' in data['programme'] and  data['programme']['directors']:
        for director in data['programme']['directors']:
            direct=nfo.createElement('director')
            direct.appendChild(nfo.createTextNode(director))
            top.appendChild(direct)

    nfo.appendChild(top)

    return nfo.toprettyxml(indent ="\t", encoding="utf-8") 

def createlistitem(data):
    list_item = xbmcgui.ListItem(label=data['programme']['title'])

    art={'icon': data['programme']['img'],
        'thumb':  data['programme']['img'],
        'poster': data['programme']['poster'] if data['programme']['poster'] else data['programme']['img'],
        'fanart': data['programme']['photo'] if data['programme']['photo'] else data['programme']['img']}
    list_item.setArt(art)
    vt=list_item.getVideoInfoTag()
    vt.setTitle(data['programme']['title'])
    vt.setGenres(data['programme']['genres'])
    vt.setPlot(data['programme']['plot'])
    if(data['programme']['episode_number']):
        vt.setEpisode(data['programme']['episode_number'])
    if(data['programme']['series_number']):
        vt.setSeason(data['programme']['series_number'])
    if(data['programme']['year']):
        vt.setYear(data['programme']['year'])
    vt.setDateAdded(data['programme']['dateadded'])
    if data['programme']['actors']:
        actors=[]
        for actor in data['programme']['actors']:
            act=xbmc.Actor(actor)
            actors.append(act)
        vt.setCast(actors)

    if data['programme']['directors']:
        vt.setDirectors(data['programme']['directors'])

    list_item.setProperty('IsPlayable', 'true')
    return list_item

def get_proxy():
    proxies=request.getproxies()
    logDbg("Proxy: {}".format(proxies))
    return proxies