Storage for World of Tanks mods.
```
source/scripts:  
  gitcompileall.py - my modification to standard compileall which uses git calls to retrieve commit date  
  /client:  
    PYmodsCore.py - a lil' ol' code dump with prototypes of inter-mod classes  
    /mods:  
      \_\_init__.py - stub file for client.mods package  
      CameraNode.py - obsolete mod loader  
    /helpers/i18n:  
      \_\_init__.py - transforms helpers.i18n from a module to package  
      _i18nDebugger.py - a simple and soon to be rewritten localisation debugger  
      _translatorsFix.py - script by GPCracker, which fixes placement of .mo files into res_mods folder  
      ButtonReplacer.py - localisation editor, replacement to editing .mo files  
      HangarPainter.py - hangar text colorizer  
    /gui/mods:  
      mod_BanksLoader.py - automatic installer for .bnk files  
      mod_CamoSelector.py - custom camoudlage installer  
      mod_Horns.py - plays horn sound and sends a message to chat upon button press  
      mod_LampLights.py - allows to attach light sources and models onto tanks  
      mod_RadialMenu.py - custom battle commands menu maker  
      mod_pro_RadialMenu.py - PROTanki version of the script  
      mod_RemodEnabler.py - custom models and skins dispatcher  
      mod_RibbonsRecolor.py - failed attempt to recolor battle efficiency ribbons  
      mod_SunController.py - battle arena time of day manager  
      mod_UT_announcer.py - frag, some medals and battle time sound notifier  
```