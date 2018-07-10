# -*- coding: utf-8 -*-
import BigWorld
import PYmodsCore
import traceback
from Avatar import PlayerAvatar
from Vehicle import Vehicle
from constants import ARENA_GUI_TYPE
from gui.Scaleform.daapi.view.battle.shared.minimap.plugins import ArenaVehiclesPlugin
from gui.battle_control.arena_info import vos_collections
from helpers import dependency
from skeletons.gui.battle_session import IBattleSessionProvider


class PlayersPanelController(PYmodsCore.PYmodsConfigInterface):
    vCache = property(lambda self: self.__vCache)

    sessionProvider = dependency.descriptor(IBattleSessionProvider)

    def __init__(self):
        self.__hpCache = dict()
        self.__vCache = set()
        self.uiFlash = None
        super(PlayersPanelController, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.1.2 (%(file_compile_date)s)'
        self.author = 'by PolarFox (forked %s)' % self.author
        self.data = {'textFields': {}}
        vxEvents.onStateChanged += self.__onStateChanged
        super(PlayersPanelController, self).init()

    def loadLang(self):
        pass

    def updateMod(self):
        pass

    def createTemplate(self):
        pass

    def registerSettings(self):
        pass

    def readCurrentSettings(self, quiet=True):
        self.data['textFields'].update(self.loadJsonData().get('textFields', {}))

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
        playerTeam = player.team
        team = player.arena.vehicles[vehicleID]['team']
        panelSide = 'left' if playerTeam == team else 'right'
        currentHP = self.__hpCache[vehicleID]['current']
        maxHP = self.__hpCache[vehicleID]['max']
        for fieldName, fieldData in sorted(self.data['textFields'].iteritems()):
            barWidth = currentHP
            if panelSide + 'Width' in fieldData:
                barWidth = fieldData[panelSide + 'Width'] * (float(currentHP) / maxHP)
            self.uiFlash.as_setPPTextS(self.ID + fieldName, [vehicleID, (fieldData[panelSide + 'Text'] % {
                'curHealth': currentHP,
                'maxHealth': maxHP,
                'barWidth': barWidth
            }) if not fieldData.get('hideIfDead', False) or barWidth else ''])

    def onEndBattle(self):
        BigWorld.player().arena.onVehicleKilled -= self.onVehicleKilled
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
            self.__hpCache[vehicleID]['current'] = health if vehicleID in self.__vCache else self.__hpCache[vehicleID][
                'max']
        if self.uiFlash:
            self.setHPField(vehicleID)

    def validateCache(self, vehicleID):
        if vehicleID not in self.__vCache:
            self.__vCache.add(vehicleID)

    def __onStateChanged(self, eventType, parentUI, componentUI):
        if parentUI != FLASH.COMPONENT_CORE_UI:
            return
        if eventType == BATTLE_FLASH_EVENT_ID.COMPONENT_READY:
            self.uiFlash = componentUI
            self.__setSettings()
            self.onStartBattle()
        if eventType == BATTLE_FLASH_EVENT_ID.COMPONENT_DISPOSE:
            self.uiFlash = None

    def __setSettings(self):
        for fieldName, fieldData in self.data['textFields'].iteritems():
            self.uiFlash.as_setPPConfigS(self.ID + fieldName, fieldData)


mod_playersHP = None
try:
    from gui.vxBattleFlash import vxBattleFlash, vxBattleFlashAliases
    from gui.vxBattleFlash.events import vxEvents, BATTLE_FLASH_EVENT_ID
    from gui.vxBattleFlash.constants import FLASH
    mod_playersHP = PlayersPanelController()
    statistic_mod = PYmodsCore.Analytics(mod_playersHP.ID, mod_playersHP.version, 'UA-76792179-11')
except ImportError:
    print '%(mod_ID)s: Battle Flash API (vxBattleFlash) not found. Text viewing disabled.'
except StandardError:
    traceback.print_exc()
else:
    @PYmodsCore.overrideMethod(ArenaVehiclesPlugin, '_ArenaVehiclesPlugin__setInAoI')
    def new_setInAoI(base, self, entry, isInAoI):
        result = base(self, entry, isInAoI)
        try:
            for vehicleID, entry2 in self._entries.iteritems():
                if entry == entry2 and isInAoI:
                    if vehicleID in mod_playersHP.vCache:
                        break
                    mod_playersHP.updateHealth(vehicleID)
        except StandardError:
            traceback.print_exc()
        finally:
            return result


    @PYmodsCore.overrideMethod(PlayerAvatar, 'vehicle_onEnterWorld')
    def new_vehicle_onEnterWorld(base, self, vehicle):
        result = base(self, vehicle)
        try:
            vehicleID = vehicle.id
            mod_playersHP.validateCache(vehicleID)
            mod_playersHP.updateHealth(vehicleID)
        except StandardError:
            traceback.print_exc()
        finally:
            return result


    @PYmodsCore.overrideMethod(Vehicle, 'onHealthChanged')
    def new_vehicle_onHealthChanged(base, self, newHealth, attackerID, attackReasonID):
        result = base(self, newHealth, attackerID, attackReasonID)
        try:
            mod_playersHP.updateHealth(self.id, newHealth)
        except StandardError:
            traceback.print_exc()
        finally:
            return result
