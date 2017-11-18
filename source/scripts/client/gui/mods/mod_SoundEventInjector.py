# -*- coding: utf-8 -*-
import PYmodsCore
import ResMgr
import glob
import items.vehicles
import nations
import os
import traceback
from Avatar import PlayerAvatar
from ReloadEffect import _BarrelReloadDesc
from debug_utils import LOG_ERROR
from helpers.EffectsList import _SoundEffectDesc
from items.components import sound_components
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

    def readCurrentSettings(self, quiet=True):
        configPath = self.configPath + 'configs/'
        if not os.path.exists(configPath):
            LOG_ERROR('%s config folder not found:' % self.ID, configPath)
            os.makedirs(configPath)
        for confPath in glob.iglob(configPath + '*.json'):
            confName = os.path.basename(confPath).split('.')[0]
            try:
                confdict = PYmodsCore.loadJson(self.ID, confName, {}, os.path.dirname(confPath) + '/')
            except StandardError:
                print '%s: config %s is invalid.' % (self.ID, os.path.basename(confPath))
                traceback.print_exc()
                continue
            if not quiet:
                print '%s: loading %s.json' % (self.ID, confName)
            self.confList.add(confName)
            for itemType, itemsDict in confdict.iteritems():
                if itemType not in self.data:
                    if not quiet:
                        print '%s: invalid item type in %s: %s' % (self.ID, confName, itemType)
                    continue
                itemsData = self.data[itemType]
                if itemType in ('engines', 'guns'):
                    for nationName, nationData in itemsDict.iteritems():
                        if nationName.split(':')[0] not in nations.NAMES:
                            print '%s: unknown nation in %s data: %s' % (self.ID, itemType, nationName)
                            continue
                        itemsData.setdefault(nationName, {}).update(nationData)
                if itemType in ('gun_reload_effects', 'shot_effects', 'sound_notifications'):
                    for itemName in itemsDict:
                        itemsData.setdefault(itemName, {}).update(itemsDict[itemName])

    def load(self):
        pass

    def onInitComplete(self):
        self.readCurrentSettings(False)
        if any(self.data[key] for key in ('engines', 'gun_reload_effects', 'shot_effects', 'guns')):
            items.vehicles.init(True, None)
        print '%s: initialised.' % (self.message())


@PYmodsCore.overrideMethod(items.vehicles, '_readEngine')
def new_readEngine(base, xmlCtx, section, item, *args):
    base(xmlCtx, section, item, *args)
    nationID, _ = item.id
    sounds = item.sounds
    itemData = _config.data['engines'].get(nations.NAMES[nationID], {}).get(item.name, {})
    item.sounds = sound_components.WWTripleSoundConfig(sounds.wwsound, itemData.get('wwsoundPC', sounds.wwsoundPC),
                                                       itemData.get('wwsoundNPC', sounds.wwsoundNPC))


@PYmodsCore.overrideMethod(items.vehicles, '_readReloadEffectGroups')
def new_readReloadEffects(base, xmlPath):
    res = base(xmlPath)
    effectsData = _config.data['gun_reload_effects']
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
        elif _config.data['guns']:
            print '%s: gun effects config not found' % _config.ID
    return res


@PYmodsCore.overrideMethod(items.vehicles, '_readGun')
def new_readGun(base, xmlCtx, section, item, unlocksDescrs=None, _=None):
    base(xmlCtx, section, item, unlocksDescrs, _)
    nationID, itemID = item.id
    item.effects = items.vehicles.g_cache._gunEffects.get(
        _config.data['guns'].get(nations.NAMES[nationID], {}).get(item.name, {}).get('effects', ''), item.effects)


@PYmodsCore.overrideMethod(items.vehicles.VehicleType, '__init__')
def new_vehicleType_init(base, self, nationID, *args, **kwargs):
    base(self, nationID, *args, **kwargs)
    for item in self.engines:
        nationID, itemID = item.id
        sounds = item.sounds
        itemData = _config.data['engines'].get(nations.NAMES[nationID], {}).get(item.name, {})
        item.sounds = sound_components.WWTripleSoundConfig(sounds.wwsound, itemData.get('wwsoundPC', sounds.wwsoundPC),
                                                           itemData.get('wwsoundNPC', sounds.wwsoundNPC))
    for turrets in self.turrets:
        for turret in turrets:
            for item in turret.guns:
                nationID, itemID = item.id
                item.effects = items.vehicles.g_cache._gunEffects.get(
                    _config.data['guns'].get(self.name, {}).get(item.name, {}).get(
                        'effects',
                        _config.data['guns'].get(nations.NAMES[nationID], {}).get(item.name, {}).get('effects', '')),
                    item.effects)


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


_config = ConfigInterface()
_config.onInitComplete()
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version, 'UA-76792179-13', _config.confList)
