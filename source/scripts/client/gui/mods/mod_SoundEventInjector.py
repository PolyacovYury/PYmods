# -*- coding: utf-8 -*-
from itertools import chain

import BigWorld
import ResMgr
import SoundGroups
import nations
import traceback
from Avatar import PlayerAvatar
from OpenModsCore import Analytics, ConfigNoInterface, SimpleConfigInterface, find_attr, overrideMethod
from ReloadEffect import ReloadEffectsType, _AutoReloadDesc, _BarrelReloadDesc, _DualGunReloadDesc, _SimpleReloadDesc
from gui.IngameSoundNotifications import IngameSoundNotifications
from helpers.EffectsList import ImpactNames, KeyPoint, _SoundEffectDesc, _TracerSoundEffectDesc
from items.components.sound_components import WWTripleSoundConfig as SoundConfig
from items.vehicles import VehicleType, _VEHICLE_TYPE_XML_PATH, __readEffectsTimeLine as readEffectsTimeLine, g_cache
from material_kinds import EFFECT_MATERIALS

reloadTypes = {
    ReloadEffectsType.SIMPLE_RELOAD: _SimpleReloadDesc, ReloadEffectsType.BARREL_RELOAD: _BarrelReloadDesc,
    ReloadEffectsType.AUTO_RELOAD: _AutoReloadDesc, ReloadEffectsType.DUALGUN_RELOAD: _DualGunReloadDesc}
mismatchSlots = {
    'soundEvent': 'sound', 'shellDt': 'loopShellDt', 'shellDtLast': 'loopShellLastDt',
    'clipShellLoadT': 'clipShellLoadDuration', 'almostCompleteT': 'almostCompleteDuration'}
modifiers = {
    'duration': (lambda x: x * 1000.0), 'shellDuration': (lambda x: x * 1000.0),
    'clipShellLoadT': (lambda x: x * 1000.0), 'almostCompleteT': (lambda x: x * 1000.0)}


class ConfigInterface(ConfigNoInterface, SimpleConfigInterface):
    def __init__(self):
        self.confList = set()
        self.effectsXmlPath = _VEHICLE_TYPE_XML_PATH + 'common/gun_effects.xml'
        self.effectsXml = None
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.3.2 (%(file_compile_date)s)'
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.data = {
            'engines': {}, 'guns': {}, 'gun_effects': {}, 'gun_reload_effects': {}, 'shot_effects': {},
            'sound_notifications': {}}
        super(ConfigInterface, self).init()

    def loadLang(self):
        pass

    def readData(self, quiet=True):
        for data in self.data.values():
            data.clear()
        self.effectsXml = ResMgr.openSection(self.effectsXmlPath)
        self.readConfigDir(quiet)
        print self.LOG, 'loaded configs:', ', '.join(x + '.json' for x in sorted(self.confList))
        self.injectEffects()
        self.effectsXml = None

    def onReadConfig(self, quiet, dir_path, name, json_data, sub_dirs, names):
        self.confList.add(name)
        for itemType, itemsDict in json_data.iteritems():
            if itemType not in self.data:
                if not quiet:
                    print self.LOG, 'invalid item type in', name + ':', itemType
                continue
            itemsData = self.data[itemType]
            if itemType in ('engines', 'guns'):
                for nationName, nationData in itemsDict.iteritems():
                    if nationName.split(':')[0] not in nations.NAMES:
                        print self.LOG, 'unknown nation in', itemType, 'in', name + ':', nationName
                        continue
                    for itemName in nationData:
                        itemsData.setdefault(nationName, {}).setdefault(itemName, {}).update(nationData[itemName])
            if itemType in ('gun_reload_effects', 'shot_effects', 'sound_notifications'):
                for itemName in itemsDict:
                    itemsData.setdefault(itemName, {}).update(itemsDict[itemName])
            if itemType == 'gun_effects':
                for itemName, itemData in itemsDict.iteritems():
                    if 'origin' not in itemData:
                        print self.LOG, name + ':', itemName, 'has no origin'
                        continue
                    origin = itemData['origin']
                    if origin not in self.effectsXml.keys():
                        print self.LOG, name + ':', itemName, 'has unknown origin:', origin
                        continue
                    itemName = intern(itemName)
                    for key in itemData.keys():
                        if key not in ('origin', 'timeline', 'effects'):
                            print self.LOG, name + ': incorrect key', key, 'in', itemName, 'ignored'
                            itemData.pop(key, None)
                    if 'effects' in itemData:
                        for key in itemData['effects'].keys():
                            if key != 'shotSound':
                                print self.LOG, name + ': only shotSound effects are supported,', key, 'ignored'
                                itemData['effects'].pop(key)
                    itemsData.setdefault(itemName, {}).update(itemData)

    def injectEffects(self):
        for sname, effData in self.data['gun_effects'].iteritems():
            if sname not in g_cache.gunEffects:
                g_cache.gunEffects[sname] = readEffectsTimeLine(
                    ((None, self.effectsXmlPath), effData['origin']), self.effectsXml[effData['origin']])
            effectDesc = g_cache.gunEffects[sname]
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
                print self.LOG, 'wrong reload effect type:', effData['type'], 'available:', sorted(reloadTypes.keys())
                continue
            reloadType = reloadTypes[effData['type']]
            orig, desc, sect = g_cache._gunReloadEffects.get(sname, None), None, ResMgr.DataSection()
            if not isinstance(orig, reloadType):  # None is not an instance too
                if orig is not None:
                    print self.LOG, 'changing type of reload effect %s. Might cause problems!' % sname
                orig, desc = None, reloadType(sect, effData['type'])
            desc_slots = list(chain.from_iterable(getattr(cls, '__slots__', ()) for cls in reloadType.__mro__))
            for slot in desc_slots:
                if slot == '_intuitionOverrides':
                    continue
                slotName = mismatchSlots.get(slot, slot)
                if slotName in effData:
                    value = effData[slotName]
                else:
                    value = getattr(orig or desc, slot)
                    if slot in modifiers:
                        value = modifiers[slot](value)
                sect.writeString(slotName, str(value))
            desc_overrides = (orig or desc)._intuitionOverrides
            data_overrides = effData.get('intuition_overrides', {})
            for slot in desc_slots:
                slotName = mismatchSlots.get(slot, slot)
                if slotName in data_overrides:
                    value = data_overrides[slotName]
                else:
                    if slot not in desc_overrides:
                        continue
                    value = desc_overrides[slot]
                    if slot in modifiers:
                        value = modifiers[slot](value)
                sect.writeString('intuition_overrides/' + slotName, str(value))
            new_desc = reloadType(sect, effData['type'])
            if orig is None:
                g_cache._gunReloadEffects[sname] = new_desc
            else:  # set new attributes to existing descriptors, otherwise they don't update
                [setattr(orig, slot, getattr(new_desc, slot)) for slot in desc_slots]
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
                        effectDesc._soundName = tuple(
                            tuple(filter(None, (typeData.get(key),))) or effectDesc._soundName[idx]
                            for idx, key in enumerate(('wwsoundPC', 'wwsoundNPC')))
            for effType in (x for x in (tuple(x + 'Hit' for x in EFFECT_MATERIALS) + (
                    'armorBasicRicochet', 'armorRicochet', 'armorResisted', 'armorHit', 'armorCriticalHit')) if x in effData):
                typeData = effData[effType]
                for effectDesc in res[effType].effectsList._EffectsList__effectDescList:
                    if isinstance(effectDesc, _SoundEffectDesc):
                        effectDesc._impactNames = ImpactNames(
                            *(tuple(filter(None, (typeData.get(key),))) or getattr(effectDesc._impactNames, key)
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
        is_new_list = isinstance(effectsData, (list, tuple))
        if is_old_list != is_new_list:
            if is_new_list:
                gun.effects = g_cache.gunEffects.get(effectsData[0], gun.effects)
            else:
                print self.LOG, 'item %s needs %s effects as list but one string was provided. Skipping...' % (
                    gun.name, len(gun.effects))
            return
        if not is_new_list:
            gun.effects = g_cache.gunEffects.get(effectsData, gun.effects)
            return
        if len(gun.effects) != len(effectsData):
            print self.LOG, 'item %s needs %s effects as list but %s were provided. Skipping...' % (
                gun.name, len(gun.effects), len(effectsData))
            return
        effects = []
        for effectName in effectsData:
            gun_effect = g_cache.gunEffects.get(effectName)
            if gun_effect is None:
                print self.LOG, 'gun effect', effectName, 'not found'
            else:
                effects.append(gun_effect)
        if len(effects) == len(gun.effects):
            gun.effects = effects


@overrideMethod(VehicleType, '__init__')
def new_vehicleType_init(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.inject_vehicleType(self)


@overrideMethod(PlayerAvatar, '__initGUI')  # overrides initGUI instead of readConfigs because ProTanki
def new_initGUI(base, self):
    result = base(self)
    events = find_attr(self.soundNotifications, 'events')
    new_categories = {'fx': 'fxEvent', 'voice': 'infEvent'}
    new_additional = {
        'fxEvent': {'cooldownFx': 0},
        'infEvent': {'infChance': 100, 'cooldownEvent': 0, 'queue': 1, 'lifetime': 5, 'priority': 0}}
    notificationsData = g_config.data['sound_notifications']
    for eventName, override in notificationsData.iteritems():
        event = events.get(eventName)
        if event is None:
            print g_config.LOG, 'sound_notifications event', eventName, 'not found'
            continue
        for category, sound in override.iteritems():
            category = new_categories.get(category, category)
            if category in new_additional:
                [event.setdefault(k, v) for k, v in new_additional[category].iteritems()]
            if category == 'fxEvent':
                if category not in event:
                    event[category] = []
                if not isinstance(event[category], list):
                    event[category] = [event[category]]
                event[category].append(sound)
            else:
                event[category] = sound
            if 'queue' in event and event['queue'] not in self.soundNotifications._IngameSoundNotifications__queues:
                self.soundNotifications._IngameSoundNotifications__queues[event['queue']] = []
                self.soundNotifications._IngameSoundNotifications__playingEvents[event['queue']] = None

    return result


@overrideMethod(IngameSoundNotifications, 'play')
def new_play(base, self, eventName, *a, **k):
    event = g_config.data['sound_notifications'].get(eventName, {})
    for category in event:
        if not self.isCategoryEnabled(category):
            self._IngameSoundNotifications__enabledSoundCategories.add(category)
    return base(self, eventName, *a, **k)


@overrideMethod(IngameSoundNotifications, '__playFX')
def new_playFX(___, self, eventName, vehicleID, position, *_, **__):
    cooldown = self._IngameSoundNotifications__fxCooldowns
    if eventName in cooldown and cooldown[eventName]:
        return
    eventData = find_attr(self, 'events').get(eventName, None)
    if 'fxEvent' not in eventData or not self.isCategoryEnabled('fx'):
        return
    if float(eventData.get('cooldownFx', 0)) > 0:
        cooldown[eventName] = {'time': float(eventData['cooldownFx'])}
    events = eventData['fxEvent']
    if not isinstance(events, list):
        events = [events]
    for event in events:
        if vehicleID is not None:
            vehicle = BigWorld.entity(vehicleID)
            if vehicle:
                SoundGroups.g_instance.playSoundPos(event, vehicle.position)
        elif position is not None:
            SoundGroups.g_instance.playSoundPos(event, position)
        else:
            SoundGroups.g_instance.playSound2D(event)


@overrideMethod(PlayerAvatar, 'updateVehicleGunReloadTime')
def updateVehicleGunReloadTime(base, self, vehicleID, timeLeft, baseTime):
    if (self._PlayerAvatar__prevGunReloadTimeLeft != timeLeft and timeLeft == 0.0
            and not self.guiSessionProvider.shared.vehicleState.isInPostmortem):
        try:
            if 'fx' in g_config.data['sound_notifications'].get('gun_reloaded', {}):
                SoundGroups.g_instance.playSound2D(g_config.data['sound_notifications']['gun_reloaded']['fx'])
        except StandardError:
            traceback.print_exc()
    base(self, vehicleID, timeLeft, baseTime)


g_config = ConfigInterface()
statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-13', g_config.confList)
