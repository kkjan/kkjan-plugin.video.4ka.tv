import sys
import xbmcvfs
import subprocess
import xbmc
from urllib.parse import quote, quote_plus, unquote
import xbmcaddon
import time
import json
import os
import threading

import_path = xbmcvfs.translatePath("special://home/addons/plugin.video.4ka.tv")
sys.path.insert(1, import_path)  
from resources.lib.logger import *
from resources.lib.importdialog import *
from resources.lib.functions import *
import resources.lib.progressdialog as progressdialogBG


_addon = xbmcaddon.Addon('plugin.video.4ka.tv')
recordings=sys.argv[1].split(';')
logDbg("   ---   ".join(sys.argv))




logDbg("thread export start")

overidealldestfile=False
step=int(100/len(recordings))
position=0
message=""
totalsize=0
totalcnt=len(recordings)
pDialog = xbmcgui.DialogProgressBG()
pDialog.create(_addon.getLocalizedString(30107),_addon.getLocalizedString(30102).format(0,totalcnt))
pDialog.update(0,message="")
transfered=0
for record in recordings:
    message=message+'\u25CF'+record+"\n"
    totalsize+=xbmcvfs.Stat(record).st_size()
try:
    i=0
    save_path="library://video/"
    destdirdialog=xbmcgui.Dialog()
    save_path= destdirdialog.browseSingle(0, _addon.getLocalizedString(30099), '', '', False, False, save_path )
    for rec in recordings:
        i+=1
        src_dir=os.path.dirname(rec)
        full_src_file_name=os.path.basename(rec)
        srcfname,fname_ext = os.path.splitext(full_src_file_name)

        destpath=os.path.join(save_path,srcfname)
        jsoninfo=[]
        nfo=""
        if xbmcvfs.exists(os.path.join(src_dir,srcfname+'.json')):
            jsonf=xbmcvfs.File(os.path.join(src_dir,srcfname+'.json'),'r')
            jsoninfo=json.loads(jsonf.read())
            if 'info' in jsoninfo:
                jsoninfo=convertjsininfofromoldformat(jsoninfo) #OLD FORMAT
            if 'programme' in jsoninfo:
                destfname=createfilename(jsoninfo)
                year=" ({})".format(jsoninfo['programme']['year']) if jsoninfo['programme']['year'] else ""
                if jsoninfo['programme']['series']==True:
                    #Series
                    destpath=os.path.join(save_path,sanitize_str_for_path(jsoninfo['programme']['title']+year))
                    tvshownfo=createnfo(jsoninfo,'tvshow')
                    if tvshownfo:
                        xbmcvfs.mkdirs(destpath)
                        nfof=xbmcvfs.File(os.path.join(destpath,'tvshow.nfo'),'wb')
                        nfof.write(tvshownfo)
                        nfof.close()
                    if(jsoninfo['programme']['series_number']):
                        destpath=os.path.join(destpath,"Session {:02d}".format(jsoninfo['programme']['series_number']))
                    nfo=createnfo(jsoninfo,'episodedetails')
                elif jsoninfo['programme']['movie']==True:  
                     nfo=createnfo(jsoninfo,'movie')
                     destpath=os.path.join(save_path,destfname) 
                else:
                     nfo=createnfo(jsoninfo,'movie')
                     destpath=os.path.join(save_path,destfname)
                    
        xbmcvfs.mkdirs(destpath)
        full_file_name=destfname+fname_ext
        destfile=os.path.join(destpath,full_file_name)
        logDbg("DEST FILE: "+destfile)
        position+=step
        override=False
        if(xbmcvfs.exists(destfile)):
            if(not overidealldestfile):
                overidedstfiledlg = importdialog.importdialog(_addon,_addon.getLocalizedString(30101)+'?', destfile)

            if overidedstfiledlg ==1:
                override=True
            elif overidedstfiledlg ==2:
                override=True
                overidealldestfile=True

            elif overidedstfiledlg ==4:
                    overidealldestfile=True

            elif overidedstfiledlg ==-1:
                    url="plugin://" + xbmcaddon.Addon().getAddonInfo('id')+'/recordingutility'
                    xbmc.executebuiltin("Container.Refresh(%s)" % url)
                    quit()
        

        if(override or not xbmcvfs.exists(destfile)):
            
            xbmcvfs.delete(destfile)
            filesize=xbmcvfs.Stat(rec).st_size()
            stop_threads = False
            progress=threading.Thread(target=updateprogressdialog,args=(_addon,pDialog,destfile,filesize,i,transfered,totalsize,totalcnt,lambda: stop_threads,))
            progress.start()
            if(xbmcvfs.copy(rec,destfile)):
                #TODO generate NFO files
                if nfo:
                    nfof=xbmcvfs.File(os.path.join(destpath,destfname+'.nfo'),'wb')
                    nfof.write(nfo)
                    nfof.close()
                jsonf=xbmcvfs.File(os.path.join(destpath,destfname+'.json'),'wb')
                json.dump(jsoninfo,jsonf)
                jsonf.close()
                if(xbmcvfs.exists(os.path.join(src_dir,srcfname+'-fanart.jpg'))):
                    xbmcvfs.copy(os.path.join(src_dir,srcfname+'-fanart.jpg'),os.path.join(destpath,destfname+'-fanart.jpg'))
                if(xbmcvfs.exists(os.path.join(src_dir,srcfname+'-poster.jpg'))):
                    xbmcvfs.copy(os.path.join(src_dir,srcfname+'-poster.jpg'),os.path.join(destpath,destfname+'-poster.jpg'))
                if(xbmcvfs.exists(os.path.join(src_dir,srcfname+'-banner.jpg'))):
                    xbmcvfs.copy(os.path.join(src_dir,srcfname+'-banner.jpg'),os.path.join(destpath,destfname+'-banner.jpg'))
            stop_threads = True
            progress.join()
        transfered+=xbmcvfs.Stat(rec).st_size()

finally:
    pDialog.close()
    

deleteallsourcefiles=False   
for rec in recordings:
    src_dir=os.path.dirname(rec)
    full_src_file_name=os.path.basename(rec)
    srcfname,fname_ext = os.path.splitext(full_src_file_name)
    if(not deleteallsourcefiles):
        delsrcfile = importdialog.importdialog(_addon,_addon.getLocalizedString(30105)+'?', message)

    if delsrcfile ==1:

        if xbmcvfs.delete(rec):
            xbmcvfs.delete(os.path.join(src_dir,srcfname+".json"))
            xbmcvfs.delete(rec+".cmd.txt")
            xbmcvfs.delete(rec+".stderr.txt")
            xbmcvfs.delete(rec+".stdout.txt")
            xbmcvfs.delete(os.path.join(src_dir,srcfname+".pid"))
            xbmcvfs.delete(os.path.join(src_dir,srcfname+"-fanart.jpg"))
            xbmcvfs.delete(os.path.join(src_dir,srcfname+"-poster.jpg"))
            xbmcvfs.delete(os.path.join(src_dir,srcfname+"-banner.jpg"))
            src_dir=deletedirifempty(src_dir)
            
    elif delsrcfile ==2:
            deleteallsourcefiles=True
            if xbmcvfs.delete(rec):
                xbmcvfs.delete(os.path.join(src_dir,srcfname+".json"))
                xbmcvfs.delete(rec+".cmd.txt")
                xbmcvfs.delete(rec+".stderr.txt")
                xbmcvfs.delete(rec+".stdout.txt")
                xbmcvfs.delete(os.path.join(src_dir,srcfname+".pid"))
                xbmcvfs.delete(os.path.join(src_dir,srcfname+"-fanart.jpg"))
                xbmcvfs.delete(os.path.join(src_dir,srcfname+"-poster.jpg"))
                xbmcvfs.delete(os.path.join(src_dir,srcfname+"-banner.jpg"))
                src_dir=deletedirifempty(src_dir)
    
    elif delsrcfile ==4:
            deleteallsourcefiles=True

    elif delsrcfile ==-1:
            quit()
    
    message=message.replace('\u25CF'+rec+"\n","")

logDbg("thread export exiting")

