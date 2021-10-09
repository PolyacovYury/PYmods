import nations
from items import _xml
from items.components import shared_components as sc
from items.readers import shared_readers
from items.vehicles import g_cache


def readModels(xmlCtx, section, item):
    item.modelsSets = {'default': sc.ModelStatesPaths(_xml.readNonEmptyString(xmlCtx, section, 'models/undamaged'), '', '')}


def readEmblemSlots(xmlCtx, section, item):
    if section.has_key('emblemSlots'):
        item.emblemSlots, _ = shared_readers.readEmblemSlots(xmlCtx, section, 'emblemSlots')
    elif section.has_key('customizationSlots'):
        item.emblemSlots, item.slotsAnchors = shared_readers.readCustomizationSlots(xmlCtx, section, 'customizationSlots')


def readCamouflage(xmlCtx, section, item):
    if section.has_key('camouflage'):
        item.camouflage = shared_readers.readCamouflage(xmlCtx, section, 'camouflage', default=sc.DEFAULT_CAMOUFLAGE)


# noinspection PyUnusedLocal
def getOrigItem(xmlCtx, section, itemTypeName):
    soundID = section.readString('soundID', '')
    if ':' not in soundID:
        return
    nation, soundID = soundID.split(':')
    nationID = nations.INDICES[nation]
    itemTypeName_plural = itemTypeName
    if not itemTypeName_plural.endswith('s'):
        itemTypeName_plural += 's'
    return getattr(g_cache, itemTypeName_plural)(nationID).get(getattr(g_cache, itemTypeName + 'IDs')(nationID).get(soundID))
