import copy
from OpenModsCore import overrideMethod, remDups
from gui.Scaleform.daapi.view.lobby.customization.tooltips import ElementTooltip
from gui.shared.formatters import text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.tooltips import formatters
from items.vehicles import getItemByCompactDescr
from .shared import fixIconPath, getInsigniaUserName
from .. import g_config


@overrideMethod(ElementTooltip, '_packItemBlocks')
def _packItemBlocks(base, self, statsConfig, *a, **k):
    ctx = self._ElementTooltip__ctx
    if g_config.data['enabled'] and ctx and not ctx.isPurchase:
        statsConfig.buyPrice = False
        statsConfig.sellPrice = False
        statsConfig.inventoryCount = False
        statsConfig.showBonus = False
        if self._item.isProgressive:
            self._progressionLevel = self._progressionLevel or 1
    return base(self, statsConfig, *a, **k)


@overrideMethod(ElementTooltip, '_packTitleBlock')
def _packTitleBlock(base, self, *a, **k):
    if self._item.itemTypeID != GUI_ITEM_TYPE.INSIGNIA:
        return base(self, *a, **k)
    return formatters.packTitleDescBlock(
        title=text_styles.highTitle(getInsigniaUserName(self._item)), descPadding=formatters.packPadding(top=-5))


@overrideMethod(ElementTooltip, '_packIconBlock')
def _packIconBlock(base, self, *a, **k):
    data = base(self, *a, **k)
    if data and 'data' in data and 'imagePath' in data['data']:
        data['data']['imagePath'] = fixIconPath(data['data']['imagePath'])
    return data


@overrideMethod(ElementTooltip, '_packSuitableBlock')
def _packSuitableBlock(base, self, *a, **k):
    if not self._item.descriptor.filter or not self._item.descriptor.filter.include:
        return base(self, *a, **k)
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
    result = base(self, *a, **k)
    for idx, data in backups.items():
        self._item.descriptor.filter.include[idx].nations = data
    return result


@overrideMethod(ElementTooltip, '_packAppliedBlock')
@overrideMethod(ElementTooltip, '_packSpecialBlock')
def _packBlock(base, self, *a, **k):
    ctx = self._ElementTooltip__ctx
    return None if g_config.data['enabled'] and ctx and not ctx.isPurchase else base(self, *a, **k)
