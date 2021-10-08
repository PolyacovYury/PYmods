__modID__ = '%(mod_ID)s'
__date__ = '%(file_compile_date)s'
from OpenModsCore import Analytics
from config import g_config
from . import loader, processor

statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-23')
