# -*- coding: utf-8 -*-

import sys
import xbmcvfs
import subprocess
import xbmc
from urllib.parse import quote, quote_plus, unquote
import xbmcaddon
import time
import os

import_path = xbmcvfs.translatePath("special://home/addons/plugin.video.4ka.tv")
sys.path.insert(1, import_path)  
from resources.lib.logger import *
from resources.lib.functions import find_files

_addon = xbmcaddon.Addon('plugin.video.4ka.tv')

duration=sys.argv[1]
fname=sys.argv[2]
f_ext=sys.argv[3]
ffmpeg_additional_settings=sys.argv[4]
save_path=sys.argv[5]
ffmpeg_path=sys.argv[6]
url=unquote(sys.argv[7])
debug=True
logDbg('records url and fname type: %s, %s' %(type(fname),type(url)))
#logDbg("recoring channel ...   record item: "+url)


'''
temp=xbmcvfs.translatePath("special://temp")+"testfile.mp4"
cmd=[ffmpeg_path,'-loglevel','debug','-y','-i',url,'-c','copy','-bsf:a','aac_adtstoasc',temp]
logDbg("The commandline is %s"%(' '.join(cmd)))

p=subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,shell=False)

stdout, stderr = p.communicate()
logDbg(stdout)
logDbg(stderr)
xbmcvfs.copy(temp,save_path)
xbmcvfs.delete(temp)
'''
msg=(_addon.getLocalizedString(30083)).format(fname)
xbmc.executebuiltin('Notification({},{})'.format(_addon.getLocalizedString(30082),msg))

'''
while True:
    dirs,files=xbmcvfs.listdir(save_path)
    if any(f.endswith(".pid") for f in files):
        logDbg("Some recording is in progress. Wait for the finish...")
        time.sleep(120)
    else:
        break
'''
while True:
    _save_path=_addon.getSetting('save_path') #ROOT Save dir
    files=find_files(_save_path,['.pid'])
    if any(f.endswith(".pid") for f in files):
        logDbg("Some recording is in progress. Wait for the finish...")
        time.sleep(120)
    else:
        break

f=os.path.join(save_path,fname+f_ext)
#,'-bsf:a','aac_adtstoasc',
cmd=[ffmpeg_path,'-loglevel','debug','-y','-i',url,'-acodec','copy','-vcodec','copy','-reconnect_at_eof', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '300', '-nostdin']
if ffmpeg_additional_settings:
    cmd=cmd+ffmpeg_additional_settings.split(' ')
cmd.append(f)
logDbg("Recording start: "+fname)
logDbg("The commandline is %s"%(' '.join(cmd)))

flogbase=fname

if debug:
    stdoutf=xbmcvfs.translatePath('special://temp')+flogbase+'.stdout.txt' 
    stdout=open(stdoutf, 'w+')
    stderrf=xbmcvfs.translatePath('special://temp')+flogbase+'.stderr.txt' 
    stderr=open(stderrf, 'w+')
    cmdf=xbmcvfs.File(f+".cmd.txt",'w')
    cmdf.write(' '.join(cmd))
    cmdf.close()

pidf=os.path.join(save_path,fname+".pid")

p=subprocess.Popen(cmd, stdout=stdout,stderr=stderr,shell=False)
pid=xbmcvfs.File(pidf,'w')
pid.write(bytearray(repr(p.pid).encode('utf-8')))
pid.close()
p.wait()
#stdout, stderr = p.communicate()
#if stderr:
#    with codecs.open(xbmcvfs.translatePath('special://temp')+fname+'.stderr.txt' , 'w') as fstderr:
#        fstderr.write(stderr)

#if stdout:
#    with codecs.open(xbmcvfs.translatePath('special://temp')+fname+'.stdout.txt' , 'w') as fstdout:
#        fstdout.write(stdout)
#logDbg(stdout)
#logDbg(stderr)
'''
try:
    video=xbmcvfs.File(f,'w')
    while True:
        data = p.stdout.read(1000000)
        if data:
            video.write(bytearray(data))
        else:
            break
finally:
    video.close()
'''
if  debug:
    stderr.close()
    stdout.close()

if debug:
    logDbg("Copy file: "+stdoutf+" -> "+f+'.stderr.txt')
    xbmcvfs.copy(stdoutf,f+'.stderr.txt')
    logDbg("Copy file: "+stderrf+" -> "+f+'.stdout.txt')
    xbmcvfs.copy(stderrf,f+'.stdout.txt')
    xbmcvfs.delete(stdoutf)
    xbmcvfs.delete(stderrf)


logDbg("Recording finished: "+fname)
msg=(_addon.getLocalizedString(30084)).format(fname)
xbmc.executebuiltin('Notification({},{})'.format(_addon.getLocalizedString(30082),msg))
xbmcvfs.delete(pidf)