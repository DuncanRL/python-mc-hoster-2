if True:  # IMPORTS:
    from subprocess import PIPE, Popen
    from re import search, compile
    from threading import Thread
    import time
    from sys import platform
    from os.path import isfile
    from json import dumps

    import pip
    import uuid

    def pinstall(package):
        pip.main(['install', package])

    try:
        from mcuuid import mcuuid
    except:
        pinstall("mcuuid")
        from mcuuid import mcuuid

    try:
        from discord_webhook import *
    except:
        pinstall("discord_webhook")
        from discord_webhook import *

    try:
        from discord import *
    except:
        pinstall("discord")
        from discord import *


class MCServer:
    def __init__(self, serverPath, popenCommand):
        self.startServer(serverPath,popenCommand)
    
    def startServer(self,serverPath,popenCommand):
        if platform in ["win32", "win64"]:
            self.ServerPopen = Popen(popenCommand, cwd=serverPath, stdin=PIPE,
                                     stdout=PIPE, stderr=PIPE,close_fds=True)
        elif platform == "linux":
            self.ServerPopen = Popen(["/bin/bash", "-c", popenCommand], cwd=serverPath,
                             stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)

