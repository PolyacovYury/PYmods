# -*- coding: utf-8 -*-
import BigWorld
import Keys
import traceback
from Avatar import PlayerAvatar
from PYmodsCore import PYmodsConfigInterface, Analytics, overrideMethod, checkKeys
from Vehicle import Vehicle
from constants import ARENA_GUI_TYPE
from gui.Scaleform.daapi.view.battle.shared.minimap.plugins import ArenaVehiclesPlugin
from gui.battle_control.arena_info import vos_collections
from helpers import dependency
from skeletons.gui.battle_session import IBattleSessionProvider


class PlayersPanelController(PYmodsConfigInterface):
    vCache = property(lambda self: self.__vCache)

    sessionProvider = dependency.descriptor(IBattleSessionProvider)

    def __init__(self):
        self.__hpCache = dict()
        self.__vCache = set()
        self.displayed = True
        super(PlayersPanelController, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.2.1 (%(file_compile_date)s)'
        self.author = 'by PolarFox (forked %s)' % self.author
        self.defaultKeys = {'toggle_key': [[Keys.KEY_LALT, Keys.KEY_RALT]]}
        self.data = {'enabled': True, 'textFields': {}, 'mode': 0, 'toggle_key': self.defaultKeys['toggle_key']}
        self.i18n = {
            'UI_description': 'PlayersPanelHP',
            'UI_setting_mode_text': 'Displaying mode',
            'UI_setting_mode_tooltip': (
                ' • <b>Always</b> - HP markers will always be displayed.\n'
                ' • <b>Toggle</b> - HP markers will be toggled on/off upon toggle key press.\n'
                ' • <b>Holding</b> - HP markers will only be displayed <b>while</b> the toggle key is pressed.'),
            'UI_setting_mode_always': 'Always',
            'UI_setting_mode_toggle': 'Toggle',
            'UI_setting_mode_holding': 'Holding',
            'UI_setting_toggle_key_text': 'Toggle hotkey',
            'UI_setting_toggle_key_tooltip': 'Pressing this button in-battle toggles HP markers displaying.'}
        g_PlayersPanelAPI.events.onUIReady += self.onStartBattle
        super(PlayersPanelController, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createOptions('mode',
                                                  [self.i18n['UI_setting_mode_' + x] for x in
                                                   ('always', 'toggle', 'holding')])],
                'column2': [self.tb.createHotKey('toggle_key')]}

    def readCurrentSettings(self, quiet=True):
        for fieldName in self.data['textFields']:
            g_PlayersPanelAPI.delete(self.ID + fieldName)
        super(PlayersPanelController, self).readCurrentSettings(quiet)
        self.data['textFields'].update(self.loadDataJson().get('textFields', {}))
        self.displayed = not self.data['mode']
        for fieldName, fieldData in self.data['textFields'].iteritems():
            g_PlayersPanelAPI.create(self.ID + fieldName, fieldData)

    def onApplySettings(self, settings):
        super(PlayersPanelController, self).onApplySettings(settings)
        self.displayed = not settings['mode']

    @staticmethod
    def getVehicleHealth(vehicleID):
        if hasattr(BigWorld.entity(vehicleID), 'health'):
            vehicle = BigWorld.entity(vehicleID)
            return vehicle.health if vehicle.isCrewActive and vehicle.health >= 0 else 0
        else:
            vehicle = BigWorld.player().arena.vehicles.get(vehicleID)
            if vehicle is not None and vehicle['vehicleType'] is not None:
                return vehicle['vehicleType'].maxHealth
            return ''

    def onStartBattle(self):
        BigWorld.player().arena.onVehicleKilled += self.onVehicleKilled
        collection = vos_collections.VehiclesInfoCollection().iterator(self.sessionProvider.getArenaDP())
        for vInfoVO in collection:
            vehicleID = vInfoVO.vehicleID
            self.__hpCache[vehicleID] = {'current': self.getVehicleHealth(vehicleID), 'max': vInfoVO.vehicleType.maxHealth}
            self.setHPField(vehicleID)

    def setHPField(self, vehicleID):
        player = BigWorld.player()
        if player.arena.guiType in (ARENA_GUI_TYPE.EPIC_RANDOM, ARENA_GUI_TYPE.EPIC_RANDOM_TRAINING):
            return
        team = player.arena.vehicles[vehicleID]['team']
        panelSide = 'left' if player.team == team else 'right'
        currentHP = self.__hpCache[vehicleID]['current']
        maxHP = self.__hpCache[vehicleID]['max']
        for fieldName, fieldData in sorted(self.data['textFields'].iteritems()):
            barWidth = currentHP
            if 'width' in fieldData[panelSide]:
                barWidth = fieldData[panelSide]['width'] * (float(currentHP) / maxHP)
            g_PlayersPanelAPI.update(self.ID + fieldName, {'vehicleID': vehicleID, 'text': (
                    fieldData[panelSide]['text'] % {'curHealth': currentHP, 'maxHealth': maxHP, 'barWidth': barWidth}
            ) if self.displayed and (not fieldData.get('hideIfDead', False) or barWidth) else ''})

    def onEndBattle(self):
        BigWorld.player().arena.onVehicleKilled -= self.onVehicleKilled
        self.displayed = not self.data['mode']
        self.__hpCache.clear()
        self.__vCache.clear()

    def onVehicleKilled(self, targetID, *_):
        if targetID in self.__hpCache:
            self.__hpCache[targetID]['current'] = 0
            self.setHPField(targetID)

    def updateHealth(self, vehicleID, newHealth=-1):
        if vehicleID not in self.__hpCache or newHealth == -1:
            vehicle = BigWorld.player().arena.vehicles.get(vehicleID)
            maxHealth = vehicle['vehicleType'].maxHealth if vehicle['vehicleType'] is not None else -1
            self.__hpCache[vehicleID] = {'current': self.getVehicleHealth(vehicleID), 'max': maxHealth}
        else:
            health = newHealth if newHealth > 0 else 0
            self.__hpCache[vehicleID]['current'] = health if vehicleID in self.__vCache else self.__hpCache[vehicleID]['max']
        self.setHPField(vehicleID)

    def validateCache(self, vehicleID):
        if vehicleID not in self.__vCache:
            self.__vCache.add(vehicleID)

    def onHotkeyPressed(self, event):
        if not hasattr(BigWorld.player(), 'arena') or not self.data['enabled'] or not self.data['mode']:
            return
        if self.data['mode'] == 1 and checkKeys(self.data['toggle_key'], event.key) and event.isKeyDown():
            self.displayed = not self.displayed
        elif self.data['mode'] == 2:
            self.displayed = checkKeys(self.data['toggle_key'])
        for vehicleID in self.__hpCache:
            self.setHPField(vehicleID)


g_config = None
try:
    from PlayersPanelAPI import g_PlayersPanelAPI

    g_config = PlayersPanelController()
    statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-11')
except ImportError:
    print '%(mod_ID)s: Battle Flash API not found.'
except StandardError:
    traceback.print_exc()
else:
    @overrideMethod(ArenaVehiclesPlugin, '_setInAoI')
    def new_setInAoI(base, self, entry, isInAoI):
        result = base(self, entry, isInAoI)
        try:
            for vehicleID, entry2 in self._entries.iteritems():
                if entry == entry2 and isInAoI:
                    if vehicleID in g_config.vCache:
                        break
                    g_config.updateHealth(vehicleID)
        except StandardError:
            traceback.print_exc()
        finally:
            return result


    @overrideMethod(PlayerAvatar, 'vehicle_onEnterWorld')
    def new_vehicle_onEnterWorld(base, self, vehicle):
        result = base(self, vehicle)
        try:
            vehicleID = vehicle.id
            g_config.validateCache(vehicleID)
            g_config.updateHealth(vehicleID)
        except StandardError:
            traceback.print_exc()
        finally:
            return result


    @overrideMethod(Vehicle, 'onHealthChanged')
    def new_vehicle_onHealthChanged(base, self, newHealth, attackerID, attackReasonID):
        result = base(self, newHealth, attackerID, attackReasonID)
        try:
            g_config.updateHealth(self.id, newHealth)
        except StandardError:
            traceback.print_exc()
        finally:
            return result
