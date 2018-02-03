import items.vehicles
import nations
from PYmodsCore import loadJson, refreshCurrentVehicle
from gui import SystemMessages
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from items.vehicles import CAMOUFLAGE_KINDS, CAMOUFLAGE_KIND_INDICES
from .. import g_config
from ..utils import getCurrentNationID


class CamoSelectorUI(AbstractWindowView):
    def py_onSyncData(self):
        # noinspection PyUnresolvedReferences
        texts = {
            'header': g_config.i18n['UI_flash_header'],
            'nations': map(lambda x: i18n.makeString('#nations:%s' % x), nations.NAMES) + [
                g_config.i18n['UI_flash_camoMode_modded'], g_config.i18n['UI_flash_camoMode_international']],
            'camouflages': [[] for _ in xrange(len(nations.NAMES) + 2)],
            'randomOptions': {'text': g_config.i18n['UI_flash_randomOptions_text'],
                              'tooltip': g_config.tb.createTooltip('randomOptions', 'flash'),
                              'options': [g_config.i18n['UI_flash_randomOptions_OFF'],
                                          g_config.i18n['UI_flash_randomOptions_overrideRandom'],
                                          g_config.i18n['UI_flash_randomOptions_includeInRandom']]},
            'useFor': {'header': g_config.tb.createLabel('useFor_header', 'flash'),
                       'ally': g_config.tb.createLabel('useFor_ally', 'flash'),
                       'enemy': g_config.tb.createLabel('useFor_enemy', 'flash')},
            'season': {'header': g_config.tb.createLabel('season_header', 'flash'),
                       'winter': g_config.tb.createLabel('season_winter', 'flash'),
                       'summer': g_config.tb.createLabel('season_summer', 'flash'),
                       'desert': g_config.tb.createLabel('season_desert', 'flash')},
            'installTooltip': g_config.i18n['UI_flash_installTooltip'],
            'save': g_config.i18n['UI_flash_save']}
        settings = [[] for _ in xrange(len(nations.NAMES) + 2)]
        for idx, nation in enumerate(nations.NAMES + ('modded', 'international')):
            nationID = min(idx, len(nations.NAMES) - 1)
            camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
            camoNames = {camouflage['name']: camoID for camoID, camouflage in camouflages.items()}
            for camoName in camoNames.keys():
                if nation == 'modded':
                    if camoName not in g_config.camouflages['modded']:
                        del camoNames[camoName]
                elif nation == 'international':
                    if camoName not in g_config.origInterCamo:
                        del camoNames[camoName]
                elif camoName in g_config.interCamo:
                    del camoNames[camoName]
            for camoName in sorted(camoNames.keys()):
                camoID = camoNames[camoName]
                camouflageDesc = camouflages[camoID]
                camouflage = g_config.camouflages.get(nation, {}).get(camoName, {})
                texts['camouflages'][idx].append(camoName)
                camoSettings = {'randomOption': camouflage.get('random_mode', 2),
                                'camoInShop': g_config.customizationController.dataAggregator._elementIsInShop(
                                    camoID, 0, nationID),
                                'isInternational': camoName in g_config.interCamo,
                                'useFor': {'ally': camouflage.get('useForAlly', True),
                                           'enemy': camouflage.get('useForEnemy', True)},
                                'season': {}}
                for key, kind in CAMOUFLAGE_KINDS.items():
                    if camouflage.get('season') is not None:
                        camoSettings['season'][key] = key in camouflage['season']
                    else:
                        camoSettings['season'][key] = kind == camouflageDesc['kind']
                settings[idx].append(camoSettings)
        self.flashObject.as_syncData({'texts': texts, 'settings': settings, 'ids': g_config.backup})
        self.changeNation(getCurrentNationID())

    def changeNation(self, nationID):
        g_config.backupNationID = nationID
        if self._isDAAPIInited():
            self.flashObject.as_changeNation(nationID)

    def onWindowClose(self):
        g_config.activePreviewCamo = None
        SystemMessages.pushMessage('temp_SM' + g_config.i18n['UI_camouflageRestore'],
                                   SystemMessages.SM_TYPE.CustomizationForGold)
        refreshCurrentVehicle()
        self.destroy()

    def as_isModalS(self):
        if self._isDAAPIInited():
            return False

    @staticmethod
    def py_onSettings(settings):
        for idx, nation in enumerate(nations.NAMES + ('modded', 'international')):
            nationID = min(idx, len(nations.NAMES) - 1)
            camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
            nationConf = g_config.camouflages.setdefault(nation, {})
            camoNames = {camouflage['name']: camoID for camoID, camouflage in camouflages.items()}
            for camoName in camoNames.keys():
                if nation == 'modded':
                    if camoName not in g_config.camouflages['modded']:
                        del camoNames[camoName]
                elif nation == 'international':
                    if camoName not in g_config.origInterCamo:
                        del camoNames[camoName]
                elif camoName in g_config.interCamo:
                    del camoNames[camoName]
            for camoNum, camoName in enumerate(sorted(camoNames.keys())):
                nationConf.setdefault(camoName, {})
                camoID = camoNames[camoName]
                camouflageDesc = camouflages[camoID]
                camoInShop = g_config.customizationController.dataAggregator._elementIsInShop(camoID, 0, nationID)
                isInter = camoName in g_config.interCamo
                newSettings = settings[idx][camoNum]
                nationConf[camoName]['random_mode'] = newSettings.randomOption
                nationConf[camoName]['useForAlly'] = newSettings.useFor.ally
                nationConf[camoName]['useForEnemy'] = newSettings.useFor.enemy
                enabledSeason = []
                for key in ('winter', 'summer', 'desert'):
                    if getattr(newSettings.season, key):
                        enabledSeason.append(key)
                    nationConf[camoName]['season'] = ','.join(enabledSeason)
                for confFolderName in g_config.configFolders:
                    configFolder = g_config.configFolders[confFolderName]
                    if camoName in configFolder:
                        loadJson(g_config.ID, 'settings', dict((key, nationConf[key]) for key in configFolder),
                                 g_config.configPath + 'camouflages/' + confFolderName + '/', True, False)
                if nationConf[camoName]['random_mode'] == 2 or nationConf[camoName]['random_mode'] == 1 and not isInter:
                    del nationConf[camoName]['random_mode']
                kindNames = filter(None, nationConf[camoName]['season'].split(','))
                if len(kindNames) == 1 and kindNames[0] == CAMOUFLAGE_KIND_INDICES[camouflageDesc['kind']] or camoInShop:
                    del nationConf[camoName]['season']
                for team in ('Ally', 'Enemy'):
                    if nationConf[camoName]['useFor%s' % team]:
                        del nationConf[camoName]['useFor%s' % team]
                if not nationConf[camoName]:
                    del nationConf[camoName]
            if nation in g_config.camouflages and not nationConf and nation != 'modded':
                del g_config.camouflages[nation]
        newSettings = {}
        if g_config.disable:
            newSettings['disable'] = g_config.disable
        for nation in nations.NAMES + ('international',):
            if nation in g_config.camouflages:
                newSettings[nation] = g_config.camouflages[nation]
        loadJson(g_config.ID, 'settings', newSettings, g_config.configPath, True)

        SystemMessages.pushMessage('temp_SM' + g_config.i18n['UI_camouflageSave'],
                                   SystemMessages.SM_TYPE.CustomizationForGold)
        refreshCurrentVehicle()

    @staticmethod
    def py_printLog(*args):
        for arg in args:
            print arg

    @staticmethod
    def py_onShowPreset(nationID, mode, camoID):
        nationName = ('modded', 'international', nations.NAMES[nationID])[mode]
        camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
        camoNames = {camouflage['name']: camoID for camoID, camouflage in camouflages.items()}
        for camoName in camoNames.keys():
            if nationName == 'modded':
                if camoName not in g_config.camouflages['modded']:
                    del camoNames[camoName]
            elif nationName == 'international':
                if camoName not in g_config.origInterCamo:
                    del camoNames[camoName]
            elif camoName in g_config.interCamo:
                del camoNames[camoName]
        g_config.activePreviewCamo = sorted(camoNames.keys())[int(camoID)]
        SystemMessages.pushMessage('temp_SM' + g_config.i18n['UI_camouflagePreview'] +
                                   g_config.activePreviewCamo.join(('<b>', '</b>')),
                                   SystemMessages.SM_TYPE.CustomizationForGold)
        g_config.backup['mode'] = mode
        newIdx = nationID if mode == 2 else (len(nations.NAMES) + mode - 2)
        g_config.backup['camoID'][newIdx] = camoID
        refreshCurrentVehicle()

    @staticmethod
    def py_onApplyPreset():
        pass  # installSelectedCamo()
