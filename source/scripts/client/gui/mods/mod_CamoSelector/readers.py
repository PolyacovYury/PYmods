import ResMgr
import items
import items._xml as ix
import items.vehicles as iv
import items.components.c11n_components as cc
import nations
import os
from PYmodsCore import overrideMethod
from items.components import shared_components
from items.components.c11n_constants import SeasonType
from items.readers.c11n_readers import CamouflageXmlReader


class LegacyCamouflageReader(CamouflageXmlReader):
    def _readFromXml(self, target, xmlCtx, section):
        super(LegacyCamouflageReader, self)._readFromXml(target, xmlCtx, section)
        if section.has_key('colors'):
            palettes = [[]]
            for p_name, p_section in section['colors'].items():
                palettes[0].append(iv._readColor(((xmlCtx, 'colors'), 'palette 0'), p_section, ''))
            target.palettes = tuple(palettes)


@overrideMethod(iv.Cache, 'customization20')
def new_customization20(base, *args, **kwargs):
    from . import g_config
    cache = base(*args, **kwargs)
    if g_config.data['enabled'] and 'modded' not in cache.priceGroupNames:
        for configDir in sorted(g_config.configFolders, key=lambda s: s.lower()):
            filePath = g_config.configPath + 'camouflages/' + configDir + '/'
            updateCustomizationCache(cache, '.' + filePath, g_config.i18n['UI_flash_camoMode_modded'])
    return cache


# noinspection PyUnboundLocalVariable,PyUnboundLocalVariable
@overrideMethod(iv, '_vehicleValues')
def new_vehicleValues(_, xmlCtx, section, sectionName, defNationID):
    section = section[sectionName]
    if section is None:
        return
    else:
        ctx = (xmlCtx, sectionName)
        for vehName, subsection in section.items():
            if 'all' not in vehName:
                if ':' not in vehName:
                    vehName = ':'.join((nations.NAMES[defNationID], vehName))
                try:
                    nationID, vehID = iv.g_list.getIDsByName(vehName)
                except Exception:
                    ix.raiseWrongXml(xmlCtx, sectionName, "unknown vehicle name '%s'" % vehName)

                yield items.vehicles.VehicleValue(vehName, items.makeIntCompactDescrByID('vehicle', nationID, vehID), ctx,
                                                  subsection)
            else:
                for vehNameAll in items.vehicles.g_list._VehicleList__ids.keys():
                    nationID, vehID = items.vehicles.g_list.getIDsByName(vehNameAll)
                    yield items.vehicles.VehicleValue(vehNameAll,
                                                      items.makeIntCompactDescrByID('vehicle', nationID, vehID),
                                                      ctx, subsection)


def updateCustomizationCache(cache, folder, groupName):
    createPriceGroup(cache)
    __readCamoFolder(groupName, cache, cc.CamouflageItem, folder, cache.camouflages)


def __readCamoFolder(groupName, cache, itemCls, folder, storage):
    itemsFileName = os.path.join(folder, 'settings.xml')
    dataSection = ResMgr.openSection(itemsFileName)
    try:
        _readItems(groupName, cache, itemCls, (None, 'settings.xml'), dataSection, storage)
    finally:
        ResMgr.purge(itemsFileName)


def _readItems(groupName, cache, itemCls, xmlCtx, section, storage):
    """Read items and corresponding item groups from xml.

    :param itemCls: Target item class
    :param xmlCtx: Tuple with xml context used by ResMgr
    :param section: Section pointing to xml element with item group collection
    :param storage: dict to store loaded values
    :return: dictionary {id, item} of loaded items
    """
    reader = LegacyCamouflageReader()
    groupsDict = cache.priceGroups
    itemToGroup = cache.itemToPriceGroup
    group = cc.ItemGroup(itemCls)
    itemPrototype = itemCls()
    itemPrototype.season = SeasonType.ALL
    itemPrototype.priceGroup = 'modded'
    itemPrototype.invisibilityFactor = 0
    itemPrototype.historical = False
    itemPrototype.i18n = shared_components.I18nExposedComponent(groupName, '')
    group.itemPrototype = itemPrototype
    j = 0
    if section.has_key('camouflages'):
        section = section['camouflages']
    for i_name, i_section in section.items():
        iCtx = (xmlCtx, '{0} {1}'.format(i_name, j))
        j += 1
        item = itemCls(group)
        reader._readFromXml(item, iCtx, i_section)
        item.i18n = shared_components.I18nExposedComponent(i_name, '')
        item.id = max(20000, *storage) + 1
        if item.compactDescr in itemToGroup:
            ix.raiseWrongXml(iCtx, 'id', 'duplicate item. id: %s found in group %s' % (
                item.id, itemToGroup[item.compactDescr]))
        storage[item.id] = item
        if item.priceGroup:
            if item.priceGroup not in cache.priceGroupNames:
                ix.raiseWrongXml(iCtx, 'priceGroup', 'unknown price group %s for item %s' % (item.priceGroup, item.id))
            priceGroupId = cache.priceGroupNames[item.priceGroup]
            item.priceGroupTags = groupsDict[priceGroupId].tags
            itemToGroup[item.compactDescr] = groupsDict[priceGroupId].compactDescr
            itemNotInShop = i_section.readBool('notInShop', True)
            iv._copyPriceForItem(groupsDict[priceGroupId].compactDescr, item.compactDescr, itemNotInShop)
        else:
            ix.raiseWrongXml(iCtx, 'priceGroup', 'no price for item %s' % item.id)


def createPriceGroup(cache):
    if 20000 in cache.priceGroups:
        if cache.priceGroups[20000].name != 'modded':
            ix.raiseWrongXml((None, ''), 'priceGroup', 'CamoSelector price group ID needs to be changed!')
        return
    priceGroup = cc.PriceGroup()
    priceGroup.id = 20000
    priceGroup.name = intern('modded')
    priceGroup.notInShop = True
    priceGroup.tags = frozenset(map(intern, ('modded', 'notInShop', 'legacy', 'camouflages', 'common') + nations.NAMES))
    for tag in priceGroup.tags:
        cache.priceGroupTags.setdefault(tag, []).append(priceGroup)
    cache.priceGroupNames[priceGroup.name] = priceGroup.id
    cache.priceGroups[priceGroup.id] = priceGroup
