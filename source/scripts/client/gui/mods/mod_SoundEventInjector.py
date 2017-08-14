# -*- coding: utf-8 -*-
import PYmodsCore
import ResMgr
import glob
import items.vehicles
import nations
import os
import traceback
from ReloadEffect import _BarrelReloadDesc
from debug_utils import LOG_ERROR
from gui import IngameSoundNotifications
from helpers.EffectsList import _SoundEffectDesc
from items.components import sound_components
from material_kinds import EFFECT_MATERIALS


class _Config(PYmodsCore.Config):
    def __init__(self):
        super(self.__class__, self).__init__('%(mod_ID)s')
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.data = {'engines': {}, 'gun_reload_effects': {}, 'shot_effects': {}, 'sound_notifications': {}, 'guns': {}}

    def updateMod(self):
        pass

    def update_data(self, doPrint=False):
        configPath = self.configPath + 'configs/'
        for confPath in glob.iglob(configPath + '*.json'):
            if not os.path.exists(configPath):
                LOG_ERROR('%s config folder not found:' % self.ID, configPath)
                os.makedirs(configPath)
            try:
                confdict = self.loadJson(os.path.basename(confPath).split('.')[0], {}, os.path.dirname(confPath) + '/')
            except StandardError:
                print '%s: config %s is invalid.' % (self.ID, os.path.basename(confPath))
                traceback.print_exc()
                continue
            for itemType, itemsDict in confdict.iteritems():
                if itemType not in self.data:
                    continue
                itemsData = self.data[itemType]
                if itemType in ('engines', 'guns'):
                    for nationName, nationData in itemsDict.iteritems():
                        if nationName not in nations.NAMES:
                            print '%s: unknown nation in %s data: %s' % (self.ID, itemType, nationName)
                            continue
                        itemsData[nationName] = {}
                        for itemName in nationData:
                            itemsData[nationName][itemName] = nationData[itemName]
                if itemType in ('gun_reload_effects', 'shot_effects', 'sound_notifications'):
                    for itemName in itemsDict:
                        itemsData.setdefault(itemName, {}).update(itemsDict[itemName])

    def load(self):
        self.update_data(True)
        if any(self.data[key] for key in ('engines', 'gunReloadEffects', 'shot_effects')):
            items.vehicles.init(True, None)
        print '%s: initialised.' % (self.message())


@PYmodsCore.overrideMethod(items.vehicles, '_readEngine')
def new_readEngine(base, xmlCtx, section, item, *args):
    base(xmlCtx, section, item, *args)
    nationID, itemID = item.id
    nationName = nations.NAMES[nationID]
    enginesData = _config.data['engines']
    if nationName not in enginesData:
        return
    engines = enginesData[nationName]
    if item.name not in engines:
        return
    sounds = item.sounds
    itemData = engines[item.name]
    item.sounds = sound_components.WWTripleSoundConfig(sounds.wwsound, itemData.get('wwsoundPC', sounds.wwsoundPC),
                                                       itemData.get('wwsoundNPC', sounds.wwsoundNPC))


@PYmodsCore.overrideMethod(items.vehicles, '_readReloadEffectGroups')
def new_readReloadEffects(base, xmlPath):
    res = base(xmlPath)
    effectsData = _config.data['gunReloadEffects']
    for sname in res:
        if sname not in effectsData:
            continue
        effData = effectsData[sname]
        descr = res[sname]
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
    return res


@PYmodsCore.overrideMethod(items.vehicles, '_readShotEffects')
def new_readShotEffects(base, xmlCtx, section):
    res = base(xmlCtx, section)
    effectsData = _config.data['shot_effects']
    sname = xmlCtx[1]
    if sname in effectsData:
        effData = effectsData[sname]
        for effType in (x for x in ('projectile',) if x in effData):
            typeData = effData[effType]
            for effectDesc in res[effType][2]._EffectsList__effectDescList:
                if isinstance(effectDesc, _SoundEffectDesc):
                    effectDesc._soundNames = tuple(typeData.get(key, effectDesc._soundNames[idx]) for idx, key in
                                                   enumerate(('wwsoundPC', 'wwsoundNPC')))
        for effType in (x for x in (tuple(x + 'Hit' for x in EFFECT_MATERIALS) + (
                'armorBasicRicochet', 'armorRicochet', 'armorResisted', 'armorHit', 'armorCriticalHit')) if x in effData):
            typeData = effData[effType]
            for effectDesc in res[effType].effectsList._EffectsList__effectDescList:
                if isinstance(effectDesc, _SoundEffectDesc):
                    effectDesc._impactNames = tuple(typeData.get(key, effectDesc._impactNames[idx]) for idx, key in
                                                    enumerate(('impactNPC_PC', 'impactPC_NPC', 'impactNPC_NPC')))
    return res


@PYmodsCore.overrideMethod(items.vehicles, '_readEffectGroups')
def new_readEffectGroups(base, xmlPath, withSubgroups=False):
    res = base(xmlPath, withSubgroups)
    if 'gun_effects' in xmlPath:
        newXmlPath = '../' + _config.configPath + 'configs/gun_effects.xml'
        if ResMgr.isFile(newXmlPath):
            res.update(base(newXmlPath, withSubgroups))
    return res


@PYmodsCore.overrideMethod(items.vehicles, '_readGun')
def new_readGun(base, xmlCtx, section, item, unlocksDescrs=None, _=None):
    base(xmlCtx, section, item, unlocksDescrs, _)
    nationID, itemID = item.id
    item.effects = items.vehicles.g_cache._gunEffects.get(
        _config.data['guns'].get(nations.NAMES[nationID], {}).get(item.name, {}).get('effects', ''), item.effects)


@PYmodsCore.overrideMethod(IngameSoundNotifications.IngameSoundNotifications, '_IngameSoundNotifications__readConfig')
def new_readConfig(base, self):
    base(self)
    events = self._IngameSoundNotifications__events
    notificationsData = _config.data['sound_notifications']
    for eventName, event in events.iteritems():
        if eventName in notificationsData:
            for category in event:
                event[category]['sound'] = notificationsData[eventName].get(category, event[category]['sound'])

    self._IngameSoundNotifications__events = events


_config = _Config()
_config.load()
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version.split(' ', 1)[0], 'UA-76792179-')
