import Math
from gui.Scaleform.daapi.view.lobby.customization.shared import C11nTabs
from gui.Scaleform.daapi.view.lobby.customization.vehicle_anchors_updater import VehicleAnchorsUpdater as VAU, \
    _LINES_SHIFT_FROM_CENTRE
from gui.customization.shared import C11nId
from gui.shared.gui_items.customization.outfit import Area
from .shared import CSTabs

_ASPECT_RATIO = {C11nTabs.EMBLEM: 1.0, C11nTabs.INSCRIPTION: 2.0, CSTabs.EMBLEM: 1.0, CSTabs.INSCRIPTION: 2.0}
_ANCHOR_SHIFT_FROM_CENTRE = {C11nTabs.EMBLEM: 0.5, C11nTabs.INSCRIPTION: 0.3, CSTabs.EMBLEM: 0.5, CSTabs.INSCRIPTION: 0.3}


class VehicleAnchorsUpdater(VAU):
    def setAnchors(self, displayObjects, menuSlotId):
        if self.__vehicleCustomizationAnchors is None:
            return
        processedObjectIds = {}
        self._delAllAnchors()
        for displayObject in displayObjects:
            if not hasattr(displayObject, 'slotData'):
                continue
            slot = displayObject.slotData.slotId
            sId = C11nId(areaId=slot.areaId, slotType=slot.slotId, regionIdx=slot.regionId)
            anchorParams = self.__getAnchorParams(sId)
            if anchorParams is None:
                continue
            anchorPos = Math.Vector3(anchorParams.pos)
            bottom = Math.Vector3(anchorParams.pos)
            size = 0.0
            normal = Math.Vector3(anchorParams.normal)
            if self.__ctx.currentTab in self.__ctx.tabsData.REGIONS:
                if sId.areaId != Area.GUN:
                    normal.normalise()
                    anchorPos -= normal * 0.2
            elif self.__ctx.currentTab in (self.__ctx.tabsData.EMBLEM, self.__ctx.tabsData.INSCRIPTION):
                size = anchorParams.slotDescriptor.size
                decalUp = normal * (anchorParams.slotDescriptor.rayUp * normal)
                slotHeight = size / _ASPECT_RATIO[self.__ctx.currentTab]
                if sId == menuSlotId:
                    shift = slotHeight * _LINES_SHIFT_FROM_CENTRE
                    bottom = anchorPos - decalUp * shift * self.__vScale
                else:
                    item = self.__ctx.currentOutfit.getContainer(sId.areaId).slotFor(sId.slotType).getItem(sId.regionIdx)
                    if item is not None or self.__ctx.currentTab == self.__ctx.tabsData.EMBLEM:
                        shift = slotHeight * _ANCHOR_SHIFT_FROM_CENTRE[self.__ctx.currentTab]
                        anchorPos += decalUp * shift * self.__vScale
            scaleformUid = self.__vehicleCustomizationAnchors.addAnchor(
                anchorPos, normal, bottom, size, displayObject, True, True, True)
            processedObjectIds[sId] = scaleformUid

        self.__processedAnchors = processedObjectIds

