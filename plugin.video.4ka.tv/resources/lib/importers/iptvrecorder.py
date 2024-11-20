import xbmc
import xbmcgui
import json
import xbmcaddon
import datetime
import re

from resources.lib.baseimporter import *
from resources.lib.functions import *


class  Importer(BaseImporter):
    def __init__(self):
        BaseImporter.__init__(self)
        self.name="IPTV recorder"
        self.addon=xbmcaddon.Addon('plugin.video.iptv.recorder')
    
    def getImporterName(self):
        # This could be a Print (or default return value) or an Exception
        return self.name
    
    def getRecordPath(self):
        return self.addon.getSetting('recordings')

    #retun list of tuples (path,listitem)
    def getallrecordings(self,filter):
        files=find_files(self.getRecordPath(),filter)
        litems=[]
        for f in files:
            dir=os.path.dirname(f)
            full_file_name=os.path.basename(f)
            filename = os.path.splitext(full_file_name)[0]
            list_item = xbmcgui.ListItem(label=filename)
            litems.append((f,list_item,False))
        return litems
    
    def getjsoninfo(self,file):
        # This could be a Print (or default return value) or an Exception
        dir=os.path.dirname(file)
        full_file_name=os.path.basename(file)
        filename = os.path.splitext(full_file_name)[0]
        if xbmcvfs.exists(os.path.join(dir,filename+'.json')):
            jsonf=xbmcvfs.File(os.path.join(dir,filename+'.json'),'r')
            data=json.loads(jsonf.read())
            jsonf.close()
            jsoninfo={}
            jsoninfo['programme'] ={'title' :   data['programme']['title'],
            'sub_title':data['programme']['sub_title'],
            'channelid' : data['programme']['channelid'],
            'start':data['programme']['start'],
            'stop':data['programme']['stop'],
            'duration':int(data['programme']['stop'],)-int(data['programme']['start'],),
            'dateadded':datetime.datetime.fromtimestamp(int(data['programme']['start'],)).strftime("%Y-%m-%dT%H:%M:%S"),
             'year' : int(data['programme']['date']) if 'date' in data['programme'] else None,
             'plot':data['programme']['description'],
             'playable':True,
             'episode' : data['programme']['episode'],
             'series_number':None,
            'episode_number':None,
            'img':None,
            'genres':data['programme']['categories'].replace(' ','').split(',')
            }

            # find series and episode number:
            jsoninfo['programme']['series']= None
            if(data['programme']['episode'] and data['programme']['episode']!="MOVIE"):
                p = re.compile(r'^[Ee](\d+)')
                matches=p.match(data['programme']['episode'])
                if matches:
                    jsoninfo['programme'] ['episode_number'] = int(matches.group(1))
                p = re.compile(r'^[Ss](\d+)')
                matches=p.match(data['programme']['episode'])
                if matches:
                    jsoninfo['programme'] ['series_number'] = int(matches.group(1))
                    jsoninfo['programme']['series']= True
                p = re.compile(r'[Ss](\d+)[EexX](\d+)')
                matches=p.match(data['programme']['episode'])
                if matches:
                    jsoninfo['programme'] ['series_number'] = int(matches.group(1))
                    jsoninfo['programme'] ['episode_number'] = int(matches.group(2))
                    jsoninfo['programme']['series']= True

    
            jsoninfo['programme']['movie']= True if(data['programme']['episode']=='MOVIE') else None
                
            jsoninfo['channel']={
                    'channelname' : data['channel']['channelname'],
                    'channelid':data['channel']['channelid'],
                    "thumbnail":data['channel']['thumbnail']
            }
        return jsoninfo
    
    def delete(self,file):
        dir=os.path.dirname(file)
        full_file_name=os.path.basename(file)
        filename = os.path.splitext(full_file_name)[0]
        jsonf=os.path.join(dir,filename+'.json')
        xbmcvfs.delete(file)
        xbmcvfs.delete(jsonf)

        return
    def getPyFile(self):
        return "iptvrecorder.py"