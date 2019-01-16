# -*- coding: utf-8 -*-
import BigWorld
import Keys
import Math
import fnmatch
import os
import traceback
from PYmodsCore import PYmodsConfigInterface, refreshCurrentVehicle, checkKeys, loadJson, showI18nDialog, overrideMethod, \
    remDups, PYViewTools
from collections import OrderedDict
from functools import partial
from gui import InputHandler, SystemMessages
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.daapi.view.login.LoginView import LoginView
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.app_loader import g_appLoader
from helpers import dependency
from items.components import c11n_constants
from items.components.chassis_components import SplineConfig
from items.components.component_constants import ALLOWED_EMBLEM_SLOTS as AES
from items.components.shared_components import EmblemSlot
from items.vehicles import g_cache
from skeletons.gui.shared.utils import IHangarSpace
from vehicle_systems.tankStructure import TankPartNames
from . import __date__, __modID__
from .remods import chassis_params


class ConfigInterface(PYmodsConfigInterface):
    hangarSpace = dependency.descriptor(IHangarSpace)
    modelDescriptor = property(lambda self: {
        'name': '', 'message': '', 'whitelist': [],
        'chassis': {'undamaged': '', 'emblemSlots': [], 'AODecals': [], 'hullPosition': [], 'soundID': ''},
        'hull': {'undamaged': '', 'emblemSlots': [], 'exhaust': {'nodes': [], 'pixie': ''},
                 'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
        'turret': {'undamaged': '', 'emblemSlots': [],
                   'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
        'gun': {'undamaged': '', 'emblemSlots': [], 'soundID': '',
                'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
        'engine': {'soundID': ''},
        'common': {'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}}})

    def __init__(self):
        self.teams = ('player', 'ally', 'enemy')
        self.settings = {}
        self.modelsData = {'models': {}, 'selected': {'player': {}, 'ally': {}, 'enemy': {}}}
        self.isModAdded = False
        self.collisionMode = 0
        self.isInHangar = False
        self.currentTeam = self.teams[0]
        self.previewRemod = None
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = __modID__
        self.version = '3.1.0 (%s)' % __date__
        self.author += ' (thx to atacms)'
        self.defaultKeys = {'ChangeViewHotkey': [Keys.KEY_F2, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
                            'SwitchRemodHotkey': [Keys.KEY_F3, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
                            'CollisionHotkey': [Keys.KEY_F4, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]]}
        self.data = {'enabled': True,
                     'isDebug': True,
                     'ChangeViewHotkey': self.defaultKeys['ChangeViewHotkey'],
                     'CollisionHotkey': self.defaultKeys['CollisionHotkey'],
                     'SwitchRemodHotkey': self.defaultKeys['SwitchRemodHotkey']}
        self.i18n = {
            'UI_description': 'Remod Enabler',
            'UI_flash_header': 'Remods setup',
            'UI_flash_header_tooltip': "Extended setup for RemodEnabler by "
                                       "<font color='#DD7700'><b>Polyacov_Yury</b></font>",
            'UI_flash_header_simple': 'Remods for ',
            'UI_flash_header_main': 'Advanced settings',
            'UI_flash_header_setup': 'Remods setup',
            'UI_flash_header_create': 'Create remod',
            'UI_flash_remodSetupBtn': 'Remods setup',
            'UI_flash_remodCreateBtn': 'Create remod',
            'UI_flash_remodCreate_name_text': 'Remod name',
            'UI_flash_remodCreate_name_tooltip': 'Remod unique ID and config file name.',
            'UI_flash_remodCreate_message_text': 'Author message',
            'UI_flash_remodCreate_message_tooltip': 'This message is displayed in hangar every time the remod is selected.'
                                                    '\nLeave blank if not required.',
            'UI_flash_remodCreate_name_empty': '<b>Remod creation failed:</b>\nname is empty.',
            'UI_flash_remodCreate_error': '<b>Remod creation failed:</b>\ncheck python.log for additional information.',
            'UI_flash_remodCreate_success': '<b>Remod created successfully</b>.',
            'UI_flash_whiteDropdown_default': 'Expand',
            'UI_flash_useFor_header_text': 'Use this item for:',
            'UI_flash_useFor_player_text': 'Player',
            'UI_flash_useFor_ally_text': 'Allies',
            'UI_flash_useFor_enemy_text': 'Enemies',
            'UI_flash_WLVehDelete_header': 'Confirmation',
            'UI_flash_WLVehDelete_text': 'Are you sure you want to disable this remod for this vehicle?',
            'UI_flash_vehicleDelete_success': 'Vehicle deleted from <b>%s</b> whitelist: <b>%s</b>',
            'UI_flash_remodAdd_success': 'Remod <b>%s</b> installed on <b>%s</b>.',
            'UI_flash_vehicleAdd_success': 'Vehicle added to <b>%s</b> whitelist: <b>%s</b>',
            'UI_flash_vehicleAdd_dupe': 'Vehicle already in <b>%s</b> whitelist: <b>%s</b>',
            'UI_flash_vehicleAdd_notSupported':
                'Vehicle can\'t be added to <b>%s</b> whitelist:%s is not supported by RemodEnabler.',
            'UI_flash_addBtn': 'Add',
            'UI_flash_removeBtn': 'Remove',
            'UI_flash_backBtn': 'Back',
            'UI_flash_advancedBtn': 'Advanced',
            'UI_flash_saveBtn': 'Save',
            'UI_flash_unsaved_header': 'Unsaved settings',
            'UI_flash_unsaved_text': 'Unsaved setting changes detected. Do you want to save them?',
            'UI_flash_notFound': '(nothing found)',
            'UI_setting_isDebug_text': 'Enable extended log printing',
            'UI_setting_isDebug_tooltip': 'If enabled, your python.log will be harassed with mod\'s debug information.',
            'UI_setting_ChangeViewHotkey_text': 'View mode switch hotkey',
            'UI_setting_ChangeViewHotkey_tooltip': (
                'This hotkey will switch the preview mode in hangar.\n<b>Possible modes:</b>\n'
                ' • Player tank\n • Ally tank\n • Enemy tank'),
            'UI_setting_CollisionHotkey_text': 'Collision view switch hotkey',
            'UI_setting_CollisionHotkey_tooltip': (
                '<b>WARNING: this module is non-functional. Apologies for the inconvenience.</b>\n'
                'This hotkey will switch collision preview mode in hangar.\n'
                '<b>Possible modes:</b>\n • OFF\n • Model replace\n • Model add'),
            'UI_setting_SwitchRemodHotkey_text': 'Remod switch hotkey',
            'UI_setting_SwitchRemodHotkey_tooltip': 'This hotkey will cycle through all remods.',
            'UI_collision_compare_enable': '<b>RemodEnabler:</b>\nDisabling collision comparison mode.',
            'UI_collision_compare_disable': '<b>RemodEnabler:</b>\nEnabling collision comparison mode.',
            'UI_collision_enable': '<b>RemodEnabler:</b>\nEnabling collision mode.',
            'UI_collision_unavailable': '<b>RemodEnabler:</b>\nCollision displaying is currently not supported.',
            'UI_install_remod': '<b>RemodEnabler:</b>\nRemod installed: ',
            'UI_install_default': '<b>RemodEnabler:</b>\nDefault model applied.',
            'UI_install_wheels_unsupported':
                '<b>RemodEnabler:</b>\nWARNING: wheeled vehicles are NOT processed. '
                'At least until WG moves params processing out of Vehicular, which is an inaccessible part of game engine.',
            'UI_mode': '<b>RemodEnabler:</b>\nCurrent display mode: ',
            'UI_mode_player': 'player tank preview',
            'UI_mode_ally': 'ally tank preview',
            'UI_mode_enemy': 'enemy tank preview'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [self.tb.createHotKey('ChangeViewHotkey'),
                            self.tb.createHotKey('CollisionHotkey')],
                'column2': [self.tb.createHotKey('SwitchRemodHotkey'),
                            self.tb.createControl('isDebug')]}

    def onMSADestroy(self):
        refreshCurrentVehicle()

    def onApplySettings(self, settings):
        super(ConfigInterface, self).onApplySettings(settings)
        if self.isModAdded:
            kwargs = dict(id='RemodEnablerUI', enabled=self.data['enabled'])
            try:
                BigWorld.g_modsListApi.updateModification(**kwargs)
            except AttributeError:
                BigWorld.g_modsListApi.updateMod(**kwargs)

    def readCurrentSettings(self, quiet=True):
        super(ConfigInterface, self).readCurrentSettings(quiet)
        self.settings = loadJson(self.ID, 'settings', self.settings, self.configPath)
        self.modelsData['models'].clear()
        self.modelsData['selected'] = selectedData = loadJson(
            self.ID, 'remodsCache', self.modelsData['selected'], self.configPath)
        remodTanks = set()
        for root, _, fNames in os.walk(self.configPath + 'remods/'):
            for fName in fnmatch.filter(fNames, '*.json'):
                sName = fName.split('.')[0]
                confDict = loadJson(self.ID, sName, {}, root, encrypted=True)
                if not confDict:
                    print self.ID + ': error while reading', fName + '.'
                    continue
                settingsDict = self.settings.setdefault(sName, {team: confDict[team] for team in self.teams})
                self.modelsData['models'][sName] = pRecord = self.modelDescriptor
                pRecord['name'] = sName
                pRecord['message'] = confDict.get('message', '')
                settingsDict['whitelist'] = pRecord['whitelist'] = whitelist = remDups(
                    x.strip() for x in settingsDict.get('whitelist', confDict['whitelist']) if x.strip())
                for xmlName in whitelist:
                    remodTanks.add(xmlName)
                    for team in selectedData:
                        if xmlName not in selectedData[team] or selectedData[team][xmlName] is None:
                            if settingsDict[team]:
                                selectedData[team][xmlName] = sName
                            else:
                                selectedData[team][xmlName] = None
                if self.data['isDebug']:
                    if not whitelist:
                        print self.ID + ': empty whitelist for', sName + '.'
                    else:
                        print self.ID + ': whitelist for', sName + ':', whitelist
                for key, data in pRecord.iteritems():
                    if key in ('name', 'message', 'whitelist'):
                        continue
                    if key == 'common':
                        confSubDict = confDict
                    else:
                        confSubDict = confDict.get(key)
                    if not confSubDict:
                        continue
                    if 'undamaged' in data:
                        data['undamaged'] = confSubDict['undamaged']
                    if 'AODecals' in data and 'AODecals' in confSubDict and 'hullPosition' in confSubDict:
                        data['AODecals'] = []
                        for subList in confSubDict['AODecals']:
                            m = Math.Matrix()
                            for strNum, row in enumerate(subList):
                                for colNum, elemNum in enumerate(row):
                                    m.setElement(strNum, colNum, elemNum)
                            data['AODecals'].append(m)
                        data['hullPosition'] = confSubDict['hullPosition']
                    if 'camouflage' in data and 'exclusionMask' in confSubDict.get('camouflage', {}):
                        data['camouflage']['exclusionMask'] = confSubDict['camouflage']['exclusionMask']
                        if 'tiling' in confSubDict['camouflage']:
                            data['camouflage']['tiling'] = confSubDict['camouflage']['tiling']
                    elif key == 'common' and self.data['isDebug']:
                        print self.ID + ': default camomask not found for', sName
                    if 'emblemSlots' in data:
                        data['emblemSlots'] = slots = []
                        for subDict in confSubDict.get('emblemSlots', []):
                            if subDict['type'] not in AES:
                                print g_config.ID + ': not supported emblem slot type:', subDict['type'] + ', expected:', AES
                                continue
                            descr = EmblemSlot(
                                Math.Vector3(tuple(subDict['rayStart'])), Math.Vector3(tuple(subDict['rayEnd'])),
                                Math.Vector3(tuple(subDict['rayUp'])), subDict['size'],
                                subDict.get('hideIfDamaged', False), subDict['type'],
                                subDict.get('isMirrored', False),
                                subDict.get('isUVProportional', True), subDict.get('emblemId', None),
                                subDict.get('slotId', c11n_constants.customizationSlotIds[key][subDict['type']][0]),
                                subDict.get('applyToFabric', True))
                            slots.append(descr)
                    if 'exhaust' in data and 'exhaust' in confSubDict:
                        if 'nodes' in confSubDict['exhaust']:
                            data['exhaust']['nodes'] = confSubDict['exhaust']['nodes']
                        if 'pixie' in confSubDict['exhaust']:
                            data['exhaust']['pixie'] = confSubDict['exhaust']['pixie']
                    if key == 'chassis':
                        for k in chassis_params + ('chassisLodDistance',):
                            data[k] = confSubDict[k]
                    if 'soundID' in data and 'soundID' in confSubDict:
                        data['soundID'] = confSubDict['soundID']
                if self.data['isDebug']:
                    print self.ID + ': config for', sName, 'loaded.'

        for sName in self.settings.keys():
            if sName not in self.modelsData['models']:
                del self.settings[sName]

        if not self.modelsData['models']:
            if not quiet:
                print self.ID + ': no configs found, model module standing down.'
        for team in self.teams:
            for xmlName in selectedData[team].keys():
                if xmlName not in remodTanks:
                    del selectedData[team][xmlName]
                    continue
                if selectedData[team][xmlName] is None or (
                        selectedData[team][xmlName] and selectedData[team][xmlName] not in self.modelsData['models']):
                    selectedData[team][xmlName] = next(
                        (sName for sName in sorted(self.modelsData['models']) if xmlName in self.settings[sName]['whitelist']
                         and self.settings[sName][team]), None) or ''
        loadJson(self.ID, 'remodsCache', selectedData, self.configPath, True, quiet=quiet)
        loadJson(self.ID, 'settings', self.settings, self.configPath, True, quiet=quiet)

    def load(self):
        from .config_converter import migrateConfigs
        migrateConfigs(self)
        super(ConfigInterface, self).load()

    def findModelDesc(self, xmlName, currentTeam, notForPreview=True):
        if not self.modelsData['models']:
            return
        selected = self.modelsData['selected'][currentTeam]
        if not self.previewRemod or notForPreview:
            if xmlName not in selected or not selected[xmlName]:
                return
            return self.modelsData['models'][selected[xmlName]]
        else:
            return self.modelsData['models'][self.previewRemod]

    def registerSettings(self):
        super(ConfigInterface, self).registerSettings()
        if not hasattr(BigWorld, 'g_modsListApi'):
            return
        # noinspection PyArgumentList
        g_entitiesFactories.addSettings(
            ViewSettings('RemodEnablerUI', RemodEnablerUI, 'RemodEnabler.swf', ViewTypes.WINDOW, None,
                         ScopeTemplates.GLOBAL_SCOPE, False))
        kwargs = dict(
            id='RemodEnablerUI', name=self.i18n['UI_flash_header'], description=self.i18n['UI_flash_header_tooltip'],
            icon='gui/flash/RemodEnabler.png', enabled=self.data['enabled'], login=False, lobby=True, callback=lambda: (
                    g_appLoader.getDefLobbyApp().containerManager.getContainer(ViewTypes.TOP_WINDOW).getViewCount()
                    or g_appLoader.getDefLobbyApp().loadView(SFViewLoadParams('RemodEnablerUI'))))
        try:
            BigWorld.g_modsListApi.addModification(**kwargs)
        except AttributeError:
            BigWorld.g_modsListApi.addMod(**kwargs)
        self.isModAdded = True

    def lobbyKeyControl(self, event):
        if not event.isKeyDown() or self.isMSAWindowOpen:
            return
        if self.modelsData['models'] and not self.previewRemod:
            if checkKeys(self.data['ChangeViewHotkey']):
                newModeNum = (self.teams.index(self.currentTeam) + 1) % len(self.teams)
                self.currentTeam = self.teams[newModeNum]
                try:
                    from gui.mods.mod_skinner import g_config as _
                    _.currentTeam = self.currentTeam
                except ImportError:
                    pass
                if self.data['isDebug']:
                    print self.ID + ': changing display mode to', self.currentTeam
                SystemMessages.pushMessage(
                    'temp_SM%s<b>%s</b>' % (self.i18n['UI_mode'], self.i18n['UI_mode_' + self.currentTeam]),
                    SystemMessages.SM_TYPE.Warning)
                refreshCurrentVehicle()
            if checkKeys(self.data['SwitchRemodHotkey']):
                curTankType = self.currentTeam
                snameList = sorted(self.modelsData['models'].keys()) + ['']
                selected = self.modelsData['selected'][curTankType]
                vehName = RemodEnablerUI.py_getCurrentVehicleName()
                if vehName not in selected:
                    return
                snameIdx = (snameList.index(selected[vehName]) + 1) % len(snameList)
                for Idx in xrange(snameIdx, len(snameList) - 1):
                    curPRecord = self.modelsData['models'][snameList[Idx]]
                    if vehName not in curPRecord['whitelist']:
                        continue
                    selected[vehName] = curPRecord['name']
                    break
                else:
                    selected[vehName] = ''
                loadJson(self.ID, 'remodsCache', self.modelsData['selected'], self.configPath, True,
                         quiet=not self.data['isDebug'])
                refreshCurrentVehicle()
        if checkKeys(self.data['CollisionHotkey']):
            SystemMessages.pushMessage('temp_SM' + self.i18n['UI_collision_unavailable'],
                                       SystemMessages.SM_TYPE.CustomizationForGold)
            return
            # noinspection PyUnreachableCode
            self.collisionMode += 1
            self.collisionMode %= 3
            if self.collisionMode == 0:
                if self.data['isDebug']:
                    print self.ID + ': disabling collision displaying'
                SystemMessages.pushMessage('temp_SM' + self.i18n['UI_collision_compare_disable'],
                                           SystemMessages.SM_TYPE.CustomizationForGold)
            elif self.collisionMode == 2:
                if self.data['isDebug']:
                    print self.ID + ': enabling collision display comparison mode'
                SystemMessages.pushMessage('temp_SM' + self.i18n['UI_collision_compare_enable'],
                                           SystemMessages.SM_TYPE.CustomizationForGold)
            else:
                if self.data['isDebug']:
                    print self.ID + ': enabling collision display'
                SystemMessages.pushMessage('temp_SM' + self.i18n['UI_collision_enable'],
                                           SystemMessages.SM_TYPE.CustomizationForGold)
            refreshCurrentVehicle()


class RemodEnablerUI(AbstractWindowView, PYViewTools):
    def _populate(self):
        super(self.__class__, self)._populate()
        g_config.hangarSpace.onVehicleChanged += self.onVehicleReloaded
        self.newRemodData = OrderedDict()

    def _dispose(self):
        g_config.hangarSpace.onVehicleChanged -= self.onVehicleReloaded

    def onVehicleReloaded(self):
        vehicleName = self.py_getCurrentVehicleName()
        if vehicleName is not None:
            self.flashObject.as_onVehicleReloaded(vehicleName)

    def py_onRequestSettings(self):
        g_config.readCurrentSettings(not g_config.data['isDebug'])
        texts = {k[9:]: v for k, v in g_config.i18n.iteritems() if k.startswith('UI_flash_')}
        self.flashObject.as_updateData(texts, g_config.settings, g_config.modelsData['selected'])

    def py_checkSettings(self, settings, cache):
        settings = self.objToDict(settings)
        cache = self.objToDict(cache)
        if g_config.settings != settings or g_config.modelsData['selected'] != cache:
            showI18nDialog(
                g_config.i18n['UI_flash_unsaved_header'], g_config.i18n['UI_flash_unsaved_text'], 'common/confirm',
                lambda confirm: (
                    (self.py_onSaveSettings(settings, cache) if confirm else None), self.flashObject.as_onSettingsChecked()))
            return False
        else:
            return True

    def py_getRemodData(self):
        appearance = self.getCurrentAppearance()
        vehName = self.py_getCurrentVehicleName()
        if vehName:
            try:
                data = self.newRemodData
                data.clear()
                data['message'] = ''
                for team in g_config.teams:
                    data[team] = True
                data['whitelist'] = [vehName] if vehName else []
                vDesc = appearance._HangarVehicleAppearance__vDesc
                for key in TankPartNames.ALL + ('engine',):
                    data[key] = OrderedDict()
                modelsSet = appearance._HangarVehicleAppearance__outfit.modelsSet or 'default'
                for key in TankPartNames.ALL:
                    data[key]['undamaged'] = getattr(vDesc, key).modelsSets[modelsSet].undamaged
                chassis = data['chassis']
                from .remods import chassis_params
                for key in chassis_params + ('chassisLodDistance',):
                    obj = _asdict(getattr(vDesc.chassis, key))
                    chassis[key] = obj
                chassis['splineDesc']['segmentModelSets'] = chassis['splineDesc']['segmentModelSets'][modelsSet]
                chassis['hullPosition'] = vDesc.chassis.hullPosition.list()
                chassis['AODecals'] = [[[decal.get(strIdx, colIdx) for colIdx in xrange(3)] for strIdx in xrange(4)]
                                       for decal in vDesc.chassis.AODecals]
                for partName in ('gun', 'chassis', 'engine'):
                    data[partName]['soundID'] = getattr(vDesc, partName).name
                pixieID = ''
                for key, value in g_cache._customEffects['exhaust'].iteritems():
                    if value == vDesc.hull.customEffects[0]._selectorDesc:
                        pixieID = key
                        break
                data['hull']['exhaust'] = {'nodes': list(vDesc.hull.customEffects[0].nodes), 'pixie': pixieID}
                exclMask = vDesc.type.camouflage.exclusionMask
                if exclMask:
                    camouflage = data['camouflage'] = OrderedDict()
                    camouflage['exclusionMask'] = exclMask
                    camouflage['tiling'] = vDesc.type.camouflage.tiling
                for partName in TankPartNames.ALL[1:]:
                    part = getattr(vDesc, partName)
                    exclMask = part.camouflage.exclusionMask if hasattr(part, 'camouflage') else ''
                    if exclMask:
                        camouflage = data[partName]['camouflage'] = OrderedDict()
                        camouflage['exclusionMask'] = exclMask
                        camouflage['tiling'] = part.camouflage.tiling
                for partName in TankPartNames.ALL:
                    part = getattr(vDesc, partName)
                    data[partName]['emblemSlots'] = []
                    for slot in part.emblemSlots:
                        slotDict = OrderedDict()
                        for key in ('rayStart', 'rayEnd', 'rayUp'):
                            slotDict[key] = getattr(slot, key).list()
                        for key in ('size', 'hideIfDamaged', 'type', 'isMirrored', 'isUVProportional', 'emblemId', 'slotId',
                                    'applyToFabric'):
                            slotDict[key] = getattr(slot, key)
                        data[partName]['emblemSlots'].append(slotDict)
            except StandardError:
                SystemMessages.pushMessage(
                    'temp_SM' + g_config.i18n['UI_flash_remodCreate_error'], SystemMessages.SM_TYPE.Warning)
                traceback.print_exc()
        else:
            self.py_sendMessage('', '', 'vehicleAdd', 'notSupported')
        modelDesc = getattr(appearance._HangarVehicleAppearance__vDesc, 'modelDesc', None)
        if modelDesc is not None:
            return {'isRemod': True, 'name': modelDesc['name'], 'message': modelDesc['message'], 'vehicleName': vehName,
                    'whitelist': modelDesc['whitelist'], 'ally': g_config.settings[modelDesc['name']]['ally'],
                    'enemy': g_config.settings[modelDesc['name']]['enemy'],
                    'player': g_config.settings[modelDesc['name']]['player']}
        else:
            return {'isRemod': False, 'name': '', 'message': '', 'vehicleName': vehName, 'ally': False, 'enemy': False,
                    'player': True, 'whitelist': [vehName] if vehName else []}

    @staticmethod
    def py_onShowRemod(remodName):
        g_config.previewRemod = remodName
        refreshCurrentVehicle()

    def py_onModelRestore(self):
        g_config.previewRemod = None
        refreshCurrentVehicle()

    @staticmethod
    def getCurrentAppearance():
        return g_config.hangarSpace.space.getVehicleEntity().appearance

    @staticmethod
    def py_getCurrentVehicleName():
        vDesc = RemodEnablerUI.getCurrentAppearance()._HangarVehicleAppearance__vDesc
        if vDesc is not None:
            return vDesc.name.split(':')[1].lower()
        else:
            return None

    def py_onRequestRemodDelete(self, vehicleName, remodName):
        showI18nDialog(
            g_config.i18n['UI_flash_WLVehDelete_header'], g_config.i18n['UI_flash_WLVehDelete_text'], 'common/confirm',
            partial(self.flashObject.as_onRemodDeleteConfirmed, vehicleName, remodName))

    def py_onSaveSettings(self, settings, cache):
        g_config.settings = settings = self.objToDict(settings)
        g_config.modelsData['selected'] = cache = self.objToDict(cache)
        loadJson(g_config.ID, 'remodsCache', cache, g_config.configPath, True, quiet=not g_config.data['isDebug'])
        loadJson(g_config.ID, 'settings', settings, g_config.configPath, True, quiet=not g_config.data['isDebug'])
        g_config.readCurrentSettings(not g_config.data['isDebug'])
        refreshCurrentVehicle()

    def py_onCreateRemod(self, settings):
        try:
            if not settings.name:
                SystemMessages.pushMessage('temp_SM' + g_config.i18n['UI_flash_remodCreate_name_empty'],
                                           SystemMessages.SM_TYPE.Warning)
                return
            from collections import OrderedDict
            data = self.newRemodData
            data['message'] = settings.message
            for team in g_config.teams:
                data[team] = getattr(settings, team)
            data['whitelist'] = settings.whitelist
            loadJson(g_config.ID, str(settings.name), data, g_config.configPath + 'remods/', True, False, sort_keys=False)
            g_config.readCurrentSettings()
            SystemMessages.pushMessage(
                'temp_SM' + g_config.i18n['UI_flash_remodCreate_success'], SystemMessages.SM_TYPE.CustomizationForGold)
        except StandardError:
            SystemMessages.pushMessage(
                'temp_SM' + g_config.i18n['UI_flash_remodCreate_error'], SystemMessages.SM_TYPE.Warning)
            traceback.print_exc()

    @staticmethod
    def py_sendMessage(vehicleName, remodName, action, status):
        SystemMessages.pushMessage(
            'temp_SM' + g_config.i18n['UI_flash_%s_%s' % (action, status)] % (remodName, vehicleName),
            SystemMessages.SM_TYPE.CustomizationForGold)

    def onWindowClose(self):
        self.py_onModelRestore()
        self.destroy()


def _asdict(obj):
    if isinstance(obj, SplineConfig):
        result = OrderedDict()
        result['segmentModelSets'] = OrderedDict((setName, OrderedDict((
            ('left', obj.segmentModelLeft(setName)),
            ('right', obj.segmentModelRight(setName)),
            ('secondLeft', obj.segment2ModelLeft(setName)),
            ('secondRight', obj.segment2ModelRight(setName))))) for setName in sorted(obj._SplineConfig__segmentModelSets))
        for attrName in obj.__slots__[1:]:
            attrName = attrName.strip('_')
            result[attrName] = getattr(obj, attrName)
        return result
    elif hasattr(obj, '_fields'):
        return OrderedDict(zip(obj._fields, (_asdict(x) for x in obj)))
    elif isinstance(obj, (Math.Vector3, Math.Vector2)):
        return obj.list()
    elif isinstance(obj, (list, tuple)):
        return [_asdict(x) for x in obj]
    else:
        return obj


def inj_hkKeyEvent(event):
    LobbyApp = g_appLoader.getDefLobbyApp()
    try:
        if LobbyApp and g_config.data['enabled']:
            g_config.lobbyKeyControl(event)
    except StandardError:
        print g_config.ID + ': ERROR at inj_hkKeyEvent'
        traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent
g_config = ConfigInterface()


@overrideMethod(LoginView, '_populate')
def new_Login_populate(base, self):
    base(self)
    g_config.isInHangar = False


@overrideMethod(LobbyView, '_populate')
def new_Lobby_populate(base, self):
    base(self)
    g_config.isInHangar = True
