####################################################################
# Hydra Research Nautilus plugin for Ultimaker Cura
# A plugin to install config files and Duet functionality
# for the Nautilus printer
#
# Written by Zach Rose
# Based on the Dremel 3D20 plugin written by Tim Schoenmackers
# and the DuetRRF Plugin by Thomas Kriechbaumer
# contains code from the GCodeWriter Plugin by Ultimaker
#
# the Dremel plugin source can be found here:
# https://github.com/timmehtimmeh/Cura-Dremel-3D20-Plugin
#
# the GCodeWriter plugin source can be found here:
# https://github.com/Ultimaker/Cura/tree/master/plugins/GCodeWriter
#
# the DuetRRFPlugin source can be found here:
# https://github.com/Kriechi/Cura-DuetRRFPlugin
#
# This plugin is released under the terms of the LGPLv3 or higher.
# The full text of the LGPLv3 License can be found here:
# https://github.com/HydraResearchLLC/Nautilus/blob/master/LICENSE
####################################################################

import os # for listdir
import os.path # for isfile and join and path
import sys
import zipfile
import shutil  # For deleting plugin directories;
import stat    # For setting file permissions correctly;
import re #For escaping characters in the settings.
import json
import copy
import struct
import time
import configparser
import requests
import urllib
import ssl

from distutils.version import StrictVersion # for upgrade installations

from UM.i18n import i18nCatalog
from UM.Extension import Extension
from UM.Message import Message
from UM.Resources import Resources
from UM.Logger import Logger
from UM.Preferences import Preferences
from UM.Mesh.MeshWriter import MeshWriter
from UM.Settings.InstanceContainer import InstanceContainer
from UM.Qt.Duration import DurationFormat
from UM.Qt.Bindings.Theme import Theme
from UM.PluginRegistry import PluginRegistry
from . import NautilusDuet
from . import Upgrader
from cura.CuraApplication import CuraApplication

from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtGui import QPixmap, QScreen, QColor, qRgb, QImageReader, QImage, QDesktopServices
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice, QRect, Qt, QSize, pyqtSlot, QObject, QUrl, pyqtProperty


catalog = i18nCatalog("cura")


class Nautilus(QObject, MeshWriter, Extension):
    # The version number of this plugin - please change this in all three of the following Locations:
    # 1) here
    # 2) plugin.json
    # 3) package.json
    version = "1.0.11"

    ##  Dictionary that defines how characters are escaped when embedded in
    #   g-code.
    #
    #   Note that the keys of this dictionary are regex strings. The values are
    #   not.
    escape_characters = {
        re.escape("\\"): "\\\\",  # The escape character.
        re.escape("\n"): "\\n",   # Newlines. They break off the comment.
        re.escape("\r"): "\\r"    # Carriage return. Windows users may need this for visualisation in their editors.
    }

    def __init__(self):
        super().__init__()
        self._application = CuraApplication.getInstance()
        self.getPref = self._application.getPreferences()
        self._setting_keyword = ";SETTING_"

        self.this_plugin_path=os.path.join(Resources.getStoragePath(Resources.Resources), "plugins","Nautilus","Nautilus")
        self.gitUrl = 'https://api.github.com/repos/HydraResearchLLC/Nautilus-Config-Cura/releases/latest'
        self.fullJson = json.loads(requests.get(self.gitUrl).text)
        self.pregitUrl = 'https://api.github.com/repos/HydraResearchLLC/Nautilus-Config-Cura/releases'
        self.preJson = json.loads(requests.get(self.pregitUrl).text)
        self._preferences_window = None

        self._message = None
        self.local_meshes_path = None
        self.local_printer_def_path = None
        self.local_materials_path = None
        self.local_quality_path = None
        self.local_extruder_path = None
        self.local_variants_path = None
        self.local_setvis_path = None
        self.local_global_dir = None
        Logger.log("i", "Nautilus Plugin setting up")
        self.local_meshes_path = os.path.join(Resources.getStoragePathForType(Resources.Resources), "meshes")
        self.local_printer_def_path = Resources.getStoragePath(Resources.DefinitionContainers)#os.path.join(Resources.getStoragePath(Resources.Resources),"definitions")
        self.local_materials_path = os.path.join(Resources.getStoragePath(Resources.Resources), "materials")
        self.local_quality_path = os.path.join(Resources.getStoragePath(Resources.Resources), "quality")
        self.local_extruder_path = os.path.join(Resources.getStoragePath(Resources.Resources),"extruders")
        self.local_variants_path = os.path.join(Resources.getStoragePath(Resources.Resources), "variants")
        self.local_setvis_path = os.path.join(Resources.getStoragePath(Resources.Resources), "setting_visibility")
        self.local_global_dir = os.path.join(Resources.getStoragePath(Resources.Resources),"machine_instances")
        self.setvers = self.getPref.getValue("metadata/setting_version")

        Duet=NautilusDuet.NautilusDuet()
        self.addMenuItem(catalog.i18nc("@item:inmenu","Nautilus Connections"), Duet.showSettingsDialog)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Preferences"), self.showPreferences)

        #if the plugin was never installed, add relevant preferences and ensure profiles install
        if self.getPref.getValue("Nautilus/install_status") is None:
            self.getPref.addPreference("Nautilus/install_status", "unknown")

        if self.getPref.getValue("Nautilus/profile_status") is None:
            self.getPref.addPreference("Nautilus/profile_status","unknown")

        if self.getPref.getValue("Nautilus/configversion") is None:
            Logger.log("i","reseting config version")
            self.getPref.addPreference("Nautilus/configversion","0.0")

        if self.getPref.getValue("Nautilus/auto_status") is None:
            self.getPref.addPreference("Nautilus/auto_status", "No")

        if self.getPref.getValue("Nautilus/prerel_status") is None:
            self.getPref.addPreference("Nautilus/prerel_status","No")

        if self.getPref.getValue("Nautilus/curr_version") is None:
            self.getPref.addPreference("Nautilus/curr_version", "0.0")


        # if something got messed up, force installation
        if not self.isInstalled() and self.getPref.getValue("Nautilus/install_status") is "installed":
            self.getPref.setValue("Nautilus/install_status", "unknown")

        # if it's installed, and it's listed as uninstalled, then change that to reflect the truth
        if self.isInstalled() and self.getPref.getValue("Nautilus/install_status") is "uninstalled":
            self.getPref.setValue("Nautilus/install_status", "installed")

        # if the version isn't the same, then force installation
        if not self.versionsMatch():
            self.getPref.setValue("Nautilus/install_status", "unknown")

        # Check the preferences to see if the user uninstalled the files -
        # if so don't automatically install them
        if self.getPref.getValue("Nautilus/install_status") is "unknown":
            # if the user never installed the files, then automatically install it
            self.installPluginFiles()

        #if manual updates and new profiles exist, alert the user an update is avalable
        if self.configVersionsMatch() == False and self.getPref.getValue("Nautilus/install_status")!="uninstalled" and self.getPref.getValue("Nautilus/auto_status")!="Yes":
            self._message = Message(catalog.i18nc("@info:status", "New Cura configuration is available for the Nautilus. \nTo enable automatic updates open Preferences under Extensions->Hydra Research Nautilus Plugin."), 0, False)
            self._message.addAction("download_config", catalog.i18nc("@action:button", "Update"), "globe", catalog.i18nc("@info:tooltip", "Update Nautilus config."))
            self._message.actionTriggered.connect(self._onMessageActionTriggered)
            self._message.show()

        Logger.log("i","Nautilus plugin done setting up")
        self.printPrefs()
    def printPrefs(self):
        Logger.log("i","inbound preferences")
        Logger.log("i","curr_version: "+self.getPref.getValue("Nautilus/curr_version"))
        Logger.log("i","configversion: "+self.getPref.getValue("Nautilus/configversion"))
        Logger.log("i","prerel_status: "+self.getPref.getValue("Nautilus/prerel_status"))
        Logger.log("i","profile_status: "+self.getPref.getValue("Nautilus/profile_status"))
        Logger.log("i","install_status: "+self.getPref.getValue("Nautilus/install_status"))
        Logger.log("i","auto_status: "+self.getPref.getValue("Nautilus/auto_status"))

    def createPreferencesWindow(self):
        path = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), "Nautilusprefs.qml")
        Logger.log("i", "Creating Nautilus preferences UI "+path)
        self._preferences_window = self._application.createQmlComponent(path, {"manager": self})

    def showPreferences(self):
        if self._preferences_window is None:
            self.createPreferencesWindow()
            statuss=self.getPref.getValue("Nautilus/install_status")
        self._preferences_window.show()

    def hidePreferences(self):
        if self._preferences_window is not None:
            self._preferences_window.hide()

    # function so that the preferences menu can open website the version
    @pyqtSlot()
    def openPluginWebsite(self):
        url = QUrl('https://github.com/HydraResearchLLC/Nautilus/releases', QUrl.TolerantMode)
        if not QDesktopServices.openUrl(url):
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not navigate to https://github.com/HydraResearchLLC/Nautilus.6/releases"))
            message.show()

    @pyqtSlot()
    def showHelp(self):
        Logger.log("i", "Nautilus Plugin opening help page: https://www.hydraresearch3d.com/resources/")
        try:
            if not QDesktopServices.openUrl(QUrl("https://www.hydraresearch3d.com/resources/")):
                message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not open https://www.hydraresearch3d.com/resources/ please navigate to the page for assistance"))
                message.show()
        except:
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not open https://www.hydraresearch3d.com/resources/ please navigate to the page for assistance"))
            message.show()

    @pyqtSlot()
    def reportIssue(self):
        Logger.log("i", "Nautilus Plugin opening issue page: https://github.com/HydraResearchLLC/Nautilus/issues/new")
        try:
            if not QDesktopServices.openUrl(QUrl("https://github.com/HydraResearchLLC/Nautilus/issues/new")):
                message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not open https://github.com/HydraResearchLLC/Nautilus/issues/new please navigate to the page and report an issue"))
                message.show()
        except:
            message = Message(catalog.i18nc("@info:status", "Nautilus plugin could not open https://github.com/HydraResearchLLC/Nautilus/issues/new please navigate to the page and report an issue"))
            message.show()

    @pyqtSlot()
    def changeAutoStatus(self):
        if self.getPref.getValue("Nautilus/auto_status") == "Yes":
            self.getPref.setValue("Nautilus/auto_status", "No")
        elif self.getPref.getValue("Nautilus/auto_status") == "No":
            self.getPref.setValue("Nautilus/auto_status", "Yes")
        else:
            Logger.log("i","something's broken")

    @pyqtSlot()
    def manualUpdate(self):
        Logger.log("i","manual update")
        self.configDownload()

    @pyqtSlot()
    def changePreStatus(self):
        self.printPrefs()
        if self.getPref.getValue("Nautilus/prerel_status") == "No":
            self.getPref.setValue("Nautilus/prerel_status", "Yes")
            #self.uninstallPluginFiles(True)
            Logger.log("i","change pre status 2")
            self.configDownload()
        elif self.getPref.getValue("Nautilus/prerel_status") == "Yes":
            self.getPref.setValue("Nautilus/prerel_status", "No")
            self.uninstallPluginFiles(True)
            Logger.log("i","change pre status")
            self.configDownload()
        else:
            Logger.log("i","something's broken")

    @pyqtProperty(str)
    def getVersion(self):
        numba = Nautilus.version
        Logger.log("i","Nailed it! "+numba)
        Logger.log("i","profile status is: "+str(self.getPref.getValue("Nautilus/profile_status")))
        return str(numba)

    @pyqtProperty(str)
    def showUpdateButton(self):
        if self.getPref.getValue("Nautilus/auto_status") is "No" and (self.configVersionsMatch()== False or self.getPref.getValue("Nautilus/profile_status")=="downloaded"):
            return "Yes"
        else:
            return "No"

    @pyqtProperty(str)
    def configVersionNo(self):
        if self.getPref.getValue("Nautilus/prerel_status") == "Yes":
            newVersion = json.dumps(self.preJson[0]['tag_name'])
        else:
            newVersion = json.dumps(self.fullJson['tag_name'])
        return(str(newVersion))


    @pyqtProperty(str)
    def profileUpdateStatus(self):
        #If user manually uninstalled profiles
        Logger.log("i","Weirdness information: ")
        self.printPrefs()
        if not self.isInstalled():
            Logger.log("i","not isInstalled")
        else:
            Logger.log("i","isInstalled")
        if self.configVersionsMatch():
            Logger.log("i","versions match")
        else:
            Logger.log("i","versions don't match")

        if self.getPref.getValue("Nautilus/install_status")=="uninstalled" and self.isInstalled() == False:
            return "Profiles have been manually uninstalled"
        #If profiles are installed and up to date
        elif self.getPref.getValue("Nautilus/profile_status") == "installed" and self.configVersionsMatch():
            return "Profiles are up to date"
        #If profiles are downloaded but install failed or Cura hasn't been restarted
        elif self.getPref.getValue("Nautilus/profile_status") == "downloaded" and self.configVersionsMatch():
            return "New profiles have been downloaded. Click to install profiles"
        #If an update is available
        elif not self.configVersionsMatch():
            return "New profiles available"
        #Catch all incase something broke along the way
        else:
            return "This is weird, restart Cura. If that doesn't work, contact support"

    # returns true if the versions match and false if they don't
    def versionsMatch(self):
        # get the currently installed plugin version number
        installedVersion = self.getPref.getValue("Nautilus/curr_version")
        Logger.log("i","profile status is: "+str(self.getPref.getValue("Nautilus/profile_status")))
        if StrictVersion(installedVersion) == StrictVersion(Nautilus.version):
            # if the version numbers match, then return true
            Logger.log("i", "Nautilus Plugin versions match: "+installedVersion+" matches "+Nautilus.version)
            return True
        else:
            Logger.log("i", "Nautilus Plugin installed version: " +installedVersion+ " doesn't match this version: "+Nautilus.version)
            return False

    def configVersionsMatch(self):
        if self.getPref.getValue("Nautilus/prerel_status") == "Yes":
            newVersion = json.dumps(self.preJson[0]['tag_name'])
        else:
            newVersion = json.dumps(self.fullJson['tag_name'])
        Logger.log("i","profile status is: "+str(self.getPref.getValue("Nautilus/profile_status")))
        installedVersion = self.getPref.getValue("Nautilus/configversion")
        if StrictVersion(installedVersion) == StrictVersion(newVersion):
            Logger.log("i","Some stuff, it's chill. have "+installedVersion + "git has " + newVersion)
            return True
        else:
            Logger.log("i","No Bueno " + newVersion + " have " + installedVersion)
            if self.getPref.getValue("Nautilus/auto_status")=="Yes":
                self.configDownload()
                Logger.log("i", "Auto-updating config")
            return False

    def _onMessageActionTriggered(self, message, action):
        if action == "download_config":
            Logger.log("i","message action")
            self.configDownload()

    def _onDownloadComplete(self,versionNo):
        Logger.log("i","profile status is: "+str(self.getPref.getValue("Nautilus/profile_status")))
        if self._message:
            self._message.hide()
            self._message = None
        Logger.log("i","display download confirmation")
        if self.getPref.getValue("Nautilus/install_status")=="installed":
            self._message = Message(catalog.i18nc("@info:status", "Downloaded configuration version {}, restart Cura to install").format(versionNo))
            self._message.show()
        self.installPluginFiles()

    def configDownload(self):
        self.printPrefs()
        if self.getPref.getValue("Nautilus/prerel_status") == "Yes":
            configUrl = json.dumps(self.preJson[0]['assets'][0]['browser_download_url'])
            versionNo = json.dumps(self.preJson[0]['tag_name'])
        else:
            configUrl = json.dumps(self.fullJson['assets'][0]['browser_download_url'])
            versionNo = json.dumps(self.fullJson['tag_name'])

        Logger.log("i", "Downloading from " + str(configUrl))
        Logger.log("i", "Downloading to " + str(self.this_plugin_path))
        try:
            if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
                ssl._create_default_https_context = ssl._create_unverified_context
            opener = urllib.request.build_opener()
            opener.addheaders = [('Accept','application/octet-stream')]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(configUrl,os.path.join(self.this_plugin_path,'Nautilus.zip'))
            self.getPref.setValue("Nautilus/configversion", versionNo)
            Logger.log("i","Config Downloaded, set version " + versionNo)
            self.getPref.setValue("Nautilus/profile_status","downloaded")
            self._onDownloadComplete(versionNo)

        except Exception as inst:
            Logger.log("i","There was an error connecting to github")
            Logger.log("i", type(inst))
        return


    # check to see if the plugin files are all installed
    def isInstalled(self):
        HRNautilusDefFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus.def.json")
        nautilusExtruderDefFile = os.path.join(self.local_extruder_path,"hydra_research_nautilus_extruder.def.json")
        nautilusMatDir = os.path.join(self.local_materials_path,"nautilusmat")
        nautilusQualityDir = os.path.join(self.local_quality_path,"nautilusquals")
        nautilusVariantsDir = os.path.join(self.local_variants_path,"nautilusvars")
        nautilusSettingVisDir = os.path.join(self.local_setvis_path,'hrn_settings')
        sstatus = 0
        # if some files are missing then return that this plugin as not installed
        if not os.path.isfile(HRNautilusDefFile):
            Logger.log("i", "Nautilus definition file is NOT installed ")
            sstatus += 1
            return False
        if not os.path.isfile(nautilusExtruderDefFile):
            Logger.log("i", "Nautilus extruder file is NOT installed ")
            sstatus += 1
            return False
        if not os.path.isdir(nautilusMatDir):
            Logger.log("i", "Nautilus material files are NOT installed ")
            sstatus += 1
            return False
        if not os.path.isdir(nautilusQualityDir):
            Logger.log("i", "Nautilus quality files are NOT installed ")
            sstatus += 1
            return False
        if not os.path.isdir(nautilusVariantsDir):
            Logger.log("i", "Nautilus variant files are NOT installed ")
            sstatus += 1
            return False
        if not os.path.isdir(nautilusSettingVisDir):
            Logger.log("i","Nautilus setting visibility file is NOT installed")
            sstatus += 1
            return False

        # if everything is there, return True
        if sstatus < 1:
            Logger.log("i", "Nautilus Plugin all files ARE installed")
            #self.getPref.setValue("Nautilus/install_status", "installed")
            #self.getPref.setValue("Nautilus/profile_status", "installed")
            return True

    # install based on preference checkbox
    @pyqtSlot(bool)
    def changePluginInstallStatus(self, bInstallFiles):
        if bInstallFiles and not self.isInstalled():
            self.installPluginFiles()
            message = Message(catalog.i18nc("@info:status", "Nautilus configuration files have been installed. Restart cura to complete installation"))
            message.show()
        elif self.isInstalled():
            Logger.log("i","Uninstalling")
            self.uninstallPluginFiles(False)

    # Install the plugin files.
    def installPluginFiles(self):
        self.printPrefs()
        Logger.log("i", "Nautilus Plugin installing printer files")
        if not os.path.isfile(os.path.join(self.this_plugin_path,"Nautilus.zip")):
            Logger.log("i","install plugin files")
            self.configDownload()
        upper = Upgrader.Upgrader()
        value = upper.configFixer()
        if value:
            self.uninstallPluginFiles(value)
        try:
            restartRequired = False
            zipdata = os.path.join(self.this_plugin_path,"Nautilus.zip")
            Logger.log("i","Nautilus Plugin installing from: " + zipdata)

            with zipfile.ZipFile(zipdata, "r") as zip_ref:
                for info in zip_ref.infolist():
                    Logger.log("i", "Nautilus Plugin: found in zipfile: " + info.filename )
                    folder = None
                    if info.filename.endswith("nautilus.def.json"):
                        folder = self.local_printer_def_path
                    elif info.filename.endswith("hydra_research_nautilus_extruder.def.json"):
                        folder = self.local_extruder_path
                    elif info.filename.endswith("nautilus.cfg"):
                        folder = self.local_setvis_path
                    elif info.filename.endswith("fdm_material"):
                        folder = self.local_materials_path
                    elif info.filename.endswith("0.inst.cfg"):
                        folder = self.local_variants_path
                        Logger.log("i", "Finding Variants")
                    elif info.filename.endswith(".cfg"):
                        folder = self.local_quality_path
                        Logger.log("i", "Finding Quality")
                    elif info.filename.endswith(".stl"):
                        folder = self.local_meshes_path
                        if not os.path.exists(folder): #Cura doesn't create this by itself. We may have to.
                            os.mkdir(folder)

                    if folder is not None:
                        extracted_path = zip_ref.extract(info.filename, path = folder)
                        permissions = os.stat(extracted_path).st_mode
                        os.chmod(extracted_path, permissions | stat.S_IEXEC) #Make these files executable.
                        Logger.log("i", "Nautilus Plugin installing " + info.filename + " to " + extracted_path)
                        restartRequired = True
                        if folder is self.local_variants_path:
                            Logger.log("i", "The variant is " + extracted_path)
                            config = configparser.ConfigParser()
                            config.read(extracted_path)
                            Logger.log("i", "The sections are " + str(config.sections()))
                            config['metadata']['setting_version']=self.setvers
                            with open(extracted_path,'w') as configfile:
                                config.write(configfile)

        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while installing the files")
            message = Message(catalog.i18nc("@info:status", "Nautilus Plugin experienced an error installing the files"))
            message.show()

        if restartRequired!=False and self.isInstalled()!=False:
            # either way, the files are now installed, so set the prefrences value
            self.getPref.setValue("Nautilus/install_status", "installed")
            self.getPref.setValue("Nautilus/curr_version",Nautilus.version)
            self.getPref.setValue("Nautilus/profile_status", "installed")
            Logger.log("i", "Nautilus Plugin is now installed - Please restart ")
            Logger.log("i", "Profile status is: "+str(self.getPref.getValue("Nautilus/profile_status")))
            #self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))



    # Uninstall the plugin files.
    def uninstallPluginFiles(self, quiet):
        Logger.log("i", "Nautilus Plugin uninstalling plugin files")
        restartRequired = False
        # remove the printer definition file
        try:
            HRNautilusDefFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus.def.json")
            if os.path.isfile(HRNautilusDefFile):
                Logger.log("i", "Nautilus Plugin removing printer definition from " + HRNautilusDefFile)
                os.remove(HRNautilusDefFile)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the extruder definition file
        try:
            HRNautilusExtruderFile = os.path.join(self.local_printer_def_path,"hydra_research_nautilus_extruder.def.json")
            if os.path.isfile(HRNautilusExtruderFile):
                Logger.log("i", "Nautilus Plugin removing extruder definition from " + HRNautilusExtruderFile)
                os.remove(HRNautilusExtruderFile)
                restartRequired = True
        except: # Installing a new plug-in should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the material directory
        try:
            nautilusmatDir = os.path.join(self.local_materials_path,"nautilusmat")
            if os.path.isdir(nautilusmatDir):
                Logger.log("i", "Nautilus Plugin removing material files from " + nautilusmatDir)
                shutil.rmtree(nautilusmatDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the extruder file
        try:
            nautilusExtruder = os.path.join(self.local_extruder_path,"hydra_research_nautilus_extruder.def.json")
            if os.path.isfile(nautilusExtruder):
                Logger.log("i", "Nautilus Plugin removing extruder file from " + nautilusExtruder)
                os.remove(nautilusExtruder)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the platform file (on windows this doesn't work because it needs admin rights)
        try:
            nautilusSTLfile = os.path.join(self.local_meshes_path,"hydra_research_nautilus_platform.stl")
            if os.path.isfile(nautilusSTLfile):
                Logger.log("i", "Nautilus Plugin removing stl file from " + nautilusSTLfile)
                os.remove(nautilusSTLfile)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        # remove the folder containing the quality files
        try:
            nautilusQualityDir = os.path.join(self.local_quality_path,"hr_nautilus")
            if os.path.isdir(nautilusQualityDir):
                Logger.log("i", "Nautilus Plugin removing quality files from " + nautilusQualityDir)
                shutil.rmtree(nautilusQualityDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        #remove the folder containing the variant Files
        try:
            nautilusVariantsDir = os.path.join(self.local_variants_path,"nautilus")
            if os.path.isdir(nautilusVariantsDir):
                Logger.log("i", "Nautilus Plugin removing variants files from " + nautilusVariantsDir)
                shutil.rmtree(nautilusVariantsDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d", "An exception occurred in Nautilus Plugin while uninstalling files")

        #remove the setting visibility file
        try:
            nautilusSettingVisDir = os.path.join(self.local_setvis_path,"hrn_settings")
            if os.path.isfile(nautilusSettingVisDir):
                Logger.log("i", "Nautilus Plugin removing setting visibility files from" +nautilusSettingVisDir)
                shutil.rmtree(nautilusSettingVisDir)
                restartRequired = True
        except: # Installing a new plugin should never crash the application.
            Logger.logException("d","An exception occurred in Nautilus Plugin while uninstalling files")

        # prompt the user to restart
        if restartRequired and quiet == False:
            if os.path.isfile(os.path.join(self.local_global_dir,"Hydra+Research+Nautilus.global.cfg")):
                message = Message(catalog.i18nc("@info:status","You have at least one Nautilus added into Cura. Remove it from your Preferences menu before restarting to avoid an error!"))
                message.show()
            message = Message(catalog.i18nc("@info:status", "Nautilus files have been uninstalled, please restart Cura to complete uninstallation."))
            message.show()
        self.getPref.setValue("Nautilus/install_status", "uninstalled")
        self.getPref.setValue("Nautilus/configversion", "0.0")
        self.getPref.setValue("Nautilus/profile_status", "unknown")
        #self._application.getPreferences().writeToFile(Resources.getStoragePath(Resources.Preferences, self._application.getApplicationName() + ".cfg"))
