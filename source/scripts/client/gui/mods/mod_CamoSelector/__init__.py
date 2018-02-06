# -*- coding: utf-8 -*-
__modID__ = '%(mod_ID)s'
__date__ = '%(file_compile_date)s'
import time

from PYmodsCore import overrideMethod
from gui.Scaleform.framework.entities.View import ViewKey
from .shared import getCurrentNationID
from .config import g_config
from . import settings
from . import readers
import BigWorld
import CurrentVehicle
import Keys
import ResMgr
import heapq
import items.vehicles
import nations
import random
import traceback
import weakref
from Account import Account
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from gui import InputHandler, SystemMessages, g_tankActiveCamouflage
from gui.ClientHangarSpace import ClientHangarSpace
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.LobbyView import _LobbySubViewsLifecycleHandler
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASON_IDX_TO_TYPE, SEASON_TYPE_TO_NAME
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.Scaleform.framework.managers.loaders import ViewLoadParams
from gui.app_loader import g_appLoader
from gui.customization import ICustomizationService
# from gui.customization.data_aggregator import DataAggregator
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.customization.outfit import Area
from helpers import i18n, dependency
from items import _xml
from items.components.c11n_constants import CustomizationType
from items.vehicles import CAMOUFLAGE_KINDS, CAMOUFLAGE_KIND_INDICES
from vehicle_systems.CompoundAppearance import CompoundAppearance


# @overrideMethod(items.vehicles.Cache, 'customization')
def new_customization(base, self, nationID):
    origDescr = base(self, nationID)
    if g_config.data['enabled'] and g_config.configFolders and nationID not in g_config.changedNations:
        g_config.changedNations.append(nationID)
        for configDir in g_config.configFolders:
            modDescr = items.vehicles._readCustomization(
                '../' + g_config.configPath + 'camouflages/' + configDir + '/settings.xml', nationID, (0, 65535))
            if 'custom_camo' in modDescr['camouflageGroups']:
                if 'custom_camo' not in origDescr['camouflageGroups']:
                    origDescr['camouflageGroups']['custom_camo'] = modDescr['camouflageGroups']['custom_camo']
                    origDescr['camouflageGroups']['custom_camo']['ids'][:] = []
                del modDescr['camouflageGroups']['custom_camo']
            newID = max((max(origDescr['camouflages'].iterkeys()) + 1, 5001))
            camouflages = modDescr['camouflages'].values()
            modDescr['camouflages'].clear()
            for camo in camouflages:
                if g_config.data['fullAlpha']:
                    colors = []
                    for color in camo['colors'][:3]:
                        rgba = []
                        for idx in xrange(3):
                            rgba.append(color - (color >> 8 << 8))
                            color = color >> 8
                        rgba.append(255)
                        colors.append(rgba[0] + (rgba[1] << 8) + (rgba[2] << 16) + (rgba[3] << 24))
                    colors.append(camo['colors'][3])
                    camo['colors'] = tuple(colors)
                modDescr['camouflages'][newID] = camo
                origDescr['camouflageGroups']['custom_camo']['ids'].append(newID)
                newID += 1
            origDescr = items.vehicles._joinCustomizationParams(nationID, modDescr, origDescr)
        self._Cache__customization[nationID] = origDescr
    return origDescr


# @overrideMethod(DataAggregator, '_elementIsInShop')
# def new_elementIsInShop(base, self, criteria, cType, nationID):
#     if cType == CustomizationType.CAMOUFLAGE:
#         customization = items.vehicles.g_cache.customization(nationID)
#         if customization['camouflages'][criteria]['name'] in g_config.camouflages['modded']:
#             return False
#     return base(self, criteria, cType, nationID)


def readInstalledCamouflages(self):
    if g_currentPreviewVehicle.isPresent():
        vDesc = g_currentPreviewVehicle.item.descriptor
    elif g_currentVehicle.isPresent():
        vDesc = g_currentVehicle.item.descriptor
    else:
        return
#     nationName, vehName = vDesc.name.split(':')
#     if g_config.camouflagesCache.get(nationName, {}).get(vehName) is None:
#         return
#     for idx in xrange(3):
#         self.showGroup(0, idx)
#         if g_config.camouflagesCache[nationName][vehName].get(CAMOUFLAGE_KIND_INDICES[idx]) is None:
#             continue
#         camoKindName = CAMOUFLAGE_KIND_INDICES[idx]
#         camoName = g_config.camouflagesCache[nationName][vehName][camoKindName]
#         for itemIdx, item in enumerate(g_customizationController.carousel.items):
#             if item['element']._rawData['name'] == camoName:
#                 self.installCustomizationElement(itemIdx)
#                 break
#         else:
#             SystemMessages.pushMessage('PYmods_SM' + g_config.i18n['UI_customOrInvalid'].format(
#                 kind=g_config.i18n['UI_customOrInvalid_%s' % CAMOUFLAGE_KIND_INDICES[idx]], name=camoName),
#                                        SystemMessages.SM_TYPE.CustomizationForGold)
#     g_customizationController._dataAggregator.start()
#     try:
#         self.backToSelectorGroup()
#     except Exception as e:
#         if False:
#             print e


def installSelectedCamo():
    if g_currentPreviewVehicle.isPresent():
        vDesc = g_currentPreviewVehicle.item.descriptor
    elif g_currentVehicle.isPresent():
        vDesc = g_currentVehicle.item.descriptor
    else:
        return
#     nationName, vehName = vDesc.name.split(':')
#     nationID = vDesc.type.customizationNationID
#     compDescr = vDesc.type.compactDescr
#     assert nations.NAMES[nationID] == nationName, (nationName, nations.NAMES[nationID])
#     if g_customizationController.slots.currentSlotsData is None:
#         activeCamo = g_tankActiveCamouflage['historical'].get(compDescr)
#         if activeCamo is None:
#             activeCamo = g_tankActiveCamouflage.get(compDescr, 0)
#         customization = items.vehicles.g_cache.customization(nationID)
#         if g_config.activePreviewCamo is not None:
#             camoNames = {camouflage['name']: camoID for camoID, camouflage in customization['camouflages'].items()}
#             camoID = camoNames[g_config.activePreviewCamo]
#             if compDescr in g_config.hangarCamoCache:
#                 del g_config.hangarCamoCache[compDescr]
#         elif compDescr in g_config.hangarCamoCache:
#             camoID = g_config.hangarCamoCache[compDescr][activeCamo][0]
#         else:
#             return
#         camouflage = customization['camouflages'][camoID]
#         camoName = camouflage['name']
#         nationConf = g_config.camouflages.get(nations.NAMES[nationID])
#         interConf = g_config.camouflages.get('international', {})
#         camoKindNums = (camouflage['kind'],)
#         if camoName in g_config.camouflages['modded']:
#             camoKindNames = filter(None, g_config.camouflages['modded'].get(camoName, {}).get('season', '').split(','))
#             camoKindNums = tuple(CAMOUFLAGE_KINDS[name] for name in camoKindNames)
#         elif camoName in interConf:
#             seasonStr = interConf.get(camoName, {}).get('season')
#             if seasonStr is not None:
#                 camoKindNames = filter(None, seasonStr.split(','))
#                 camoKindNums = tuple(CAMOUFLAGE_KINDS[name] for name in camoKindNames)
#         elif nationConf is not None:
#             seasonStr = nationConf.get(camoName, {}).get('season')
#             if seasonStr is not None:
#                 camoKindNames = filter(None, seasonStr.split(','))
#                 camoKindNums = tuple(CAMOUFLAGE_KINDS[name] for name in camoKindNames)
#         for camoKindNum in camoKindNums:
#             if g_config.camouflagesCache.get(nationName, {}).get(vehName, {}).get(
#                     CAMOUFLAGE_KIND_INDICES[camoKindNum]) == camoName:
#                 SystemMessages.pushMessage('PYmods_SM' + g_config.i18n['UI_installCamouflage_already'].format(
#                     name=camoName, kind=g_config.i18n['UI_setting_hangarCamo_%s' % CAMOUFLAGE_KIND_INDICES[camoKindNum]]),
#                                            SystemMessages.SM_TYPE.CustomizationForGold)
#                 continue
#             g_config.camouflagesCache.setdefault(nationName, {}).setdefault(vehName, {})[
#                 CAMOUFLAGE_KIND_INDICES[camoKindNum]] = camoName
#             SystemMessages.pushMessage('PYmods_SM' + g_config.i18n['UI_installCamouflage'].format(
#                 name=camoName, kind=g_config.i18n['UI_setting_hangarCamo_%s' % CAMOUFLAGE_KIND_INDICES[camoKindNum]]),
#                                        SystemMessages.SM_TYPE.CustomizationForGold)
#             loadJson(g_config.ID, 'camouflagesCache', g_config.camouflagesCache, g_config.configPath, True)
#         return
#     camoCache = list(vDesc.camouflages)
#     for item in g_customizationController.cart.items:
#         if item['type'] != CustomizationType.CAMOUFLAGE:
#             continue
#         camoKindNum = item['object']._rawData['kind']
#         camoName = item['object']._rawData['name']
#         g_config.camouflagesCache.setdefault(nationName, {}).setdefault(vehName, {})[
#             CAMOUFLAGE_KIND_INDICES[camoKindNum]] = camoName
#         camoCache[camoKindNum] = (item['object'].getID(), int(time.time()), 7)
#     selectedSeason = []
#     for camoKind in g_config.camouflagesCache.get(nationName, {}).get(vehName, {}):
#         selectedSeason.append(CAMOUFLAGE_KINDS[camoKind])
#     slotList = heapq.nsmallest(1, selectedSeason, key=lambda x: abs(x - g_customizationController.slots.currentSlotIdx))
#     slotIdx = slotList[0] if slotList else 0
#     g_tankActiveCamouflage[compDescr] = slotIdx
#     vDesc.camouflages = tuple(camoCache)
#     g_config.hangarCamoCache[compDescr] = tuple(camoCache)
#     if vehName in g_config.camouflagesCache.get(nationName, {}) and not g_config.camouflagesCache[nationName][vehName]:
#         del g_config.camouflagesCache[nationName][vehName]
#     if nationName in g_config.camouflagesCache and not g_config.camouflagesCache[nationName]:
#         del g_config.camouflagesCache[nationName]
#     loadJson(g_config.ID, 'camouflagesCache', g_config.camouflagesCache, g_config.configPath, True)
#     refreshCurrentVehicle()
#     SystemMessages.pushMessage('PYmods_SM' + g_config.i18n['UI_camouflageSelect'],
#                                SystemMessages.SM_TYPE.CustomizationForGold)


"""from gui.shared.utils.HangarSpace import g_hangarSpace
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.customization.outfit import Area
from gui.app_loader import g_appLoader
from gui.Scaleform.framework import ViewTypes
from items.components.c11n_constants import SeasonType
import items.vehicles

print items.vehicles.g_cache.customization20().camouflages[
    g_appLoader.getDefLobbyApp().containerManager.getContainer(ViewTypes.LOBBY_SUB).getView().getModifiedOutfit(
        SeasonType.SUMMER).getContainer(Area.HULL).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE).getItem(idx=0).id].texture
"""

@overrideMethod(MainView, 'clearCustomizationItem')
def new_clearCustomizationItem(base, self, areaId, slotId, regionId, seasonIdx, *args, **kwargs):
    print areaId, slotId, regionId, seasonIdx
    try:
        # received: 1 23 0 0
        # areaId: Area.HULL
        # slotId: GUI_ITEM_TYPE.PAINT
        # regionId: idx of a part in MultiSlot
        # seasonIdx: SEASONS_CONSTANTS.SUMMER_INDEX
        if slotId == GUI_ITEM_TYPE.CAMOUFLAGE:
            assert not g_currentPreviewVehicle.isPresent()
            vDesc = g_currentVehicle.item.descriptor
            nationName, vehName = vDesc.name.split(':')
            season = SEASON_IDX_TO_TYPE.get(seasonIdx, self._currentSeason)
            camoKind = SEASON_TYPE_TO_NAME[season]
            outfit = self._modifiedOutfits[season]
            item = outfit.getContainer(areaId).slotFor(slotId).getItem(idx=regionId)
            # FUCK
            # camoName = item
        #    if g_config.camouflagesCache.get(nationName, {}).get(vehName) is not None:
        #        vehDict = g_config.camouflagesCache[nationName][vehName]
        #        if vehDict.get(camoKind) is not None and vehDict[camoKind] == camoName:
        #            del vehDict[camoKind]
        #        loadJson(g_config.ID, 'camouflagesCache', g_config.camouflagesCache, g_config.configPath, True)
    finally:
        base(self, areaId, slotId, regionId, seasonIdx, *args, **kwargs)


# @overrideMethod(_LobbySubViewsLifecycleHandler, 'onViewCreated')
# def new_onViewCreated(base, self, view):
#     if view is not None:
#         alias = view.key
#         if alias == VIEW_ALIAS.LOBBY_CUSTOMIZATION and alias in self._LobbySubViewsLifecycleHandler__loadingSubViews:
#             BigWorld.callback(0.0, g_customizationController.events.onCartFilled)
#     base(self, view)


@overrideMethod(MainView, '_populate')
def new_MV_populate(base, self):
    base(self)
    if g_config.data['enabled']:
        readInstalledCamouflages(self)


def updateGUIState():
    view = g_appLoader.getDefLobbyApp().containerManager.getViewByKey(ViewKey('CamoSelectorUI'))
    if view is None:
        return
    nationID = getCurrentNationID()
    if nationID is not None and g_config.backupNationID != nationID:
        view.changeNation(nationID)


# @overrideMethod(CurrentVehicle._CurrentVehicle, 'selectVehicle')
# def new_selectVehicle(base, self, vehInvID=0):
#     base(self, vehInvID)
#     updateGUIState()
#
#
# @overrideMethod(CurrentVehicle._CurrentPreviewVehicle, 'selectVehicle')
# def new_selectPreviewVehicle(base, self, *args):
#     base(self, *args)
#     updateGUIState()


@overrideMethod(Account, 'onBecomeNonPlayer')
def new_onBecomeNonPlayer(base, self):
    base(self)
    g_config.hangarCamoCache.clear()
    g_config.currentOverriders = dict.fromkeys(('Ally', 'Enemy'))


# @overrideMethod(CompoundAppearance, '_CompoundAppearance__getCamouflageParams')
# def new_ca_getCamouflageParams(base, self, vDesc, vID):
#     result = base(self, vDesc, vID)
#     if 'modded' not in g_config.camouflages:
#         g_config.readCamouflages(False)
#     if (not g_config.data['enabled'] or result[0] is not None and g_config.data['useBought'] or vDesc.name in
#             g_config.disable
#             or vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault']):
#         return result
#     nationName, vehName = vDesc.name.split(':')
#     isPlayer = vID == BigWorld.player().playerVehicleID
#     isAlly = BigWorld.player().guiSessionProvider.getArenaDP().getVehicleInfo(vID).team == BigWorld.player().team
#     curTeam = 'Ally' if isAlly else 'Enemy'
#     otherTeam = 'Ally' if not isAlly else 'Enemy'
#     camoKind = BigWorld.player().arena.arenaType.vehicleCamouflageKind
#     camoKindName = CAMOUFLAGE_KIND_INDICES[camoKind]
#     nationID = vDesc.type.customizationNationID
#     camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
#     camoNames = {camouflage['name']: id for id, camouflage in camouflages.items()}
#     if isPlayer and g_config.camouflagesCache.get(nationName, {}).get(vehName, {}).get(camoKindName) is not None:
#         for camoName in camoNames:
#             if camoName == g_config.camouflagesCache[nationName][vehName][camoKindName]:
#                 return camoNames[camoName], int(time.time()), 7
#     selectedCamouflages = []
#     overriders = []
#     for key in ('modded', 'international', nationName):
#         for camoName in g_config.camouflages.get(key, {}):
#             if camoName not in camoNames:
#                 continue
#             camoConfig = g_config.camouflages[key][camoName]
#             camouflage = camouflages[camoNames[camoName]]
#             if camoConfig.get('random_mode', 2) != 1:
#                 continue
#             if camoKindName not in camoConfig.get('season', CAMOUFLAGE_KIND_INDICES[camouflage['kind']]):
#                 continue
#             if not camoConfig.get('useFor%s' % curTeam, True):
#                 continue
#             if camouflage['allow'] and vDesc.type.compactDescr not in camouflage['allow'] or \
#                     vDesc.type.compactDescr in camouflage['deny']:
#                 continue
#             if vDesc.type.compactDescr in camouflage['tiling']:
#                 overriders.append(camoName)
#             else:
#                 print 'CamoSelector: a vehicle was not whitelisted and (or) blacklisted, but is missing:', vehName
#                 print camouflage['tiling']
#     if overriders:
#         if g_config.currentOverriders[curTeam] is None:
#             otherOverrider = g_config.currentOverriders[otherTeam]
#             if len(overriders) > 1 and otherOverrider in overriders:
#                 overriders.remove(otherOverrider)
#             g_config.currentOverriders[curTeam] = overriders[vID % len(overriders)]
#         selectedCamouflages = [camoNames[g_config.currentOverriders[curTeam]]]
#     if g_config.data['doRandom'] and not selectedCamouflages:
#         for camoID, camouflage in camouflages.items():
#             camoName = camouflage['name']
#             checked = {'modded': False, 'international': False, nationName: False}
#             for key in checked:
#                 if camoName not in g_config.camouflages.get(key, {}):
#                     continue
#                 checked[key] = True
#                 camoConfig = g_config.camouflages[key][camoName]
#                 if camoConfig.get('random_mode', 2) != 2:
#                     continue
#                 if not camoConfig.get('useFor%s' % curTeam, True):
#                     continue
#                 if camouflage['allow'] and vDesc.type.compactDescr not in camouflage['allow'] or \
#                         vDesc.type.compactDescr in camouflage['deny']:
#                     continue
#                 if vDesc.type.compactDescr not in camouflage['tiling']:
#                     continue
#                 if camoKindName not in camoConfig.get('season', CAMOUFLAGE_KIND_INDICES[camouflage['kind']]):
#                     continue
#                 selectedCamouflages.append(camoID)
#             if not any(checked.values()):
#                 if camouflage['kind'] == CAMOUFLAGE_KINDS[camoKindName]:
#                     selectedCamouflages.append(camoID)
#     if not selectedCamouflages:
#         selectedCamouflages.append(None)
#     camouflageId = vID % len(selectedCamouflages)
#     return selectedCamouflages[camouflageId], int(time.time()), 7


# @overrideMethod(ClientHangarSpace, 'recreateVehicle')
# def new_cs_recreateVehicle(base, self, vDesc, vState, onVehicleLoadedCallback=None):
#     if g_config.data['enabled']:
#         if 'modded' not in g_config.camouflages:
#             g_config.readCamouflages(True)
#         nationID = vDesc.type.customizationNationID
#         customization = items.vehicles.g_cache.customization(nationID)
#         if g_config.activePreviewCamo is not None:
#             for camoID, camouflage in customization['camouflages'].items():
#                 if camouflage['name'] == g_config.activePreviewCamo:
#                     vDesc.camouflages = tuple((camoID, time.time(), 7) for _ in xrange(3))
#                     break
#             else:
#                 SystemMessages.pushMessage('PYmods_SM' + g_config.i18n['UI_camouflagePreviewError'] +
#                                            g_config.activePreviewCamo.join(('<b>', '</b>')),
#                                            SystemMessages.SM_TYPE.CustomizationForGold)
#                 print 'CamoSelector: camouflage not found for nation %s: %s' % (nationID, g_config.activePreviewCamo)
#                 g_config.activePreviewCamo = None
#         elif vDesc.type.compactDescr in g_config.hangarCamoCache:
#             vDesc.camouflages = g_config.hangarCamoCache[vDesc.type.compactDescr]
#         elif vDesc.name not in g_config.disable and not (
#                 vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault']):
#             nationName, vehName = vDesc.name.split(':')
#             selectedForVeh = g_config.camouflagesCache.get(nationName, {}).get(vehName, {})
#             selectedCamo = {}
#             camoByKind = {0: [], 1: [], 2: []}
#             for camoID, camouflage in customization['camouflages'].items():
#                 camoName = camouflage['name']
#                 nationConf = g_config.camouflages.get(nationName)
#                 interConf = g_config.camouflages.get('international', {})
#                 camoKindNames = (CAMOUFLAGE_KIND_INDICES[camouflage['kind']],)
#                 if camoName in g_config.camouflages['modded']:
#                     camoKindNames = filter(None,
#                                            g_config.camouflages['modded'].get(camoName, {}).get('season', '').split(','))
#                 elif camoName in interConf:
#                     seasonStr = interConf.get(camoName, {}).get('season')
#                     if seasonStr is not None:
#                         camoKindNames = filter(None, seasonStr.split(','))
#                 elif nationConf is not None:
#                     seasonStr = nationConf.get(camoName, {}).get('season')
#                     if seasonStr is not None:
#                         camoKindNames = filter(None, seasonStr.split(','))
#                 for camoKindName in camoKindNames:
#                     if selectedForVeh.get(camoKindName) is not None:
#                         if camouflage['name'] == selectedForVeh[camoKindName]:
#                             selectedCamo[CAMOUFLAGE_KINDS[camoKindName]] = camoID
#                     camoByKind[CAMOUFLAGE_KINDS[camoKindName]].append(camoID)
#             for kind in camoByKind:
#                 if not camoByKind[kind]:
#                     camoByKind[kind].append(None)
#             tmpCamouflages = []
#             for idx in xrange(3):
#                 if vDesc.camouflages[idx][0] is not None:
#                     tmpCamouflages.append(vDesc.camouflages[idx])
#                 elif selectedCamo.get(idx) is not None:
#                     tmpCamouflages.append((selectedCamo[idx], int(time.time()), 7))
#                 elif g_config.data['doRandom']:
#                     tmpCamouflages.append((random.choice(camoByKind[idx]), int(time.time()), 7))
#                 else:
#                     tmpCamouflages.append(vDesc.camouflages[idx])
#             vDesc.camouflages = tuple(tmpCamouflages)
#             g_config.hangarCamoCache[vDesc.type.compactDescr] = tuple(tmpCamouflages)
#             if g_config.data['hangarCamoKind'] < 3:
#                 idx = g_config.data['hangarCamoKind']
#             else:
#                 idx = random.randrange(3)
#             g_tankActiveCamouflage[vDesc.type.compactDescr] = idx
#     base(self, vDesc, vState, onVehicleLoadedCallback)
