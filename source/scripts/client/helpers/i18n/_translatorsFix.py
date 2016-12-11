import os
import gettext
import ResMgr


def __dir__():
    return ['_getTranslator']


def _getTranslator(domain):
    # Determine local resource path to the localization file
    res_path = os.path.join('text/LC_MESSAGES', domain + '.mo')
    # Resolving to absolute path
    # ResMgr do the job of finding the real file location
    abs_path = ResMgr.resolveToAbsolutePath(res_path)
    # Getting a reversed path from file to resource storage
    # A little trick to solve a problem :)
    rev_path = os.path.relpath('.', res_path)
    # Most of os.path functions use path calculation algorithms
    # and don't call filesystem at all. So if you want to understand
    # how it works - just imagine that *.mo is a folder.
    # And now the final stage - getting path of storage where file is located
    srg_path = os.path.normpath(os.path.join(abs_path, rev_path))
    # Now it could be used in gettext translation request
    return gettext.translation(domain, srg_path, languages=['text'])
