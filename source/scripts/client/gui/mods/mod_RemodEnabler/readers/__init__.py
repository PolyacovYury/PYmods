from items import ITEM_TYPES, _xml, customizations as c11n, vehicle_items
from items.customizations import CustomizationOutfit
from .common import readCamouflage
from .part_readers import readChassis, readEngine, readGun, readHull, readTurret


def readModelDesc(xmlCtx, section, item):
    item.message = _xml.readStringOrEmpty(xmlCtx, section, 'message')
    for attr in ('player', 'ally', 'enemy'):
        setattr(item, attr, _xml.readBool(xmlCtx, section, attr, True))
    item.whitelist = _xml.readTupleOfStrings(xmlCtx, section, 'whitelist')
    for attr, reader in ('chassis', readChassis), (
            'hull', readHull), ('turret', readTurret), ('gun', readGun), ('engine', readEngine):
        subsection = _xml.getSubsection(xmlCtx, section, attr, attr != 'engine')
        if subsection is not None:
            reader((xmlCtx, attr), subsection, getattr(item, attr))
    readCamouflage(xmlCtx, section, item)
    item.outfit['hide_materials'] = _xml.readStringOrEmpty(xmlCtx, section, 'outfit/hide_materials')
    item.outfit['component'] = c11n.ComponentXmlDeserializer(c11n._CUSTOMIZATION_CLASSES).decode(
        c11n.CustomizationOutfit.customType, (xmlCtx, 'outfit'), section['outfit']
    ) if section.has_key('outfit') else CustomizationOutfit()


class ModelDesc(object):
    __slots__ = (
        'name', 'message', 'player', 'ally', 'enemy', 'whitelist',
        'chassis', 'hull', 'gun', 'turret', 'engine', 'camouflage', 'outfit')

    def __init__(self):
        for slot in self.__slots__:
            setattr(self, slot, None)
        createItem = lambda _itemType: vehicle_items.createInstallableItem(
            _itemType, 0, 0, '') if _itemType is not None else vehicle_items.Hull()
        for (attr, itemType) in (
                ('chassis', ITEM_TYPES.vehicleChassis), ('hull', None),
                ('turret', ITEM_TYPES.vehicleTurret), ('gun', ITEM_TYPES.vehicleGun), ('engine', ITEM_TYPES.vehicleEngine)):
            setattr(self, attr, createItem(itemType))
        self.outfit = {}
