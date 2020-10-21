# -*- coding: utf-8 -*-
import ResMgr
import SoundGroups
import glob
import nations
import os
import traceback
from Avatar import PlayerAvatar
from PYmodsCore import PYmodsConfigInterface, loadJson, overrideMethod, Analytics
from ReloadEffect import ReloadEffectsType, _SimpleReloadDesc, _BarrelReloadDesc, _AutoReloadDesc, _DualGunReloadDesc
from debug_utils import LOG_ERROR
from helpers.EffectsList import _SoundEffectDesc, _TracerSoundEffectDesc, ImpactNames, KeyPoint
from items.components.sound_components import WWTripleSoundConfig as SoundConfig
from items.vehicles import g_cache, VehicleType, __readEffectsTimeLine as readEffectsTimeLine, _VEHICLE_TYPE_XML_PATH
from material_kinds import EFFECT_MATERIALS

reloadTypes = {ReloadEffectsType.SIMPLE_RELOAD: _SimpleReloadDesc, ReloadEffectsType.BARREL_RELOAD: _BarrelReloadDesc,
               ReloadEffectsType.AUTO_RELOAD: _AutoReloadDesc, ReloadEffectsType.DUALGUN_RELOAD: _DualGunReloadDesc}
mismatchSlots = {'soundEvent': 'sound', 'shellDt': 'loopShellDt', 'shellDtLast': 'loopShellLastDt',
                 'clipShellLoadT': 'clipShellLoadDuration', 'almostCompleteT': 'almostCompleteDuration'}
modifiers = {'duration': (lambda x: x * 1000.0), 'shellDuration': (lambda x: x * 1000.0),
             'clipShellLoadT': (lambda x: x * 1000.0), 'almostCompleteT': (lambda x: x * 1000.0)}


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.confList = set()
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.3.0 (%(file_compile_date)s)'
        self.data = {'engines': {}, 'guns': {}, 'gun_effects': {}, 'gun_reload_effects': {}, 'shot_effects': {},
                     'sound_notifications': {}}
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
        effectsXmlPath = _VEHICLE_TYPE_XML_PATH + 'common/gun_effects.xml'
        effectsXml = ResMgr.openSection(effectsXmlPath)
        for confPath in glob.iglob(configPath + '*.json'):
            confName = os.path.basename(confPath).split('.')[0]
            try:
                confdict = loadJson(self.ID, confName, {}, os.path.dirname(confPath) + '/')
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
                            print self.ID + ': unknown nation in', itemType, 'in', confName + ':', nationName
                            continue
                        for itemName in nationData:
                            itemsData.setdefault(nationName, {}).setdefault(itemName, {}).update(nationData[itemName])
                if itemType in ('gun_reload_effects', 'shot_effects', 'sound_notifications'):
                    for itemName in itemsDict:
                        itemsData.setdefault(itemName, {}).update(itemsDict[itemName])
                if itemType == 'gun_effects':
                    for itemName, itemData in itemsDict.iteritems():
                        if 'origin' not in itemData:
                            print self.ID + ':', confName + ':', itemName, 'has no origin'
                            continue
                        origin = itemData['origin']
                        if origin not in effectsXml.keys():
                            print self.ID + ':', confName + ':', itemName, 'has unknown origin:', origin
                            continue
                        itemName = intern(itemName)
                        for key in itemData.keys():
                            if key not in ('origin', 'timeline', 'effects'):
                                print self.ID + ':', confName + ': incorrect key', key, 'in', itemName, 'ignored'
                                itemData.pop(key, None)
                        if 'effects' in itemData:
                            for key in itemData['effects'].keys():
                                if key != 'shotSound':
                                    print self.ID + ':', confName + ': only shotSound effects are supported,', key, 'ignored'
                                    itemData['effects'].pop(key)
                        itemsData.setdefault(itemName, {}).update(itemData)
        print self.ID + ': loaded configs:', ', '.join(x + '.json' for x in sorted(self.confList))
        for sname, effData in self.data['gun_effects'].iteritems():
            if sname not in g_cache._gunEffects:
                g_cache._gunEffects[sname] = readEffectsTimeLine(
                    ((None, effectsXmlPath), effData['origin']), effectsXml[effData['origin']])
            effectDesc = g_cache._gunEffects[sname]
            if 'timeline' in effData:
                for keyPointName, timePoint in effData['timeline'].iteritems():
                    for keyPoint in effectDesc.keyPoints:
                        if keyPoint.name == keyPointName:
                            effectDesc.keyPoints.remove(keyPoint)
                            effectDesc.keyPoints.append(keyPoint._replace(time=float(timePoint)))
                            break
                    else:
                        effectDesc.keyPoints.append(KeyPoint(keyPointName, timePoint))
                effectDesc.keyPoints.sort(key=lambda i: i.time)
            if 'effects' in effData and 'shotSound' in effData['effects']:
                data = effData['effects']['shotSound']
                for effect in effectDesc.effectsList._EffectsList__effectDescList:
                    if effect.TYPE == '_ShotSoundEffectDesc':
                        effect._soundName = tuple(
                            (tuple(data[key]) if key in data else effectDesc._soundName[idx])
                            for idx, key in enumerate(('wwsoundPC', 'wwsoundNPC')))
        for sname, effData in self.data['gun_reload_effects'].iteritems():
            if effData['type'] not in reloadTypes:
                print self.ID + ': wrong reload effect type:', effData['type'], 'available:', sorted(reloadTypes.keys())
                continue
            reloadType = reloadTypes[effData['type']]
            orig, desc, sect = g_cache._gunReloadEffects.get(sname, None), None, ResMgr.DataSection()
            if not isinstance(orig, reloadType):  # None is not an instance too
                if orig is not None:
                    print self.ID + ': changing type of reload effect %s. Might cause problems!' % sname
                orig, desc = None, reloadType(sect)
            for slot in reloadType.__slots__:
                slotName = mismatchSlots.get(slot, slot)
                if slotName in effData:
                    value = effData[slotName]
                else:
                    value = getattr(orig or desc, slot)
                    if slot in modifiers:
                        value = modifiers[slot](value)
                sect.writeString(slotName, str(value))
            new_desc = reloadType(sect)
            if orig is None:
                g_cache._gunReloadEffects[sname] = new_desc
            else:  # set new attributes to existing descriptors, otherwise they don't update
                [setattr(orig, slot, getattr(new_desc, slot)) for slot in reloadType.__slots__]
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
                        item.sounds = SoundConfig('', itemData.get('wwsoundPC', s[0]), itemData.get('wwsoundNPC', s[1]))
                    elif item_type == 'guns':
                        if 'effects' in itemData:
                            self.overrideGunEffects(item, itemData['effects'])
                        if 'reloadEffect' in itemData:
                            item.reloadEffect = g_cache._gunReloadEffects.get(itemData['reloadEffect'], item.reloadEffect)
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
                        effectDesc._impactNames = ImpactNames(*(
                            typeData.get(key, getattr(effectDesc._impactNames, key))
                            for key in ('impactNPC_PC', 'impactPC_NPC', 'impactNPC_NPC', 'impactFNPC_PC')))
        for vehicleType in g_cache._Cache__vehicles.itervalues():
            self.inject_vehicleType(vehicleType)

    def inject_vehicleType(self, vehicleType):
        for item in vehicleType.engines:
            nationID = item.id[0]
            itemData = self.data['engines'].get(nations.NAMES[nationID], {}).get(item.name)
            if itemData:
                s = item.sounds.getEvents()
                item.sounds = SoundConfig('', itemData.get('wwsoundPC', s[0]), itemData.get('wwsoundNPC', s[1]))
        for item in (i for turrets in vehicleType.turrets for turret in turrets for i in turret.guns):
            nationID = item.id[0]
            if vehicleType.name in self.data['guns']:
                itemData = self.data['guns'][vehicleType.name].get(item.name)
            else:
                itemData = self.data['guns'].get(nations.NAMES[nationID], {}).get(item.name)
            if itemData:
                if 'effects' in itemData:
                    self.overrideGunEffects(item, itemData['effects'])
                if 'reloadEffect' in itemData:
                    item.reloadEffect = g_cache._gunReloadEffects.get(itemData['reloadEffect'], item.reloadEffect)

    def overrideGunEffects(self, gun, effectsData):
        is_old_list = isinstance(gun.effects, list)
        is_new_list = isinstance(effectsData, list)
        if is_old_list != is_new_list:
            if is_new_list:
                gun.effects = g_cache._gunEffects.get(effectsData[0], gun.effects)
            else:
                print self.ID + ': item %s needs %s effects as list but one string was provided. Skipping...' % (
                    gun.name, len(gun.effects))
            return
        if not is_new_list:
            gun.effects = g_cache._gunEffects.get(effectsData, gun.effects)
            return
        if len(gun.effects) != len(effectsData):
            print self.ID + ': item %s needs %s effects as list but %s were provided. Skipping...' % (
                gun.name, len(gun.effects), len(effectsData))
            return
        effects = []
        for effectName in effectsData:
            gun_effect = g_cache._gunEffects.get(effectName)
            if gun_effect is None:
                print self.ID + ': gun effect', effectName, 'not found'
            else:
                effects.append(gun_effect)
        if len(effects) == len(gun.effects):
            gun.effects = effects


@overrideMethod(VehicleType, '__init__')
def new_vehicleType_init(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    _config.inject_vehicleType(self)


@overrideMethod(PlayerAvatar, '_PlayerAvatar__initGUI')
def new_initGUI(base, self):
    result = base(self)
    events = self.soundNotifications._IngameSoundNotifications__events
    notificationsData = _config.data['sound_notifications']
    for eventName, event in events.iteritems():
        override = notificationsData.get(eventName, {})
        for category, sound in override.iteritems():
            if category not in event:
                event[category] = {
                    'sound': '', 'playRules': 0, 'timeout': 3.0, 'minTimeBetweenEvents': 0, 'shouldBindToPlayer': False}
            event[category]['sound'] = sound

    self.soundNotifications._IngameSoundNotifications__events = events
    return result


@overrideMethod(PlayerAvatar, 'updateVehicleGunReloadTime')
def updateVehicleGunReloadTime(base, self, vehicleID, timeLeft, baseTime):
    if (self._PlayerAvatar__prevGunReloadTimeLeft != timeLeft and timeLeft == 0.0
            and not self.guiSessionProvider.shared.vehicleState.isInPostmortem):
        try:
            if 'fx' in _config.data['sound_notifications'].get('gun_reloaded', {}):
                SoundGroups.g_instance.playSound2D(_config.data['sound_notifications']['gun_reloaded']['fx'])
        except StandardError:
            traceback.print_exc()
    base(self, vehicleID, timeLeft, baseTime)


_config = ConfigInterface()
statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-13', _config.confList)
