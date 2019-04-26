# -*- coding: utf-8 -*-
import math

import BigWorld
import CommandMapping
import Keys
import Math
import glob
import os
import string
import traceback
from PYmodsCore import PYmodsConfigInterface, loadJson, config, checkKeys, pickRandomPart, Analytics, overrideMethod, \
    sendChatMessage, events, curCV
from Vehicle import Vehicle
from constants import ARENA_BONUS_TYPE
from functools import partial
from gui import InputHandler
from gui.Scaleform.daapi.view.battle.shared import radial_menu
from gui.Scaleform.daapi.view.battle.shared.radial_menu import SHORTCUT_SETS, SHORTCUT_STATES, getKeyFromAction
from gui.Scaleform.genConsts.BATTLE_ICONS_CONSTS import BATTLE_ICONS_CONSTS
from gui.app_loader.loader import g_appLoader
from gui.battle_control import avatar_getter
from gui.battle_control.controllers.chat_cmd_ctrl import CHAT_COMMANDS
from gui.shared.utils.key_mapping import getScaleformKey
from helpers import dependency, isPlayerAvatar
from skeletons.gui.battle_session import IBattleSessionProvider

g_sessionProvider = dependency.instance(IBattleSessionProvider)


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.configsMeta = {}
        self.activeConfigs = []
        self.commands = {}
        self.wasAltMenuPressed = False
        self.bestConf = None
        self.confType = ''
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '2.1.2 (%(file_compile_date)s)'
        self.author += ' (orig by locastan/tehHedger/TRJ_VoRoN)'
        self.defaultKeys = {'mapMenu_key': [Keys.KEY_LALT]}
        self.data = {'enabled': True,
                     'mapMenu_key': self.defaultKeys['mapMenu_key'],
                     'selectedConfig': 12,
                     'chatDelay': 550,
                     'hotDelay': 350}
        self.i18n = {
            'UI_description': 'Radial Menu',
            'UI_setting_info_text': 'Special for ',
            'UI_setting_mapMenu_key_text': 'Alternative menu hotkey',
            'UI_setting_mapMenu_key_tooltip': (
                'When Radial menu is activated while this key is pressed, an alternative map-specific menu is loaded if '
                'the config provides one.'),
            'UI_setting_selectedConfig_text': 'Active config:',
            'UI_setting_selectedConfig_tooltip': 'This config will be used when Radial menu is activated.',
            'UI_setting_selectedConfig_defaultMeta': 'Default messages'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        optionsList = map(lambda x: self.configsMeta.get(x, x), self.activeConfigs)
        infoLabel = self.tb.createLabel('info')
        infoLabel['text'] += 'wotspeak.ru'
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [self.tb.createOptions('selectedConfig', optionsList)],
                'column2': [self.tb.createHotKey('mapMenu_key'),
                            infoLabel]}

    def onApplySettings(self, settings):
        super(self.__class__, self).onApplySettings(settings)
        self.readCurrentSettings()

    def readCurrentSettings(self, quiet=True):
        super(self.__class__, self).readCurrentSettings()
        self.activeConfigs[:] = ['default']
        self.configsMeta = {'default': self.i18n['UI_setting_selectedConfig_defaultMeta']}
        # noinspection SpellCheckingInspection
        self.commands = {'default': {'hotkeyOnly': [CustomMenuCommand({'command': 'RELOADINGGUN', 'hotKey': ['KEY_C']})]}}
        for confPath in glob.iglob(self.configPath + 'skins/*.json'):
            confName = os.path.basename(confPath).split('.')[0]
            try:
                confDict = loadJson(self.ID, confName, {}, os.path.dirname(confPath) + '/')
            except StandardError:
                print self.ID + ': config', os.path.basename(confPath), 'is invalid.'
                traceback.print_exc()
                continue
            self.configsMeta[confName] = confDict.get('meta', confName)
            self.activeConfigs.append(confName)
            self.commands[confName] = commands = {}
            for key in confDict:
                if key == 'meta':
                    continue
                confSect = confDict[key]
                if key == 'hotkeyOnly':
                    commands[key] = map(CustomMenuCommand, confSect)
                elif key == 'tankSpecific':
                    commands[key] = tankSect = {}
                    for tankName in confSect:
                        tankConf = confSect[tankName]
                        if isinstance(tankConf, str):
                            tankSect[tankName] = tankConf
                        else:
                            tankSect[tankName] = {
                                menuType: map(lambda x: CustomMenuCommand(x) if x else x, tankConf[menuType])
                                for menuType in tankConf}
                else:
                    commands[key] = {menuType: map(lambda x: CustomMenuCommand(x) if x else x, menuConf)
                                     for menuType, menuConf in confSect.iteritems()}

        self.data['selectedConfig'] = min(self.data['selectedConfig'], len(self.activeConfigs) - 1)


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
                return '{%s}' % key
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
        self.inPostmortem = confDict.get('inPostmortem', False)
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

        config.utils.processHotKeys(confDict, ('hotkey',), 'read')
        self.hotKeys = confDict.get('hotkey', [])

    def __repr__(self):
        return '<CMC %s (%s)>' % (self.title, self.icon)

    def handleKeys(self, keys, key):
        return not (len(self.hotKeys) == 1 and BigWorld.player().getForcedGuiControlModeFlags()) and checkKeys(keys, key)

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
                            'reload': '%.3g' % g_sessionProvider.shared.ammo.getGunReloadingState().getTimeLeft(),
                            'ammo': g_sessionProvider.shared.ammo.getCurrentShells()[1],
                            'ownVehicle': g_sessionProvider.getArenaDP().getVehicleInfo().vehicleType.shortName})
            argDict['randPart'], self.lastRandId = pickRandomPart(self.variantList, self.lastRandId, self.randomChoice)
            argDict['randPart'] = safeFmt.format(argDict['randPart'], **argDict)
            return safeFmt.format(self.cmd, **argDict)
        except StandardError:
            traceback.print_exc()


_config = ConfigInterface()
statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-10',
                          [_config.activeConfigs[_config.data['selectedConfig']]])


def getCrosshairType(player, target):
    if not isTargetCorrect(player, target):
        return SHORTCUT_STATES.DEFAULT
    elif target.publicInfo.team == player.team:
        return SHORTCUT_STATES.ALLY
    else:
        return SHORTCUT_STATES.ENEMY


def isTargetCorrect(player, target):
    if target is not None and isinstance(target, Vehicle) and target.isAlive() and player is not None and isPlayerAvatar():
        return not g_sessionProvider.getArenaDP().getVehicleInfo(target.id).isActionsDisabled()
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
                commandsData = _config.commands.get(_config.activeConfigs[_config.data['selectedConfig']], {})
                state = getCrosshairType(player, target)
                menuConf, _ = findBestFitConf(commandsData)
                commandsList = commandsData.get('hotkeyOnly', [])
                if menuConf is not None:
                    commandsList.extend(menuConf.get(state, []))
                for command in commandsList:
                    if command and command.handleKeys(command.hotKeys, event.key):
                        BigWorld.callback(_config.data['hotDelay'] / 1000.0, partial(onCustomAction, command, target))
    except StandardError:
        print 'RadialMenu: ERROR at inj_hkKeyEvent'
        traceback.print_exc()


@events.PlayerAvatar.destroyGUI.before
def new_destroyGUI(*_, **__):
    _config.bestConf = None
    _config.confType = ''


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent


@overrideMethod(radial_menu.RadialMenu, '_RadialMenu__updateMenu')
def new_updateMenu(_, self):
    data = []
    menuConf = None
    menuType = ''
    mapName = BigWorld.player().arena.arenaType.geometryName
    commandConf = _config.commands.get(_config.activeConfigs[_config.data['selectedConfig']], {})
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
                                   'key': getKeyFromAction(*((x.action,) + (() if '16' in curCV else (state,))))},
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
    if not cmd.checkCooldown() or not (cmd.inPostmortem or avatar_getter.isVehicleAlive()):
        return
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


@overrideMethod(radial_menu.RadialMenu, 'onAction')
def new_onAction(base, self, action):
    if '.' in action:
        commands = _config.commands.get(_config.activeConfigs[_config.data['selectedConfig']])
        if commands is not None:
            menuType, state, idx = action.split('.')
            targetID = self._RadialMenu__targetID
            target = BigWorld.entities.get(targetID) if targetID is not None else None
            if 'tankSpecific' in menuType:
                onCustomAction(commands['tankSpecific'][menuType.replace('tankSpecific', '')][state][int(idx)], target)
            else:
                onCustomAction(commands[menuType][state][int(idx)], target)
    else:
        base(self, action)
