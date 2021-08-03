# -*- coding: utf-8 -*-
import BigWorld
import Keys
import Math
import traceback
from PYmodsCore import PYmodsConfigInterface, refreshCurrentVehicle, checkKeys, loadJson, remDups, objToDict
from PYmodsCore.delayed import showI18nDialog, g_modsListApi
from collections import OrderedDict
from functools import partial
from gui import SystemMessages as SM
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, WindowLayer, g_entitiesFactories
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.shared.personality import ServicesLocator as SL
from helpers import dependency
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
    teams = ('player', 'ally', 'enemy')
    # noinspection PyUnusedLocal
    modelDescriptor = property(lambda self: {
        'name': '', 'message': '', 'whitelist': [],
        'chassis': {'undamaged': '', 'emblemSlots': [], 'AODecals': [], 'hullPosition': [], 'soundID': ''},
        'hull': {'undamaged': '', 'emblemSlots': [], 'exhaust': {'nodes': [], 'pixie': ''},
                 'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
        'turret': {'undamaged': '', 'emblemSlots': [],
                   'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
        'gun': {'undamaged': '', 'emblemSlots': [], 'soundID': '', 'drivenJoints': None,
                'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
        'engine': {'soundID': ''},
        'common': {'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}}})

    def __init__(self):
        self.settings = {}
        self.modelsData = {'models': {}, 'selected': {'player': {}, 'ally': {}, 'enemy': {}}}
        self.isModAdded = False
        self.currentTeam = self.teams[0]
        self.previewRemod = None
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = __modID__
        self.version = '3.1.0 (%s)' % __date__
        self.author += ' (thx to atacms)'
        self.defaultKeys = {
            'ChangeViewHotkey': [Keys.KEY_F2, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
            'SwitchRemodHotkey': [Keys.KEY_F3, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
        }
        self.data = {
            'enabled': True,
            'isDebug': True,
            'ChangeViewHotkey': self.defaultKeys['ChangeViewHotkey'],
            'SwitchRemodHotkey': self.defaultKeys['SwitchRemodHotkey']
        }
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
                'This hotkey will switch the preview mode in hangar.\n<b>Available modes:</b>\n'
                ' • Player tank\n • Ally tank\n • Enemy tank'),
            'UI_setting_SwitchRemodHotkey_text': 'Remod switch hotkey',
            'UI_setting_SwitchRemodHotkey_tooltip': 'This hotkey will cycle through all remods.',
            'UI_install_customization': '<b>RemodEnabler:</b>\nRemods are not displayed when customization is open.',
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
        return {
            'modDisplayName': self.i18n['UI_description'], 'enabled': self.data['enabled'],
            'column1': [
                self.tb.createHotKey('ChangeViewHotkey'),
                self.tb.createControl('isDebug'),
            ],
            'column2': [
                self.tb.createHotKey('SwitchRemodHotkey'),
            ]}

    @property
    def collisionMode(self):
        try:
            from gui.mods.mod_hangarcollision import g_config as hc_config
            return hc_config.collisionMode
        except ImportError:
            return 0

    def onMSADestroy(self):
        refreshCurrentVehicle()

    def onApplySettings(self, settings):
        super(ConfigInterface, self).onApplySettings(settings)
        if self.isModAdded:
            g_modsListApi.updateModification(id='RemodEnablerUI', enabled=self.data['enabled'])

    def readCurrentSettings(self, quiet=True):
        self.settings = loadJson(self.ID, 'settings', self.settings, self.configPath)
        self.modelsData['models'].clear()
        self.modelsData['selected'] = selectedData = loadJson(
            self.ID, 'remodsCache', self.modelsData['selected'], self.configPath)
        self.readConfigDir(quiet, recursive=True, dir_name='remods')
        changed_xmlNames = set()
        for remod_name in self.settings.keys():
            if remod_name not in self.modelsData['models']:
                del self.settings[remod_name]
            else:
                changed_xmlNames.update(self.settings[remod_name]['whitelist'])

        if not self.modelsData['models']:
            if not quiet:
                print self.LOG, 'no configs found, model module standing down.'
        for team, teamData in selectedData.items():
            for xmlName in teamData.keys():
                if xmlName not in changed_xmlNames:
                    teamData.pop(xmlName)
                    continue
                remod_name = teamData[xmlName]
                if remod_name and remod_name not in self.modelsData['models']:
                    teamData[xmlName] = remod_name = next(
                        (name for name in sorted(self.modelsData['models']) if remod_name in name), None)
                if remod_name is None or (remod_name and remod_name not in self.modelsData['models']):
                    teamData[xmlName] = next(
                        (name for name in sorted(self.modelsData['models'])
                         if xmlName in self.settings[name]['whitelist'] and self.settings[name][team]),
                        None) or ''
        loadJson(self.ID, 'remodsCache', selectedData, self.configPath, True, quiet=quiet)
        loadJson(self.ID, 'settings', self.settings, self.configPath, True, quiet=quiet)

    # noinspection PyTypeChecker
    def onReadConfig(self, quiet, dir_path, name, json_data, sub_dirs, names):
        remod_name = (dir_path and (dir_path + '/')) + name
        selectedData = self.modelsData['selected']
        old_settings = None
        old_setting_names = [_name for _name in self.settings if _name == name]
        if old_setting_names and remod_name not in old_setting_names:
            if len(old_setting_names) > 1:
                print self.LOG, 'multiple settings for remod', remod_name + ':', old_setting_names,
                print 'skipping settings migration'
            else:
                old_settings = self.settings.pop(old_setting_names[0])
        settings = self.settings.setdefault(remod_name, old_settings or {team: json_data[team] for team in self.teams})
        self.modelsData['models'][remod_name] = descr = self.modelDescriptor
        descr['name'] = remod_name
        descr['message'] = json_data.get('message', '')
        settings['whitelist'] = descr['whitelist'] = whitelist = remDups(
            x.strip() for x in settings.get('whitelist', json_data['whitelist']) if x.strip())
        for xmlName in whitelist:
            for team in selectedData:
                if xmlName not in selectedData[team] or selectedData[team][xmlName] is None:
                    selectedData[team][xmlName] = remod_name if settings[team] else None
        if self.data['isDebug']:
            print self.LOG, 'whitelist for', remod_name + ':', whitelist
        for key, data in descr.iteritems():
            if key in ('name', 'message', 'whitelist'):
                continue
            if key == 'common':
                confSubDict = json_data
            else:
                confSubDict = json_data.get(key)
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
                print self.LOG, 'default camomask not found for', remod_name
            if 'emblemSlots' in data:
                data['emblemSlots'] = slots = []
                for subDict in confSubDict.get('emblemSlots', ()):
                    if subDict['type'] not in AES:
                        print self.LOG, 'not supported emblem slot type:', subDict['type'] + ', expected:', AES
                        continue
                    subDict.update({k: Math.Vector3(subDict[k]) for k in ('rayStart', 'rayEnd', 'rayUp')})
                    slots.append(EmblemSlot(**subDict))
            if 'exhaust' in data and 'exhaust' in confSubDict:
                if 'nodes' in confSubDict['exhaust']:
                    data['exhaust']['nodes'] = confSubDict['exhaust']['nodes']
                if 'pixie' in confSubDict['exhaust']:
                    data['exhaust']['pixie'] = confSubDict['exhaust']['pixie']
            if key == 'chassis':
                for k in chassis_params + ('chassisLodDistance',):
                    data[k] = confSubDict[k]
            for k in ('soundID', 'drivenJoints'):
                if k in data and k in confSubDict:
                    data[k] = confSubDict[k]
        if self.data['isDebug']:
            print self.LOG, 'config for', remod_name, 'loaded.'

    def migrateConfigs(self):
        from .config_converter import migrateConfigs
        migrateConfigs(self)

    def findModelDesc(self, xmlName, currentTeam, forPreview=False):
        if not self.modelsData['models']:
            return
        selected = self.modelsData['selected'][currentTeam]
        if self.previewRemod and forPreview:
            return self.modelsData['models'][self.previewRemod]
        if xmlName not in selected or not selected[xmlName]:
            return
        return self.modelsData['models'][selected[xmlName]]

    def registerSettings(self):
        super(ConfigInterface, self).registerSettings()
        # noinspection PyArgumentList
        g_entitiesFactories.addSettings(
            ViewSettings('RemodEnablerUI', RemodEnablerUI, 'RemodEnabler.swf', WindowLayer.WINDOW, None,
                         ScopeTemplates.GLOBAL_SCOPE, False))
        self.isModAdded = g_modsListApi.addModification(
            id='RemodEnablerUI', name=self.i18n['UI_flash_header'], description=self.i18n['UI_flash_header_tooltip'],
            icon='gui/flash/RemodEnabler.png', enabled=self.data['enabled'], login=False, lobby=True, callback=lambda: (
                    SL.appLoader.getDefLobbyApp().containerManager.getContainer(WindowLayer.TOP_WINDOW).getViewCount()
                    or SL.appLoader.getDefLobbyApp().loadView(SFViewLoadParams('RemodEnablerUI')))) != NotImplemented

    def onHotkeyPressed(self, event):
        if (not hasattr(BigWorld.player(), 'databaseID') or not event.isKeyDown()
                or not self.data['enabled'] or not self.modelsData['models'] or self.previewRemod or self.isMSAOpen):
            return
        if checkKeys(self.data['ChangeViewHotkey'], event.key):
            newModeNum = (self.teams.index(self.currentTeam) + 1) % len(self.teams)
            self.currentTeam = self.teams[newModeNum]
            try:
                from gui.mods.mod_skinner import g_config as _
                _.currentTeam = self.currentTeam
            except ImportError:
                _ = None
            if self.data['isDebug']:
                print self.LOG, 'changing display mode to', self.currentTeam
            SM.pushMessage(
                'temp_SM%s<b>%s</b>' % (self.i18n['UI_mode'], self.i18n['UI_mode_' + self.currentTeam]),
                SM.SM_TYPE.Warning)
            refreshCurrentVehicle()
        if checkKeys(self.data['SwitchRemodHotkey'], event.key):
            curTankType = self.currentTeam
            snameList = sorted(self.modelsData['models'].keys()) + ['']
            selected = self.modelsData['selected'][curTankType]
            vehName = RemodEnablerUI.py_getCurrentVehicleName()
            if vehName not in selected:
                return
            snameIdx = (snameList.index(selected[vehName]) + 1) % len(snameList)
            for Idx in xrange(snameIdx, len(snameList) - 1):
                if vehName not in self.settings[snameList[Idx]]['whitelist']:
                    continue
                selected[vehName] = snameList[Idx]
                break
            else:
                selected[vehName] = ''
            loadJson(self.ID, 'remodsCache', self.modelsData['selected'], self.configPath, True, quiet=not self.data['isDebug'])
            refreshCurrentVehicle()


class RemodEnablerUI(AbstractWindowView):
    def _populate(self):
        super(RemodEnablerUI, self)._populate()
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
        settings = objToDict(settings)
        cache = objToDict(cache)
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
        if not vehName:
            self.py_sendMessage('', '', 'vehicleAdd', 'notSupported')
        else:
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
                    obj = _asDict(getattr(vDesc.chassis, key))
                    chassis[key] = obj
                modelsSets = chassis['splineDesc']['segmentModelSets']
                chassis['splineDesc']['segmentModelSets'] = modelsSets.get(modelsSet, modelsSets['default'])
                chassis['hullPosition'] = vDesc.chassis.hullPosition.list()
                chassis['AODecals'] = [[[decal.get(strIdx, colIdx) for colIdx in xrange(3)] for strIdx in xrange(4)]
                                       for decal in vDesc.chassis.AODecals]
                for partName in ('gun', 'chassis', 'engine'):
                    data[partName]['soundID'] = getattr(vDesc, partName).name
                data['gun']['drivenJoints'] = vDesc.gun.drivenJoints
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
                    data[partName]['emblemSlots'] = [_asDict(slot) for slot in part.emblemSlots]
            except StandardError:
                SM.pushMessage('temp_SM' + g_config.i18n['UI_flash_remodCreate_error'], SM.SM_TYPE.Warning)
                traceback.print_exc()
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
        g_config.settings = settings = objToDict(settings)
        g_config.modelsData['selected'] = cache = objToDict(cache)
        loadJson(g_config.ID, 'remodsCache', cache, g_config.configPath, True, quiet=not g_config.data['isDebug'])
        loadJson(g_config.ID, 'settings', settings, g_config.configPath, True, quiet=not g_config.data['isDebug'])
        g_config.readCurrentSettings(not g_config.data['isDebug'])
        refreshCurrentVehicle()

    def py_onCreateRemod(self, settings):
        try:
            if not settings.name:
                SM.pushMessage('temp_SM' + g_config.i18n['UI_flash_remodCreate_name_empty'], SM.SM_TYPE.Warning)
                return
            from collections import OrderedDict
            data = self.newRemodData
            data['message'] = settings.message
            for team in g_config.teams:
                data[team] = getattr(settings, team)
            data['whitelist'] = settings.whitelist
            loadJson(g_config.ID, str(settings.name), data, g_config.configPath + 'remods/', True, False, sort_keys=False)
            g_config.readCurrentSettings()
            SM.pushMessage('temp_SM' + g_config.i18n['UI_flash_remodCreate_success'], SM.SM_TYPE.CustomizationForGold)
        except StandardError:
            SM.pushMessage('temp_SM' + g_config.i18n['UI_flash_remodCreate_error'], SM.SM_TYPE.Warning)
            traceback.print_exc()

    @staticmethod
    def py_sendMessage(vehicleName, remodName, action, status):
        SM.pushMessage(
            'temp_SM' + g_config.i18n['UI_flash_%s_%s' % (action, status)] % (remodName, vehicleName),
            SM.SM_TYPE.CustomizationForGold)

    def onWindowClose(self):
        self.py_onModelRestore()
        self.destroy()

    @staticmethod
    def py_printLog(*args):
        for arg in args:
            print arg


def _asDict(obj):
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
        return OrderedDict(zip(obj._fields, (_asDict(x) for x in obj)))
    elif isinstance(obj, (Math.Vector3, Math.Vector2)):
        return obj.list()
    elif isinstance(obj, (list, tuple)):
        return [_asDict(x) for x in obj]
    else:
        return obj


g_config = ConfigInterface()
