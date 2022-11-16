#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Wrapper pre 4KA TV"""
import json
from sys import platform
import requests
import datetime
import time
from xml.dom import minidom 
import codecs
from resources.lib.logger import *
import os
import time
import resources.lib.progress as progressdialogBG

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

    def logdevicestartup(self):
        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"
        data = {'device_token' : self.device_token,
                'application': "3.1.12",
                'firmware': "22" }
        req = requests.post('https://backoffice.swan.4net.tv/api/device/logDeviceStart', json=data,headers=headers)
        j=req.json()
        return j['success']
        
 
    def pairingdevice(self):
        result=-1
        if not self.username or not self.password:
            raise UserNotDefinedException()
        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"
        data = {  'login' : self.username,
                'password' : self.password,
                'id_brand' : 1}
        
                    #Pairing device
        req = requests.post('https://backoffice.swan.4net.tv/api/device/pairDeviceByLogin', json=data,headers=headers)
        j = req.json()
        if j['success']==True:
            self.device_token=j['token']
            data = {'device_token' : self.device_token,
                    'device_type_code' : self.device_type_code,
                    'model' : self.model,
                    'name' : self.name,
                    'serial_number' : self.serial_number }
            req = requests.post('https://backoffice.swan.4net.tv/api/device/completeDevicePairing', json=data,headers=headers)
            return self.device_token
        elif "validation_errors" in j['message'] and j['success']==False:
            raise TooManyDevicesException(j['message']['validation_errors'][0])
        elif j['success']==False:
            raise UserInvalidException()
        else:
            raise PairingException('Detail: '+j['message'])

        
     

    def get_devicesetting(self):
        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"
        data = {'device_token' : self.device_token}
        req = requests.post('https://backoffice.swan.4net.tv/api/getDeviceSettings/', json=data, headers=headers)
        j = req.json()
        self._device_settings=j
        return self._device_settings

        
    
    #function download channel related streams address from swan
    def get_4KATV_stream(self, ch_id,start,end):
        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"
        data = {'device_token' : self.device_token,
                 'channel_id':ch_id,
                 'start':start,
                 'end':end}
        req = requests.get('https://backoffice.swan.4net.tv/contentd/api/device/getContent',data, headers=headers)
        j = req.json()
        return j['stream_uri']


    def get_channels_live(self,type='tv'):
        ch =list()

        j=self.dl_4KATV_channels()
        epg=self.dl_4KATV_epg_json(hourspast=6,hoursfuture=6)
        now=time.time()

        with open(os.path.join(self.datapath,'epg-live-channel.json'), 'w') as json_file:
                json.dump(epg, json_file)
                json_file.close()

        with open(os.path.join(self.datapath,'live-channel.json'), 'w') as json_file:
                json.dump(j, json_file)
                json_file.close()


        #datetimeformat=xbmc.getRegion('dateshort')+" "+xbmc.getRegion('time')
        datetimeformat=xbmc.getRegion('dateshort')+" "+"%H:%M"
        for channel in j['channels']:
            if channel['type']==type:
                ch_ids=list(filter(lambda x:x["epg_id"]==channel['id_epg'],epg['broadcasts']))
                ch_ids1=list(filter(lambda x:x["endTimestamp"]>now,ch_ids))
                ch_ids_curr=list(filter(lambda x:x["startTimestamp"]<now,ch_ids1))
                if ch_ids_curr:
                    ch_ids_next=list(filter(lambda x:x["startTimestamp"]==ch_ids_curr[0]['endTimestamp'],ch_ids1))
                else:
                    ch_ids_next=""
                ch ={ 'name' : channel['name'],
                    'prg_name': ch_ids_curr[0]['name'] if ch_ids_curr else " ",
                    'next_prg_name': ch_ids_next[0]['name'] if ch_ids_next else " ",
                        'next_prg_start': datetime.datetime.fromtimestamp(int(ch_ids_next[0]['startTimestamp'])).strftime(datetimeformat) if ch_ids_next else " ",
                    'next_prg_end': datetime.datetime.fromtimestamp(int(ch_ids_next[0]['endTimestamp'])).strftime(datetimeformat) if ch_ids_next else " ",
                    'id_epg' : channel['id_epg'],
                    'tvg-name' : channel['name'].replace(" ","_"),
                    'start' : datetime.datetime.fromtimestamp(int(ch_ids_curr[0]['startTimestamp'])).strftime(datetimeformat) if ch_ids_curr else " ",
                    'end' : datetime.datetime.fromtimestamp(int(ch_ids_curr[0]['endTimestamp'])).strftime(datetimeformat) if ch_ids_curr else " ",
                    'duration' : datetime.datetime.fromtimestamp(int(ch_ids_curr[0]['endTimestamp'])-int(ch_ids_curr[0]['startTimestamp'])).strftime(datetimeformat) if ch_ids_curr else " ",
                    'tvg-logo' : "https://epg.swan.4net.tv/files/channel_logos/"+str(channel['id'])+".png",
                    'content_source' :  channel['content_sources'][0]['stream_profile_urls']['adaptive'],
                    'type' :  channel['type']}
                plot=''
                if ch_ids_curr and  'episode_name' in ch_ids_curr[0]:
                    plot+=ch_ids_curr[0]['episode_name']+'[CR]'
                elif ch_ids_curr and  'description' in ch_ids_curr[0]:
                    plot += ch_ids_curr[0]['description']
                ch['plot']=plot

                if ch_ids_curr and 'thumbnail' in ch_ids_curr[0]: 
                    ch['img'] = "https://epg.swan.4net.tv/files/program_photos/_300/"+str(ch_ids_curr[0]['thumbnail']['extension'])
                elif ch_ids_curr and  'photos' in ch_ids_curr[0]:
                    ch['img'] = "https://epg.swan.4net.tv/files/program_photos/_300/"+str(ch_ids_curr[0]['photos'][0]['extension'])
                else:
                    ch['img'] = 'DefaultVideo.png'

                if ch_ids_curr and  'genre' in ch_ids_curr[0]:
                    ch['genre']=ch_ids_curr[0]['genre']
                else:
                    ch['genre']=''

                if ch_ids_curr and 'year' in ch_ids_curr[0]:
                    ch['year']=ch_ids_curr[0]['year']
                else:
                    ch['year']=None

                self.channels.append(ch)
        return self.channels    

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

    def get_4KATVtags(self):
        subcats =[]
        sc=list
          
        j=self.dl_4KATV_tags()
        for scid in j['tags'].keys():
            sc ={ 'name' : j['tags'][scid]['name'],
                    'id_tag' : scid,
                    'type' : j['tags'][scid]['type']}
            if 'photo' in j['tags'][scid]:
                sc['img'] = "https://epg.swan.4net.tv/files/program_photos/_300/"+str(j['tags'][scid]['photo']['extension'])
            else:
                    sc['img'] = 'DefaultVideoIcon.png'
            subcats.append(sc)
        return subcats  

    def get_content(self,id,episode,q=None):
        subcats=list()
    
        fromdat=datetime.datetime.now()-datetime.timedelta(days=7)
        todat=datetime.datetime.now()
        fromdt=int((fromdat-datetime.datetime(1970,1,1)).total_seconds())
        todt=int((todat-datetime.datetime(1970,1,1)).total_seconds())
        epg_special='special_epg_from['+str(fromdt)+']'

        bec=self.dl_4KATV_allchannelgroups()  

        epg_ids=''
        broad_ch_epg=list()
        i=1
        for broad_ch_epgs in bec["channel_groups"]:
            for chan in broad_ch_epgs['channels']:
                broad_ch_epg.append(chan)
                i=i+1

        for ch in broad_ch_epg:
            epg_ids=epg_ids+str(ch["id_epg"])+','
        
        epg_ids=epg_ids[:-1]

        if not episode:
            
            data={
                'lng':self.lang,
                'epg_id':epg_ids,
                'tag_id':id,
                'from':fromdt,
                'to':todt,
                'limit':100,
                epg_special:epg_ids
            }
            url='https://epg.swan.4net.tv/search?v=3.1&tagged_only=0'
        if q:
            data={
                'lng':self.lang,
                'epg_id':epg_ids,
                'from':fromdt,
                'to':todt,
                'limit':100,
                epg_special:epg_ids,
                'q':q
            }
            url='https://epg.swan.4net.tv/search?v=3.1&tagged_only=0'  

        if episode:
            data={
                'lng':self.lang,
                'id_broadcast':id,
                'epg_id':epg_ids,
                'tag_id':id,
                'from':fromdt,
                'to':todt,
                'limit':100,
                epg_special:epg_ids
            }
            url='https://epg.swan.4net.tv/export/program?&&loadFullDetail=1&limit_similar=30&loadFullDetail=1'
        
        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"
        req = requests.get(url, params=data, headers=headers)        
        j = req.json()
        logDbg('get_content '+req.url)
        if  j['error']==True:
            raise StreamNotResolvedException(j['message'])
        else:
            if not episode:
                dat=j['broadcasts']
            else:
                dat=j['related_broadcasts']
            datetimeformat=xbmc.getRegion('dateshort')+" "+xbmc.getRegion('time')
            for br in dat:
                ch_id=list(filter(lambda x:x["id_epg"]==br['epg_id'],broad_ch_epg))
                isSeries=768 in br['tag_ids'] #768-id forSeries tag
                sc ={ 'name' : br['name']+" - "+ch_id[0]['name']+": "+datetime.datetime.fromtimestamp(int(br['startTimestamp'])).strftime(datetimeformat)+" - "+ str(datetime.timedelta(seconds=(int(br['endTimestamp'])-int(br['startTimestamp'])))),
                        'ch_id' : ch_id[0]['id'],
                        'br_id':br['id'],
                        'start':br['startTimestamp'],
                        'end':br['endTimestamp'],
                        'date':br['start']}
                if 'thumbnail' in br: 
                    sc['img'] = "https://epg.swan.4net.tv/files/program_photos/_300/"+str(br['thumbnail']['extension'])
                elif ('photos'in br)and (len(br["photos"])>0):
                    sc['img'] = "https://epg.swan.4net.tv/files/program_photos/_300/"+str(br['photos'][0]['extension'])
                else:
                    sc['img'] = 'DefaultVideo.png'
                if'description' in br:
                    sc['info']=br['description']
                else:
                    sc['info']=br['name']
                if'genre' in br:
                    sc['genre']=br['genre']
                else:
                    sc['genre']=''
                if'year' in br:
                    sc['year']=br['year']
                else:
                    sc['year']=None
                if isSeries:
                    sc['series']=1
                else:
                    sc['series']=0
                subcats.append(sc)
        return subcats  



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

                # for tvheadend
                # strtmp="#EXTINF:-1 tvg-id=\""+str(channel['id_epg'])+"\" tvg-logo=\"https://epg.swan.4net.tv/files/channel_logos/"+str(channel['id'])+".png\" channel=\""+channel['name']+" tvg-name=\""+channel['name']+"\","+channel['name']+"\npipe:///storage/.kodi/addons/tools.ffmpeg-tools/bin/ffmpeg -fflags +genpts -i \""+channel['content_sources'][0]['stream_profile_urls']['adaptive']+"\" -vcodec copy -acodec copy -f mpegts  -mpegts_service_type digital_tv -metadata service_provider="+str(channel['id'])+" -metadata service_name= pipe:1"

                # for IPTV Simple client
                radio=""
                if channel['type'] =='radio':
                    radio=" radio=\"true\" "
                strtmp="#EXTINF:-1 tvg-id=\""+str(channel['id_epg'])+"\" tvg-name=\""+channel['tvg-name']+"\" tvg-logo=\""+channel['tvg-logo']+radio+"\", "+channel['name']+"\n"+channel['content_source']
                f.write("%s\n" % strtmp)

    def generateepg(self,epgpath,hourspast=1,hoursfuture=1):

        guide = minidom.Document() 
 
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
            scale=55/len(j['broadcasts'])
        i=1
        for prg in j['broadcasts']:
            if self.progress:
                self.progress.setpozition(i*scale+45)
            i=i+1

            programme=guide.createElement('programme')
            programme.setAttribute('channel',str(prg['epg_id']))
            startdt=datetime.datetime.utcfromtimestamp(prg['startTimestamp']+tz)
            programme.setAttribute('start',str(startdt.strftime("%Y%m%d%H%M%S " ))+timez)
            stopdt=datetime.datetime.utcfromtimestamp(prg['endTimestamp']+tz)
            programme.setAttribute('stop',str(stopdt.strftime("%Y%m%d%H%M%S "))+timez)
            title=guide.createElement('title')
            title.setAttribute('lang','sk')
            title.appendChild(guide.createTextNode(prg['name']))
            programme.appendChild(title)
            desc=guide.createElement('desc')
            desc.setAttribute('lang','sk')
            if 'description' in prg:
                desc.appendChild(guide.createTextNode(prg['description']))
            else:
                desc.appendChild(guide.createTextNode(" "))
            programme.appendChild(desc)
            dat=guide.createElement('year')
            if 'year' in prg:
                dat.appendChild(guide.createTextNode(str(prg['year'])))
            else:
                dat.appendChild(guide.createTextNode(" "))
            programme.appendChild(dat)
            

            category=guide.createElement('category')
            category.setAttribute('lang','sk')
            if 'genre' in prg:
                category.appendChild(guide.createTextNode(prg['genre']))
            elif 'format' in prg:
                category.appendChild(guide.createTextNode(prg['format']))
            else:
                category.appendChild(guide.createTextNode(" "))
            programme.appendChild(category)

            icon=guide.createElement('icon')
            if 'thumbnailUrl300' in prg:
                icon.setAttribute('src',str(j['image_server'])+str(prg['thumbnailUrl300']))
            programme.appendChild(icon)
            

            tv.appendChild(programme)

        guide.appendChild(tv) 

        xml_str = guide.toprettyxml(indent ="\t", encoding="utf-8")  

        with codecs.open(epgpath, "wb") as f: 
            f.write(xml_str)  

    def dl_4KATV_channels(self):
        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"
        data = {'device_token' : self.device_token}
        try:
            req_src = requests.post('https://backoffice.swan.4net.tv/api/device/getSources', json=data, headers=headers,timeout=(5,120))
        except requests.exceptions.Timeout:
            logDbg("Download error TIMEOUT: "+req_src.url)
        except requests.exceptions.TooManyRedirects:
            logDbg("Download error TOMANY REDIRECTS : "+req_src.url)
        except requests.exceptions.RequestException as e:
            logDbg("Download error: "+req_src.url)
      
        j = req_src.json()

        
        if  j['success']==False:
            raise StreamNotResolvedException(j['message'])

        return j

    def dl_4KATV_tags(self):
        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"
        
        data={"lng" :self.lang}
        try:
            req_tag = requests.get('https://epg.swan.4net.tv/export/tag?',params=data, headers=headers,timeout=(5,120))
        except requests.exceptions.Timeout:
            logDbg("Download error TIMEOUT: "+req_tag.url)
        except requests.exceptions.TooManyRedirects:
            logDbg("Download error TOMANY REDIRECTS : "+req_tag.url)
        except requests.exceptions.RequestException as e:
            logDbg("Download error: "+req_tag.url)
        j = req_tag.json()
        if  j['error']==True:
            raise StreamNotResolvedException(j['message'])

        return j

    def dl_4KATV_allchannelgroups(self):
        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"
        data = {'device_token' : self.device_token}
        try:
            req_all_ch_grp = requests.post('https://backoffice.swan.4net.tv/api/device/getAllChannelGroups', json=data, headers=headers,timeout=(5,120))
        except requests.exceptions.Timeout:
            logDbg("Download error TIMEOUT: "+req_all_ch_grp.url)
        except requests.exceptions.TooManyRedirects:
            logDbg("Download error TOMANY REDIRECTS : "+req_all_ch_grp.url)
        except requests.exceptions.RequestException as e:
            logDbg("Download error: "+req_all_ch_grp.url)

        j = req_all_ch_grp.json()
    
        return j

    def dl_4KATV_epg_json(self,hourspast=1,hoursfuture=1):

        bec = self.dl_4KATV_allchannelgroups()
        
        today=datetime.datetime.now()
        #today.replace(tzinfo='timezone.utc').astimezone(tz=None)
        fromdat=today-datetime.timedelta(hours=hourspast)
        todat=today+datetime.timedelta(hours=hoursfuture)
        fromdt=int((fromdat-datetime.datetime(1970,1,1)).total_seconds())
        todt=int((todat-datetime.datetime(1970,1,1)).total_seconds())

        epg_ids=''
        for broad_ch_epgs in bec["channel_groups"]:
            broad_ch_epg=broad_ch_epgs['channels']
            for ch in broad_ch_epg:
                epg_ids=epg_ids+str(ch["id_epg"])+','
        epg_ids=epg_ids[:-1]

        headers = _COMMON_HEADERS
        headers["Content-Type"] = "application/json;charset=utf-8"
        data={'lng':self.lang,
            "epg_id":epg_ids,
            "from":str(fromdt),
            "to":str(todt)
             }
        try:
            req_broadcast = requests.get('https://epg.swan.4net.tv/export/broadcast', params=data, headers=headers,timeout=(5,120))
        except requests.exceptions.Timeout:
            logDbg("Download error TIMEOUT: "+req_broadcast.url)
        except requests.exceptions.TooManyRedirects:
            logDbg("Download error TOMANY REDIRECTS : "+req_broadcast.url)
        except requests.exceptions.RequestException as e:
            logDbg("Download error: "+req_broadcast.url)

        j = req_broadcast.json()

        return j

    def save_4KATV_jsons(self,hourspast=1,hoursfuture=1):
        j=self.dl_4KATV_channels()
        with open(os.path.join(self.datapath,'sources-channel.json'), 'w') as json_file:
            json.dump(j, json_file)
            json_file.close()


        j=self.dl_4KATV_tags()
        with open(os.path.join(self.datapath,'tags.json'), 'w') as json_file:
            json.dump(j, json_file)
            json_file.close()

        j=self.dl_4KATV_epg_json(hourspast,hoursfuture)
        with open(os.path.join(self.datapath,'broadcast-epg.json'), 'w') as json_file:
            json.dump(j, json_file)
            json_file.close()

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
    
    def get_iptvm_epg(self,hourspast,hoursfutre):
        from collections import defaultdict
        import re
        j=self.dl_4KATV_epg_json(hourspast,hoursfutre)

        tz=time.timezone
        m, s = divmod(tz, 60)
        h, m = divmod(m, 60)
        if tz >=0:
            timez="+"+'{0:02d}'.format(h)+'{0:02d}'.format(m)
        else:
            timez='{0:03d}'.format(h)+'{0:02d}'.format(m)
        epg=dict()
        for prg in j['broadcasts']:
            stopdt=datetime.datetime.utcfromtimestamp(prg['endTimestamp']+tz)
            startdt=datetime.datetime.utcfromtimestamp(prg['startTimestamp']+tz)
            chnl_id=str(prg['epg_id'])
            if not chnl_id in epg:
                epg[chnl_id]=[]
            
            if 'genre' in prg:
                genre=prg['genre']
            elif 'format' in prg:
                genre=prg['format']
            else:
                genre=""

            if 'thumbnailUrl300' in prg:
                image=str(j['image_server'])+str(prg['thumbnailUrl300'])
            else:
                image=""
            
            if 'description' in prg:
                description=prg['description']
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
            date=date)          
            )
        return epg
            