import traceback

import ResMgr

from debug_utils import LOG_ERROR, LOG_NOTE, LOG_WARNING, LOG_CURRENT_EXCEPTION
wasPrint = False


def __dir__():
    return ['i18n_hook_makeString']


def old_makeString(*_, **kwargs):
    _ = kwargs
    LOG_ERROR('i18n hook failed')
    return ''


def i18n_hook_makeString(key, *args, **kwargs):
    global wasPrint
    try:
        text = old_makeString(key, *args, **kwargs)
        debuggerCfg = ResMgr.openSection('scripts/client/helpers/i18n/i18nDebugger.xml')
        if debuggerCfg is not None:
            if debuggerCfg['enable'] is not None and debuggerCfg['enable'].asBool:
                if debuggerCfg['key'] is not None:
                    if debuggerCfg['key'].asWideString.strip():
                        for keyToFind in debuggerCfg['key'].asWideString.strip().split(';'):
                            if keyToFind in key:
                                print 'i18n: detected: ' + key + ', text: ' + text
                                traceback.print_stack()
                    elif not wasPrint:
                        wasPrint = True
                        LOG_NOTE('Key section empty.')
                elif not wasPrint:
                    wasPrint = True
                    LOG_NOTE('Key section missing.')
                if debuggerCfg['text'] is not None:
                    if debuggerCfg['text'].asWideString.strip():
                        for textToFind in debuggerCfg['text'].asWideString.strip().split(';'):
                            if textToFind in text:
                                print 'i18n: detected: %s in %s at %s' % (textToFind, text, key)
                                traceback.print_stack()
                    elif not wasPrint:
                        wasPrint = True
                        LOG_NOTE('Text section empty.')
                elif not wasPrint:
                    wasPrint = True
                    LOG_NOTE('Text section missing.')
            elif not wasPrint:
                wasPrint = True
                LOG_NOTE('i18nDebugger disabled.')
        elif not wasPrint:
            wasPrint = True
            LOG_ERROR('scripts/client/helpers/i18n/i18nDebugger.xml not found')

        return text
    except StandardError:
        LOG_CURRENT_EXCEPTION()
        LOG_WARNING('Key string incompatible with args', key, args, kwargs)
        return key
