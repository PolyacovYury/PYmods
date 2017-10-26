# -*- coding: utf-8 -*-
import math
import time

import BigWorld
import CommandMapping
import Keys
import Math
import ResMgr
import codecs
import json
import os
import random
import re
import string
import traceback
from Avatar import PlayerAvatar
from DetachedTurret import DetachedTurret
from constants import ARENA_BONUS_TYPE
from functools import partial
from gui import InputHandler
from gui.Scaleform.daapi.view.battle.shared import radial_menu
from gui.Scaleform.daapi.view.battle.shared.radial_menu import SHORTCUT_SETS, SHORTCUT_STATES, getKeyFromAction
from gui.Scaleform.genConsts.BATTLE_ICONS_CONSTS import BATTLE_ICONS_CONSTS
from gui.app_loader.loader import g_appLoader
from gui.battle_control.controllers.chat_cmd_ctrl import CHAT_COMMANDS
from gui.shared.utils.key_mapping import getScaleformKey
from helpers import dependency, isPlayerAvatar
from skeletons.gui.battle_session import IBattleSessionProvider

g_sessionProvider = dependency.instance(IBattleSessionProvider)

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString
MAX_CHAT_MESSAGE_LENGTH = 220


class _Config(object):
    def __init__(self):
        self.filePath = __file__
        self.ID = os.path.basename(self.filePath).split('.')[0].replace('mod_', '')
        self.version = '2.1.0 (%s)' % time.strftime('%d.%m.%Y', time.localtime(
            os.stat('%s/%s' % (BigWorld.curCV, self.filePath)).st_mtime))
        self.fileDir = '%s/%s/' % (BigWorld.curCV, os.path.dirname(self.filePath))
        self.author = 'by Polyacov_Yury (PROTanki edition)'
        self.defaultKeys = {'mapMenu_key': [Keys.KEY_LALT], 'mapMenu_Key': ['KEY_LALT']}
        self.data = {'enabled': True,
                     'mapMenu_key': self.defaultKeys['mapMenu_key'],
                     'mapMenu_Key': self.defaultKeys['mapMenu_Key'],
                     'chatDelay': 550,
                     'hotDelay': 350}
        self.commands = {}
        self.bestConf = None
        self.confType = ''
        self.wasAltMenuPressed = False

    def update_data(self):
        self.commands = {}
        data = self.loadJson(os.path.basename(self.filePath).split('.')[0], self.data, self.fileDir)
        for key in data:
            confSect = data[key]
            if key in self.data:
                self.data[key] = confSect
            elif key == 'hotkeyOnly':
                self.commands[key] = map(CustomMenuCommand, confSect)
            elif key == 'tankSpecific':
                self.commands[key] = tankSect = {}
                for tankName in confSect:
                    tankConf = confSect.get(tankName, {})  # this tells IDE that this is a dict, not list|object|tuple
                    if isinstance(tankConf, str):
                        tankSect[tankName] = tankConf
                    else:
                        tankSect[tankName] = {menuType: map(lambda x: CustomMenuCommand(x) if x else x, tankConf[menuType])
                                              for menuType in tankConf}
            else:
                self.commands[key] = {menuType: map(lambda x: CustomMenuCommand(x) if x else x, menuConf)
                                      for menuType, menuConf in confSect.iteritems()}

        self.readHotKeys(self.data)

    @staticmethod
    def readHotKeys(data):
        for key in data:
            if 'key' not in key:
                continue
            data[key] = []
            for keySet in data.get(key.replace('key', 'Key'), []):
                if isinstance(keySet, list):
                    data[key].append([])
                    for hotKey in keySet:
                        hotKeyName = hotKey if 'KEY_' in hotKey else 'KEY_' + hotKey
                        data[key][-1].append(getattr(Keys, hotKeyName))
                else:
                    hotKeyName = keySet if 'KEY_' in keySet else 'KEY_' + keySet
                    data[key].append(getattr(Keys, hotKeyName))

    def byte_ify(self, inputs):
        if inputs:
            if isinstance(inputs, dict):
                return {self.byte_ify(key): self.byte_ify(value) for key, value in inputs.iteritems()}
            elif isinstance(inputs, list):
                return [self.byte_ify(element) for element in inputs]
            elif isinstance(inputs, tuple):
                return tuple(self.byte_ify(element) for element in inputs)
            elif isinstance(inputs, unicode):
                # noinspection PyArgumentEqualDefault
                return inputs.encode('utf-8')
            else:
                return inputs
        return inputs

    @staticmethod
    def json_comments(text):
        regex = r'\s*(\/{2}).*$'
        regex_inline = r'(:?(?:\s)*([A-Za-zА-Яа-я\d\.{}]*)|((?<=\").*\"),?)(?:\s)*((((\/{2})).*)|)$'
        lines = text.split('\n')
        excluded = []
        for index, line in enumerate(lines):
            if re.search(regex, line):
                if re.search(r'^' + regex, line, re.IGNORECASE):
                    excluded.append(lines[index])
                elif re.search(regex_inline, line):
                    lines[index] = re.sub(regex_inline, r'\1', line)
        for line in excluded:
            lines.remove(line)
        return '\n'.join(lines), excluded

    @staticmethod
    def json_dumps(conf):
        return json.dumps(conf, sort_keys=True, indent=4, ensure_ascii=False, encoding='utf-8-sig', separators=(',', ': '))

    def loadJson(self, name, oldConfig, path):
        config_new = oldConfig
        if not os.path.exists(path):
            os.makedirs(path)
        new_path = '%s%s.json' % (path, name)
        if os.path.isfile(new_path):
            data = ''
            excluded = []
            try:
                with codecs.open(new_path, 'r', encoding='utf-8-sig') as json_file:
                    data, excluded = self.json_comments(json_file.read())
                    config_new = self.byte_ify(json.loads(data))
            except StandardError:
                print new_path
                traceback.print_exc()
                if excluded:
                    print data
        else:
            with codecs.open(new_path, 'w', encoding='utf-8-sig') as json_file:
                data = self.json_dumps(oldConfig)
                json_file.write(self.byte_ify(data))
                config_new = oldConfig
                print '%s: ERROR: Config not found, creating default: %s' % (self.ID, new_path)
        return config_new

    def load(self):
        self.update_data()
        print '%s v.%s %s: initialized.' % (self.ID, self.version, self.author)


def checkKeys(keys):
    if not keys:
        return False
    for key in keys:
        if isinstance(key, int) and not BigWorld.isKeyDown(key):
            return False
        if isinstance(key, list) and not any(BigWorld.isKeyDown(x) for x in key):
            return False

    return True


def pickRandomPart(variantList, lastRandId, doNext=False):
    if not len(variantList):
        return ['', -1]
    if len(variantList) > 1:
        if doNext:
            newId = lastRandId + 1
            if newId >= len(variantList) or newId < 0:
                newId = 0
        else:
            bLoop = True
            newId = 0
            while bLoop:
                newId = random.randrange(len(variantList))
                bLoop = newId == lastRandId

        return variantList[newId], newId
    return variantList[0], 0


def __splitMsg(msg):
    if len(msg) <= MAX_CHAT_MESSAGE_LENGTH:
        return msg, ''
    strPart = msg[:MAX_CHAT_MESSAGE_LENGTH]
    splitPos = strPart.rfind(' ')
    if splitPos == -1:
        splitPos = MAX_CHAT_MESSAGE_LENGTH
    return msg[:splitPos], msg[splitPos:]


def __sendMessagePart(msg, chanId):
    class PYmods_chat(object):
        from messenger.m_constants import PROTO_TYPE
        from messenger.proto import proto_getter

        def __init__(self):
            pass

        @proto_getter(PROTO_TYPE.BW_CHAT2)
        def proto(self):
            return None

    msg = msg.encode('utf-8')
    import BattleReplay
    if PYmods_chat.proto is None or BattleReplay.isPlaying():
        from messenger import MessengerEntry
        MessengerEntry.g_instance.gui.addClientMessage('OFFLINE: %s' % msg, True)
        return
    else:
        if chanId == 0:
            PYmods_chat.proto.arenaChat.broadcast(msg, 1)
        if chanId == 1:
            PYmods_chat.proto.arenaChat.broadcast(msg, 0)
        if chanId == 2:
            PYmods_chat.proto.unitChat.broadcast(msg, 1)


def sendChatMessage(fullMsg, chanId, delay):
    currPart, remains = __splitMsg(fullMsg)
    __sendMessagePart(currPart, chanId)
    if len(remains) == 0:
        return
    BigWorld.callback(delay / 1000.0, partial(sendChatMessage, remains, chanId))


class CameraManager:
    PING_SELF = 100
    PING_MAX = PING_CAMERA = 101
    PING_MIN = 0

    @staticmethod
    def clamp(val, m, b):
        return m if val < m else b if val > b else val

    @staticmethod
    def pos2name(pos):
        # noinspection SpellCheckingInspection
        sqr = 'KJHGFEDCBA'
        line = '1234567890'
        return '%s%s' % (sqr[int(pos[1]) - 1], line[int(pos[0]) - 1])

    def getSquareForPos(self, position):
        position = Math.Vector2(position[0], position[2])
        arenaDesc = BigWorld.player().arena.arenaType
        bottomLeft, upperRight = arenaDesc.boundingBox
        spaceSize = upperRight - bottomLeft
        relPos = position - bottomLeft
        relPos[0] = self.clamp(relPos[0], 0.1, spaceSize[0])
        relPos[1] = self.clamp(relPos[1], 0.1, spaceSize[1])
        return self.pos2name((math.ceil(relPos[0] / spaceSize[0] * 10), math.ceil(relPos[1] / spaceSize[1] * 10)))

    def name2cell(self, name):
        if name == '{ownPos}':
            return self.PING_SELF
        if name == '{viewPos}':
            return self.PING_CAMERA
        try:
            row = string.ascii_uppercase.index(name[0])
            if row > 8:
                row -= 1
            column = (int(name[1]) + 9) % 10
            return row + column * 10
        except StandardError:
            return -1

    def getViewPos(self):
        viewPoint = BigWorld.player().inputHandler.ctrl.getDesiredShotPoint()
        if viewPoint is None:
            return ''
        else:
            return self.getSquareForPos(viewPoint)

    def getOwnPos(self):
        ownPos = BigWorld.entities[BigWorld.player().playerVehicleID].position
        return self.getSquareForPos(ownPos)


class SafeFormatter(string.Formatter):
    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            try:
                return kwargs[key]
            except KeyError:
                return key.join(('{', '}'))
        else:
            super(self.__class__, self).get_value(key, args, kwargs)


camMgr = CameraManager()
safeFmt = SafeFormatter()


class CustomMenuCommand:
    PING_DELAY = 1.0
    DEFAULT_COOLDOWN = 1.1
    ALL_ICONS = dict(filter(lambda x: not x[0].startswith('__'), BATTLE_ICONS_CONSTS.__dict__.items())).values()
    ALL_COMMANDS = dict(filter(lambda x: not x[0].startswith('__'), CHAT_COMMANDS.__dict__.items())).values()
    ALL_CHANNELS = ('Team', 'All', 'Squad')

    def __nonzero__(self):
        return True

    def __init__(self, confDict):
        self.lastRandId = -1
        self.nextUseStamp = 0
        self.randomChoice = True
        self.variantList = []
        self.cmd = confDict.get('text', '')
        self.title = confDict.get('title', 'NO CONFIG')
        chatMode = confDict.get('chatMode', 'Team')
        self.channel = chatMode if chatMode in self.ALL_CHANNELS else 'Team'
        self.builtinCmd = confDict.get('command', '').strip()
        if self.builtinCmd and self.builtinCmd not in self.ALL_COMMANDS:
            print 'RadialMenu: unsupported command: %s' % self.builtinCmd
            self.builtinCmd = ''
        cmdIcon = confDict.get('icon', 'Stop')
        self.icon = cmdIcon if cmdIcon in self.ALL_ICONS else 'Stop'
        if confDict.get('sequentChoice'):
            self.randomChoice = False
        self.cooldownDelay = confDict.get('cooldown', self.DEFAULT_COOLDOWN)
        self.pingList = filter(lambda id: CameraManager.PING_MIN <= id <= CameraManager.PING_MAX,
                               map(camMgr.name2cell, confDict.get('ping', '').split(' ')))
        variants = confDict.get('variants')
        if variants is not None:
            self.variantList.extend(variants)

        confDict['hotkey'] = []
        _config.readHotKeys(confDict)
        self.hotKeys = confDict['hotkey']

    def __repr__(self):
        return '<CMC %s (%s)>' % (self.title, self.icon)

    def handleKeys(self, keyCodes):
        return False \
            if len(self.hotKeys) == 1 and BigWorld.player()._PlayerAvatar__forcedGuiCtrlModeFlags \
            else checkKeys(keyCodes)

    def doPing(self, seqId):
        if seqId == len(self.pingList):
            return
        cellId = self.pingList[seqId]
        if cellId == CameraManager.PING_SELF:
            cellId = camMgr.name2cell(camMgr.getOwnPos())
        elif cellId == CameraManager.PING_CAMERA:
            cellId = camMgr.name2cell(camMgr.getViewPos())
        player = BigWorld.player()
        backup_FGCM = player._PlayerAvatar__forcedGuiCtrlModeFlags
        player._PlayerAvatar__forcedGuiCtrlModeFlags = True
        chatCommands = g_sessionProvider.shared.chatCommands
        chatCommands.sendAttentionToCell(cellId)
        player._PlayerAvatar__forcedGuiCtrlModeFlags = backup_FGCM
        BigWorld.callback(self.PING_DELAY, partial(self.doPing, seqId + 1))

    def checkCooldown(self):
        return self.nextUseStamp < BigWorld.time()

    def updateCooldown(self):
        self.nextUseStamp = BigWorld.time() + self.cooldownDelay

    def format(self, argDict):
        try:
            BigWorld.callback(self.PING_DELAY, partial(self.doPing, 0))
            argDict.update({'randPart': '',
                            'viewPos': camMgr.getViewPos(),
                            'ownPos': camMgr.getOwnPos(),
                            'reload': '%.3g' % g_sessionProvider.shared.ammo.getGunReloadingState(0).getTimeLeft(),
                            'ammo': g_sessionProvider.shared.ammo.getCurrentShells(0)[1],
                            'ownVehicle': g_sessionProvider.getArenaDP().getVehicleInfo().vehicleType.shortName})
            argDict['randPart'], self.lastRandId = pickRandomPart(self.variantList, self.lastRandId, not self.randomChoice)
            argDict['randPart'] = safeFmt.format(argDict['randPart'], **argDict)
            return safeFmt.format(self.cmd, **argDict)
        except StandardError:
            traceback.print_exc()


_config = _Config()
_config.load()


def getCrosshairType(player, target):
    if not isTargetCorrect(player, target):
        return SHORTCUT_STATES.DEFAULT
    elif target.publicInfo.team == player.team:
        return SHORTCUT_STATES.ALLY
    else:
        return SHORTCUT_STATES.ENEMY


def isTargetCorrect(player, target):
    if target is not None and not isinstance(target, DetachedTurret) and target.isAlive() and player is not None and \
            isPlayerAvatar():
        vInfo = g_sessionProvider.getArenaDP().getVehicleInfo(target.id)
        return not vInfo.isActionsDisabled()
    else:
        return False


def findBestFitConf(commandConf):
    if _config.bestConf is not None:
        return _config.bestConf, _config.confType
    vehicleTypeDescr = g_sessionProvider.getArenaDP().getVehicleInfo().vehicleType
    vehicleType = vehicleTypeDescr.classTag
    vehicleName = vehicleTypeDescr.iconName
    if '-' in vehicleName:
        vehicleName = vehicleName.split('-', 1)[1]
    menuConf = None
    menuType = ''
    allMenuConf = commandConf.get('tankSpecific')
    if allMenuConf is not None:
        menuConf = allMenuConf.get(vehicleName)
        menuType = 'tankSpecific' + vehicleName
        if menuConf is not None:
            if isinstance(menuConf, str):
                menuConf = allMenuConf.get(menuConf)
                menuType = 'tankSpecific' + menuConf
    if menuConf is None and vehicleType is not None:
        menuConf = commandConf.get(vehicleType + 'Menu')
        menuType = vehicleType + 'Menu'
    if menuConf is None:
        menuConf = commandConf.get('TankMenu')
        menuType = 'TankMenu'
    if vehicleType is not None:
        _config.bestConf, _config.confType = menuConf, menuType
    return menuConf, menuType


def inj_hkKeyEvent(event):
    BattleApp = g_appLoader.getDefBattleApp()
    try:
        if BattleApp and _config.data['enabled']:
            isDown = checkKeys(_config.data['mapMenu_key'])
            if isDown or _config.wasAltMenuPressed:
                _config.wasAltMenuPressed = isDown
                CommandMapping.g_instance.onMappingChanged()
            if event.isKeyDown():
                target = BigWorld.target()
                player = BigWorld.player()
                commandsData = _config.commands
                state = getCrosshairType(player, target)
                menuConf, _ = findBestFitConf(commandsData)
                commandsList = commandsData.get('hotkeyOnly', [])
                if menuConf is not None:
                    commandsList.extend(menuConf.get(state, []))
                for command in commandsList:
                    if command and command.handleKeys(command.hotKeys):
                        BigWorld.callback(_config.data['hotDelay'] / 1000.0, partial(onCustomAction, command, target))
    except StandardError:
        print 'RadialMenu: ERROR at inj_hkKeyEvent'
        traceback.print_exc()


def new_destroyGUI(self):
    old_destroyGUI(self)
    _config.bestConf = None
    _config.confType = ''


old_destroyGUI = PlayerAvatar._PlayerAvatar__destroyGUI
PlayerAvatar._PlayerAvatar__destroyGUI = new_destroyGUI
InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent


def new_updateMenu(self):
    data = []
    menuConf = None
    menuType = ''
    mapName = BigWorld.player().arena.arenaType.geometryName
    commandConf = _config.commands
    if checkKeys(_config.data['mapMenu_key']):
        menuConf = commandConf.get('Map_' + mapName)
        menuType = 'Map_' + mapName
        if menuConf is None:
            menuConf = commandConf.get('Map_default')
            menuType = 'Map_default'
    if menuConf is None:
        menuConf, menuType = findBestFitConf(commandConf)
    for state in SHORTCUT_STATES.ALL:
        stateData = map(lambda x: {'title': x.title,
                                   'action': x.action,
                                   'icon': x.icon,
                                   'key': getKeyFromAction(*((x.action,) + (() if '16' in BigWorld.curCV else (state,))))},
                        SHORTCUT_SETS[state])
        if menuConf is not None:
            menuState = state.replace('_spg', '')
            for idx in xrange(min(len(menuConf.get(menuState, [])), len(stateData))):
                if not menuConf[menuState][idx]:
                    continue
                keys = menuConf[menuState][idx].hotKeys
                if keys:
                    hotKeys = filter(lambda x: not isinstance(x, list), keys)
                    if not hotKeys:
                        hotKeys = keys[0]
                    hotkey = hotKeys[0] if len(hotKeys) == 1 else 0
                else:
                    hotkey = 0
                stateData[idx] = {'title': menuConf[menuState][idx].title,
                                  'action': '.'.join((menuType, menuState, '%s' % idx)),
                                  'icon': menuConf[menuState][idx].icon,
                                  'key': getScaleformKey(hotkey)}
        data.append({'state': state,
                     'data': stateData})

    self.as_buildDataS(data)


def onCustomAction(cmd, target):
    if not cmd.checkCooldown():
        return
    else:
        player = BigWorld.player()
        if target is None:
            target = BigWorld.entities.get(player.playerVehicleID)
        if cmd.channel == 'All' and player.arena.bonusType == ARENA_BONUS_TYPE.TRAINING:
            chanId = 0
        elif cmd.channel in ('Team', 'All'):
            chanId = 1
        else:
            chanId = 2
        targetInfo = player.arena.vehicles.get(target.id, {})
        targetDict = {'name': target.publicInfo.name,
                      'vehicle': targetInfo['vehicleType'].type.shortUserString,
                      'clan': targetInfo['clanAbbrev']}
        msg = cmd.format(targetDict)
        if cmd.builtinCmd:
            chatCommands = g_sessionProvider.shared.chatCommands
            if chatCommands is not None:
                chatCommands.handleChatCommand(cmd.builtinCmd, target.id)
            BigWorld.callback(_config.data['chatDelay'] / 1000.0,
                              partial(sendChatMessage, msg.decode('utf-8'), chanId, _config.data['chatDelay']))
        else:
            sendChatMessage(msg.decode('utf-8'), chanId, _config.data['chatDelay'])
        cmd.updateCooldown()


def new_onAction(self, action):
    if '.' in action:
        commands = _config.commands
        if commands is not None:
            menuType, state, idx = action.split('.')
            targetID = self._RadialMenu__targetID
            target = BigWorld.entities.get(targetID) if targetID is not None else None
            if 'tankSpecific' in menuType:
                onCustomAction(commands['tankSpecific'][menuType.replace('tankSpecific', '')][state][int(idx)], target)
            else:
                onCustomAction(commands[menuType][state][int(idx)], target)
    else:
        old_onAction(self, action)


old_updateMenu = radial_menu.RadialMenu._RadialMenu__updateMenu
radial_menu.RadialMenu._RadialMenu__updateMenu = new_updateMenu
old_onAction = radial_menu.RadialMenu.onAction
radial_menu.RadialMenu.onAction = new_onAction
