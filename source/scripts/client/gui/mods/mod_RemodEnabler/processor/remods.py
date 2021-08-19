import copy

from PYmodsCore import overrideMethod
from gui.shared.gui_items import GUI_ITEM_TYPE
from items.components import shared_components
from vehicle_systems import camouflages
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config


class VehicleTypeProxy(object):  # I would tear off the hands that made me write this crap
    __slots__ = ('_vDesc', '_type')

    def __init__(self, vDesc):  # see items.vehicles.Cache.vehicle() and VehicleType.__init__() for details
        self._vDesc = vDesc  # all this just to break the attribute link
        self._type = vDesc.type  # holy shit

    def __getattr__(self, item):
        value = getattr(self._type, item)
        if item != 'camouflage':
            return value
        modelDesc = self._vDesc.chassis.modelsSets.get('RemodEnabler_modelDesc', None)
        if modelDesc is None or modelDesc.camouflage is None:
            return value
        new_value = modelDesc.camouflage
        return value._replace(**{field: getattr(new_value, field) or getattr(value, field) for field in value._fields})

    def __setattr__(self, key, value):
        if key in self.__slots__:
            super(VehicleTypeProxy, self).__setattr__(key, value)
        else:
            setattr(self._type, key, value)


def apply(vDesc, modelDesc, outfit):
    modelsSet = outfit.modelsSet or 'default'
    vDesc.type = VehicleTypeProxy(vDesc)  # all this to break the attribute link
    for partName in TankPartNames.ALL + ('engine',):
        emptyPart, remodPart, vehiclePart = (getattr(x, partName) for x in (g_config.emptyModelDesc, modelDesc, vDesc))
        for slots in (getattr(cls, '__slots__', ()) for cls in type(emptyPart).__mro__):
            for attr in slots:
                if attr == 'hullPosition':  # only needed for some readers
                    continue
                emptyAttr, remodAttr, vehicleAttr = (getattr(x, attr) for x in (emptyPart, remodPart, vehiclePart))
                if emptyAttr == remodAttr:
                    continue
                if attr == 'modelsSets':
                    old_models = vehicleAttr[modelsSet]
                    vehicleAttr[modelsSet] = shared_components.ModelStatesPaths(
                        remodAttr['default'].undamaged, old_models.destroyed, old_models.exploded)
                    vehiclePart.models = vehicleAttr['default']
                    continue
                if attr == 'camouflage':
                    vehiclePart.camouflage = vehicleAttr._replace(
                        **{field: getattr(remodAttr, field) or getattr(vehicleAttr, field) for field in vehicleAttr._fields})
                    continue
                if partName == 'hull' and attr == 'customEffects':
                    if isinstance(remodAttr[0], list):
                        vehicleAttr[0].nodes = remodAttr[0]
                        continue
                if attr == 'slotsAnchors':
                    remodAttr = vehicleAttr + remodAttr
                if remodAttr == 'void':
                    remodAttr = emptyAttr
                setattr(vehiclePart, attr, remodAttr)
    if modelDesc.chassis.AODecals:
        vDesc.chassis.AODecals = copy.deepcopy(vDesc.chassis.AODecals)
        vDesc.chassis.AODecals[0].setElement(
            3, 1, vDesc.chassis.AODecals[0].translation.y + modelDesc.chassis.hullPosition.y - vDesc.chassis.hullPosition.y)
    component = modelDesc.outfit['component']
    for itemTypeID in (GUI_ITEM_TYPE.ATTACHMENT, GUI_ITEM_TYPE.SEQUENCE):
        slot = outfit.misc.slotFor(itemTypeID)
        slot.clear()
    outfit.misc.unpack(component)


@overrideMethod(camouflages, 'updateFashions')
def updateFashions(base, appearance):
    base(appearance)
    modelDesc = getattr(appearance.typeDescriptor, 'modelDesc', None)
    if not appearance.isAlive or not all(list(appearance.fashions)) or not modelDesc:
        return
    camouflages.setMaterialsVisibility(appearance, modelDesc.outfit['hide_materials'], False)
