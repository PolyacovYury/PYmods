# -*- coding: utf-8 -*-
import PYmodsCore
import glob
import items.vehicles
import nations
import os
import traceback
from ReloadEffect import _BarrelReloadDesc
from debug_utils import LOG_ERROR
from items.components import sound_components


class _Config(PYmodsCore.Config):
    def __init__(self):
        super(self.__class__, self).__init__('%(mod_ID)s')
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.data = {'engines': {}, 'gunReloadEffects': {}}

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
            for itemType, itemsData in confdict.iteritems():
                if itemType not in self.data:
                    continue
                items = self.data[itemType]
                if itemType in ('engines',):
                    for nationName, nationData in itemsData.iteritems():
                        if nationName not in nations.NAMES:
                            print '%s: unknown nation in %s data: %s' % (self.ID, itemType, nationName)
                            continue
                        items[nationName] = {}
                        for itemName in nationData:
                            items[nationName][itemName] = nationData[itemName]
                if itemType in ('gunReloadEffects',):
                    for itemName in itemsData:
                        items[itemName] = itemsData[itemName]

    def load(self):
        self.update_data(True)
        if any(self.data.values()):
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


_config = _Config()
_config.load()
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version.split(' ', 1)[0], 'UA-76792179-')
