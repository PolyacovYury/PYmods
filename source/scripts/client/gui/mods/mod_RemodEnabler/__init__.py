__modID__ = '%(mod_ID)s'
__date__ = '%(file_compile_date)s'
from OpenModsCore import Analytics
from config import g_config

try:
    from gui.mods import mod_skinner
except ImportError:
    pass
import processor

statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-4')
