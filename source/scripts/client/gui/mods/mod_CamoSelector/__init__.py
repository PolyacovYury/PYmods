# -*- coding: utf-8 -*-
__modID__ = '%(mod_ID)s'
__date__ = '%(file_compile_date)s'
from .config import g_config
try:
    from . import processors, readers, settings
except Exception:
    g_config.data['enabled'] = False
    raise
