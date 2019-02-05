# -*- coding: utf-8 -*-
import PYmodsCore
import ResMgr
import SoundGroups
import glob
import items.vehicles
import nations
import os
import traceback
from Avatar import PlayerAvatar
from ReloadEffect import _BarrelReloadDesc
from debug_utils import LOG_ERROR
from helpers.EffectsList import _SoundEffectDesc, _TracerSoundEffectDesc
from items.components import sound_components
from items.vehicles import g_cache
from material_kinds import EFFECT_MATERIALS


class ConfigInterface(PYmodsCore.PYmodsConfigInterface):
    def __init__(self):
        self.confList = set()
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.1 (%(file_compile_date)s)'
        self.data = {'engines': {}, 'gun_reload_effects': {}, 'shot_effects': {}, 'sound_notifications': {}, 'guns': {}}
        super(ConfigInterface, self).init()

    def loadLang(self):
        pass

    def updateMod(self):
        pass

    def createTemplate(self):
        pass

    def registerSettings(self):
        pass

    def readCurrentSettings(self, quiet=True):
        configPath = self.configPath + 'configs/'
        if not os.path.exists(configPath):
            LOG_ERROR('config folder not found: ' + configPath)
            os.makedirs(configPath)
        for confPath in glob.iglob(configPath + '*.json'):
            confName = os.path.basename(confPath).split('.')[0]
            try:
                confdict = PYmodsCore.loadJson(self.ID, confName, {}, os.path.dirname(confPath) + '/')
            except StandardError:
                print self.ID + ': config', os.path.basename(confPath), 'is invalid.'
                traceback.print_exc()
                continue
            self.confList.add(confName)
            for itemType, itemsDict in confdict.iteritems():
                if itemType not in self.data:
                    if not quiet:
                        print self.ID + ': invalid item type in', confName + ':', itemType
                    continue
                itemsData = self.data[itemType]
                if itemType in ('engines', 'guns'):
                    for nationName, nationData in itemsDict.iteritems():
                        if nationName.split(':')[0] not in nations.NAMES:
                            print self.ID + ': unknown nation in', itemType, 'data:', nationName
                            continue
                        itemsData.setdefault(nationName, {}).update(nationData)
                if itemType in ('gun_reload_effects', 'shot_effects', 'sound_notifications'):
                    for itemName in itemsDict:
                        itemsData.setdefault(itemName, {}).update(itemsDict[itemName])
        print self.ID + ': loaded configs:', ', '.join(x + '.json' for x in sorted(self.confList))
        newXmlPath = '../' + self.configPath + 'configs/gun_effects.xml'
        if ResMgr.isFile(newXmlPath):
            g_cache._gunEffects.update(items.vehicles._readEffectGroups(newXmlPath))
        elif self.data['guns']:
            print self.ID + ': gun effects config not found'
        for item_type, items_storage in (('engines', g_cache._Cache__engines), ('guns', g_cache._Cache__guns)):
            for nationID, nation_items in enumerate(items_storage):
                nationData = self.data[item_type].get(nations.NAMES[nationID])
                if not nationData:
                    continue
                for item in nation_items.itervalues():
                    itemData = nationData.get(item.name)
                    if not itemData:
                        continue
                    if item_type == 'engines':
                        s = item.sounds.getEvents()
                        item.sounds = sound_components.WWTripleSoundConfig(
                            '', itemData.get('wwsoundPC', s[0]), itemData.get('wwsoundNPC', s[1]))
                    elif item_type == 'guns' and 'effects' in itemData:
                        item.effects = items.vehicles.g_cache._gunEffects.get(itemData['effects'], item.effects)
        for sname, descr in g_cache._gunReloadEffects.iteritems():
            effData = self.data['gun_reload_effects'].get(sname)
            if effData is None:
                continue
            descr.duration = float(effData.get('duration', descr.duration * 1000.0)) / 1000.0
            descr.soundEvent = effData.get('sound', descr.soundEvent)
            if effData['type'] == 'BarrelReload' and isinstance(descr, _BarrelReloadDesc):
                descr.lastShellAlert = effData.get('lastShellAlert', descr.lastShellAlert)
                descr.shellDuration = effData.get('shellDuration', descr.shellDuration * 1000.0) / 1000.0
                descr.startLong = effData.get('startLong', descr.startLong)
                descr.startLoop = effData.get('startLoop', descr.startLoop)
                descr.stopLoop = effData.get('stopLoop', descr.stopLoop)
                descr.loopShell = effData.get('loopShell', descr.loopShell)
                descr.loopShellLast = effData.get('loopShellLast', descr.loopShellLast)
                descr.ammoLow = effData.get('ammoLow', descr.ammoLow)
                descr.caliber = effData.get('caliber', descr.caliber)
                descr.shellDt = effData.get('loopShellDt', descr.shellDt)
                descr.shellDtLast = effData.get('loopShellLastDt', descr.shellDtLast)
        for sname, index in g_cache.shotEffectsIndexes.iteritems():
            effData = self.data['shot_effects'].get(sname)
            if effData is None:
                continue
            res = g_cache.shotEffects[index]
            for effType in (x for x in ('projectile',) if x in effData):
                typeData = effData[effType]
                for effectDesc in res[effType][2]._EffectsList__effectDescList:
                    if isinstance(effectDesc, _TracerSoundEffectDesc):
                        effectDesc._soundName = tuple((typeData.get(key, effectDesc._soundName[idx]),) for idx, key in
                                                      enumerate(('wwsoundPC', 'wwsoundNPC')))
            for effType in (x for x in (tuple(x + 'Hit' for x in EFFECT_MATERIALS) + (
                    'armorBasicRicochet', 'armorRicochet', 'armorResisted', 'armorHit', 'armorCriticalHit')) if x in effData):
                typeData = effData[effType]
                for effectDesc in res[effType].effectsList._EffectsList__effectDescList:
                    if isinstance(effectDesc, _SoundEffectDesc):
                        effectDesc._impactNames = tuple(typeData.get(key, effectDesc._impactNames[idx]) for idx, key in
                                                        enumerate(('impactNPC_PC', 'impactPC_NPC', 'impactNPC_NPC')))
        for vehicleType in g_cache._Cache__vehicles.itervalues():
            self.inject_vehicleType(vehicleType)

    def inject_vehicleType(self, vehicleType):
        for item in vehicleType.engines:
            nationID, itemID = item.id
            itemData = self.data['engines'].get(nations.NAMES[nationID], {}).get(item.name)
            if itemData:
                s = item.sounds.getEvents()
                item.sounds = sound_components.WWTripleSoundConfig(
                    '', itemData.get('wwsoundPC', s[0]), itemData.get('wwsoundNPC', s[1]))
        for turrets in vehicleType.turrets:
            for turret in turrets:
                for item in turret.guns:
                    nationID, itemID = item.id
                    if vehicleType.name in self.data['guns']:
                        itemData = self.data['guns'].get(vehicleType.name, {}).get(item.name)
                    else:
                        itemData = self.data['guns'].get(nations.NAMES[nationID], {}).get(item.name)
                    if itemData and 'effects' in itemData:
                        item.effects = items.vehicles.g_cache._gunEffects.get(itemData['effects'], item.effects)


@PYmodsCore.overrideMethod(items.vehicles.VehicleType, '__init__')
def new_vehicleType_init(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    _config.inject_vehicleType(self)


@PYmodsCore.overrideMethod(PlayerAvatar, '_PlayerAvatar__initGUI')
def new_initGUI(base, self):
    result = base(self)
    events = self.soundNotifications._IngameSoundNotifications__events
    notificationsData = _config.data['sound_notifications']
    for eventName, event in events.iteritems():
        if eventName in notificationsData:
            for category in event:
                event[category]['sound'] = notificationsData[eventName].get(category, event[category]['sound'])

    self.soundNotifications._IngameSoundNotifications__events = events
    return result


@PYmodsCore.overrideMethod(PlayerAvatar, 'updateVehicleGunReloadTime')
def updateVehicleGunReloadTime(base, self, vehicleID, timeLeft, baseTime):
    if ((self._PlayerAvatar__prevGunReloadTimeLeft != timeLeft and timeLeft == 0.0) and not
            self.guiSessionProvider.shared.vehicleState.isInPostmortem):
        try:
            if 'fx' in _config.data['sound_notifications'].get('gun_reloaded', {}):
                SoundGroups.g_instance.playSound2D(_config.data['sound_notifications']['gun_reloaded']['fx'])
        except StandardError:
            traceback.print_exc()
    base(self, vehicleID, timeLeft, baseTime)


_config = ConfigInterface()
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version, 'UA-76792179-13', _config.confList)
