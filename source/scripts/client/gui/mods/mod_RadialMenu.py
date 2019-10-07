# -*- coding: utf-8 -*-
import BigWorld
import CommandMapping
import Keys
import Math
import glob
import math_utils
import os
import string
import traceback
from PYmodsCore import PYmodsConfigInterface, loadJson, config, checkKeys, pickRandomPart, Analytics, overrideMethod, \
    sendChatMessage, loadJsonOrdered, events
from Vehicle import Vehicle
from collections import OrderedDict
from constants import ARENA_BONUS_TYPE
from functools import partial
from gui import GUI_CTRL_MODE_FLAG
from gui.Scaleform.daapi.view.battle.shared import radial_menu
from gui.Scaleform.daapi.view.battle.shared.radial_menu import SHORTCUT_SETS, SHORTCUT_STATES, getKeyFromAction
from gui.Scaleform.genConsts.BATTLE_ICONS_CONSTS import BATTLE_ICONS_CONSTS
from gui.battle_control import avatar_getter, minimap_utils
from gui.battle_control.controllers.chat_cmd_ctrl import CHAT_COMMANDS
from gui.battle_control.minimap_utils import MINIMAP_DIMENSION
from gui.shared.gui_items.Vehicle import VEHICLE_TYPES_ORDER
from gui.shared.utils.key_mapping import getScaleformKey
from helpers import isPlayerAvatar
from messenger import MessengerEntry


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.configMeta = {}
        self.commands = OrderedDict()
        self.altMenuActive = False
        super(ConfigInterface, self).__init__()

    @property
    def selectedCommands(self):
        return self.commands.values()[self.data['selectedConfig']]

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '2.2.0 (%(file_compile_date)s)'
        self.author += ' (orig by locastan/tehHedger/TRJ_VoRoN)'
        self.defaultKeys = {'mapMenu_key': [Keys.KEY_LALT]}
        self.data = {'enabled': True,
                     'mapMenu_key': self.defaultKeys['mapMenu_key'],
                     'selectedConfig': 12,
                     'chatDelay': 550,
                     'hotDelay': 350}
        self.i18n = {
            'description': 'Radial Menu',
            'UI_setting_info_text': 'Special for ',
            'UI_setting_mapMenu_key_text': 'Alternative menu hotkey',
            'UI_setting_mapMenu_key_tooltip': (
                'When Radial menu is activated while this key is pressed, an alternative map-specific menu is loaded if '
                'the config provides one.'),
            'UI_setting_selectedConfig_text': 'Active config:',
            'UI_setting_selectedConfig_tooltip': 'This config will be used when Radial menu is activated.',
            'UI_setting_selectedConfig_defaultMeta': 'Default messages',
            'battleMessage_commandOnDelay': 'This command is on delay, please wait.'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        infoLabel = self.tb.createLabel('info')
        infoLabel['text'] += 'wotspeak.ru'
        return {'modDisplayName': self.i18n['description'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createOptions('selectedConfig', [self.configMeta[x] for x in self.commands])],
                'column2': [self.tb.createHotKey('mapMenu_key'),
                            infoLabel]}

    def migrateConfigs(self):
        for path in sorted(glob.iglob(self.configPath + 'skins/*.json'), key=string.lower):
            new_config = OrderedDict()
            dir_path, full_name = os.path.split(path)
            name = os.path.splitext(full_name)[0]
            old_config = loadJsonOrdered(self.ID, dir_path, name)
            if not old_config:
                print self.ID + ': error while reading', full_name + '.'
                continue
            for key, data in old_config.iteritems():
                if key.endswith('Menu'):
                    new_key = key[:-4]
                    if new_key not in VEHICLE_TYPES_ORDER:
                        new_key = 'default' if new_key == 'Tank' else key
                    new_config[new_key] = data
                elif key == 'tankSpecific':
                    new_config.update(data)
                else:
                    new_config[key] = data
            loadJson(self.ID, name, new_config, dir_path, True, sort_keys=False)

    def onApplySettings(self, settings):
        super(ConfigInterface, self).onApplySettings(settings)
        self.updateCommandData()

    def readCurrentSettings(self, quiet=True):
        super(ConfigInterface, self).readCurrentSettings(quiet)
        self.updateCommandData()
        self.updateMod()

    def updateCommandData(self):
        self.configMeta = {'default': self.i18n['UI_setting_selectedConfig_defaultMeta']}
        self.commands.clear()
        self.commands['default'] = {'hotkeyOnly': [CustomMenuCommand({'command': 'RELOADINGGUN', 'hotKey': ['KEY_C']})]}
        for path in sorted(glob.iglob(self.configPath + 'skins/*.json'), key=string.lower):
            dir_path, full_name = os.path.split(path)
            name = os.path.splitext(full_name)[0]
            try:
                confDict = loadJson(self.ID, name, {}, dir_path)
            except StandardError:
                print self.ID + ': config', full_name, 'is invalid.'
                traceback.print_exc()
                continue
            self.configMeta[name] = confDict.get('meta', name)
            self.commands[name] = commands = {}
            for key, confSect in confDict.iteritems():
                if key == 'meta':
                    continue
                if isinstance(confSect, basestring):
                    commands[key] = confSect
                elif key == 'hotkeyOnly':
                    commands[key] = [CustomMenuCommand(x) for x in confSect]
                else:
                    commands[key] = {menuType: [CustomMenuCommand(x) if x else x for x in menuConf]
                                     for menuType, menuConf in confSect.iteritems()}
        self.data['selectedConfig'] = min(self.data['selectedConfig'], len(self.commands) - 1)

    def onHotkeyPressed(self, event):
        if not isPlayerAvatar() or not self.data['enabled']:
            return
        isDown = checkKeys(self.data['mapMenu_key'])
        if isDown != self.altMenuActive:
            self.altMenuActive = isDown
            CommandMapping.g_instance.onMappingChanged()
        if not event.isKeyDown():
            return
        target = BigWorld.target()
        player = BigWorld.player()
        state = getCrosshairType(player, target)
        commandsList = self.selectedCommands.get('hotkeyOnly', [])
        menuConf, _ = self.findBestFitConf()
        if menuConf is not None:
            commandsList.extend(menuConf.get(state, []))
        for command in commandsList:
            if command and command.handleKeys(command.hotKeys, event.key):
                command.onCustomAction(target.id if target is not None else None, True)

    def findBestFitConf(self, mapName=None):
        commandConf = self.selectedCommands
        vehicleTypeDescr = BigWorld.player().guiSessionProvider.getArenaDP().getVehicleInfo().vehicleType
        vehicleClass = vehicleTypeDescr.classTag
        vehicleName = vehicleTypeDescr.iconName
        if '-' in vehicleName:
            vehicleName = vehicleName.split('-', 1)[1]
        menuConf, menuType = None, ''
        if mapName is not None and self.altMenuActive:
            menuType = 'Map_' + mapName
            menuConf = commandConf.get(menuType)
            if menuConf is None:
                menuType = 'Map_default'
                menuConf = commandConf.get(menuType)
        if menuConf is None:
            menuType = vehicleName
            menuConf = commandConf.get(menuType)
            if menuConf is not None:
                if isinstance(menuConf, str):
                    menuConf = commandConf.get(menuConf)
                    menuType = menuConf
        if menuConf is None and vehicleClass is not None:
            menuType = vehicleClass
            menuConf = commandConf.get(menuType)
        if menuConf is None:
            menuType = 'default'
            menuConf = commandConf.get(menuType)
        return menuConf, menuType


class CellHelper(object):
    PING_SELF = 100
    PING_MAX = PING_CAMERA = 101
    PING_MIN = 0

    @staticmethod
    def getCellIdFromName(name):
        if name == '{ownPos}':
            return CellHelper.PING_SELF
        if name == '{viewPos}':
            return CellHelper.PING_CAMERA
        try:
            row = string.ascii_uppercase.index(name[0])
            if row > 8:
                row -= 1
            column = (int(name[1]) - 1) % MINIMAP_DIMENSION
            return column * MINIMAP_DIMENSION + row
        except StandardError:
            return -1

    @staticmethod
    def getPosCellId(view):
        player = BigWorld.player()
        if view:
            point = player.inputHandler.ctrl.getDesiredShotPoint()
        else:
            point = BigWorld.entity(player.playerVehicleID).position
        if point is None:
            return -1
        box = BigWorld.player().arena.arenaType.boundingBox
        p = math_utils.clampVector3(Math.Vector3(box[0][0], 0, box[0][1]), Math.Vector3(box[1][0], 0, box[1][1]), point)
        return int(minimap_utils.getCellIdxFromPosition(p, box))


class SafeFormatter(string.Formatter):
    def get_value(self, key, args, kwargs):
        try:
            return super(SafeFormatter, self).get_value(key, args, kwargs)
        except KeyError:
            return '{%s}' % key


class CommandQueue(object):
    def __init__(self):
        self.__queue = []
        self.__callbackID = None
        events.PlayerAvatar.destroyGUI.before(self.cancel)

    def addToQueue(self, delay, callback, *a, **kw):
        self.__queue.append((delay, partial(callback, *a, **kw)))
        if self.__callbackID is None:
            self.__callbackID = BigWorld.callback(self.__queue[0][0], self.onQueueCalled)

    def onQueueCalled(self):
        _, callback = self.__queue.pop(0)
        try:
            callback()
        except StandardError:
            traceback.print_exc()
        self.__callbackID = None
        if self.__queue:
            self.__callbackID = BigWorld.callback(self.__queue[0][0], self.onQueueCalled)

    def cancel(self):
        if self.__callbackID is not None:
            BigWorld.cancelCallback(self.__callbackID)
            self.__callbackID = None
        self.__queue[:] = []


class CustomMenuCommand(object):
    PING_DELAY = 1.0
    DEFAULT_COOLDOWN = 1.1
    ALL_ICONS = tuple(v for k, v in BATTLE_ICONS_CONSTS.__dict__.iteritems() if not k.startswith('__'))
    ALL_COMMANDS = tuple(v for k, v in CHAT_COMMANDS.__dict__.iteritems() if not k.startswith('__'))
    ALL_CHANNELS = ('Team', 'All', 'Squad')

    def __init__(self, confDict):
        self.lastRandId = -1
        self.nextUseStamp = 0
        self.randomChoice = not confDict.get('sequentChoice')
        self.text = confDict.get('text', '')
        self.title = confDict.get('title', 'NO CONFIG')
        self.inPostmortem = confDict.get('inPostmortem', False)
        self.command = confDict.get('command', '').strip()
        if self.command and self.command not in self.ALL_COMMANDS:
            print 'RadialMenu: unsupported command: %s' % self.command
            self.command = ''
        chatMode = confDict.get('chatMode', 'Team')
        self.chatMode = chatMode if chatMode in self.ALL_CHANNELS else 'Team'
        icon = confDict.get('icon', 'Stop')
        self.icon = icon if icon in self.ALL_ICONS else 'Stop'
        self.cooldownDelay = confDict.get('cooldown', self.DEFAULT_COOLDOWN)
        self.pingList = [x for x in [CellHelper.getCellIdFromName(x) for x in confDict.get('ping', '').split(' ')]
                         if CellHelper.PING_MIN <= x <= CellHelper.PING_MAX]
        self.variantList = confDict.get('variants', [])

        config.utils.processHotKeys(confDict, ('hotkey',), 'read')
        self.hotKeys = confDict.get('hotkey', [])

    def handleKeys(self, keys, key):
        return not (len(self.hotKeys) == 1 and BigWorld.player().getForcedGuiControlModeFlags()) and checkKeys(keys, key)

    def pingCellId(self, cellId):
        player = BigWorld.player()
        backup_FGCM = player.getForcedGuiControlModeFlags()
        player.setForcedGuiControlMode(GUI_CTRL_MODE_FLAG.CURSOR_ATTACHED)
        player.guiSessionProvider.shared.chatCommands.sendAttentionToCell(cellId)
        player.setForcedGuiControlMode(backup_FGCM)

    def checkCooldown(self):
        return self.nextUseStamp < BigWorld.time()

    def updateCooldown(self):
        self.nextUseStamp = BigWorld.time() + self.cooldownDelay

    def format(self, argDict):
        try:
            sessionProvider = BigWorld.player().guiSessionProvider
            argDict.update({'randPart': '',
                            'viewPos': minimap_utils.getCellName(CellHelper.getPosCellId(True)),
                            'ownPos': minimap_utils.getCellName(CellHelper.getPosCellId(False)),
                            'reload': '%.3g' % sessionProvider.shared.ammo.getGunReloadingState().getTimeLeft(),
                            'ammo': sessionProvider.shared.ammo.getCurrentShells()[1],
                            'ownVehicle': sessionProvider.getArenaDP().getVehicleInfo().vehicleType.shortName})
            argDict['randPart'], self.lastRandId = pickRandomPart(self.variantList, self.lastRandId, self.randomChoice)
            argDict['randPart'] = safeFmt.vformat(argDict['randPart'], (), argDict)
            return safeFmt.vformat(self.text, (), argDict)
        except StandardError:
            traceback.print_exc()
            return ''

    def onCustomAction(self, targetID, fromHotKey=False):
        if not self.checkCooldown():
            MessengerEntry.g_instance.gui.addClientMessage(g_config.i18n['battleMessage_commandOnDelay'], True)
            return
        if not (self.inPostmortem or avatar_getter.isVehicleAlive()):
            return
        player = BigWorld.player()
        target = BigWorld.entity(targetID) if targetID is not None else None
        if target is None:
            target = BigWorld.entity(player.playerVehicleID)
        chanId = 2
        if self.chatMode == 'All' and player.arena.bonusType == ARENA_BONUS_TYPE.TRAINING:
            chanId = 0
        elif self.chatMode in ('Team', 'All'):
            chanId = 1
        targetInfo = player.arena.vehicles.get(target.id, {})
        targetInf = {'name': target.publicInfo.name,
                     'vehicle': targetInfo['vehicleType'].type.shortUserString,
                     'clan': targetInfo['clanAbbrev']}
        delay = g_config.data['hotDelay'] / 1000.0 if fromHotKey else 0.0
        if self.command:
            chatCommands = player.guiSessionProvider.shared.chatCommands
            if chatCommands is not None:
                g_queue.addToQueue(0, chatCommands.handleChatCommand, self.command, target.id)
                delay += g_config.data['chatDelay'] / 1000.0
        g_queue.addToQueue(delay, sendChatMessage, self.format(targetInf).decode('utf-8'), chanId, g_config.data['chatDelay'])
        for cellId in self.pingList:
            if cellId == CellHelper.PING_SELF:
                cellId = CellHelper.getPosCellId(False)
            elif cellId == CellHelper.PING_CAMERA:
                cellId = CellHelper.getPosCellId(True)
            g_queue.addToQueue(self.PING_DELAY, self.pingCellId, cellId)
        self.updateCooldown()


g_queue = CommandQueue()
safeFmt = SafeFormatter()
g_config = ConfigInterface()
statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-10',
                          [g_config.commands.keys()[g_config.data['selectedConfig']]])


def getCrosshairType(player, target):
    if not isTargetCorrect(player, target):
        return SHORTCUT_STATES.DEFAULT
    elif target.publicInfo.team == player.team:
        return SHORTCUT_STATES.ALLY
    else:
        return SHORTCUT_STATES.ENEMY


def isTargetCorrect(player, target):
    return (target is not None and isinstance(target, Vehicle) and target.isAlive() and player is not None
            and isPlayerAvatar() and not player.guiSessionProvider.getArenaDP().getVehicleInfo(target.id).isActionsDisabled())


@overrideMethod(radial_menu.RadialMenu, '_RadialMenu__updateMenu')
def new_updateMenu(base, self):
    data = []
    mapName = BigWorld.player().arena.arenaType.geometryName
    menuConf, menuType = g_config.findBestFitConf(mapName)
    if menuConf is None:
        return base(self)
    for state in SHORTCUT_STATES.ALL:
        stateData = [{'title': x.title, 'action': x.action, 'icon': x.icon, 'key': getKeyFromAction(x.action, state)}
                     for x in SHORTCUT_SETS[state]]
        state = state.replace('_spg', '')
        if state not in menuConf:
            continue
        for idx in xrange(min(len(menuConf[state]), len(stateData))):
            command = menuConf[state][idx]
            if not command:
                continue
            hotkey = 0
            keys = command.hotKeys
            if keys:
                hotKeys = [x for x in keys if not isinstance(x, list)]
                if not hotKeys:
                    hotKeys = keys[0]
                hotkey = hotKeys[0] if len(hotKeys) == 1 else 0
            stateData[idx] = {'title': command.title, 'icon': command.icon, 'key': getScaleformKey(hotkey),
                              'action': '.'.join((menuType, state, '%s' % idx))}
        data.append({'state': state, 'data': stateData})
    self.as_buildDataS(data)


@overrideMethod(radial_menu.RadialMenu, 'onAction')
def new_onAction(base, self, action):
    if '.' not in action:
        return base(self, action)
    menuType, state, idx = action.split('.')
    g_config.selectedCommands[menuType][state][int(idx)].onCustomAction(self._RadialMenu__targetID)
