# -*- coding: utf-8 -*-
import traceback

import BigWorld
import PYmodsCore
from Avatar import PlayerAvatar
from Vehicle import Vehicle
from gui.Scaleform.daapi.view.battle.shared.minimap.plugins import ArenaVehiclesPlugin
from gui.battle_control.arena_info import vos_collections
from helpers import dependency
from skeletons.gui.battle_session import IBattleSessionProvider


class PlayersPanelController(object):
    vCache = property(lambda self: self.__vCache)

    sessionProvider = dependency.descriptor(IBattleSessionProvider)

    def __init__(self, container):
        self.container = container
        self.version = '1.0 (%(file_compile_date)s)'
        self.__hpCache = dict()
        self.__vCache = set()
        self.__component = None
        vxBattleFlash.register(self.container)
        vxBattleFlash.onStateChanged += self.__onStateChanged
        print '%s v.%s by PolarFox (forked by Polyacov_Yury): initialised.' % (self.container, self.version)

    @staticmethod
    def getVehicleHealth(vehicleID):
        if hasattr(BigWorld.entity(vehicleID), 'health'):
            vehicle = BigWorld.entity(vehicleID)
            return vehicle.health if vehicle.isCrewActive else ''
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
        playerTeam = BigWorld.player().team
        team = BigWorld.player().arena.vehicles[vehicleID]['team']
        self.__component.as_setPPTextS(self.container + 'text', [
            vehicleID, "<font face='$FieldFont' color='#FFFFFF' size='11'>%s/%s</font>" % (
                self.__hpCache[vehicleID]['current'], self.__hpCache[vehicleID]['max'])])
        self.__component.as_setPPTextS(self.container + 'img', [
            vehicleID, "<img src='img://icons/hp_alive_%s.png' width='%d' height='14'>" % (
                'l' if playerTeam == team else 'r',
                72 * (float(self.__hpCache[vehicleID]['current']) / self.__hpCache[vehicleID]['max']))
            if float(self.__hpCache[vehicleID]['current']) else ''])
        self.__component.as_setPPTextS(self.container + 'bg', [
            vehicleID, "<img src='img://icons/hp_bg.png' width='70' height='12'>"])

    def onEndBattle(self):
        BigWorld.player().arena.onVehicleKilled -= self.onVehicleKilled
        self.__hpCache.clear()
        self.__vCache.clear()

    def onVehicleKilled(self, targetID, attackerID, equipmentID, reason):
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
        if self.__component:
            self.setHPField(vehicleID)

    def validateCache(self, vehicleID):
        if vehicleID not in self.__vCache:
            self.__vCache.add(vehicleID)

    def __onStateChanged(self, eventType, compID, compUI):
        if compID != self.container:
            return
        if eventType == vxBattleFlashEvents.COMPONENT_READY:
            self.__component = compUI
            self.__setSettings()
            self.onStartBattle()
        if eventType == vxBattleFlashEvents.COMPONENT_DISPOSE:
            self.onEndBattle()
            self.__component = None

    def __setSettings(self):
        self.__component.as_setPPConfigS(self.container + 'text', {'leftX': 106, 'leftY': 3, 'rightX': -110, 'rightY': 3,
                                                                   'align': 'center'})
        self.__component.as_setPPConfigS(self.container + 'img', {'leftX': 70, 'leftY': 3, 'rightX': -146, 'rightY': 3,
                                                                  'align': 'left'})
        self.__component.as_setPPConfigS(self.container + 'bg', {'leftX': 71, 'leftY': 4, 'rightX': -145, 'rightY': 4,
                                                                 'align': 'left'})


def new_ArenaVehiclesPlugin__setInAoI(self, entry, isInAoI):
    result = old_ArenaVehiclesPlugin__setInAoI(self, entry, isInAoI)
    try:
        for vehicleID, entry2 in self._entries.iteritems():
            if entry == entry2 and isInAoI:
                if vehicleID in mod_playersHP.vCache:
                    break
                mod_playersHP.updateHealth(vehicleID)
    finally:
        return result


def new_vehicle_onEnterWorld(self, vehicle):
    result = old_vehicle_onEnterWorld(self, vehicle)
    try:
        vehicleID = vehicle.id
        mod_playersHP.validateCache(vehicleID)
        mod_playersHP.updateHealth(vehicleID)
    finally:
        return result


def new_vehicle_onHealthChanged(self, newHealth, attackerID, attackReasonID):
    result = old_vehicle_onHealthChanged(self, newHealth, attackerID, attackReasonID)
    try:
        mod_playersHP.updateHealth(self.id, newHealth)
    finally:
        return result


try:
    from gui.mods.vxBattleFlash import *

    mod_playersHP = PlayersPanelController('%(mod_ID)s')

except ImportError:
    vxBattleFlash = None
    vxBattleFlashEvents = None
    vxBattleFlashAliases = None
    mod_playersHP = None
    print '%(mod_ID)s: Battle Flash API (vxBattleFlash) not found. Text viewing disabled.'
except StandardError:
    vxBattleFlash = None
    vxBattleFlashEvents = None
    vxBattleFlashAliases = None
    mod_playersHP = None
    traceback.print_exc()
else:
    old_vehicle_onHealthChanged = Vehicle.onHealthChanged
    Vehicle.onHealthChanged = new_vehicle_onHealthChanged
    old_ArenaVehiclesPlugin__setInAoI = ArenaVehiclesPlugin._ArenaVehiclesPlugin__setInAoI
    ArenaVehiclesPlugin._ArenaVehiclesPlugin__setInAoI = new_ArenaVehiclesPlugin__setInAoI
    old_vehicle_onEnterWorld = PlayerAvatar.vehicle_onEnterWorld
    PlayerAvatar.vehicle_onEnterWorld = new_vehicle_onEnterWorld
    statistic_mod = PYmodsCore.Analytics(mod_playersHP.container, mod_playersHP.version.split(' ', 1)[0], 'UA-76792179-11')
