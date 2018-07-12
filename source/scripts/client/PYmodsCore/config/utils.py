import BigWorld
import Keys
import traceback
from functools import partial

modSettingsContainers = {}


def smart_update(dict1, dict2):
    changed = False
    for k in dict1:
        v = dict2.get(k)
        if isinstance(v, dict):
            changed |= smart_update(dict1[k], v)
        elif v is not None:
            if isinstance(v, unicode):
                v = v.encode('utf-8')
            changed |= dict1[k] != v
            dict1[k] = v
    return changed


def processHotKeys(data, keys, mode):
    add = lambda key: key if 'KEY_' in key else 'KEY_' + key
    if mode == 'read':
        process = lambda key: getattr(Keys, add(key))
    elif mode == 'write':
        process = lambda key: add(BigWorld.keyToString(key))
    else:
        assert False, 'unknown hotkey conversion mode'
    make = lambda keySet: [make(key) if isinstance(key, list) else process(key) for key in keySet]
    for dataKey in keys:  # configs have 'Key', code checks for 'key'. >_<
        newKey = dataKey.replace('key', 'Key')
        if (newKey if mode == 'read' else dataKey) not in data:
            continue
        data[(dataKey if mode == 'read' else newKey)] = make(data.pop((newKey if mode == 'read' else dataKey)))


def registerSettings(config, mode='full'):
    """
    Register a settings block in this mod's settings window.
    """
    try:
        from helpers import getClientLanguage
        newLang = str(getClientLanguage()).lower()
        if newLang != config.lang:
            config.lang = newLang
            config.loadLang()
    except StandardError:
        traceback.print_exc()
    try:
        # noinspection PyUnresolvedReferences
        from gui.vxSettingsApi import vxSettingsApi
        if config.modSettingsID not in modSettingsContainers:
            modSettingsContainers[config.modSettingsID] = config.containerClass(config.modSettingsID, config.configPath)
        msc = modSettingsContainers[config.modSettingsID]
        msc.onMSAPopulate += config.onMSAPopulate
        msc.onMSADestroy += config.onMSADestroy
        vxSettingsApi.onDataChanged += config.onDataChanged
        if mode == 'block':
            for blockID in config.blockIDs:
                vxSettingsApi.addMod(
                    config.modSettingsID, config.ID + blockID, partial(config.createTemplate, blockID),
                    config.getDataBlock(blockID), partial(config.onApplySettings, blockID), config.onButtonPress)
        else:
            vxSettingsApi.addMod(config.modSettingsID, config.ID, config.createTemplate, config.getData(),
                                 config.onApplySettings, config.onButtonPress)
    except ImportError:
        print '%s: no-GUI mode activated' % config.ID
    except StandardError:
        traceback.print_exc()
