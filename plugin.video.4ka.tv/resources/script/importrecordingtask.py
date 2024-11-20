import sys
import xbmcvfs
import subprocess
import xbmc
from urllib.parse import quote, quote_plus, unquote
import xbmcaddon
import time
import os
import threading
import json
import_path = xbmcvfs.translatePath("special://home/addons/plugin.video.4ka.tv")
sys.path.insert(1, import_path)  
from resources.lib.logger import *
from resources.lib.importdialog import *
from resources.lib.functions import *
import resources.lib.progressdialog as progressdialogBG
import resources.lib.progressdialog as progressdialogBG


_addon = xbmcaddon.Addon('plugin.video.4ka.tv')
recordings=sys.argv[1].split(';')
logDbg("   ---   ".join(sys.argv))
importer=loadimporter(sys.argv[2])


logDbg("thread import start")
destpath=_addon.getSettingString('save_path') 
allfilestodest=False
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
    for rec in recordings:
        i+=1
        full_file_name=sanitize_str_for_path(os.path.basename(rec))
        filename = os.path.splitext(full_file_name)[0]
        jsoninfo=importer.getjsoninfo(rec)
        if(not allfilestodest):
            save_path=_addon.getSettingString('save_path') 
            if jsoninfo['programme']['series']==True and jsoninfo['programme']['playable']==True:
            #Series
                parentpath=os.path.join(save_path,"Series")
            elif jsoninfo['programme']['movie']:
                parentpath=os.path.join(save_path,"Movies")
            else:
                parentpath=os.path.join(save_path,"Others",sanitize_str_for_path(jsoninfo['programme']['title']))
            destdirchangeret = importdialog.importdialog(_addon,_addon.getLocalizedString(30103)+'?', parentpath)

            if (destdirchangeret==1):
                destdirdialog=xbmcgui.Dialog()
                parentpath= destdirdialog.browseSingle(0, _addon.getLocalizedString(30099), '', '', False, False, _addon.getSettingString('save_path') )
            if (destdirchangeret==2):
                allfilestodest=True
                destdirdialog=xbmcgui.Dialog()
                parentpath= destdirdialog.browseSingle(0, _addon.getLocalizedString(30099), '', '', False, False, _addon.getSettingString('save_path') )
            if (destdirchangeret==4):
                allfilestodest=True
            if (destdirchangeret==-1):
                quit()

        year=" ({})".format(jsoninfo['programme']['year']) if jsoninfo['programme']['year'] else ""
        if("Series" in parentpath):
            jsoninfo['programme']['series']=True
            destpath=os.path.join(parentpath,sanitize_str_for_path(jsoninfo['programme']['title']+year))
            if(jsoninfo['programme']['series_number']):
                    destpath=os.path.join(destpath,"Session {:02d}".format(jsoninfo['programme']['series_number']))
        elif("Movies" in parentpath):
            jsoninfo['programme']['movie']=True
            destpath=os.path.join(parentpath,sanitize_str_for_path(jsoninfo['programme']['title']+year))
        else: # not movie or series
            destpath=os.path.join(parentpath,sanitize_str_for_path(jsoninfo['programme']['title']+year))

        xbmcvfs.mkdirs(destpath)
        destfile=os.path.join(destpath,full_file_name)
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
                jsonf=xbmcvfs.File(os.path.join(destpath,filename+'.json'),'w')
                json.dump(jsoninfo,jsonf)
                jsonf.close()
            stop_threads = True
            progress.join()
        transfered+=xbmcvfs.Stat(rec).st_size()
        

        
finally:
    pDialog.close()
    

deleteallsourcefiles=False   
for rec in recordings:

    if(not deleteallsourcefiles):
        delsrcfile = importdialog.importdialog(_addon,_addon.getLocalizedString(30105)+'?', message)
    if delsrcfile ==1:
            importer.delete(rec)
    elif delsrcfile ==2:
            deleteallsourcefiles=True
            importer.delete(rec)
    elif delsrcfile ==4:
            deleteallsourcefiles=True

    elif delsrcfile ==-1:
            quit()
    
    message=message.replace('\u25CF'+rec+"\n","")
logDbg("thread import exiting")

