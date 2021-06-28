import copy
import os
from PYmodsCore import overrideMethod, remDups
from gui.Scaleform.daapi.view.lobby.customization.tooltips import ElementTooltip
from gui.shared.formatters import text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.tooltips import formatters
from helpers.i18n import makeString as _ms
from items.vehicles import getItemByCompactDescr
from .shared import getInsigniaNation, nationName

insignia_names = {
    'wh': '#vehicle_customization:special_style/kv2_w',
    'chuck': '#vehicle_customization:special_style/ny_2021_chuck',
}


@overrideMethod(ElementTooltip, '_packItemBlocks')
def _packItemBlocks(base, self, statsConfig):
    ctx = self._ElementTooltip__ctx
    if ctx and not ctx.isPurchase:
        statsConfig.buyPrice = False
        statsConfig.sellPrice = False
        statsConfig.inventoryCount = False
        statsConfig.showBonus = False
        if self._item.isProgressive:
            self._progressionLevel = self._progressionLevel or 1
    return base(self, statsConfig)


@overrideMethod(ElementTooltip, '_packTitleBlock')
def _packTitleBlock(base, self):
    if self._item.itemTypeID != GUI_ITEM_TYPE.INSIGNIA:
        return base(self)
    nationID = getInsigniaNation(self._item)
    if nationID is not None:
        title = nationName(nationID)
    else:
        texture = os.path.basename(self._item.getIconApplied(None))
        texture_id = texture.partition('_')[2].rpartition('_')[0]
        title = _ms(insignia_names[texture_id]) if texture_id in insignia_names else texture_id
    return formatters.packTitleDescBlock(
        title=text_styles.highTitle(self._item.userName or title), descPadding=formatters.packPadding(top=-5))


@overrideMethod(ElementTooltip, '_packIconBlock')
def _packIconBlock(base, self, isHistorical=False, isDim=False):
    data = base(self, isHistorical, isDim)
    if (data and 'data' in data and 'imagePath' in data['data']
            and '4278190335,4278255360,4294901760,4278190080' in data['data']['imagePath']):
        data['data']['imagePath'] = '../../' + data['data']['imagePath'].split('"', 2)[1]
    return data


@overrideMethod(ElementTooltip, '_packSuitableBlock')
def _packSuitableBlock(base, self):
    if not self._item.descriptor.filter or not self._item.descriptor.filter.include:
        return base(self)
    backups = {}
    for idx, node in enumerate(self._item.descriptor.filter.include):
        if not node.vehicles:
            continue
        backups[idx] = copy.copy(node.nations)
        if node.nations is None:
            node.nations = []
        for intCD in node.vehicles:
            node.nations.append(getItemByCompactDescr(intCD).customizationNationID)
        node.nations = remDups(node.nations)
    result = base(self)
    for idx, data in backups.items():
        self._item.descriptor.filter.include[idx].nations = data
    return result


@overrideMethod(ElementTooltip, '_packAppliedBlock')
@overrideMethod(ElementTooltip, '_packSpecialBlock')
def _packBlock(base, self):
    ctx = self._ElementTooltip__ctx
    return None if ctx and not ctx.isPurchase else base(self)
