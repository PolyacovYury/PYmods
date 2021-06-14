Storage for World of Tanks mods.
```
source/scripts:
  compiler.py - my modification of standard compileall which uses git calls to retrieve commit dates
  generate_configs.py - build configs automagic generator
  mtimestore.py - my implementation of kareltucek's git-mtime-extension, also made it more versatile
  pack_wotmods.py - archive packer
  /client:
    /gui/mods:
      /mod_CamoSelector - custom camouflage installer
      /mod_RemodEnabler - custom models dispatcher
      /mod_Skinner - custom skins dispatcher
      mod_AppreciationBadges.py - adds custom badges to those who install the mod
      mod_BanksLoader.py - automatic installer for .bnk files
      mod_CamoSelector.py - mod loader stub file for CamoSelector
      mod_HangarScreenshots - hides GUI and blocks camera position changing upon button press
      mod_Horns.py - plays horn sound and sends a message to chat upon button press
      mod_IngameGUITextTweaks.py - adds a vehicle class icon and strips out nicknames when needed
      mod_InsigniaOnGun.py - makes gun insignias appear on vehicles that didn't deserve it yet
      mod_LampLights.py - allows to attach light sources and models onto tanks
      mod_LogSwapper.py - because placing log for received damage on the top of the screen was a smart move by WG
      mod_PlayerHPAnnouncer.py - plays a sound when your HP drops below 50, 25 or 10%
      mod_PlayersPanelHP.py - well, the name is self-explanatory
      mod_RadialMenu.py - custom battle commands menu maker
      mod_RemodEnabler.py - mod loader stub file for RemodEnabler
      mod_ShowVehicle.py - displays your vehicle's hull and turret in sniper mode
      mod_Skinner.py - mod loader stub file for Skinner
      mod_SoundEventInjector.py - an alternative to editing scipts/item_defs/vehicles/ for audio mod makers
      mod_StatPaints.py - paints vehicles depending on their driver's WGR value
      mod_UT_announcer.py - frag, some medals and battle time sound notifier
      mod_VMTFix.py - Vehicle Model Transparency Fix - because transparent elements don't display on player vehicle
      mod_VoiceOverrider.py - switches some switches in SoundGroups to make different voiceover versions appear
    /helpers/i18n:
      __init__.py - transforms helpers.i18n from a module to package and adds a mod loader to it
      _i18nDebugger.py - a simple localisation debugger
      ButtonReplacer.py - localisation editor, replacement to editing .mo files
      HangarPainter.py - hangar text colorizer
    /mods:
      __init__.py - stub file for client.mods package
      CameraNode.py - obsolete mod loader
    /PYmodsCore - a good ol' code dump with inter-mod classes and functions
```
After cloning it is recommended to run `python source\scripts\mtimestore.py -r` and read and follow instructions in
res/res/res.md file, otherwise correct buildage of the mods is not guaranteed.
