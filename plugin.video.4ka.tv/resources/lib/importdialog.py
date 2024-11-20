import xbmc, xbmcgui,time
import os

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_BACKSPACE = 110
BACK_ACTIONS = [ACTION_PREVIOUS_MENU, ACTION_NAV_BACK, ACTION_BACKSPACE]

BTNYESID=10
BTNYESALLID=11
BTNCHANGEID=12
BTNCHANGEALLID=13
BTNCANCELID=14
HEADERID=1
TEXTID=9

class ImportDialog(xbmcgui.WindowXMLDialog):
    def __init__(self,*args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.title = 101
        self.msg = 102
        self.scrollbar = 103
        self.closebutton = 201
        self.ret=None
        self.title= kwargs['title']
        self.msg = kwargs['msg']
    
    def onInit(self):
        self.getControl(HEADERID).setLabel(self.title)
        self.getControl(TEXTID).setText(self.msg)

    def onClick(self, controlid):
        if controlid == BTNYESID:
            self.ret=1
        elif controlid == BTNYESALLID:
            self.ret=2
        elif controlid == BTNCHANGEID:
            self.ret=3
        elif controlid == BTNCHANGEALLID:
            self.ret=4
        elif controlid == BTNCANCELID:
            self.ret=-1

        self.close()

    def onAction(self, action):
        if action.getId() in BACK_ACTIONS:
            self.close()
              

        
def importdialog(_addon,title,message):
    dial=ImportDialog("importdialog.xml", _addon.getAddonInfo('path'),'Default',title=title,msg=message)
    
    dial.doModal()
    ret=dial.ret
   
    return ret
