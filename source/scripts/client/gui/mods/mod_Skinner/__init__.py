__modID__ = '%(mod_ID)s'
__date__ = '%(file_compile_date)s'
from PYmodsCore import Analytics
from config import g_config

try:
    from gui.mods import mod_remodenabler
except ImportError:
    pass
from . import loader, processor

statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-23')
