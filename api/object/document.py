import os
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

from api.client import Client
from api.helper import Singleton
import api.object.parser as parser
from api.object.item import Item
from api.object.collection import Collection

class Document(Item):
    
    PATH = ".remapy"

    def __init__(self, entry, parent: Collection):
        super(Document, self).__init__(entry, parent)
        
        # Remarkable tablet paths
        self.path = "%s/%s" % (self.PATH, self.uuid)
        self.path_zip = "%s.zip" % self.path
        self.path_rm_files = "%s/%s" % (self.path, self.uuid)

        # RemaPy paths
        self.path_remapy = "%s/.remapy" % self.path
        self.path_svg = "%s/%s_" % (self.path_remapy, self.name)

        # Other props
        self.current_page = entry["CurrentPage"]
        self.current_svg_page = self.path_svg + str(self.current_page).zfill(5) + ".svg"
        self.state = Item.STATE_DOCUMENT_LOCAL_NOTEBOOK if os.path.exists(self.path) else Item.STATE_DOCUMENT_ONLINE
        self.download_url = None
        self.blob_url = None

        self.state_listener = []


    def clear_cache(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
        self.update_state(Item.STATE_DOCUMENT_ONLINE)


    def sync(self, force=False):

        # Download if needed
        if force or self.state != Item.STATE_DOCUMENT_LOCAL_NOTEBOOK:
            self._download_raw()
            self._write_remapy_metadata()

        parser.rm_to_svg(self.path_rm_files, self.path_svg, background="white")


    def _download_raw(self, path=None):
        self.update_state(Item.STATE_DOCUMENT_DOWNLOADING)
        path = self.path if path == None else path

        if os.path.exists(path):
            shutil.rmtree(path)

        if self.blob_url == None:
            self.blob_url = self.rm_client.get_blob_url(self.uuid)

        raw_file = self.rm_client.get_raw_file(self.blob_url)
        with open(self.path_zip, "wb") as out:
            out.write(raw_file)
        
        with zipfile.ZipFile(self.path_zip, "r") as zip_ref:
            zip_ref.extractall(path)
        
        os.remove(self.path_zip)
        self.update_state(Item.STATE_DOCUMENT_LOCAL_NOTEBOOK)


    def add_state_listener(self, listener):
        self.state_listener.append(listener)
    

    def update_state(self, state):
        self.state = state
        
        for listener in self.state_listener:
            listener(self)


    def _write_remapy_metadata(self):
        Path(self.path_remapy).mkdir(parents=True, exist_ok=True)
        with open("%s/metadata.yaml" % self.path_remapy, "w") as out:
            out.write(self.modified_str())
