#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Wrapper pre 4KA TV"""
import json
import requests
import datetime
import time
from xml.dom import minidom 
import codecs
from resources.lib.logger import *
import os
import time


_COMMON_HEADERS = { "User-Agent" :	"okhttp/3.12.1",
                    "Connection": "Keep-Alive"}




class _4KATVException(Exception):
    def __init__(self, id):
        self.id = id


class UserNotDefinedException(_4KATVException):
    def __init__(self):
        self.id = 30601

class UserInvalidException(_4KATVException):
    def __init__(self):
        self.id = 30602

class TooManyDevicesException(_4KATVException):
    def __init__(self,detail):
        self.id = 30603
        self.detail = detail
       

class StreamNotResolvedException(_4KATVException):
    def __init__(self, detail):
        self.id = 30604
        self.detail = detail

class PairingException(_4KATVException):
    def __init__(self, detail):
        self.id = 30605
        self.detail = detail

class DeviceNotAuthorizedToPlayException(_4KATVException):
    def __init__(self, detail):
        self.id = 30606
        self.detail = detail
        
class C_4KATV:

    def __init__(self,username =None,password=None,device_token=None, device_type_code = None, model=None,name=None, serial_number=None, datapath=None,epg_lang=None,progress=None):
        self.username = username
        self.password = password
        self._live_channels = {}
        self.device_token = device_token
        self.subscription_code = None
        self.locality = None
        self.offer = None
        self.device_type_code = device_type_code
        self.model = model
        self.name = name
        self.serial_number = serial_number
        self.channels=[]
        self.datapath = datapath
        self.lang = epg_lang
        if progress:
            self.progress=progress
        else:
            self.progress=None


    def _post(self,url,data):
        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"
        try:
            res = requests.post(url, json=data, headers=headers,timeout=(5,120))
        except requests.exceptions.Timeout:
            logDbg("Download error TIMEOUT: "+res.url)
        except requests.exceptions.TooManyRedirects:
            logDbg("Download error TOMANY REDIRECTS : "+res.url)
        except requests.exceptions.RequestException as e:
            logDbg("Download error: "+res.url)

        return res

    def _get(self,url,param):
        headers = _COMMON_HEADERS
        try:
            res=requests.get(url,param,headers=headers,timeout=(5,120))
        except requests.exceptions.Timeout:
            logDbg("Download error TIMEOUT: "+res.url)
        except requests.exceptions.TooManyRedirects:
            logDbg("Download error TOMANY REDIRECTS : "+res.url)
        except requests.exceptions.RequestException as e:
            logDbg("Download error: "+res.url)
        return res

    #function for login device with device token (after succesfully pairing)
    def logdevicestartup(self):
        data = {'device_token' : self.device_token,
                'application': "3.1.12",
                'firmware': "22" }
        req = self._post('https://backoffice.swan.4net.tv/api/device/logDeviceStart', data)
        j=req.json()
        return j['success']
        
    #function for pairing device
    #if is not set device token, device try to login with username/password and try to obtain device token. 
    #Device token would by saved for login function for next use
    def pairingdevice(self):
        result=-1
        if not self.username or not self.password:
            raise UserNotDefinedException()
        data = {  'login' : self.username,
                'password' : self.password,
                'id_brand' : 1}
        
                    #Pairing device
        req = self._post('https://backoffice.swan.4net.tv/api/device/pairDeviceByLogin', data)
        j = req.json()
        if j['success']==True:
            self.device_token=j['token']
            data = {'device_token' : self.device_token,
                    'device_type_code' : self.device_type_code,
                    'model' : self.model,
                    'name' : self.name,
                    'serial_number' : self.serial_number }
            req = self._post('https://backoffice.swan.4net.tv/api/device/completeDevicePairing', data)
            return self.device_token
        elif "validation_errors" in j['message'] and j['success']==False:
            raise TooManyDevicesException(j['message']['validation_errors'][0])
        elif j['success']==False:
            raise UserInvalidException()
        else:
            raise PairingException('Detail: '+j['message'])

        
     
    #function for to obtain device setting. not used now
    def get_devicesetting(self):
        data = {'device_token' : self.device_token}
        req = self._post('https://backoffice.swan.4net.tv/api/getDeviceSettings/', data)
        j = req.json()
        self._device_settings=j
        return self._device_settings

        
    
    #function for download channel related streams address from 4katv(swan)
    def get_4KATV_stream(self, ch_id,start,end):
        data = {'device_token' : self.device_token,
                 'channel_id':ch_id,
                 'start':start,
                 'end':end}

        req = self._get('https://backoffice.swan.4net.tv/contentd/api/device/getContent',data)
        j = req.json()
        if(j['success']==True):
            return j['stream_uri']
        else:
            logDbg("get_4KATV_stream: "+j['message'])
            raise DeviceNotAuthorizedToPlayException('Detail: '+j['message'])

    #function for get channel and EPG for live stream. Used in main.py
    def get_channels_live(self,type='tv'):
        ch =list()

        j=self.dl_4KATV_channels()
        epg=self.dl_4KATV_epg_json(hourspast=6,hoursfuture=6)
        now=time.time()
        tags=self.dl_4KATV_tags()

        #datetimeformat=xbmc.getRegion('dateshort')+" "+xbmc.getRegion('time')
        datetimeformat=xbmc.getRegion('dateshort').replace('%-', '%').replace('%#', '%') +" "+"%H:%M"
        for channel in j['channels']:
            if channel['type']==type:
                #ch_ids=list(filter(lambda x:x["id_epg"]==channel['id_epg'],epg['broadcasts']))
                ch_ids=epg['broadcasts'][str(channel['id_epg'])]
  
               # ch_ids_curr=list(filter(lambda x:x["live"]==True,ch_ids))
             
                ch_ids1=list(filter(lambda x:x["timestamp_end"]>now,ch_ids))
                ch_ids_curr=list(filter(lambda x:x["timestamp_start"]<now,ch_ids1))
                
                if ch_ids_curr:
                    ch_ids_next=list(filter(lambda x:x["timestamp_start"]==ch_ids_curr[0]['timestamp_end'],ch_ids))
                else:
                    ch_ids_next=""
                ch ={ 'name' : channel['name'],
                     'ch_id':channel['id'],
                    'prg_name': ch_ids_curr[0]['name'] if ch_ids_curr else " ",
                    'next_prg_name': ch_ids_next[0]['name'] if ch_ids_next else " ",
                    'next_prg_start': datetime.datetime.fromtimestamp(int(ch_ids_next[0]['timestamp_start'])).strftime(datetimeformat) if ch_ids_next else " ",
                    'next_prg_end': datetime.datetime.fromtimestamp(int(ch_ids_next[0]['timestamp_end'])).strftime(datetimeformat) if ch_ids_next else " ",
                    'id_epg' : channel['id_epg'],
                    'tvg-name' : channel['name'].replace(" ","_"),
                    'start' : datetime.datetime.fromtimestamp(int(ch_ids_curr[0]['timestamp_start'])).strftime(datetimeformat) if ch_ids_curr else " ",
                    'end' : datetime.datetime.fromtimestamp(int(ch_ids_curr[0]['timestamp_end'])).strftime(datetimeformat) if ch_ids_curr else " ",
                    'timestamp_start':ch_ids_curr[0]['timestamp_start'],
                    'timestamp_end':ch_ids_curr[0]['timestamp_end'],
                    'duration' : datetime.datetime.fromtimestamp(int(ch_ids_curr[0]['timestamp_end'])-int(ch_ids_curr[0]['timestamp_start'])).strftime(datetimeformat) if ch_ids_curr else " ",
                    'tvg-logo' : "https://epg.swan.4net.tv/files/channel_logos/"+str(channel['id'])+".png",
                    'content_source' :  channel['content_sources'][0]['stream_profile_urls']['adaptive'],
                    'type' :  channel['type'],
                    'broadcast_id': ch_ids_curr[0]['id'] if ch_ids_curr else " "}
                plot=''
                if ch_ids_curr and  'name_episode' in ch_ids_curr[0] and ch_ids_curr[0]['name_episode']!=None:
                    plot+=ch_ids_curr[0]['name_episode']+'[CR]'
                elif ch_ids_curr and  'description_broadcast' in ch_ids_curr[0] and ch_ids_curr[0]['description_broadcast']!=None:
                    plot += ch_ids_curr[0]['description_broadcast']
                ch['plot']=plot

                if ch_ids_curr and 'photo' in ch_ids_curr[0]: 
                    ch['img'] = str(ch_ids_curr[0]['photo']['url']).replace("{size}",'300')
                elif ch_ids_curr and  'poster' in ch_ids_curr[0]:
                    ch['img'] =  str(ch_ids_curr[0]['poster']['url']).replace("{size}",'300')
                else:
                    ch['img'] = 'DefaultVideo.png'

                genres=[]
                for tag in ch_ids_curr[0]['ids_tag']:
                    genres.append(tags['tags'][str(tag)]['name'])
                if len(genres)>0:
                    ch['genre']=genres
                else:
                    ch['genre']=""
                if ch_ids_curr and 'year' in ch_ids_curr[0]:
                    ch['year']=ch_ids_curr[0]['year']
                else:
                    ch['year']=None
                self.channels.append(ch)
        return self.channels    

    #function return channels from channels json Used in main.py
    def get_channels(self):
        ch =list()

        j=self.dl_4KATV_channels()
        for channel in j['channels']:
            ch ={ 'name' : channel['name'],
                'id_epg' : channel['id_epg'],
                'tvg-name' : channel['name'].replace(" ","_"),
                'tvg-logo' : "https://epg.swan.4net.tv/files/channel_logos/"+str(channel['id'])+".png",
                'content_source' :  channel['content_sources'][0]['stream_profile_urls']['adaptive'],
                'type' :  channel['type']}
            self.channels.append(ch)
        return self.channels    

    #function return category from tags json Used in main.py
    def get_4KATVtags(self):
        subcats =[]
        sc=list
          
        j=self.dl_4KATV_tags()
        for scid in j['tags'].keys():
            sc ={ 'name' : j['tags'][scid]['name'],
                    'id_tag' : scid,
                    'type' : j['tags'][scid]['type']}
            
            if 'photo' in j['tags'][scid] and j['tags'][scid]['photo']!=None:
                sc['img'] = str(j['tags'][scid]['photo']['url']).replace("{size}","300")
            elif 'poster' in j['tags'][scid] and j['tags'][scid]['poster']!=None:
                sc['img'] = str(j['tags'][scid]['poster']['url']).replace("{size}","300")
            elif 'icons' in j['tags'][scid] and j['tags'][scid]['icons']['big']!=None:
                sc['img'] = "https://epg.swan.4net.tv/files"+str(j['tags'][scid]['icons']['big'])
            else:
                    sc['img'] = 'DefaultVideoIcon.png'
           
            #only default tags are return. Not all.
            #TODO: plugin settings for all/default tags switch
            if(j['tags'][scid]['show_in_dashboard']==True):
                subcats.append(sc)
        return subcats  

    #private function return data broadcasts from group
    def _get_broad_ch_epg(self):
        broad_ch_epg=list()
        bec=self.dl_4KATV_allchannelgroups() 
  
        for broad_ch_epgs in bec["channel_groups"]:
            for chan in broad_ch_epgs['channels']:
                broad_ch_epg.append(chan)                
        return broad_ch_epg

    #private function return epg_ids for requests
    def _get_epg_ids(self,broad_ch_epg):
        epg_ids=[]
        for ch in broad_ch_epg:
            epg_ids.append(ch["id_epg"])
        epg_ids.sort()
        return epg_ids

    #special_epg is epg without archive ("catchup_length" in json is null)
    def _get_special_epg_ids(self,broad_ch_epg):
        special_epg_ids=[]
        ret=["0"]
         #get non archived/playable items. Its caused if basic archive or full archive is  used:
        sources=list(filter(lambda x:x["catchup_length"]== None ,self.dl_4KATV_channels()['channels']))
        sources_ids=list(map(lambda x: x['id'], sources))#non Playable archive channels
        for ch in broad_ch_epg:
            if(ch['id'] in sources_ids):
                    special_epg_ids.append(ch["id_epg"])
        special_epg_ids.sort()

        ret=["0"].append(special_epg_ids)
        return ret

     #get epg  for archived ("catchup_length" in json is not null)
    def _get_archived_epg_ids(self,broad_ch_epg):
        archived_epg_ids=[]
         #get non archived/playable items. Its caused if basic archive or full archive is  used:
        sources=list(filter(lambda x:x["catchup_length"]!= None and  x["catchup_length"]>0,self.dl_4KATV_channels()['channels']))
        sources_ids=list(map(lambda x: x['id'], sources))#non Playable archive channels
        for ch in broad_ch_epg:
            if(ch['id'] in sources_ids):
                    archived_epg_ids.append(ch["id_epg"])
        archived_epg_ids.sort()

        return archived_epg_ids

    #private function return episodes
    def _get_episode(self,id):
        broad_ch_epg=self._get_broad_ch_epg()
        epg_ids=self._get_epg_ids(broad_ch_epg)
        lng=[]
        lng.append(self.lang)
        data={
            'hours_back':168,
            'hours_front':0,
            'id_broadcast':id,
            'ids_epg':epg_ids,
            'lng_priority':lng,
        }
        url='https://epg.swan.4net.tv/v2/detail'
        
        req = self._post(url, data)        
        j = req.json()
        if  j['error']==True:
            raise StreamNotResolvedException(j['message'])
        dat=[]
        broadcasts=j['related_broadcasts']['instances']
        for brd in broadcasts:
            tmp=brd
            tmp['ids_tag']=j['broadcast']['ids_tag']
            tmp['id_epg']=brd['broadcasts'][0]['id_epg']
            tmp['id_broadcast']=brd['broadcasts'][0]['id_broadcast']
            tmp['timestamp_start']=brd['broadcasts'][0]['timestamp_start']
            tmp['timestamp_end']=brd['broadcasts'][0]['timestamp_end']
            tmp['photo']=brd['broadcasts'][0]['photo']
            tmp['poster']=brd['broadcasts'][0]['poster']
            
            tmp['id']=brd['broadcasts'][0]['id_broadcast']
            dat.append(tmp)
       
        return self._prepare_content(dat,broad_ch_epg)
    
    #private function return data from search
    def _get_search_result(self,q):
        broad_ch_epg=self._get_broad_ch_epg()
        epg_ids=self._get_epg_ids(broad_ch_epg)
        special_epg_from=self._get_special_epg_ids(broad_ch_epg)
        lng=[]
        lng.append(self.lang)
        data={
                'hours_back':168,
                'hours_front':0,
                'lng_priority':lng,
                'ids_epg':epg_ids,
                'min_score':100,
                'q':q,  
                'special_epg_from':special_epg_from
            }
        url='https://epg.swan.4net.tv/v2/search'  
        req = self._post(url, data)        
        j = req.json()
        if  j['error']==True:
            raise StreamNotResolvedException(j['message'])
        return self._prepare_content(j['broadcasts'],broad_ch_epg)

    #private function return content info for tags
    def _get_tagcontent(self,id):
        broad_ch_epg=self._get_broad_ch_epg()
        lng=[]
        lng.append(self.lang)
        epg_ids=self._get_epg_ids(broad_ch_epg)
        special_epg_from=self._get_special_epg_ids(broad_ch_epg)
        data={
                'hours_back':168,
                'hours_front':0,
                'ids_epg':epg_ids,
                'special_epg_from':special_epg_from,
                'limit':102,
                'lng_priority':lng,
                'id_tag':int(id)
            }
        url='https://epg.swan.4net.tv/v2/best-rated-by-tag'
        req = self._post(url, data)        
        j = req.json()
        if  j['error']==True:
            raise StreamNotResolvedException(j['message'])
        
        return self._prepare_content(j['broadcasts'],broad_ch_epg)

    #private function return for content info from raw json
    def _prepare_content(self,dat,broad_ch_epg):
        archived_epg_ids=self._get_archived_epg_ids(broad_ch_epg)

        tags=self.dl_4KATV_tags()
        subcast=list()
        datetimeformat=xbmc.getRegion('dateshort').replace('%-', '%').replace('%#', '%') +" "+xbmc.getRegion('time')
        for br in dat:
            if(br["id_epg"] in archived_epg_ids):
                ch_id=list(filter(lambda x:x["id_epg"]==br['id_epg'],broad_ch_epg))
                isSeries=768 in br['ids_tag'] #768-id for Series tag
                name= ch_id[0]['name'] 
                if br['name_episode'] !=None:
                    name+=": "+br['name_episode']
                sc ={ 'name' : br['name']+" - "+name+": "+datetime.datetime.fromtimestamp(int(br['timestamp_start'])).strftime(datetimeformat)+" - "+ str(datetime.timedelta(seconds=(int(br['timestamp_end'])-int(br['timestamp_start'])))),
                        'ch_id' : ch_id[0]['id'],
                        'br_id':br['id'],
                        'start':br['timestamp_start'],
                        'end':br['timestamp_end'],
                        'date':datetime.datetime.fromtimestamp(int(br['timestamp_start'])).strftime("%Y-%m-%dT%H:%M:%S")}
                if 'photo' in br: 
                    sc['img'] = str(br['photo']['url']).replace("{size}",'300')
                elif 'poster'in br:
                    sc['img'] = str(br['photo']['url']).replace("{size}",'300')
                else:
                    sc['img'] = 'DefaultVideo.png'
                if'description' in br:
                    sc['info']=br['description']
                else:
                    sc['info']=br['name']
                if'year' in br:
                    sc['year']=br['year']
                else:
                    sc['year']=None
                if isSeries:
                    sc['series']=1
                else:
                    sc['series']=0
                genres=[]
                for tag in br['ids_tag']:
                    genres.append(tags['tags'][str(tag)]['name'])
                if len(genres)>0:
                    sc['genre']=genres
                else:
                    sc['genre']=""
                sc['broadcast_id']=br['id']
                subcast.append(sc)
        return subcast


    #function return content (series/playable items) Used in main.py
    def get_content(self,id,episode,q=None):
        
        if not episode:
            dat=self._get_tagcontent(id)  
        if q:
            dat=self._get_search_result(q)
        if episode:
            dat=self._get_episode(id)
        
        return dat  

    # Generate playlist. Used in service.py
    def generateplaylist(self, playlistpath):
        if self.progress:
                self.progress.setpozition(40)

        channels = self.get_channels()

        if self.progress:
                scale=60/len(channels)
        i=1

        with codecs.open(playlistpath , 'w',encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for channel in channels:
                if self.progress:
                    self.progress.setpozition(i*scale+40)
                i=i+1

                # for IPTV Simple client
                radio=""
                if channel['type'] =='radio':
                    radio=" radio=\"true\" "
                strtmp="#EXTINF:-1 tvg-id=\""+str(channel['id_epg'])+"\" tvg-name=\""+channel['tvg-name']+"\" tvg-logo=\""+channel['tvg-logo']+"\" "+radio+", "+channel['name']+"\n"+channel['content_source']
                f.write("%s\n" % strtmp)

    # Generate EPG. Used in service.py
    def generateepg(self,epgpath,hourspast=1,hoursfuture=1):

        guide = minidom.Document() 
        tags=self.dl_4KATV_tags()
 
       # epg_xml=minidom.parse(epgpath)

        tv = guide.createElement('tv') 
        
        #Get channels
        if self.progress:
                self.progress.setpozition(10)
        channels = self.get_channels()


        j=self.dl_4KATV_epg_json(hourspast,hoursfuture)

        if self.progress:
                self.progress.setpozition(15)

        if self.progress:
            scale=20/len(channels)
        i=1
        for chnl in channels:
            if self.progress:
                self.progress.setpozition(i*scale+25)
            i=i+1

            channel=guide.createElement('channel')
            channel.setAttribute('id',str(chnl['id_epg']))
            display_name=guide.createElement('display-name')
            display_name.setAttribute('lang','sk')
            display_name.appendChild(guide.createTextNode(chnl['name']))
            channel.appendChild(display_name)
            icon=guide.createElement('icon')
            icon.setAttribute('src',chnl['tvg-logo'])
            channel.appendChild(icon)
            tv.appendChild(channel)
  
        tz=time.timezone
        m, s = divmod(tz, 60)
        h, m = divmod(m, 60)
        if tz >=0:
            timez="+"+'{0:02d}'.format(h)+'{0:02d}'.format(m)
        else:
            timez='{0:03d}'.format(h)+'{0:02d}'.format(m)

        if self.progress:
            scale=55/len(channels)
        i=1
        for channel in channels:
            if self.progress:
                self.progress.setpozition(i*scale+45)
            i=i+1
            for prg in j['broadcasts'][str(channel['id_epg'])]:
                programme=guide.createElement('programme')
                programme.setAttribute('channel',str(prg['id_epg']))
                startdt=datetime.datetime.utcfromtimestamp(prg['timestamp_start']+tz)
                programme.setAttribute('start',str(startdt.strftime("%Y%m%d%H%M%S " ))+timez)
                stopdt=datetime.datetime.utcfromtimestamp(prg['timestamp_end']+tz)
                programme.setAttribute('stop',str(stopdt.strftime("%Y%m%d%H%M%S "))+timez)
                title=guide.createElement('title')
                title.setAttribute('lang','sk')
                title.appendChild(guide.createTextNode(prg['name']))
                programme.appendChild(title)
                desc=guide.createElement('desc')
                desc.setAttribute('lang','sk')

                if 'description_broadcast' in prg and prg['description_broadcast']!=None:
                    desc.appendChild(guide.createTextNode(prg['description_broadcast']))
                else:
                    desc.appendChild(guide.createTextNode(" "))
                programme.appendChild(desc)
                dat=guide.createElement('year')
                if 'year' in prg:
                    dat.appendChild(guide.createTextNode(str(prg['year'])))
                else:
                    dat.appendChild(guide.createTextNode(" "))
                programme.appendChild(dat)

             
                for tag in prg['ids_tag']:
                    category=guide.createElement('category')
                    category.setAttribute('lang','sk')
                    category.appendChild(guide.createTextNode(tags['tags'][str(tag)]['name']))
                    programme.appendChild(category)

                icon=guide.createElement('icon')
                if 'photo' in prg:
                    icon.setAttribute('src',str(prg['photo']['url']).replace("{size}",'300'))
                programme.appendChild(icon)
                

                tv.appendChild(programme)

        guide.appendChild(tv) 

        xml_str = guide.toprettyxml(indent ="\t", encoding="utf-8")  

        with codecs.open(epgpath, "wb") as f: 
            f.write(xml_str)  

    #function for download raw  channel JSON  
    def dl_4KATV_channels(self):
        data = {'device_token' : self.device_token}
  
        req_src = self._post('https://backoffice.swan.4net.tv/api/device/getSources', data)
        j = req_src.json()

        
        if  j['success']==False:
            raise StreamNotResolvedException(j['message'])

        return j

    #function for download raw tags JSON 
    def dl_4KATV_tags(self):
       
        data={"lng_priority" :self.lang}

        req_tag = self._post('https://epg.swan.4net.tv/v2/export/tag',data,)
        j = req_tag.json()
        if  j['error']==True:
            raise StreamNotResolvedException(j['message'])

        return j

    #function for download raw channels groups JSON 
    def dl_4KATV_allchannelgroups(self):
        data = {'device_token' : self.device_token}

        req_all_ch_grp = self._post('https://backoffice.swan.4net.tv/api/device/getAllChannelGroups', data)

        j = req_all_ch_grp.json()
    
        return j

    #function for download raw epg JSON 
    def dl_4KATV_epg_json(self,hourspast=1,hoursfuture=1):

        bec = self.dl_4KATV_allchannelgroups()
        
        today=datetime.datetime.now()
        #today.replace(tzinfo='timezone.utc').astimezone(tz=None)
        fromdat=today-datetime.timedelta(hours=hourspast)
        todat=today+datetime.timedelta(hours=hoursfuture)
        fromdt=int((fromdat-datetime.datetime(1970,1,1)).total_seconds())
        todt=int((todat-datetime.datetime(1970,1,1)).total_seconds())

        epg_ids=[]
        for broad_ch_epgs in bec["channel_groups"]:
            broad_ch_epg=broad_ch_epgs['channels']
            for ch in broad_ch_epg:
                epg_ids.append(ch["id_epg"])

        data={'lng_priority':self.lang,
            "ids_epg":epg_ids,
            "from":fromdt,
            "to":todt
             }
        req_broadcast = self._post('https://epg.swan.4net.tv/v2/epg', data)

        j = req_broadcast.json()

        return j
    

       
    #function for save raw json from 4KAtv (swan). Not used now. It will be used for debug from service.py(for example)
    #when raw json is saved to user data addon directory
    def save_4KATV_jsons(self,hourspast=1,hoursfuture=1):
        j=self.dl_4KATV_channels()
        with open(os.path.join(self.datapath,'sources-channel.json'), 'w') as json_file:
            json.dump(j, json_file,indent=4)
            json_file.close()


        j=self.dl_4KATV_tags()
        with open(os.path.join(self.datapath,'tags.json'), 'w') as json_file:
            json.dump(j, json_file,indent=4)
            json_file.close()

        j=self.dl_4KATV_epg_json(hourspast,hoursfuture)
        with open(os.path.join(self.datapath,'broadcast-epg.json'), 'w') as json_file:
            json.dump(j, json_file,indent=4)
            json_file.close()

    #Function for generate channels dict for IPTV manager
    def get_iptvm_channels(self):

        channels = self.get_channels()
        channels_ret = []
        for channel in channels:
            rad=False
            if channel['type'] =='radio':
                rad=True

            channels_ret.append(dict(
            id=str(channel['id_epg']),
            name=channel['name'],
            logo=channel['tvg-logo'],
            stream=channel['content_source'],
            radio=rad          
            ))
        return channels_ret
    
    #Function for generate epg dict for IPTV manager
    def get_iptvm_epg(self,hourspast,hoursfutre):
        from collections import defaultdict
        import re
        j=self.dl_4KATV_epg_json(hourspast,hoursfutre)
        tags=self.dl_4KATV_tags()
        tz=time.timezone
        m, s = divmod(tz, 60)
        h, m = divmod(m, 60)
        if tz >=0:
            timez="+"+'{0:02d}'.format(h)+'{0:02d}'.format(m)
        else:
            timez='{0:03d}'.format(h)+'{0:02d}'.format(m)
        epg=dict()
        
        for k in j['broadcasts'].keys():
            for prg in j['broadcasts'][str(k)]:
                stopdt=datetime.datetime.utcfromtimestamp(prg['timestamp_end']+tz)
                startdt=datetime.datetime.utcfromtimestamp(prg['timestamp_start']+tz)
                chnl_id=str(prg['id_epg'])
                if not chnl_id in epg:
                    epg[chnl_id]=[]
                
                genres=[]
                for tag in prg['ids_tag']:
                    genres.append(tags['tags'][str(tag)]['name'])
                if len(genres)>0:
                    genre=genres
                else:
                    genre=""

                if 'photo' in prg:
                    image=str(prg['photo']['url']).replace("{size}",'300')
                else:
                    image=""
                
                if 'description_broadcast' in prg:
                    description=prg['description_broadcast']
                else:
                    description=""

                if 'year' in prg:
                    date=str(prg['year'])
                else:
                    date=""

                epg[chnl_id].append(dict(
                start=str(startdt.strftime("%Y%m%d%H%M%S " ))+timez,
                stop=str(stopdt.strftime("%Y%m%d%H%M%S "))+timez,
                title=prg['name'],
                description=description,
                genre=genre,
                image=image,
                date=date,
                broadcast_id=prg['id'])          
                )
           
        return epg
            