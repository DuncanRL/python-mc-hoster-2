if "Imports":
    import pip
    import uuid
    import time
    import json
    import sys

    from subprocess import PIPE, Popen
    from re import search, compile
    from threading import Thread, activeCount
    from sys import platform
    from os.path import isfile
    from multiprocessing import Process

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
        import discord
    except:
        pinstall("discord")
        import discord


def getUUID(Username):
    return str(uuid.UUID(mcuuid.GetPlayerData(Username).uuid))


class ServerUnavailableException(Exception):
    pass


class InvalidPlatformException(Exception):
    pass


class MCServer:
    __platform = platform
    __stopReg = compile(
        r'\[..:..:..\] \[Server thread/INFO\]: Stopping server').search
    __doneReg = compile(r'\[..:..:..\] \[Server thread/INFO\]: Done').search

    def __init__(self, serverPath, popenCommand, printOutput=False):
        self.__ending = False
        self.__available = True
        self.__loaded = False
        self.__started = False
        self.__stopping = False
        self.__printOutput = printOutput
        self.__serverPopen = None
        self.__serverPath = serverPath
        self.__popenCommand = popenCommand
        self.__outputQueue = []
        self.__startManagerThread()

    def __getPopen(self):
        if not isinstance(self.__serverPopen, Popen):
            return None
        elif self.__serverPopen.poll() != None:
            return None
        else:
            return self.__serverPopen

    def getPopen(self):
        if not self.__available:
            raise ServerUnavailableException
            return
        return self.__getPopen()

    def getStatus(self):
        if not self.__available:
            return "Unavailable"
        elif self.__stopping:
            return "Stopping"
        elif self.__loaded:
            return "Loaded"
        elif self.__started and not self.__loaded:
            return "Starting"
        elif not self.__started:
            return "Waiting"

    def start(self):
        if not self.__available:
            raise ServerUnavailableException
            return
        else:
            self.__started = True
            while self.__getPopen() != None:
                time.sleep(0.1)
            self.__startServer(self.__serverPath, self.__popenCommand)

    def __startServer(self, serverPath, popenCommand):
        if self.__platform in ["win32", "win64"]:
            self.__serverPopen = Popen(popenCommand, cwd=serverPath, stdin=PIPE,
                                       stdout=PIPE, stderr=PIPE, close_fds=True)
        elif self.__platform == "linux":
            self.__serverPopen = Popen(["/bin/bash", "-c", popenCommand], cwd=serverPath,
                                       stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)

    def __startManagerThread(self):
        self.__managerThread = Thread(
            target=self.__manager, args=())
        self.__managerThread.start()

    def __manager(self):
        while self.__available or self.__started:
            time.sleep(0.05)
            if self.__getPopen() != None:
                self.__started = True
                for i in self.__serverPopen.stdout:
                    line = self.__convertLine(i)

                    if self.__printOutput:
                        print(line)
                    else:
                        self.__outputQueue.append(line)

                    if self.__doneReg(line):
                        self.__loaded = True
                    elif self.__stopReg(line):
                        self.__loaded = False
            else:
                self.__started = False
                self.__loaded = False
                self.__stopping = False
        self.__loaded = False
        self.__started = False

    def __convertLineLinux(self, line):
        linestr = str(line.decode())
        return linestr[2:len(linestr)-3]

    def __convertLineWindows(self, line):
        return str(line.decode().rstrip())

    if __platform in ["win32", "win64"]:
        __convertLine = __convertLineWindows
    elif __platform == "linux":
        __convertLine = __convertLineLinux
    else:
        raise InvalidPlatformException

    def getNextOutput(self):
        if len(self.__outputQueue) > 0:
            returnVal = self.__outputQueue[0]
            self.__outputQueue.remove(returnVal)
            return returnVal
        return None

    def restart(self):
        if not self.__available:
            raise ServerUnavailableException
            return
        if not self.__started:
            return False
        else:
            while not self.sendCommand("stop"):
                time.sleep(0.2)
            self.__loaded = False
            self.__stopping = True
            return True
    stop = restart

    def killServer(self):
        self.__serverPopen.kill()
        self.__serverPopen = None
        self.__ending = False
        self.__stopping = False
        self.__started = False
        self.__loaded = False
        self.__available = False

    def end(self):
        if not self.__available:
            raise ServerUnavailableException
            return
        if not self.__ending:
            self.__ending = True
            if not self.__stopping:
                self.stop()
            while self.__started:
                time.sleep(0.1)
            self.__available = False

    fullstop = end

    def sendCommand(self, command):
        if not self.__available:
            raise ServerUnavailableException
            return
        if self.__loaded:
            self.__serverPopen.stdin.write((command+"\n").encode())
            self.__serverPopen.stdin.flush()
            return True
        else:
            return False

    def isAvailable(self):
        return self.__available


class MCServerManager:
    __playerChatReg = compile(
        r'\[..:..:..\] \[Server thread/INFO\]: <.*?> .*?').search
    __playerJoinReg = compile(
        r'\[..:..:..\] \[Server thread/INFO\]: .*? joined the game').search
    __playerLeaveReg = compile(
        r'\[..:..:..\] \[Server thread/INFO\]: .*? left the game').search
    __playerShadowReg = compile(
        r'\[..:..:..\] \[Server thread/INFO\]: .*?\[local\] logged in with entity id .*?').search
    __doneReg = compile(
        r'\[..:..:..\] \[Server thread/INFO\]: Done .*?').search
    __stopReg = compile(
        r'\[..:..:..\] \[Server thread/INFO\]: Stopping server').search

    def __init__(self, optionsPath="options.json", playerListPath="players.txt"):

        optionsFile = open(optionsPath, "r")
        self.__optionsJSON = json.load(optionsFile)
        optionsFile.close()

        self.__Status = None
        self.__playerListPath = playerListPath
        self.__autoRestarting = self.__optionsJSON["autoRestarting"]
        self.__server = MCServer(
            self.__optionsJSON["serverPath"], self.__optionsJSON["popenCommand"])
        self.start()
        self.__running = True
        self.__players = []
        self.__writePlayers()
        self.__startManagerThread()

        if self.__optionsJSON["discord"]:
            if platform == "linux":
                discordServer = Popen("python3 mchost.py discord "+optionsPath)
            else:
                discordServer = Popen("python mchost.py discord "+optionsPath)

    def getPlayers(self):
        return self.__players[:]

    def __startManagerThread(self):
        self.__managerThread = Thread(target=self.__manager, args=())
        self.__managerThread.start()

    def start(self):
        self.__server.start()

    def restart(self):
        self.__server.stop()
        self.__players = []
    stop = restart

    def killServer(self):
        self.__autoRestarting = False
        self.__server.killServer()
        self.__running = False

    def end(self):
        self.__autoRestarting = False
        self.__server.end()
        self.__running = False

    def __writePlayers(self):
        playerListFile = open(self.__playerListPath, "w+")
        for i in self.__players:
            playerListFile.write(i.toString()+"\n")
        playerListFile.close()

    def __manager(self):
        while self.__server.isAvailable() or self.__running:

            self.__processOutput()

            if self.__autoRestarting and self.__server.getStatus() == "Waiting":
                self.__server.start()
            elif self.__server.getStatus() != "Loaded":
                self.__players = []

    def __processOutput(self):
        output = self.__server.getNextOutput()
        cancelOutput = False
        if output != None:

            if self.__playerChatReg(output):
                playerName = output[34:output.index("> ")]
                playerMessage = output[output.index("> ")+2:]
                self.__commandCheck(playerName, playerMessage)
                if self.__optionsJSON["discord"]:
                    DiscordWebhook(url=self.__optionsJSON["discordSettings"]["webhookURL"], content=playerMessage, username=playerName,
                                   avatar_url="https://crafatar.com/renders/head/"+getUUID(playerName)+"?overlay").execute()

            elif self.__playerJoinReg(output):
                playerName = output[33:output.index(" joined the game")]
                alreadyExists = False
                for i in self.__players:
                    if i.hasSamePlayerName(playerName):
                        alreadyExists = True
                        break
                if not alreadyExists:
                    self.__players.append(MCPlayer(playerName))
                    self.__writePlayers()
                    DiscordWebhook(url=self.__optionsJSON["discordSettings"]["webhookURL"],
                                   content=playerName + " joined the game", username="Server Hoster").execute()

            elif self.__playerLeaveReg(output):
                playerName = output[33:output.index(" left the game")]
                for i in self.__players:
                    if i.hasSamePlayerName(playerName) and not i.checkShadowTime():
                        self.__players.remove(i)
                        self.__writePlayers()
                        DiscordWebhook(url=self.__optionsJSON["discordSettings"]["webhookURL"],
                                       content=playerName + " left the game", username="Server Hoster").execute()

            elif self.__playerShadowReg(output):
                print("\nSHADOW\n")
                playerName = output[33:output.index("[local]")]
                playerFound = False
                for i in self.__players:
                    if i.hasSamePlayerName(playerName):
                        i.setShadowed()
                        playerFound = True
                        break
                if not playerFound:
                    player = MCPlayer(playerName)
                    player.setShadowed()
                    self.__players.append(player)
                self.__writePlayers()
                DiscordWebhook(url=self.__optionsJSON["discordSettings"]["webhookURL"],
                               content=playerName + " has shadowed", username="Server Hoster").execute()

            elif self.__doneReg(output):
                pass

            if not cancelOutput:
                print(output)

    def isRunning(self):
        return self.__running or self.__server.isAvailable()

    def __commandCheck(self, playerName, playerMessage):
        return True


class MCPlayer():
    def __init__(self, playerName):
        self.__playerName = playerName
        self.__shadowTime = time.time()-1
        self.__shadowed = False

    def setShadowed(self):
        self.__shadowed = True
        self.__shadowTime = time.time()

    def getShadowed(self):
        return self.__shadowed

    def checkShadowTime(self):
        if time.time() - self.__shadowTime < 1:
            return True
        return False

    def getPlayerName(self):
        return self.__playerName

    def toString(self):
        return self.__playerName + (" (Shadow)" if self.__shadowed else "")

    def hasSamePlayerName(self, player):
        if isinstance(player, MCPlayer):
            return self.__playerName == player.getPlayerName()
        else:
            return self.__playerName == player


class MCServerDiscordBot(discord.Client):
    global optionsJSON

    async def on_ready(self):
        print("[Server Hoster] Discord bot logged on as", self.user)
        self.__listMessage = await self.get_channel(optionsJSON["discordSettings"]["channel"]).send("Players Online: None")
        pins = await self.get_channel(optionsJSON["discordSettings"]["channel"]).pins()
        for i in pins:
            await i.delete()
        await self.__listMessage.pin()

    async def on_message(self, message):
        if message.is_system():
            await message.delete()
        if message.author.bot and str(message.author) == "Server Hoster#0000":
            if "the game" in message.content or "has shadowed" in message.content:
                time.sleep(0.2)
                await self.__updateOnline()

    async def __updateOnline(self):
        playersFile = open("players.txt", "r")
        playerText = playersFile.read()
        playersFile.close()
        if len(playerText) > 0:
            await self.__listMessage.edit(content="Players Online:\n"+playerText)
        else:
            await self.__listMessage.edit(content="Players Online:\nNone")
        await self.change_presence(activity=discord.Game(name="Online: "+str(playerText.count("\n"))))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "discord":
        optionsPath = ""
        for i in sys.argv[2:]:
            optionsPath += i
        optionsFile = open(optionsPath, "r")
        optionsJSON = json.load(optionsFile)
        optionsFile.close()

        bot = MCServerDiscordBot()
        bot.run(optionsJSON["discordSettings"]["token"])
    elif len(sys.argv) == 2:
        print("Missing options path.")
    else:
        mcServer = MCServerManager()


"""
TODO:
- Update player list correctly on restarts
- Add Server Hoster Messages for restarts and loads.
- Shutdown discord bot
"""
