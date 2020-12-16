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
    __platform = platform

    def __init__(self, serverPath, popenCommand, autoRestarts=True):

        self.loaded = False
        self.running = True
        self.outputQueue = []
        self.autoRestarts = autoRestarts
        self.__runServerThread = Thread(
            target=self.__runServer, args=(serverPath, popenCommand))
        self.__runServerThread.start()
        time.sleep(0.5)
        self.__outputManagerThread = Thread(
            target=self.__outputManager, args=())
        self.__outputManagerThread.start()

    def __runServer(self, serverPath, popenCommand):
        if self.__platform in ["win32", "win64"]:
            self.serverPopen = Popen(popenCommand, cwd=serverPath, stdin=PIPE,
                                     stdout=PIPE, stderr=PIPE, close_fds=True)
        elif self.__platform == "linux":
            self.serverPopen = Popen(["/bin/bash", "-c", popenCommand], cwd=serverPath,
                                     stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)

    def getNextOutput(self):
        if len(self.outputQueue) > 0:
            returnVal = self.outputQueue[0]
            self.outputQueue.remove(returnVal)
            return returnVal
        return None

    def __outputManager(self):
        while self.running:
            time.sleep(0.01)
            for i in self.serverPopen.stdout:
                self.outputQueue.append(self.__convertLine(i))

    def __convertLineLinux(self, line):
        linestr = str(line)
        return linestr[2:len(linestr)-3]

    def __convertLineWindows(self, line):
        return str(line.rstrip())[2:len(line)]
    
    if __platform in ["win32", "win64"]:
            __convertLine = __convertLineWindows
    else:
        __convertLine = __convertLineLinux


theServer = MCServer(serverPath="Server",
                     popenCommand="java -XX:ParallelGCThreads=2 -Xms1G -Xmx4G -Dfml.readTimeout=60 -jar fabric-server-launch.jar nogui", autoRestarts=False)

while theServer.running:
    out = theServer.getNextOutput()
    if out != None:
        print(out)
    time.sleep(0.01)
