# -*- coding: utf-8 -*-
import BigWorld
import Keys
import ResMgr
import traceback
from PYmodsCore import PYmodsConfigInterface, checkKeys, loadJson, objToDict, refreshCurrentVehicle, remDups
from PYmodsCore.delayed import g_modsListApi, showI18nDialog
from functools import partial
from gui import SystemMessages as SM
from gui.Scaleform.framework import ScopeTemplates as ST, ViewSettings, WindowLayer as WL, g_entitiesFactories
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.personality import ServicesLocator as SL
from items.components.component_constants import ALLOWED_EMBLEM_SLOTS as AES, ALLOWED_MISC_SLOTS as AMS
from items.vehicles import _VEHICLE_TYPE_XML_PATH
from items.writers.c11n_writers import ComponentXmlSerializer
from vehicle_systems.tankStructure import TankPartNames
from . import __date__, __modID__


class ConfigInterface(PYmodsConfigInterface):
    teams = ('player', 'ally', 'enemy')

    def __init__(self):
        self.settings = {}
        self.modelsData = {}
        self.selectedData = {k: {} for k in self.teams}
        self.emptyModelDesc = None
        self.isModAdded = False
        self.currentTeam = self.teams[0]
        self.previewRemod = None
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = __modID__
        self.version = '3.2.0 (%s)' % __date__
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
            'UI_flash_header_tooltip': (
                "Extended setup for RemodEnabler by <font color='#DD7700'><b>Polyacov_Yury</b></font>"),
            'UI_flash_header_simple': 'Remods for ',
            'UI_flash_header_main': 'Advanced settings',
            'UI_flash_header_setup': 'Remods setup',
            'UI_flash_header_create': 'Create remod',
            'UI_flash_remodSetupBtn': 'Remods setup',
            'UI_flash_remodCreateBtn': 'Create remod',
            'UI_flash_remodCreate_name_text': 'Remod name',
            'UI_flash_remodCreate_name_tooltip': 'Remod unique ID and config file name.',
            'UI_flash_remodCreate_message_text': 'Author message',
            'UI_flash_remodCreate_message_tooltip': (
                'This message is displayed in hangar every time the remod is selected.\nLeave blank if not required.'),
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
            'UI_flash_vehicleAdd_notSupported': (
                'Vehicle can\'t be added to <b>%s</b> whitelist:%s is not supported by RemodEnabler.'),
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
        self.modelsData.clear()
        self.selectedData = loadJson(self.ID, 'remodsCache', self.selectedData, self.configPath)
        self.readConfigDir(quiet, recursive=True, dir_name='remods', ext='.xml')
        changed_xmlNames = set()
        for remod_name in self.settings.keys():
            if remod_name not in self.modelsData:
                del self.settings[remod_name]
            else:
                changed_xmlNames.update(self.settings[remod_name]['whitelist'])

        if not self.modelsData:
            if not quiet:
                print self.LOG, 'no configs found, model module standing down.'
        for team, teamData in self.selectedData.items():
            for xmlName in teamData.keys():
                if xmlName not in changed_xmlNames:
                    teamData.pop(xmlName)
                    continue
                remod_name = teamData[xmlName]
                if remod_name and remod_name not in self.modelsData:
                    teamData[xmlName] = remod_name = next(
                        (name for name in sorted(self.modelsData) if remod_name in name), None)
                if remod_name is None or (remod_name and remod_name not in self.modelsData):
                    teamData[xmlName] = next(
                        (name for name in sorted(self.modelsData)
                         if xmlName in self.settings[name]['whitelist'] and self.settings[name][team]),
                        None) or ''
        loadJson(self.ID, 'remodsCache', self.selectedData, self.configPath, True, quiet=quiet)
        loadJson(self.ID, 'settings', self.settings, self.configPath, True, quiet=quiet)

    def onReadDataSection(self, quiet, path, dir_path, name, data_section, sub_dirs, names):
        from .readers import readModelDesc, ModelDesc
        if self.emptyModelDesc is None:
            self.emptyModelDesc = ModelDesc()
            self.emptyModelDesc.chassis.generalWheelsAnimatorConfig = ''  # has to not be None
        remod_name = (dir_path and (dir_path + '/')) + name
        modelDesc = ModelDesc()
        modelDesc.name = remod_name
        readModelDesc((None, remod_name), data_section, modelDesc)
        self.modelsData[remod_name] = modelDesc  # don't put it there right away
        old_settings = None
        old_setting_names = [_name for _name in self.settings if _name == name]
        if old_setting_names and remod_name not in old_setting_names:
            if len(old_setting_names) > 1:
                print self.LOG, 'multiple settings for remod', remod_name + ':', old_setting_names,
                print 'skipping settings migration'
            else:
                old_settings = self.settings.pop(old_setting_names[0])
        settings = self.settings.setdefault(
            remod_name, old_settings or {team: getattr(modelDesc, team) for team in self.teams})
        settings['whitelist'] = modelDesc.whitelist = whitelist = remDups(
            x.strip() for x in settings.get('whitelist', modelDesc.whitelist) if x.strip())
        for xmlName in whitelist:
            for team in self.selectedData:
                if xmlName not in self.selectedData[team] or self.selectedData[team][xmlName] is None:
                    self.selectedData[team][xmlName] = remod_name if settings[team] else None
        if self.data['isDebug']:
            print self.LOG, 'whitelist for', remod_name + ':', whitelist

    def migrateConfigs(self):
        from .migrators import migrateConfigs
        migrateConfigs(self)
        self.readConfigDir(False, recursive=True, dir_name='remods', ordered=True, migrate=True)

    def onMigrateConfig(self, quiet, path, dir_path, name, json_data, sub_dirs, names):
        from .migrators import migrateRemod
        migrateRemod(self, path, name, json_data)

    def findModelDesc(self, xmlName, currentTeam, forPreview=False):
        if not self.modelsData:
            return
        selected = self.selectedData[currentTeam]
        if self.previewRemod and forPreview:
            return self.modelsData[self.previewRemod]
        if xmlName not in selected or not selected[xmlName]:
            return
        return self.modelsData[selected[xmlName]]

    def registerSettings(self):
        super(ConfigInterface, self).registerSettings()
        # noinspection PyArgumentList
        g_entitiesFactories.addSettings(ViewSettings(
            'RemodEnablerUI', RemodEnablerUI, 'RemodEnabler.swf', WL.WINDOW, None, ST.GLOBAL_SCOPE, False, isModal=True))
        self.isModAdded = g_modsListApi.addModification(
            id='RemodEnablerUI', name=self.i18n['UI_flash_header'], description=self.i18n['UI_flash_header_tooltip'],
            icon='gui/flash/RemodEnabler.png', enabled=self.data['enabled'], login=False, lobby=True, callback=lambda: (
                    SL.appLoader.getDefLobbyApp().containerManager.getContainer(WL.TOP_WINDOW).getViewCount()
                    or SL.appLoader.getDefLobbyApp().loadView(SFViewLoadParams('RemodEnablerUI')))) != NotImplemented

    def onHotkeyPressed(self, event):
        if (not hasattr(BigWorld.player(), 'databaseID') or not event.isKeyDown()
                or not self.data['enabled'] or not self.modelsData or self.previewRemod or self.isMSAOpen):
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
            names = sorted(self.modelsData.keys()) + ['']
            selected = self.selectedData[self.currentTeam]
            vehName = RemodEnablerUI.py_getCurrentVehicleName()
            if vehName not in selected:
                return
            current_idx = (names.index(selected[vehName]) + 1) % (len(names))
            for name in names[current_idx:]:
                if not name or vehName in self.settings[name]['whitelist']:
                    selected[vehName] = name
                    break
            else:
                selected[vehName] = ''
            loadJson(self.ID, 'remodsCache', self.selectedData, self.configPath, True, quiet=not self.data['isDebug'])
            refreshCurrentVehicle()


class RemodEnablerUI(AbstractWindowView):
    def __init__(self, ctx=None):
        super(RemodEnablerUI, self).__init__(ctx)
        self.newRemodData = None

    def _populate(self):
        super(RemodEnablerUI, self)._populate()
        SL.hangarSpace.onVehicleChanged += self.onVehicleReloaded

    def _dispose(self):
        SL.hangarSpace.onVehicleChanged -= self.onVehicleReloaded
        super(RemodEnablerUI, self)._dispose()

    def onVehicleReloaded(self):
        vehicleName = self.py_getCurrentVehicleName()
        if vehicleName is not None:
            self.flashObject.as_onVehicleReloaded(vehicleName)

    def py_onRequestSettings(self):
        g_config.readCurrentSettings(not g_config.data['isDebug'])
        texts = {k[9:]: v for k, v in g_config.i18n.iteritems() if k.startswith('UI_flash_')}
        return texts, g_config.settings, g_config.selectedData, self.py_getCurrentVehicleName()

    def py_checkSettings(self, settings, cache):
        settings = objToDict(settings)
        cache = objToDict(cache)
        if g_config.settings == settings and g_config.selectedData == cache:
            return True
        showI18nDialog(
            g_config.i18n['UI_flash_unsaved_header'], g_config.i18n['UI_flash_unsaved_text'], 'common/confirm',
            lambda confirm: (
                (self.py_onSaveSettings(settings, cache) if confirm else None), self.flashObject.as_onSettingsChecked()))
        return False

    @staticmethod
    def py_showRemod(remodName):
        if g_config.previewRemod != remodName:
            g_config.previewRemod = remodName
            refreshCurrentVehicle()

    @staticmethod
    def py_getCurrentVehicleName():
        entity = SL.hangarSpace.getVehicleEntity()
        vDesc = entity and entity.typeDescriptor
        return vDesc and vDesc.name.split(':')[1].lower()

    def py_onRequestRemodDelete(self, vehicleName, remodName):
        showI18nDialog(
            g_config.i18n['UI_flash_WLVehDelete_header'], g_config.i18n['UI_flash_WLVehDelete_text'], 'common/confirm',
            partial(self.flashObject.as_onRemodDeleteConfirmed, vehicleName, remodName))

    def py_onSaveSettings(self, settings, cache):
        g_config.settings = settings = objToDict(settings)
        g_config.selectedData = cache = objToDict(cache)
        loadJson(g_config.ID, 'remodsCache', cache, g_config.configPath, True, quiet=not g_config.data['isDebug'])
        loadJson(g_config.ID, 'settings', settings, g_config.configPath, True, quiet=not g_config.data['isDebug'])
        g_config.readCurrentSettings(not g_config.data['isDebug'])
        refreshCurrentVehicle()

    @staticmethod
    def py_sendMessage(vehicleName, remodName, action, status):
        SM.pushMessage(
            'temp_SM' + g_config.i18n['UI_flash_%s_%s' % (action, status)] % (remodName, vehicleName),
            SM.SM_TYPE.CustomizationForGold)

    def onWindowClose(self):
        self.py_showRemod(None)
        self.destroy()

    @staticmethod
    def py_printLog(*args):
        for arg in args:
            print arg

    def py_getRemodData(self):
        entity = SL.hangarSpace.getVehicleEntity()
        appearance = entity and entity.appearance
        vDesc = entity and entity.typeDescriptor
        vehName = vDesc and vDesc.name.split(':')[1].lower()
        default = dict(
            name='', message='', vehicleName=vehName, whitelist=[vehName] if vehName else [],
            **{k: i == 0 for i, k in enumerate(g_config.teams)})
        if not vehName:
            self.py_sendMessage('', '', 'vehicleAdd', 'notSupported')
            return default
        modelDesc = vDesc.chassis.modelsSets.get('RemodEnabler_modelDesc', None)
        if modelDesc is not None:
            remod_name = modelDesc.name
            self.newRemodData = ResMgr.openSection('.' + g_config.configPath + 'remods/' + remod_name + '.xml')
            return dict(
                name=remod_name, message=modelDesc.message, vehicleName=vehName, whitelist=modelDesc.whitelist,
                **{k: g_config.settings[remod_name][k] for k in g_config.teams})
        try:
            orig_data = ResMgr.openSection(_VEHICLE_TYPE_XML_PATH + '/'.join(vDesc.name.split(':')) + '.xml')
            data = self.newRemodData = ResMgr.DataSection()
            data.writeString('message', default['message'])
            data.write('message', default['message'])
            for k in g_config.teams:
                data.writeBool(k, default[k])
            data.writeString('whitelist', ' '.join(default['whitelist']))
            outfit = appearance.outfit
            modelsSet = outfit.modelsSet or 'default'
            for partName, sectNames, path in zip((
                    TankPartNames.ALL + ('engine',)
            ), (
                    ('traces', 'tracks', 'wheels', 'drivingWheels', 'hullPosition', 'topRightCarryingPoint', 'AODecals',
                     'groundNodes', 'splineDesc', 'trackThickness', 'trackNodes', 'leveredSuspension', 'physicalTracks'),
                    ('hangarShadowTexture', 'AODecals', 'exhaust'),
                    ('multiGun', 'showEmblemsOnGun', 'AODecals', 'ceilless',
                     'wwturretRotatorSoundManual', 'turretDetachmentEffects'),
                    ('animateEmblemSlots', 'drivenJoints', 'effects', 'reloadEffect', 'impulse', 'recoil'),
                    (),
            ), (
                    'chassis/' + vDesc.chassis.name,
                    'hull',
                    'turrets0/' + vDesc.turret.name,
                    'turrets0/' + vDesc.turret.name + '/guns/' + vDesc.gun.name,
                    '',
            )):
                part = data.createSection(partName)
                orig_part = orig_data[path]
                for sectName in sectNames and ('undamaged', 'destroyed', 'exploded'):
                    part.writeString('models/' + sectName, getattr(getattr(vDesc, partName).modelsSets[modelsSet], sectName))
                for sectName in sectNames and (sectNames + ('emblemSlots', 'customizationSlots', 'camouflage')):
                    orig = orig_part[sectName]
                    if orig is None:  # DO NOT BOOL-TEST THIS
                        continue
                    desc = part.createSection(sectName)
                    desc.copy(orig)
                    if sectName == 'splineDesc':
                        modelSets = orig['modelSets']
                        if modelsSet != 'default' and modelSets is not None:
                            modelSet = modelSets[modelsSet]
                            if modelSet is not None:
                                for n in ('segmentModelLeft', 'segmentModelRight', 'segment2ModelLeft', 'segment2ModelRight'):
                                    if modelSet.has_key(n):
                                        (desc.createSection(n) if not desc.has_key(n) else desc[n]).copy(modelSet[n])
                                    elif desc.has_key(n):
                                        desc.deleteSection(n)
                        if desc.has_key('modelSets'):
                            desc.deleteSection('modelSets')
                    if sectName == 'physicalTracks':
                        for sect in desc.values():
                            modelSets = sect['modelSets']
                            if modelSets is not None:
                                modelSet = modelSets[modelsSet]
                                if modelSet is not None:
                                    sect['mainSegment']['model'].copy(modelSet['mainSegmentModel'])
                                sect.deleteSection(modelSets)
                    if sectName == 'customizationSlots':
                        for sect in list(desc.values()):
                            if sect.readString('slotType') not in AES + AMS:
                                desc.deleteSection(sect)
                    if not desc.asString and not desc.values():
                        part.deleteSection(desc)
                if partName != 'hull':
                    part.writeString('soundID', vDesc.name.split(':')[0] + ':' + getattr(vDesc, partName).name)
            hide_materials = []
            level = outfit.progressionLevel
            if level != 0:
                outfit = appearance._HangarVehicleAppearance__getStyleProgressionOutfitData(outfit)
                for levelId, levelConfig in outfit.style.styleProgressions.iteritems():
                    if levelId != level:
                        hide_materials.extend(levelConfig.get('materials', []))
            newOutfit = outfit.__class__(vehicleCD=outfit.vehicleCD)
            for itemTypeID in (GUI_ITEM_TYPE.ATTACHMENT, GUI_ITEM_TYPE.SEQUENCE):
                newOutfit.misc.setSlotFor(itemTypeID, outfit.misc.slotFor(itemTypeID))
            if not newOutfit.isEmpty() or hide_materials:
                part = data.createSection('outfit')
                if not newOutfit.isEmpty():
                    component = newOutfit.pack()
                    component.styleProgressionLevel = 0
                    ComponentXmlSerializer().encode(part, component)
                    for desc in part.values():
                        if not desc.keys():
                            part.deleteSection(desc)
                if hide_materials:
                    part.writeString('hide_materials', ' '.join(hide_materials))
        except StandardError:
            SM.pushMessage('temp_SM' + g_config.i18n['UI_flash_remodCreate_error'], SM.SM_TYPE.Warning)
            traceback.print_exc()
        return default

    def py_onCreateRemod(self, settings):
        try:
            if not settings.name:
                SM.pushMessage('temp_SM' + g_config.i18n['UI_flash_remodCreate_name_empty'], SM.SM_TYPE.Warning)
                return
            from collections import OrderedDict
            data = self.newRemodData
            data.writeString('message', settings.message)
            for team in g_config.teams:
                data.writeBool(team, getattr(settings, team))
            data.writeString('whitelist', ' '.join(settings.whitelist))
            temp = ResMgr.DataSection()
            temp.copy(data)
            new_data = ResMgr.openSection('.' + g_config.configPath + 'remods/' + settings.name + '.xml', True)
            new_data.copy(temp)
            new_data.save()
            g_config.readCurrentSettings()
            SM.pushMessage('temp_SM' + g_config.i18n['UI_flash_remodCreate_success'], SM.SM_TYPE.CustomizationForGold)
        except StandardError:
            SM.pushMessage('temp_SM' + g_config.i18n['UI_flash_remodCreate_error'], SM.SM_TYPE.Warning)
            traceback.print_exc()


g_config = ConfigInterface()
