# -*- coding: utf-8 -*-
import glob
import math
import os
import string
import traceback
from functools import partial

import BigWorld
import Math
import ResMgr

import CommandMapping
import Keys
import PYmodsCore
from constants import ARENA_BONUS_TYPE
from gui import InputHandler
from gui.Scaleform.daapi.view.battle.shared import radial_menu
from gui.Scaleform.daapi.view.battle.shared.radial_menu import SHORTCUT_SETS, SHORTCUT_STATES, getKeyFromAction
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.genConsts.BATTLE_ICONS_CONSTS import BATTLE_ICONS_CONSTS
from gui.app_loader.loader import g_appLoader
from gui.battle_control.controllers.chat_cmd_ctrl import CHAT_COMMANDS
from gui.shared.utils.key_mapping import getScaleformKey
from helpers import isPlayerAvatar

try:
    from gui.battle_control import g_sessionProvider
except ImportError:
    from helpers import dependency
    from skeletons.gui.battle_session import IBattleSessionProvider

    g_sessionProvider = dependency.instance(IBattleSessionProvider)

try:
    from gui.mods import mod_PYmodsGUI
except ImportError:
    mod_PYmodsGUI = None
    print 'RadialMenu: no-GUI mode activated'
except StandardError:
    mod_PYmodsGUI = None
    traceback.print_exc()

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString


class _Config(PYmodsCore._Config):
    def __init__(self):
        super(_Config, self).__init__(__file__)
        self.version = '2.0.0 (%s)' % self.version
        self.author = '%s (orig by locastan/tehHedger/TRJ_VoRoN)' % self.author
        self.defaultKeys = {'mapMenu_key': [Keys.KEY_LALT], 'mapMenu_Key': ['KEY_LALT']}
        self.data = {'enabled': True,
                     'mapMenu_key': self.defaultKeys['mapMenu_key'],
                     'mapMenu_Key': self.defaultKeys['mapMenu_Key'],
                     'selectedConfig': 11,
                     'chatDelay': 550,
                     'hotDelay': 350,
                     'analyticsFull': True}
        self.i18n = {
            'UI_description': 'Radial Menu',
            'UI_setting_info': 'Special for ',
            'UI_setting_mapMenuKey_text': 'Alternative menu hotkey',
            'UI_setting_mapMenuKey_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}When Radial menu is activated while this key is pressed, an '
                'alternative map-specific menu is loaded if the config provides one.{/BODY}'),
            'UI_setting_selectedConfig_text': 'Active config:',
            'UI_setting_selectedConfig_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}This config will be used when Radial menu is activated.{/BODY}'),
            'UI_setting_selectedConfig_defaultMeta': 'Default messages'}
        self.configsMeta = {}
        self.activeConfigs = []
        self.commands = {}
        self.wasAltMenuPressed = False
        self.loadLang()

    def template_settings(self):
        optionsList = [{'label': self.configsMeta.get(confName, confName)} for confName in self.activeConfigs]
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [{'type': 'Dropdown',
                             'text': self.i18n['UI_setting_selectedConfig_text'],
                             'tooltip': self.i18n['UI_setting_selectedConfig_tooltip'],
                             'itemRenderer': 'DropDownListItemRendererSound',
                             'options': optionsList,
                             'width': 200,
                             'value': self.data['selectedConfig'],
                             'varName': 'selectedConfig'}],
                'column2': [{'type': 'HotKey',
                             'text': self.i18n['UI_setting_mapMenuKey_text'],
                             'tooltip': self.i18n['UI_setting_mapMenuKey_tooltip'],
                             'value': self.data['mapMenu_key'],
                             'defaultValue': self.defaultKeys['mapMenu_key'],
                             'varName': 'mapMenu_key'},
                            {'type': 'Label',
                             'text': self.i18n['UI_setting_info'] + 'wotspeak.ru'}]}

    def apply_settings(self, settings):
        super(_Config, self).apply_settings(settings)
        self.update_data()
        _gui_config.update_template('%s' % self.ID, self.template_settings)

    def update_settings(self, doPrint=False):
        super(_Config, self).update_settings()
        _gui_config.updateFile('%s' % self.ID, self.data, self.template_settings)

    def update_data(self, doPrint=False):
        super(_Config, self).update_data(doPrint)
        self.activeConfigs = ['default']
        self.configsMeta = {'default': self.i18n['UI_setting_selectedConfig_defaultMeta']}
        # noinspection SpellCheckingInspection
        self.commands = {'default': {'hotkeyOnly': [CustomMenuCommand({'command': 'RELOADINGGUN', 'hotKey': ['KEY_C']})]}}
        for configPath in glob.iglob(self.configPath + '*.json'):
            confPath = configPath.replace('%s/' % BigWorld.curCV, '')
            confName = os.path.basename(configPath).split('.')[0]
            try:
                confDict = self.loadJson(confName, {}, os.path.dirname(configPath) + '/')
            except StandardError:
                print 'RadialMenu: config %s is invalid.' % os.path.basename(confPath)
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
                        if isinstance(tankConf, basestring):
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
                return key.join(('{', '}'))
        else:
            super(SafeFormatter, self).get_value(key, args, kwargs)


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
            else PYmodsCore.checkKeys(keyCodes)

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
                            'reload': '%.3g' % g_sessionProvider.shared.ammo._reloadingState.getTimeLeft(),
                            'ammo': g_sessionProvider.shared.ammo.getCurrentShells()[1],
                            'ownVehicle': g_sessionProvider.getArenaDP().getVehicleInfo().vehicleType.shortName})
            argDict['randPart'], self.lastRandId = PYmodsCore.pickRandomPart(self.variantList, self.lastRandId,
                                                                             not self.randomChoice)
            argDict['randPart'] = safeFmt.format(argDict['randPart'], **argDict)
            return safeFmt.format(self.cmd, **argDict)
        except StandardError:
            traceback.print_exc()


_gui_config = getattr(mod_PYmodsGUI, 'g_gui', None)
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
    if target is not None and target.isAlive() and player is not None and isPlayerAvatar():
        vInfo = g_sessionProvider.getArenaDP().getVehicleInfo(target.id)
        return not vInfo.isActionsDisabled()
    else:
        return False


def findBestFitConf(commandConf):
    vehicleTypeDescr = g_sessionProvider.getArenaDP().getVehicleInfo().vehicleType
    vehicleType = vehicleTypeDescr.classTag
    vehicleName = vehicleTypeDescr.iconName.split('-', 1)[1]
    menuConf = None
    menuType = ''
    allMenuConf = commandConf.get('tankSpecific')
    if allMenuConf is not None:
        menuConf = allMenuConf.get(vehicleName)
        menuType = 'tankSpecific' + vehicleName
        if menuConf is not None:
            if isinstance(menuConf, string):
                menuConf = allMenuConf.get(menuConf)
                menuType = 'tankSpecific' + menuConf
    if menuConf is None:
        menuConf = commandConf.get(vehicleType + 'Menu')
        menuType = vehicleType + 'Menu'
    if menuConf is None:
        menuConf = commandConf.get('TankMenu')
        menuType = 'TankMenu'
    return menuConf, menuType


def inj_hkKeyEvent(event):
    BattleApp = g_appLoader.getDefBattleApp()
    try:
        if BattleApp and _config.data['enabled']:
            isDown = PYmodsCore.checkKeys(_config.data['mapMenu_key'])
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
                    if command and command.handleKeys(command.hotKeys):
                        BigWorld.callback(_config.data['hotDelay'] / 1000.0, partial(onCustomAction, command, target))
    except StandardError:
        print 'RadialMenu: ERROR at inj_hkKeyEvent'
        traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent


def new_updateMenu(self):
    data = []
    menuConf = None
    menuType = ''
    mapName = BigWorld.player().arena.arenaType.geometryName
    commandConf = _config.commands.get(_config.activeConfigs[_config.data['selectedConfig']], {})
    if PYmodsCore.checkKeys(_config.data['mapMenu_key']):
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
                              partial(PYmodsCore.sendChatMessage, msg.decode('utf-8'), chanId, _config.data['chatDelay']))
        else:
            PYmodsCore.sendChatMessage(msg.decode('utf-8'), chanId, _config.data['chatDelay'])
        cmd.updateCooldown()


def new_onAction(self, action):
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
        old_onAction(self, action)


old_updateMenu = radial_menu.RadialMenu._RadialMenu__updateMenu
radial_menu.RadialMenu._RadialMenu__updateMenu = new_updateMenu
old_onAction = radial_menu.RadialMenu.onAction
radial_menu.RadialMenu.onAction = new_onAction


class Analytics(PYmodsCore.Analytics):
    def __init__(self):
        super(Analytics, self).__init__()
        self.mod_description = 'RadialMenu'
        self.mod_id_analytics = 'UA-76792179-10'
        self.mod_version = '2.0.0'


statistic_mod = Analytics()


def fini():
    try:
        if _config.data['analyticsFull']:
            statistic_mod.end()
    except StandardError:
        traceback.print_exc()


def new_LW_populate(self):
    old_LW_populate(self)
    try:
        if _config.data['analyticsFull']:
            statistic_mod.start()
    except StandardError:
        traceback.print_exc()


old_LW_populate = LobbyView._populate
LobbyView._populate = new_LW_populate
