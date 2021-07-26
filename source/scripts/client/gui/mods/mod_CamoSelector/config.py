# coding=utf-8
import nations
import os
from CurrentVehicle import g_currentVehicle
from PYmodsCore import Analytics, PYmodsConfigInterface, loadJson, overrideMethod, refreshCurrentVehicle
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from items import _xml as ix, makeIntCompactDescrByID as makeCD, vehicles as iv
from items.components import c11n_components as cc, c11n_constants as consts, shared_components as sc
from items.readers.c11n_readers import __xmlReaders as def_readers
from . import __date__, __modID__, migrator
from .constants import CUSTOM_GROUP_NAME, SEASON_NAME_TO_TYPE, STARTER_ITEM_ID


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.disabledVehicles = []
        self.camoForSeason = {}
        self.arenaCamoCache = {}
        self.hangarCamoCache = {}
        self.outfitCache = {}
        self.camo_settings = {'remap': {}, 'custom': {}}
        self.teamCamo = dict.fromkeys(('ally', 'enemy'))
        self.internationalCamoIDs = []
        self.modded_readers = {cls: def_readers[cls] for cls in (
            cc.PaintItem, cc.DecalItem, cc.ProjectionDecalItem, cc.ModificationItem)}
        self.modded_readers[ModdedCamouflageItem] = def_readers[cc.CamouflageItem]
        self.allowed_types = {cls.itemType: cls for cls in self.modded_readers}
        self.allowed_names = tuple(k.lower() for k, v in consts.CustomizationNamesToTypes.items() if v in self.allowed_types)
        self.modded_items = {itemType: {} for itemType in self.allowed_types}
        self.modded_groups = {}
        self.modded_lookup_name = {itemType: {} for itemType in self.allowed_types}
        self.defaults = {
            'random_enabled': True, 'random_team': False, 'ally': True, 'enemy': True, 'season': SEASONS_CONSTANTS.SEASONS[:]}
        super(ConfigInterface, self).__init__()

    def isCamoGlobal(self, camo):
        return camo.id in self.internationalCamoIDs

    def getOutfitCache(self):
        nation, vehicle = g_currentVehicle.item.descriptor.name.split(':')
        return self.outfitCache.get(nation, {}).get(vehicle, {})

    def getHangarCache(self):
        nation, vehicle = g_currentVehicle.item.descriptor.name.split(':')
        return self.hangarCamoCache.get(nation, {}).get(vehicle, {})

    def getItemKeys(self, itemID, item):
        return ('custom', item.i18n.longDescriptionSpecialKey) if item.priceGroup == CUSTOM_GROUP_NAME else ('remap', itemID)

    def getCamoSettings(self, itemsKey, itemName):
        return self.camo_settings[itemsKey].get(itemName, {})

    def init(self):
        self.ID = __modID__
        self.version = '3.1.0 (%s)' % __date__
        self.author += ' (thx to tratatank, Blither!)'
        self.data = {
            'enabled': True, 'doRandom': True, 'useBought': True, 'hangarCamoKind': 0, 'fullAlpha': False,
            'disableWithDefault': False, 'fillEmptySlots': True, 'uniformOutfit': False}
        self.i18n = {
            'UI_description': 'Camouflage selector',
            'flash_switcher_buy': 'PURCHASE',
            'flash_switcher_install': 'INSTALL',
            'flashCol_progressionDecal_changeMode_title': 'Mode change',
            'flashCol_progressionDecal_changeMode_message': (
                'Current style can not be edited.\n'
                'If you proceed, you will be moved to custom mode\'s decal tab.\nDo you want to continue?'),
            'flashCol_freeVersion_title': 'CamoSelector: free version',
            'flashCol_freeVersion_message': (
                'You are using the free version.\n'
                'Install mode is only capable of installing items added into the game using config files\n'
                'and elements available for purchase for current vehicle.\n'
                'Patreon/Boosty subscribers have access to the extended version,\n'
                'which is able to install ANY customization elements for free.'),
            'flash_freeVersion_button_boosty': 'Open Boosty in browser',
            'flash_freeVersion_button_close': 'Close',
            'flash_freeVersion_button_patreon': 'Open Patreon in browser',
            'flashCol_group_multinational': 'Multinational',
            'flashCol_group_custom': 'Custom',
            'flashCol_group_separator': ' / ',
            'flashCol_serviceMessage_settings': 'Customization element settings changed.',
            'contextMenu_season_group': 'Season remap',
            'contextMenu_season_summer': 'Apply for summer',
            'contextMenu_season_summer_remove': 'Remove from summer',
            'contextMenu_season_winter': 'Apply for winter',
            'contextMenu_season_winter_remove': 'Remove from winter',
            'contextMenu_season_desert': 'Apply for desert',
            'contextMenu_season_desert_remove': 'Remove from desert',
            'contextMenu_selectionMode_group': 'Current selection mode: ',
            'contextMenu_selectionMode_change': 'Change to ',
            'contextMenu_selectionMode_off': 'Disabled',
            'contextMenu_selectionMode_random': 'Random',
            'contextMenu_selectionMode_team': 'Team',
            'contextMenu_team_group': 'Team selection',
            'contextMenu_team_ally': 'Apply for allies',
            'contextMenu_team_ally_remove': 'Remove from allies',
            'contextMenu_team_enemy': 'Apply for enemies',
            'contextMenu_team_enemy_remove': 'Remove from enemies',
            'UI_setting_doRandom_text': 'Select random camouflages',
            'UI_setting_doRandom_tooltip': (
                'If enabled, mod will select a random available camouflage if no other option is provided.'),
            'UI_setting_useBought_text': 'Use bought camouflages in battle',
            'UI_setting_useBought_tooltip': "If enabled, mod will preserve bought camouflages on other players' tanks.",
            'UI_setting_disableWithDefault_text': 'Disable for vehicles with default camouflage',
            'UI_setting_disableWithDefault_tooltip': 'If enabled, mod will ignore vehicles with a default camouflage.',
            'UI_setting_fullAlpha_text': 'Non-transparent custom camouflages',
            'UI_setting_fullAlpha_tooltip': 'If enabled, all custom camouflages lose their transparency.\n'
                                            'Some call this "dirt-less skins".',
            'UI_setting_fillEmptySlots_text': 'Fill empty slots',
            'UI_setting_fillEmptySlots_tooltip': 'Add random camouflages if a vehicle has empty slots for them.',
            'UI_setting_uniformOutfit_text': 'Same look for all parts',
            'UI_setting_uniformOutfit_tooltip':
                'Random camouflages are picked up so that a vehicle has the same camouflage on all parts (if possible).',
            'UI_setting_hangarCamoKind_text': 'Hangar camouflage season',
            'UI_setting_hangarCamoKind_tooltip': 'This setting controls the season which is used in hangar.',
            'UI_setting_hangarCamo_winter': 'Winter', 'UI_setting_hangarCamo_summer': 'Summer',
            'UI_setting_hangarCamo_desert': 'Desert', 'UI_setting_hangarCamo_random': 'Random'}
        super(ConfigInterface, self).init()

    def loadLang(self):
        super(ConfigInterface, self).loadLang()
        for key in self.i18n:
            if not key.startswith('flashCol_'):
                continue
            self.i18n[key] = self.color_compat(self.i18n[key])

    @staticmethod
    def color_compat(to_color):
        try:
            from helpers.i18n.hangarpainter import _config
            return "<font color='#%s'>%s</font>" % (_config.data['colour'], to_color)
        except ImportError:
            return to_color

    def createTemplate(self):
        return {
            'modDisplayName': self.i18n['UI_description'], 'enabled': self.data['enabled'],
            'column1': [
                self.tb.createOptions('hangarCamoKind', [
                    self.i18n['UI_setting_hangarCamo_' + x] for x in ('winter', 'summer', 'desert', 'random')]),
                self.tb.createControl('doRandom'),
                self.tb.createControl('disableWithDefault'),
            ],
            'column2': [
                self.tb.createControl('fillEmptySlots'),
                self.tb.createControl('uniformOutfit'),
                self.tb.createControl('useBought'),
                self.tb.createControl('fullAlpha'),
            ]}

    def onMSADestroy(self):
        try:
            from gui.mods import mod_remodenabler
        except ImportError:
            refreshCurrentVehicle()

    def onApplySettings(self, settings):
        super(ConfigInterface, self).onApplySettings(settings)
        self.hangarCamoCache.clear()

    def readCurrentSettings(self, quiet=True):
        cache = iv.g_cache.customization20()
        for cType, modded_items in self.modded_items.items():
            storage = cache.itemTypes[cType]
            for item_id in modded_items:
                storage.pop(item_id, None)
            modded_items.clear()
        if not self.modded_groups:
            self.createItemGroups(cache)
        for settings in self.camo_settings.values():
            settings.clear()
        self.outfitCache = loadJson(self.ID, 'outfitCache', self.outfitCache, self.configPath)
        for name in self.allowed_names:
            self.readConfigDir(quiet, recursive=True, dir_name=name + 's', error_not_exist=False, ext='.xml')
        settings = loadJson(self.ID, 'settings', {}, self.configPath)
        self.disabledVehicles = settings.setdefault('disable', self.disabledVehicles)
        for k, v in settings.setdefault('remap', {}).items():
            self.camo_settings['remap'][int(k)] = v
        custom_settings = settings.setdefault('custom', {})
        for item_name in custom_settings.keys():
            if item_name not in self.camo_settings['custom']:
                custom_settings.pop(item_name)
            else:
                self.camo_settings['custom'][item_name].update(custom_settings[item_name])
        custom_settings.update(self.camo_settings['custom'])
        loadJson(self.ID, 'settings', settings, self.configPath, True)

    def onReadDataSection(self, quiet, path, dir_path, name, data_section, sub_dirs, names):
        dir_path = path.replace(self.configPath, '')
        if '/' not in dir_path or name != 'data':
            return
        item_type, _, item_name = dir_path.partition('/')
        item_type = item_type[:-1]
        if item_type not in self.allowed_names:
            print self.ID + ': unknown item type:', item_type
            return
        description = ''
        user_name = item_name
        if '/' in user_name and 'by ' in user_name:
            parts = user_name.split('/')
            description = next(part for part in parts if 'by ' in part)
        user_name = ' '.join(part for part in user_name.split('/') if part != description)
        cType = consts.CustomizationNamesToTypes[item_type.upper()]
        itemCls = self.allowed_types[cType]
        storage = self.modded_items[cType]
        priceGroup = self.modded_groups[itemCls]
        item = itemCls(priceGroup)
        self.modded_readers[itemCls]._readFromXml(item, (((None, self.ID), item_type), item_name), data_section)
        item.i18n = sc.I18nExposedComponent(self.color_compat(user_name), self.color_compat(description), item_name)
        item.id = max(storage or (STARTER_ITEM_ID,)) + 1
        cache = iv.g_cache.customization20()
        cache.itemTypes[cType][item.id] = storage[item.id] = item
        self.modded_lookup_name[cType][item_name] = item.id
        item.priceGroupTags = cache.priceGroups[STARTER_ITEM_ID].tags
        iv._copyPriceForItem(priceGroup.compactDescr, item.compactDescr, True)
        if cType != consts.CustomizationType.CAMOUFLAGE:
            return
        self.camo_settings['custom'][item_name] = settings = {}
        for name, default_value in self.defaults.items():
            if name == 'season':
                settings[name] = data_section.readString(name, ' '.join(default_value)).split(' ')
            else:
                settings[name] = data_section.readBool(name, default_value)

    def createItemGroups(self, cache):
        if STARTER_ITEM_ID in cache.priceGroups:
            if cache.priceGroups[STARTER_ITEM_ID].name != CUSTOM_GROUP_NAME:
                ix.raiseWrongXml((None, ''), 'priceGroup', 'CamoSelector price group ID needs to be changed!')
            return
        priceGroup = cc.PriceGroup()
        priceGroup.id = STARTER_ITEM_ID
        priceGroup.name = CUSTOM_GROUP_NAME
        priceGroup.notInShop = True
        priceGroup.tags = frozenset(map(
            intern, ('custom', 'notInShop', 'legacy', 'paints', 'camouflages', 'common') + nations.NAMES))
        for tag in priceGroup.tags:
            cache.priceGroupTags.setdefault(tag, []).append(priceGroup)
        cache.priceGroupNames[CUSTOM_GROUP_NAME] = STARTER_ITEM_ID
        cache.priceGroups[STARTER_ITEM_ID] = priceGroup
        for itemCls in self.modded_readers:
            self.modded_groups[itemCls] = group = cc.ItemGroup(itemCls)
            group.itemPrototype = prototype = itemCls()
            prototype.season = consts.SeasonType.ALL
            prototype.priceGroup = CUSTOM_GROUP_NAME
            prototype.historical = False
            prototype.tags |= frozenset((consts.ItemTags.HIDDEN_IN_UI,))
            prototype.i18n = sc.I18nExposedComponent(self.i18n['flashCol_group_custom'], '')

    def applyCamoSettings(self, currentSettings):
        for itemsKey, itemsSettings in currentSettings.items():
            for name, itemSettings in itemsSettings.items():
                self.camo_settings[itemsKey].setdefault(name, {}).update(itemSettings)
        loadJson(self.ID, 'settings', dict(self.camo_settings, **{'disable': self.disabledVehicles}), self.configPath, True)

    def migrateConfigs(self):
        camoData = {}
        for camoID, x in iv.g_cache.customization20().camouflages.iteritems():
            data = camoData.setdefault(os.path.splitext(os.path.basename(x.texture))[0], {'ids': [], 'nations': []})
            data['ids'].append(camoID)
            for filterNode in getattr(x.filter, 'include', ()):
                data['nations'] += filterNode.nations or []
        for data in camoData.itervalues():
            if set(data['nations']) >= set(idx for idx, name in enumerate(nations.NAMES) if name != 'italy'):
                self.internationalCamoIDs += data['ids']
        migrator.migrateSettings(self, camoData)

    def collectCamouflageData(self):
        self.camoForSeason = {season: {'random': [], 'ally': [], 'enemy': []} for season in SEASONS_CONSTANTS.SEASONS}
        for camoID, camo in iv.g_cache.customization20().camouflages.iteritems():
            if camoID == consts.EMPTY_ITEM_ID:
                continue
            cfg = self.getCamoSettings(*self.getItemKeys(camoID, camo))
            if not cfg.get('random_enabled', True):
                continue
            for seasonName in cfg.get('season', []) or [
                    x for x in SEASONS_CONSTANTS.SEASONS if SEASON_NAME_TO_TYPE[x] & camo.season]:
                camoForSeason = self.camoForSeason[seasonName]
                if not cfg.get('random_team', False):
                    camoForSeason['random'].append(camoID)
                    continue
                if cfg.get('ally', True):
                    camoForSeason['ally'].append(camoID)
                if cfg.get('enemy', True):
                    camoForSeason['enemy'].append(camoID)


class ModdedCamouflageItem(cc.CamouflageItem):
    def __init__(self, parentGroup=None):
        self.__palettes = []
        self.__copying = False
        cc.CamouflageItem.__init__(self, parentGroup)

    @property
    def palettes(self):
        if g_config.data['fullAlpha'] and not self.__copying:
            return tuple([color | 0xFF000000 for color in palette] for palette in self.__palettes)
        return self.__palettes

    @palettes.setter
    def palettes(self, value):
        self.__palettes = value

    def __deepcopy__(self, memo=None):
        self.__copying = True
        try:
            return cc.CamouflageItem.__deepcopy__(self, memo)
        finally:
            self.__copying = False


@overrideMethod(iv, '_vehicleValues')  # needs to be hooked before reading configs
def new_vehicleValues(_, xmlCtx, section, sectionName, defNationID):
    section = section[sectionName]
    if section is None:
        return
    ctx = (xmlCtx, sectionName)
    for vehName, subsection in section.items():
        if vehName == 'all':
            for vehNameAll in iv.g_list._VehicleList__ids.keys():
                nationID, vehID = iv.g_list.getIDsByName(vehNameAll)
                yield iv.VehicleValue(vehNameAll, makeCD('vehicle', nationID, vehID), ctx, subsection)
            continue
        if ':' not in vehName:
            vehName = nations.NAMES[defNationID] + ':' + vehName
        try:
            nationID, vehID = iv.g_list.getIDsByName(vehName)
        except Exception:
            ix.raiseWrongXml(xmlCtx, sectionName, "unknown vehicle name '%s'" % vehName)
        # noinspection PyUnboundLocalVariable
        yield iv.VehicleValue(vehName, makeCD('vehicle', nationID, vehID), ctx, subsection)


g_config = ConfigInterface()
statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-7', g_config.camo_settings['custom'])
