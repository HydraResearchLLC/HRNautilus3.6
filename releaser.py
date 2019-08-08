#
# This script generates a .curapackage and a properly zipped resources folder
# for the Nautilus plugin

import os
import tempfile
from distutils.dir_util import copy_tree
import zipfile
import shutil


path = os.path.dirname(os.path.realpath(__file__))
pluginName = 'Nautilus'
pluginPath = os.path.join('files','plugins',pluginName)
ultimakerReleasePath = os.path.join(path, pluginName)
sourcePath = os.path.join(path,'files')


def filer(filePath):
    try:
        os.makedirs(filePath)
    except OSError:
        print("error creating folders for path ", str(filePath))

def fileList(fileName):
    files = list()
    for (dirpath, dirnames, filenames) in os.walk(fileName):
        files += [os.path.join(dirpath, file) for file in filenames]
    return files

# Create the plugin temp directory in the appropriate structure for the plugin
with tempfile.TemporaryDirectory() as configDirectory:
    filer(ultimakerReleasePath)
    # include the necessary files from the root path
    copy_tree(sourcePath, os.path.join(configDirectory,pluginPath))
    copy_tree(sourcePath, ultimakerReleasePath)
    utils = ['icon.png', 'LICENSE', 'package.json']
    for util in utils:
        shutil.copy(os.path.join(path, util), configDirectory)

    # zip the file as a .curapackage so it's ready to go
    with zipfile.ZipFile(os.path.join(path, pluginName+'.curapackage'), 'w') as zf:
        pluginFiles = fileList(configDirectory)
        # add everything relevant
        for item in pluginFiles:
            if '.DS_Store' not in item:
                zf.write(os.path.join(configDirectory, item), os.path.relpath(item, configDirectory))
                shutil.copy(item,ultimakerReleasePath)
    zf.close()
    print("Update version numbers before release!")
