#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import xbmcgui
from resources.lib.logger import *


class progressdialogBG:
    def __init__(self,heading='',message=''):

        self.frompercent=0
        self.topercent=100
        self.curr=0
        self.currpos=0
        self.message=message
        self.heading=heading
        self.pDialog=xbmcgui.DialogProgressBG()
        self.pDialog.create(heading,message)
        logDbg("progress dialog crated")

    def setpercentrange(self,frompercent,topercent):
        self.frompercent=frompercent
        self.topercent=topercent

    def update(self,value,heading='',message=''):
        self.curr=value
        if heading:
            self.setheading(heading)
        
        if message:
            self.setmessage(message)
        self.pDialog.update(self.curr,heading,message)

    def scale(self):
         return float((self.topercent-self.frompercent)/100)
         
    def setheading(self,heading):
        self.heading=heading
    
    def setmessage(self,message):
        self.message=message

    def setpozition(self,value,heading='',message=''):
        scal=self.scale()
        
        self.currpos=int(scal*value+self.frompercent)
       # logDbg('Step: '+str(stp)+' value: '+str(value)+" possition "+str(self.currpos)+" minvalue "+str(self.minvalue)+" maxvalue "+str(self.maxvalue)+" minperc "+str(self.frompercent)+" maxperc "+str(self.topercent))
        if heading:
            self.setheading(heading)
        
        if message:
            self.setmessage(message)

        self.pDialog.update(self.currpos,self.heading,self.message)

    def close(self):
        self.pDialog.close()

        
    
