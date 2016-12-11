import traceback

import ResMgr

from debug_utils import LOG_ERROR, LOG_NOTE, LOG_WARNING, LOG_CURRENT_EXCEPTION
from helpers.i18n import g_translators
wasPrint = False


def __dir__():
    return ['makeString']


def makeString(key, *args, **kwargs):
    global wasPrint
    try:
        if not key or key[0] != '#':
            return key
        moName, subkey = key[1:].split(':', 1)
        if not moName or not subkey:
            return key
        translator = g_translators[moName]
        text = translator.gettext(subkey)
        if text == '?empty?':
            text = ''
        if args:
            try:
                text %= args
            except TypeError:
                LOG_WARNING("Arguments do not match string read by key '%s': %s", (key, args))
                return key

        elif kwargs:
            try:
                text %= kwargs
            except TypeError:
                LOG_WARNING("Arguments do not match string read by key '%s': %s", (key, kwargs))
                return key

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
