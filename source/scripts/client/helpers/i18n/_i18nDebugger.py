from functools import partial

import BigWorld
import ResMgr
import traceback
from debug_utils import LOG_ERROR, LOG_NOTE

keysToFind = []
textsToFind = []
debuggerCfg = ResMgr.openSection('../mods/configs/PYmods/i18nDebugger/i18nDebugger.xml')
if debuggerCfg is not None:
    if debuggerCfg['enable'] is not None and debuggerCfg['enable'].asBool:
        if debuggerCfg['key'] is not None:
            keysString = debuggerCfg['key'].asWideString.strip()
            if keysString:
                keysToFind = keysString.split(';')
            else:
                LOG_NOTE('Key section empty.')
        else:
            LOG_NOTE('Key section missing.')
        if debuggerCfg['text'] is not None:
            textsString = debuggerCfg['text'].asWideString.strip()
            if textsString:
                textsToFind = textsString.split(';')
            else:
                LOG_NOTE('Text section empty.')
        else:
            LOG_NOTE('Text section missing.')

    else:
        LOG_NOTE('i18nDebugger disabled.')
else:
    LOG_ERROR('scripts/client/helpers/i18n/i18nDebugger.xml not found')
i18nHooks = ('i18n_hook_makeString',)


def checkTexts(key, text):
    if key is not None:
        for keyToFind in keysToFind:
            if keyToFind in key:
                print 'i18n: key detected: %s in %s, text: %s' % (keyToFind, key, text)
                traceback.print_stack()
    if text is not None:
        for textToFind in textsToFind:
            if textToFind in text:
                print 'i18n: text detected: %s in %s, key: %s' % (textToFind, text, key)
                traceback.print_stack()


def old_makeString(*_, **__):
    LOG_ERROR('i18n hook failed')


def i18n_hook_makeString(key, *args, **kwargs):
    text = old_makeString(key, *args, **kwargs)
    checkTexts(key, text)
    return text


def new_I18n_attr(base, self):
    result = base.fget(self)
    checkTexts('', result)
    return result


def debugHooks():
    from items.components.shared_components import I18nString, I18nComponent
    setattr(I18nString, 'value', property(partial(new_I18n_attr, I18nString.value)))
    setattr(I18nComponent, 'userString', property(partial(new_I18n_attr, I18nComponent.userString)))
    setattr(I18nComponent, 'shortString', property(partial(new_I18n_attr, I18nComponent.shortString)))
    setattr(I18nComponent, 'description', property(partial(new_I18n_attr, I18nComponent.description)))


BigWorld.callback(0, debugHooks)
