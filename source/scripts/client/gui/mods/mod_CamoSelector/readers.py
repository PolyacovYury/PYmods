import ResMgr
import items._xml as ix
import items.components.c11n_components as cc
import items.vehicles as iv
import nations
import traceback
from PYmodsCore import overrideMethod
from items import makeIntCompactDescrByID as makeCD
from items.components import shared_components
from items.components.c11n_constants import SeasonType, EMPTY_ITEM_ID
from items.readers.c11n_readers import CamouflageXmlReader, PaintXmlReader
from . import g_config


STARTER_ITEM_ID = EMPTY_ITEM_ID + 1


class ModdedCamouflageReader(CamouflageXmlReader):
    def _readFromXml(self, target, xmlCtx, section, cache=None):
        super(ModdedCamouflageReader, self)._readFromXml(target, xmlCtx, section, cache)
        if not g_config.data['fullAlpha']:
            return
        for palette in target.palettes:
            palette[:] = [color | 0xFF000000 for color in palette]


@overrideMethod(iv.Cache, 'customization20')
def new_customization20(base, *args, **kwargs):
    cache = base(*args, **kwargs)
    if g_config.data['enabled'] and g_config.configFolders and 'custom' not in cache.priceGroupNames:
        createPriceGroup(cache)
        groupName = g_config.i18n['flashCol_group_custom']
        for configDir in sorted(g_config.configFolders, key=lambda s: s.lower()):
            filePath = g_config.configPath + 'camouflages/' + configDir + '/'
            __readCamoFolder(groupName, cache, cc.CamouflageItem, '.' + filePath, cache.camouflages)
        __readPaintFolder(groupName, cache, cc.PaintItem, '.' + g_config.configPath + 'paints/', cache.paints)
    return cache


def createPriceGroup(cache):
    if STARTER_ITEM_ID in cache.priceGroups:
        if cache.priceGroups[STARTER_ITEM_ID].name != 'custom':
            ix.raiseWrongXml((None, ''), 'priceGroup', 'CamoSelector price group ID needs to be changed!')
        return
    priceGroup = cc.PriceGroup()
    priceGroup.id = STARTER_ITEM_ID
    priceGroup.name = intern('custom')
    priceGroup.notInShop = True
    priceGroup.tags = frozenset(map(intern, ('custom', 'notInShop', 'legacy', 'paints', 'camouflages', 'common') +
                                    nations.NAMES))
    for tag in priceGroup.tags:
        cache.priceGroupTags.setdefault(tag, []).append(priceGroup)
    cache.priceGroupNames[priceGroup.name] = priceGroup.id
    cache.priceGroups[priceGroup.id] = priceGroup


@overrideMethod(iv, '_vehicleValues')
def new_vehicleValues(_, xmlCtx, section, sectionName, defNationID):
    section = section[sectionName]
    if section is None:
        return
    ctx = (xmlCtx, sectionName)
    for vehName, subsection in section.items():
        if vehName != 'all':
            if ':' not in vehName:
                vehName = nations.NAMES[defNationID] + ':' + vehName
            try:
                nationID, vehID = iv.g_list.getIDsByName(vehName)
            except Exception:
                ix.raiseWrongXml(xmlCtx, sectionName, "unknown vehicle name '%s'" % vehName)
            # noinspection PyUnboundLocalVariable
            yield iv.VehicleValue(vehName, makeCD('vehicle', nationID, vehID), ctx, subsection)
        else:
            for vehNameAll in iv.g_list._VehicleList__ids.keys():
                nationID, vehID = iv.g_list.getIDsByName(vehNameAll)
                yield iv.VehicleValue(vehNameAll, makeCD('vehicle', nationID, vehID), ctx, subsection)


def __readCamoFolder(groupName, cache, itemCls, folder, storage):
    itemsFileName = folder + '/settings.xml'
    dataSection = ResMgr.openSection(itemsFileName)
    try:
        _readItems(groupName, cache, itemCls, (None, 'settings.xml'), dataSection, storage)
    except StandardError:
        traceback.print_exc()
    finally:
        ResMgr.purge(itemsFileName)


def __readPaintFolder(groupName, cache, itemCls, folder, storage):
    folderSection = ResMgr.openSection(folder)
    for name, sect in (i for i in folderSection.items() if i[0].endswith('.xml')) if folderSection is not None else ():
        try:
            _readItems(groupName, cache, itemCls, (None, name), sect, storage)
        except StandardError:
            traceback.print_exc()
        ResMgr.purge(name)


# noinspection DuplicatedCode
def _readItems(groupName, cache, itemCls, xmlCtx, section, storage):
    reader = ModdedCamouflageReader() if itemCls == cc.CamouflageItem else PaintXmlReader()
    groupsDict = cache.priceGroups
    itemToGroup = cache.itemToPriceGroup
    group = cc.ItemGroup(itemCls)
    itemPrototype = itemCls()
    itemPrototype.season = SeasonType.ALL
    itemPrototype.priceGroup = 'custom'
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
        if itemCls == cc.CamouflageItem:
            item.invisibilityFactor = 0
            item.i18n = shared_components.I18nExposedComponent(i_name, '')
        item.id = max(STARTER_ITEM_ID, *storage) + 1
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
