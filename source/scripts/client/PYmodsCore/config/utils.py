import BigWorld
import Keys


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


KEY_ALT, KEY_CONTROL, KEY_SHIFT = range(-1, -4, -1)
SPECIAL_TO_KEYS = {
    KEY_ALT: ['KEY_LALT', 'KEY_RALT'],
    KEY_CONTROL: ['KEY_LCONTROL', 'KEY_RCONTROL'],
    KEY_SHIFT: ['KEY_LSHIFT', 'KEY_RSHIFT']}


def processHotKeys(data, keys, mode):
    add = lambda key: key if 'KEY_' in key else 'KEY_' + key
    if mode == 'read':
        process = lambda key: getattr(Keys, add(key))
    elif mode == 'write':
        process = lambda key: SPECIAL_TO_KEYS.get(key) or add(BigWorld.keyToString(key))
    else:
        assert False, 'unknown hotkey conversion mode'
    make = lambda keySet: [make(key) if isinstance(key, (list, tuple)) else process(key) for key in keySet]
    for dataKey in keys:  # configs have 'Key', code checks for 'key'. >_<
        newKey = dataKey.replace('key', 'Key')
        if (newKey if mode == 'read' else dataKey) not in data:
            continue
        data[(dataKey if mode == 'read' else newKey)] = make(data.pop((newKey if mode == 'read' else dataKey)))
