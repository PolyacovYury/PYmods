import BigWorld
import items.vehicles
from Account import Account
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui import g_tankActiveCamouflage
from gui.ClientHangarSpace import _VehicleAppearance
from gui.Scaleform.framework import ViewTypes
from gui.app_loader import g_appLoader
from gui.shared.gui_items import GUI_ITEM_TYPE
from helpers import dependency
from items.vehicles import CAMOUFLAGE_KIND_INDICES
from skeletons.gui.shared import IItemsCache
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankPartNames
from .settings import g_config
from .settings.shared import SEASON_NAME_TO_TYPE


def applyCache(outfit, season, descriptor):
    itemsCache = dependency.instance(IItemsCache)
    nationName, vehicleName = descriptor.name.split(':')
    camouflages = items.vehicles.g_cache.customization20().camouflages
    vehConfig = g_config.camouflagesCache.get(nationName, {}).get(vehicleName, {})
    seasonConfig = vehConfig.get(season, {})
    for areaName in seasonConfig.keys():
        try:
            areaId = TankPartNames.getIdx(areaName)
        except Exception as e:
            print '%s: exception while reading camouflages cache for %s in %s: %s' % (
                g_config.ID, descriptor.name, areaName, e.message)
            continue
        slot = outfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        if not seasonConfig[areaName]:
            slot.remove(0)
            continue
        camoID, paletteIdx, scale = seasonConfig[areaName]
        if camoID not in camouflages:
            print '%s: wrong camouflage ID for %s: %s' % (g_config.ID, areaName, camoID)
            del seasonConfig[areaName]
            continue
        item = itemsCache.items.getItemByCD(camouflages[camoID].compactDescr)
        if paletteIdx > len(item.palettes):
            print '%s: wrong palette idx for %s camouflage: %s (available: %s)' % (
                g_config.ID, areaName, paletteIdx, range(len(item.palettes)))
            del seasonConfig[areaName]
            continue
        if scale > len(item.scales):
            print '%s: wrong scale for %s camouflage: %s (available: %s)' % (
                g_config.ID, areaName, scale, range(len(item.scales)))
        slot.set(item)
        component = slot.getComponent()
        component.palette = paletteIdx
        component.patternSize = scale
    if not seasonConfig:
        vehConfig.pop(season, {})


@overrideMethod(_VehicleAppearance, '_VehicleAppearance__getActiveOutfit')
def new_getActiveOutfit(base, self):
    print 'getActiveOutfit'
    result = base(self).copy()
    manager = g_appLoader.getDefLobbyApp().containerManager
    if manager is not None:
        container = manager.getContainer(ViewTypes.LOBBY_SUB)
        if container is not None:
            c11nView = container.getView()
            if c11nView is not None and hasattr(c11nView, 'getCurrentOutfit'):
                return c11nView.getCurrentOutfit()  # fix for HangarFreeCam
    if g_config.data['enabled']:
        print 'enabled'
        vehicle = g_currentVehicle.item
        applyCache(result, g_tankActiveCamouflage[vehicle.intCD], vehicle.descriptor)
    return result


@overrideMethod(Account, 'onBecomeNonPlayer')
def new_onBecomeNonPlayer(base, self):
    base(self)
    g_config.hangarCamoCache.clear()
    g_config.teamCamo = dict.fromkeys(('Ally', 'Enemy'))


@overrideMethod(CompoundAppearance, '_CompoundAppearance__getVehicleOutfit')
def new_getVehicleOutfit(base, self, *a, **kw):
    result = base(self, *a, **kw).copy()
    if not self._CompoundAppearance__vehicle:
        return result
    if g_config.data['enabled']:
        applyCache(
            result, SEASON_NAME_TO_TYPE[CAMOUFLAGE_KIND_INDICES[BigWorld.player().arena.arenaType.vehicleCamouflageKind]],
            self._CompoundAppearance__typeDesc)
    return result

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
#         if g_config.teamCamo[curTeam] is None:
#             otherOverrider = g_config.teamCamo[otherTeam]
#             if len(overriders) > 1 and otherOverrider in overriders:
#                 overriders.remove(otherOverrider)
#             g_config.teamCamo[curTeam] = overriders[vID % len(overriders)]
#         selectedCamouflages = [camoNames[g_config.teamCamo[curTeam]]]
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
