
import xbmcgui


class BaseImporter:
    def __init__(self):
        self.name="BaseImporter"
    
    def getImporterName(self):
        # return name of importer
        return self.name
    
    def getRecordPath(self):
        #return record path
        save_path=""
        return save_path

    def getjsoninfo(self,file):
       #return converted json info for file
        jsoninfo={}
            
        return jsoninfo
    
    def delete(self,file):

        return