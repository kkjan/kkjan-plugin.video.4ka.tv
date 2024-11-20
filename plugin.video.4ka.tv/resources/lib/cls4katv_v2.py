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
from resources.lib.functions import get_proxy
import os


_COMMON_HEADERS = { "User-Agent" :	"okhttp/3.12.1",
                    "Connection": "Keep-Alive"}
_ArchiveHour = 240 #167-7 day, 240-10 day archive -1 hour



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
        self.additionallang=['ces']
        if progress:
            self.progress=progress
        else:
            self.progress=None


    def _post(self,url,data):
        proxies=get_proxy()
        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"

        MAX_RETRY=5
        for i in range(MAX_RETRY):
            try:
                res = requests.post(url, json=data, headers=headers,proxies=proxies,timeout=(5,120))
                break
            except requests.exceptions.Timeout:
                logDbg("Download error TIMEOUT (retry {}): {}".format(i,url))
                time.sleep(5)
            except requests.exceptions.TooManyRedirects:
                logDbg("Download error TOMANY REDIRECTS (retry {}): {}".format(i,url))
                time.sleep(5)
            except requests.exceptions.RequestException as e:
                logDbg("Download error (retry {}): {} error details: {} ".format(i,url,e))
                time.sleep(5)
        return res

    def _get(self,url,param):
        proxies=get_proxy()
        headers = _COMMON_HEADERS
        MAX_RETRY=5
        for i in range(MAX_RETRY):
            try:
                res=requests.get(url,param,headers=headers,proxies=proxies,timeout=(5,120))
                break
            except requests.exceptions.Timeout:
                logDbg("Download error TIMEOUT (retry {}): {}".format(i,url))
                time.sleep(5)
            except requests.exceptions.TooManyRedirects:
                logDbg("Download error TOMANY REDIRECTS (retry {}): {}".format(i,url))
                time.sleep(5)
            except requests.exceptions.RequestException as e:
                logDbg("Download error (retry {}): {} error details: {}".format(i,url,e))
                time.sleep(5)
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
    def get_4KATV_stream(self, ch_id,start,stop):
        data = {'device_token' : self.device_token,
                 'channel_id':ch_id,
                 'start':start,
                 'end':stop}

        req = self._get('https://backoffice.swan.4net.tv/contentd/api/device/getContent',data)
        j = req.json()
        if(j['success']==True):
            return j['stream_uri'].replace("&eta=1","")
        else:
            logDbg("get_4KATV_stream: "+j['message'])
            raise DeviceNotAuthorizedToPlayException('Detail: '+j['message'])

    #function for get channel and EPG for live stream. Used in main.py
    def get_channels_live(self,type='tv'):
        ch =list()
        self.channels.clear()
        j=self.dl_4KATV_channels()
        epg=self.dl_4KATV_epg_json(hourspast=6,hoursfuture=6)
        now=time.time()
        tags=self.dl_4KATV_tags()
        #datetimeformat=xbmc.getRegion('dateshort').replace('%-', '%').replace('%#', '%') +" "+"%H:%M"
        datetimeformat=xbmc.getRegion('dateshort').replace('%-', '%').replace('%#', '%') +" "+xbmc.getRegion('time')
        for channel in j['channels']:

            if channel['type']==type:
                if str(channel['id_epg']) in epg['broadcasts']: 
                    #ch_ids=list(filter(lambda x:x["id_epg"]==channel['id_epg'],epg['broadcasts']))
                    ch_ids=epg['broadcasts'][str(channel['id_epg'])]
  
                     # ch_ids_curr=list(filter(lambda x:x["live"]==True,ch_ids))
             
                    ch_ids1=list(filter(lambda x:x["timestamp_end"]>now,ch_ids))
                    ch_ids_curr=list(filter(lambda x:x["timestamp_start"]<now,ch_ids1))
                
                if ch_ids_curr:
                    ch_ids_next=list(filter(lambda x:x["timestamp_start"]==ch_ids_curr[0]['timestamp_end'],ch_ids))
                else:
                    ch_ids_next=""
                
                ch={}
                
                ch['programme'] ={'channelid':channel['id'],
                    'title': ch_ids_curr[0]['name_show'] if ch_ids_curr[0]['name_show'] else ch_ids_curr[0]['name'],
                    'sub_title':ch_ids_curr[0]['name'] if ch_ids_curr[0]['name_show'] and ch_ids_curr[0]['name_show'] != ch_ids_curr[0]['name'] else "",
                    'next_prg_name': ch_ids_next[0]['name'] if ch_ids_next else " ",
                    'next_prg_start': ch_ids_next[0]['timestamp_start'] if ch_ids_next else 0,
                    'next_prg_stop': ch_ids_next[0]['timestamp_end'] if ch_ids_next else 0,
                    'id_epg' : channel['id_epg'],
                    'tvg-name' : channel['name'].replace(" ","_"),
                    'start':ch_ids_curr[0]['timestamp_start'],
                    'stop':ch_ids_curr[0]['timestamp_end'],
                    'duration' : int(ch_ids_curr[0]['timestamp_end'])-int(ch_ids_curr[0]['timestamp_start']) if ch_ids_curr else 0,
                    'dateadded': datetime.datetime.fromtimestamp(int(ch_ids_curr[0]['timestamp_start'])).strftime("%Y-%m-%dT%H:%M:%S"),
                    'content_source' :  channel['content_sources'][0]['stream_profile_urls']['adaptive'].replace("&eta=1",""),
                    'type' :  channel['type'],
                    'broadcast_id': ch_ids_curr[0]['id'] if ch_ids_curr else " ",
                    'series' :768 in ch_ids_curr[0]['ids_tag'] or ('periodical' in ch_ids_curr[0] and ch_ids_curr[0]['periodical']) ,
                    'movie' : 777 in ch_ids_curr[0]['ids_tag'],
                    'series_number' : ch_ids_curr[0]['number_series'] if 'number_series' in ch_ids_curr[0] and ch_ids_curr[0] else None,
                    'episode_number' : ch_ids_curr[0]['number_episode'] if 'number_episode' in ch_ids_curr[0] else None,
                    'series_name' : ch_ids_curr[0]['series_name'] if 'series_name' in ch_ids_curr[0] and ch_ids_curr[0] else None,
                    'episode_name' : ch_ids_curr[0]['name_episode'] if 'name_episode' in ch_ids_curr[0] else None,
                    'playable' : True}
                
                if (ch['programme']['episode_number'] and ch['programme']['series_number']):
                    episode='S{:02d}E{:02d}'.format(ch['programme']['series_number'],ch['programme']['episode_number'])
                elif(ch['programme']['episode_number']):
                    episode='E{:02d}'.format(ch['programme']['episode_number'])
                elif(ch['programme']['series_number']):
                    episode='S{:02d}'.format(ch['programme']['series_number'])
                else:
                    episode=None
                ch['programme'] ['episode'] =  episode
                

                ch['channel']={
                     'channelname' : channel['name'],
                     'channelid':channel['id'],
                     "thumbnail":"https://epg.swan.4net.tv/files/channel_logos/"+str(channel['id'])+".png",
                }
                plot=''
                if ch_ids_curr and  'name_episode' in ch_ids_curr[0] and ch_ids_curr[0]['name_episode']!=None:
                    plot+=ch_ids_curr[0]['name_episode']+'[CR]'
                if ch_ids_curr and  'description_broadcast' in ch_ids_curr[0] and ch_ids_curr[0]['description_broadcast']!=None:
                    plot += ch_ids_curr[0]['description_broadcast']

                ch['programme'] ['plot']=plot

                ch['programme'] ['img'] = ''
                ch['programme'] ['photo'] = None
                ch['programme'] ['poster'] = None
                if ch_ids_curr and  'poster' in ch_ids_curr[0]:
                    ch['programme'] ['img'] =  str(ch_ids_curr[0]['poster']['url']).replace("{size}",'300')
                    ch['programme'] ['poster'] = str(ch_ids_curr[0]['poster']['url']).replace("{size}",'300')
                if ch_ids_curr and 'photo' in ch_ids_curr[0]: 
                    ch['programme'] ['img'] = str(ch_ids_curr[0]['photo']['url']).replace("{size}",'300')
                    ch['programme'] ['photo'] = str(ch_ids_curr[0]['photo']['url']).replace("{size}",'300')
                
                
                genres=[]
                for tag in ch_ids_curr[0]['ids_tag']:
                    genres.append(tags['tags'][str(tag)]['name'])
                ch['programme'] ['genres']=genres

                if ch_ids_curr and 'year' in ch_ids_curr[0]:
                    ch['programme'] ['year']=ch_ids_curr[0]['year']
                else:
                    ch['programme'] ['year']=None
                ch['programme']['actors']=j['broadcast']['actors'] if 'actors' in ch_ids_curr[0] else None
                ch['programme']['directors']=j['broadcast']['directors'] if 'directors' in ch_ids_curr[0] else None
                ch['programme']['description_show']=j['broadcast']['description_show'] if 'description_show' in ch_ids_curr[0] else None
                self.channels.append(ch)
        return self.channels    

    #function return channels from channels json Used in main.py
    def get_channels(self):
        ch =list()
        self.channels.clear()
        j=self.dl_4KATV_channels()
        for channel in j['channels']:
            ch ={ 'name' : channel['name'],
                'id' : channel['id'],
                'id_epg' : channel['id_epg'],
                'tvg-name' : channel['name'].replace(" ","_"),
                'tvg-logo' : "https://epg.swan.4net.tv/files/channel_logos/"+str(channel['id'])+".png",
                'content_source' :  channel['content_sources'][0]['stream_profile_urls']['adaptive'],
                'type' :  channel['type'],
                'catchup_length':channel['catchup_length']}
            self.channels.append(ch)
        return self.channels    

    #function return category from tags json Used in main.py
    def get_4KATVtags(self,allTags=False):
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
            if(allTags or j['tags'][scid]['show_in_dashboard']==True):
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
         #get archived/playable items. Its caused if basic archive or full archive is  used:
        sources=list(filter(lambda x:x["catchup_length"]!= None and  x["catchup_length"]>0,self.dl_4KATV_channels()['channels']))
        sources_ids=list(map(lambda x: x['id'], sources))#Playable archive channels
        for ch in broad_ch_epg:
            if(ch['id'] in sources_ids):
                    archived_epg_ids.append(ch["id_epg"])
        archived_epg_ids.sort()

        return archived_epg_ids

    #function return episodes
    def get_episodesdes(self,id):
        broad_ch_epg=self._get_broad_ch_epg()
        epg_ids=self._get_epg_ids(broad_ch_epg)
        lng=[]
        lng.append(self.lang)
        data={
            'hours_back':_ArchiveHour,
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
            logDbg("BR: "+json.dumps(brd))
            tmp=brd
            tmp['ids_tag']=j['broadcast']['ids_tag']
            tmp['id_epg']=brd['broadcasts'][0]['id_epg']
            tmp['id_broadcast']=brd['broadcasts'][0]['id_broadcast']
            tmp['timestamp_start']=brd['broadcasts'][0]['timestamp_start']
            tmp['timestamp_end']=brd['broadcasts'][0]['timestamp_end']
            tmp['photo']=brd['broadcasts'][0]['photo']
            tmp['poster']=brd['broadcasts'][0]['poster']
            tmp['playable']=True
            tmp['periodical']=j['broadcast']['periodical']
            tmp['id']=brd['broadcasts'][0]['id_broadcast']
            tmp['name_show']=j['broadcast']['name_show']
            tmp['number_series']=brd['series_number'] if 'series_number' in brd else None
            tmp['number_episode']=brd['episode_number'] if 'episode_number' in brd else None
            tmp['name_series']=j['broadcast']['name_series'] if 'name_series' in j['broadcast'] else None
            tmp['name_episode']=brd['name_episode'] if 'name_episode' in brd else None
            tmp['actors']=j['broadcast']['actors'] if 'actors' in j['broadcast'] else None
            tmp['directors']=j['broadcast']['directors'] if 'directors' in j['broadcast'] else None
            tmp['description_show']=j['broadcast']['description_show'] if 'description_show' in j['broadcast'] else None
            dat.append(tmp)
            logDbg('number_series: '+json.dumps(brd['broadcasts']))
            
       
        return self._prepare_content(dat,broad_ch_epg)
    
    #function return broadcast detail
    def get_broadcastdetail(self,id):
        broad_ch_epg=self._get_broad_ch_epg()
        epg_ids=self._get_epg_ids(broad_ch_epg)
        lng=[]
        lng.append(self.lang)
        data={
            'hours_back':_ArchiveHour,
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
        logDbg("BR: "+json.dumps(j['broadcast'],indent=4))
        tmp=j['broadcast']
        tmp['description']=j['broadcast']['description_broadcast']
        dat.append(tmp)

        return self._prepare_content(dat,broad_ch_epg)[0]
    
    #private function return data from search
    def get_search_result(self,q):
        broad_ch_epg=self._get_broad_ch_epg()
        epg_ids=self._get_epg_ids(broad_ch_epg)
        special_epg_from=self._get_special_epg_ids(broad_ch_epg)
        lng=[]
        lng.append(self.lang)
        lng+=self.additionallang
        data={
                'hours_back':_ArchiveHour,
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
        
        broadcast=[]
        for brd in j['broadcasts']:
            brd['description']=brd['description_broadcast']
            broadcast.append(brd)
        return self._prepare_content(broadcast,broad_ch_epg)

    #private function return content info for tags
    def get_tagcontent(self,id):
        broad_ch_epg=self._get_broad_ch_epg()
        lng=[]
        lng.append(self.lang)
        lng+=self.additionallang
        epg_ids=self._get_epg_ids(broad_ch_epg)
        special_epg_from=self._get_special_epg_ids(broad_ch_epg)
        data={
                'hours_back':_ArchiveHour,
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
        for br in dat:
            sc={}
            if(br["id_epg"] in archived_epg_ids):
                ch_id=list(filter(lambda x:x["id_epg"]==br['id_epg'],broad_ch_epg))
                isSeries=768 in br['ids_tag'] or ('periodical' in br and br['periodical']) #768-id for Series tag
                name= ''
                if br['name_episode'] !=None:
                    name+=": "+br['name_episode']
               
               
                if(not isSeries or  ('playable' in br and br['playable'])):
                   
                    sc['programme'] ={'title' : br['name_show'] if 'name_show' in br and br['name_show']!=None else br['name'],
                        'sub_title':br['name']+name if 'name_show' in br and br['name_show']!=None and br['name_show'] != br['name'] else '',
                        'channelid' : ch_id[0]['id'],
                        'broadcast_id':br['id'],
                        'start':br['timestamp_start'],
                        'stop':br['timestamp_end'],
                        'duration':int(br['timestamp_end'])-int(br['timestamp_start']),
                        'dateadded':datetime.datetime.fromtimestamp(int(br['timestamp_start'])).strftime("%Y-%m-%dT%H:%M:%S"),
                        }
                else:
                    sc['programme']  ={'title' : br['name_show'] if br['name_show'] else br['name'],
                        'sub_title':br['name']+name if br['name_show'] and br['name_show'] != br['name'] else name,
                        'channelid' : ch_id[0]['id'],
                        'broadcast_id':br['id'],
                        'start':br['timestamp_start'],
                        'stop':br['timestamp_end'],
                        'duration':int(br['timestamp_end'])-int(br['timestamp_start']),
                        'dateadded':datetime.datetime.fromtimestamp(int(br['timestamp_start'])).strftime("%Y-%m-%dT%H:%M:%S")}

                sc['programme'] ['img'] = 'DefaultVideo.png'
                sc['programme'] ['poster'] =None
                sc['programme'] ['photo'] =None
                if 'poster'in br:
                    sc['programme'] ['img'] = str(br['photo']['url']).replace("{size}",'300')
                    sc['programme'] ['poster'] = str(br['poster']['url']).replace("{size}",'300')
                if 'photo' in br: 
                    sc['programme'] ['img'] = str(br['photo']['url']).replace("{size}",'300')
                    sc['programme'] ['photo'] = str(br['photo']['url']).replace("{size}",'300')
                
                
                sc['programme'] ['plot']=br['description'] if 'description' in br else br['name']                
                sc['programme'] ['year']=int(br['year']) if'year' in br and br['year'] else None
                sc['programme'] ['series']=isSeries
                sc['programme'] ['movie']=777 in br['ids_tag']
                sc['programme'] ['playable']=True  if 'playable' in br and br['playable'] else False
                
                genres=[]
                for tag in br['ids_tag']:
                    genres.append(tags['tags'][str(tag)]['name'])
                sc['programme'] ['genres']=genres

                sc['programme'] ['series_number'] = br['number_series'] if 'number_series' in br and br['number_series'] else None
                sc['programme'] ['episode_number'] = br['number_episode'] if 'number_episode' in br and br['number_episode'] else None
                

                sc['programme'] ['series_name'] = br['name_series'] if 'name_series' in br and br['name_series'] else None
                sc['programme'] ['episode_name'] = br['name_episode'] if 'name_episode' in br and br['name_episode'] else None

                if (sc['programme'] ['episode_number']and sc['programme'] ['series_number']):
                    episode='S{:02d}E{:02d}'.format(sc['programme'] ['series_number'],sc['programme'] ['episode_number'])
                elif(sc['programme'] ['episode_number']):
                    episode='E{:02d}'.format(sc['programme'] ['episode_number'])
                elif(sc['programme'] ['series_number']):
                    episode='S{:02d}'.format(sc['programme'] ['series_number'])
                else:
                    episode=None
                sc['programme'] ['episode'] =  episode
                sc['channel']={
                     'channelname' : ch_id[0]['name'],
                     'channelid':ch_id[0]['id'],
                     "thumbnail":"https://epg.swan.4net.tv/files/channel_logos/"+str(ch_id[0]['id'])+".png",
                }

                sc['programme'] ['actors']=br['actors'].split(", ") if 'actors' in br and br['actors']  else None       
                sc['programme'] ['directors']=br['directors'].split(", ")  if 'directors' in br  and br['directors'] else None
                sc['programme'] ['description_show']=br['description_show'] if 'description_show' in br else None

                sc['programme'] ['url_csfd']=br['url_csfd'] if 'url_csfd' in br else None
                sc['programme'] ['url_imdb']=br['url_imdb'] if 'url_imdb' in br else None
                sc['programme'] ['type']=br['type'] if 'type' in br else None
                sc['programme'] ['rating']=br['rating'] if 'rating' in br else None
                sc['programme'] ['description_broadcast']=br['description_broadcast'] if 'description_broadcast' in br else None
         
                
    

               

                subcast.append(sc)
        return subcast
 

    # Generate playlist. Used in service.py
    def generateplaylist(self, playlistpath):
        if self.progress:
                self.progress.setposition(40)

        channels = self.get_channels()

        if self.progress:
                scale=60/len(channels)
        i=1

        with codecs.open(playlistpath , 'w',encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for channel in channels:
                if self.progress:
                    self.progress.setposition(i*scale+40)
                i=i+1

                # for IPTV Simple client
                radio=""
                if channel['type'] =='radio':
                    radio=" radio=\"true\" "
                strtmp="#EXTINF:-1 tvg-id=\""+str(channel['id_epg'])+"\" tvg-name=\""+channel['tvg-name']+"\" tvg-logo=\""+channel['tvg-logo']+"\" "+radio+"group-title=\"4KA TV\""+", "+channel['name']+"\n"+channel['content_source'].replace("&eta=1","")
                f.write("%s\n" % strtmp)

    # Generate EPG. Used in service.py
    def generateepg(self,epgpath,hourspast=1,hoursfuture=1):

        guide = minidom.Document() 
        tags=self.dl_4KATV_tags()
 
       # epg_xml=minidom.parse(epgpath)

        tv = guide.createElement('tv') 
        
        #Get channels
        if self.progress:
                self.progress.setposition(10)
        channels = self.get_channels()


        j=self.dl_4KATV_epg_json(hourspast,hoursfuture)

        if self.progress:
                self.progress.setposition(15)

        if self.progress:
            scale=20/len(channels)
        i=1
        for chnl in channels:
            if self.progress:
                self.progress.setposition(i*scale+25)
            i=i+1
            logDbg("Generate EPG channels: "+chnl['name'])
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
  
        tz=-time.timezone
        m, s = divmod(tz, 60)
        h, m = divmod(m, 60)
        if tz >=0:
            timez="+"+'{0:02d}'.format(h)+'{0:02d}'.format(m)
        else:
            timez='{0:03d}'.format(h)+'{0:02d}'.format(m)

        if self.progress:
            scale=55/len(channels)
        i=1
        #for channel in channels:
        for k in j['broadcasts'].keys():
            if self.progress:
                self.progress.setposition(i*scale+45)
            i=i+1
            for prg in j['broadcasts'][str(k)]:
            #for prg in j['broadcasts'][str(channel['id_epg'])]:
                programme=guide.createElement('programme')
                programme.setAttribute('channel',str(prg['id_epg']))
                startdt=datetime.datetime.fromtimestamp(prg['timestamp_start'])
                programme.setAttribute('start',str(startdt.strftime("%Y%m%d%H%M%S " ))+timez)
                stopdt=datetime.datetime.fromtimestamp(prg['timestamp_end'])
                programme.setAttribute('stop',str(stopdt.strftime("%Y%m%d%H%M%S "))+timez)

                name= ''
                if prg['name_episode'] !=None:
                    name+=": "+prg['name_episode']  
                tit=prg['name_show'] if 'name_show' in prg and prg['name_show']!=None else prg['name']
                subtit= prg['name']+name if 'name_show' in prg and prg['name_show']!=None and prg['name_show'] != prg['name'] else ''
                title=guide.createElement('title')
                title.setAttribute('lang','sk')
                title.appendChild(guide.createTextNode(tit))
                programme.appendChild(title)
                
                subtitle=guide.createElement('sub-title')
                subtitle.setAttribute('lang','sk')
                subtitle.appendChild(guide.createTextNode(subtit))
                programme.appendChild(subtitle)

                if (prg['number_episode'] and prg['number_series']):
                    episode='{:02d}.{:02d}.0/1'.format(prg['number_series']-1,prg['number_episode']-1)
                elif(prg['number_series']):
                    episode='{:02d}..'.format(prg['number_series']-1)
                else:
                    episode=None
                if(episode):    
                    episodenum=guide.createElement('episode-num')
                    episodenum.setAttribute('system','xmltv_ns')
                    episodenum.appendChild(guide.createTextNode(episode))
                    programme.appendChild(episodenum)

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
    
        today=datetime.datetime.now()
        #today.replace(tzinfo='timezone.utc').astimezone(tz=None)
        fromdat=today-datetime.timedelta(hours=hourspast)
        todat=today+datetime.timedelta(hours=hoursfuture)
        fromdt=int((fromdat-datetime.datetime(1970,1,1)).total_seconds())
        todt=int((todat-datetime.datetime(1970,1,1)).total_seconds())

        j = self.dl_4KATV_epg_json_timerange(fromdt,todt)

        return j
    

    #function for download raw epg JSON 
    def dl_4KATV_epg_json_timerange(self,fromts,tots):
        broad_ch_epg =self._get_broad_ch_epg()
        epg_ids=self._get_epg_ids(broad_ch_epg)
        data={'lng_priority':self.lang,
            "ids_epg":epg_ids,
            "from":fromts,
            "to":tots
                }
        req_broadcast = self._post('https://epg.swan.4net.tv/v2/epg', data)
        logDbg("dl_4KATV_epg_json_timerange "+', '.join(str(e) for e in epg_ids))
        j = req_broadcast.json()

        return j
       
    #function for save raw json from 4KAtv (swan). Not used now. It will be used for debug from service.py(for example)
    #when raw json is saved to user data addon directory
    def save_4KATV_jsons(self,hourspast=1,hoursfuture=1):
        j=self.dl_4KATV_channels()
        with open(os.path.join(self.datapath,'channel-sources.json'), 'w') as json_file:
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

        j=self.dl_4KATV_allchannelgroups() 
        with open(os.path.join(self.datapath,'channel-groups.json'), 'w') as json_file:
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

        j=self.dl_4KATV_epg_json(hourspast,hoursfutre)
        tags=self.dl_4KATV_tags()
        tz=-time.timezone
        m, s = divmod(tz, 60)
        h, m = divmod(m, 60)
        if tz >=0:
            timez="+"+'{0:02d}'.format(h)+'{0:02d}'.format(m)
        else:
            timez='{0:03d}'.format(h)+'{0:02d}'.format(m)
        epg=dict()
        
        for k in j['broadcasts'].keys():
            for prg in j['broadcasts'][str(k)]:
                stopdt=datetime.datetime.fromtimestamp(prg['timestamp_end'])
                startdt=datetime.datetime.fromtimestamp(prg['timestamp_start'])
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
                title=prg['name']
                subtitle=prg['name']

                name= ''
                if prg['name_episode'] !=None:
                    name+=": "+prg['name_episode']                     
                title=prg['name_show'] if 'name_show' in prg and prg['name_show']!=None else prg['name']
                subtitle= prg['name']+name if 'name_show' in prg and prg['name_show']!=None and prg['name_show'] != prg['name'] else ''
                if (prg['number_episode'] and prg['number_series']):
                    episode='S{:02d}E{:02d}'.format(prg['number_series'],prg['number_episode'])
                elif(prg['number_episode']):
                    episode='E{:02d}'.format(prg['number_episode'])
                elif(prg['number_series']):
                    episode='S{:02d}'.format(prg['number_series'])
                else:
                    episode=None
                epg[chnl_id].append(dict(
                start=str(startdt.strftime("%Y%m%d%H%M%S "))+timez,
                stop=str(stopdt.strftime("%Y%m%d%H%M%S "))+timez,
                title=title,
                subtitle=subtitle,
                description=description,
                genre=genre,
                image=image,
                date=date,
                episode=episode,
                broadcast_id=prg['id'])          
                )
        return epg
    
    def get_archive_epg(self,id_epg,fromts,tots):
        j=self.dl_4KATV_epg_json_timerange(fromts,tots)
        tags=self.dl_4KATV_tags()
        brcasts=[]
        for br in j['broadcasts'][id_epg]:
            isSeries=768 in br['ids_tag'] or ('periodical' in br and br['periodical'])
            name= ''
            if br['name_episode'] !=None:
                name+=": "+br['name_episode']
            sc={}               
            if(not isSeries ):

                sc['programme'] ={'title' : br['name_show'] if 'name_show' in br and br['name_show']!=None else br['name'],
                    'sub_title':br['name']+name if 'name_show' in br and br['name_show']!=None and br['name_show'] != br['name'] else '',
                    #'channelid' : ch_id[0]['id'],
                    'broadcast_id':br['id'],
                    'start':br['timestamp_start'],
                    'stop':br['timestamp_end'],
                    'duration':int(br['timestamp_end'])-int(br['timestamp_start']),
                    'dateadded':datetime.datetime.fromtimestamp(int(br['timestamp_start'])).strftime("%Y-%m-%dT%H:%M:%S"),
                    }
            else:
                sc['programme']  ={'title' : br['name_show'] if br['name_show'] else br['name'],
                    'sub_title':br['name']+name if br['name_show'] and br['name_show'] != br['name'] else name,
                    #'channelid' : ch_id[0]['id'],
                    'broadcast_id':br['id'],
                    'start':br['timestamp_start'],
                    'stop':br['timestamp_end'],
                    'duration':int(br['timestamp_end'])-int(br['timestamp_start']),
                    'dateadded':datetime.datetime.fromtimestamp(int(br['timestamp_start'])).strftime("%Y-%m-%dT%H:%M:%S")}

            sc['programme'] ['img'] = 'DefaultVideo.png'
            sc['programme'] ['poster'] =None
            sc['programme'] ['photo'] =None
            if 'poster'in br:
                sc['programme'] ['img'] = str(br['photo']['url']).replace("{size}",'300')
                sc['programme'] ['poster'] = str(br['poster']['url']).replace("{size}",'300')
            if 'photo' in br: 
                sc['programme'] ['img'] = str(br['photo']['url']).replace("{size}",'300')
                sc['programme'] ['photo'] = str(br['photo']['url']).replace("{size}",'300')
            
            
            sc['programme'] ['plot']=br['description_broadcast'] if 'description_broadcast' in br else br['name']                
            sc['programme'] ['year']=int(br['year']) if'year' in br and br['year'] else None
            sc['programme'] ['series']=isSeries
            sc['programme'] ['movie']=777 in br['ids_tag']
            sc['programme'] ['playable']=True
            
            genres=[]
            for tag in br['ids_tag']:
                genres.append(tags['tags'][str(tag)]['name'])
            sc['programme'] ['genres']=genres

            sc['programme'] ['series_number'] = br['number_series'] if 'number_series' in br and br['number_series'] else None
            sc['programme'] ['episode_number'] = br['number_episode'] if 'number_episode' in br and br['number_episode'] else None
            

            sc['programme'] ['series_name'] = br['name_series'] if 'name_series' in br and br['name_series'] else None
            sc['programme'] ['episode_name'] = br['name_episode'] if 'name_episode' in br and br['name_episode'] else None

            if (sc['programme'] ['episode_number']and sc['programme'] ['series_number']):
                episode='S{:02d}E{:02d}'.format(sc['programme'] ['series_number'],sc['programme'] ['episode_number'])
            elif(sc['programme'] ['episode_number']):
                episode='E{:02d}'.format(sc['programme'] ['episode_number'])
            elif(sc['programme'] ['series_number']):
                episode='S{:02d}'.format(sc['programme'] ['series_number'])
            else:
                episode=None
            sc['programme'] ['episode'] =  episode
            sc['programme'] ['actors']=br['actors'].split(", ") if 'actors' in br and br['actors']  else None       
            sc['programme'] ['directors']=br['directors'].split(", ")  if 'directors' in br  and br['directors'] else None
            sc['programme'] ['description_show']=br['description_show'] if 'description_show' in br else None

            sc['programme'] ['url_csfd']=br['url_csfd'] if 'url_csfd' in br else None
            sc['programme'] ['url_imdb']=br['url_imdb'] if 'url_imdb' in br else None
            sc['programme'] ['type']=br['type'] if 'type' in br else None
            sc['programme'] ['rating']=br['rating'] if 'rating' in br else None
            sc['programme'] ['description_broadcast']=br['description_broadcast'] if 'description_broadcast' in br else None
            brcasts.append(sc)   
        return brcasts

            