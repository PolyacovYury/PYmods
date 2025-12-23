Storage for World of Tanks mods.
---
This repo is provided as an archive of my mods' source code with the attached history of 15-year-old me's coding prowess :)  
Feel free to fork the repo and update/upgrade/support the mods however you see fit. A `(thx to Polyacov_Yury)` in startup python.log message(s) is appreciated.

Notable forks:
- https://github.com/pupitetris/PYmods-new-VoiceOverrider/ - awesome rework/upgrade of VoiceOverrider

Other projects (also in need of support):
- https://github.com/PolyacovYury/PYmods/wiki - (some) docs on the intricacies of the mods' internals
- https://github.com/PolyacovYury/ModPacker - data-driven modpack installer
- https://github.com/OpenMods-WoT/core/ (fka PYmodsCore) - some common APIs that greatly simplify mod creation by abstracting away boilerplate code
  - is a submodule in `core/` folder
- https://github.com/OpenMods-WoT/build_tools - a collection of automation tools that enables reproducible .pycs, .wotmods and .zips
  - is a submodule in `build_tools/` folder
- https://koreanrandom.com/forum/topic/44153- - central hub with links to other topics that also has screenshots and descriptions of some of the mods
---
After cloning, it is recommended to:
 - run `git submodule update --init --recursive`
 - copy all files in `build_tools/hooks` into `.git/hooks`
 - run `py -2 build_tools/mtimestore.py -r`
 - read and follow instructions in res/res/res.md file
otherwise correct building of the mods is not guaranteed.
```
build_data/
  archives/ - lists of files that need to be bundle-ified into mod archives
  wotmods/ - lists of files that need to be bundle-ified into .wotmod files
  debug_targets.txt - list of local folders that need to receive freshly-built wotmod files for testing
  GAME_VERSION - contains the version of the game client that will be baked into mod archives by build_tools/release.cmd
  release_targets.txt - list of local folders that need to receive freshly-built mod archives for upload to file shares
build_tools/
  hooks/ - git hooks that simplify working with the repo by automagically starting debug.cmd and release.cmd when appropriate
  compiler.py - my modification of standard compileall which uses git calls to retrieve commit dates
  debug.cmd - launch to compile all sources into .pyc, then pack .pyc into .wotmods
  mtimestore.py - my implementation of kareltucek's git-mtime-extension, also made it more versatile
  packer.py - archive and wotmod packer
  release.cmd - launch to pack all .wotmods and assets into .zip archives for publishing
core/ - OpenModsCore source code, used for IDE code discovery
res/
  configs/ - folder for mods' configs
  flash/ - source code for .swf components, also see swc.md
  img/ - images added to .zip archives
  meta/ - renamed into meta.xml for .wotmods that need it
  res/
    audioww/ - .bnk files for mods, see res.md
    Axes/ - model with the X/Y/Z axis pointers, used by LampLights
    gui/ - images added to .wotmods
    scripts/ - this should probably have been in the folder above...
    vehicles/ - models for remods for RemodEnabler, see res.md
    wotmods/ - pre-compiled mods by other authors used as API providers
source/scripts/
  /client:
    /gui/mods:
      /mod_CamoSelector - custom camouflage installer
      /mod_RemodEnabler - custom models dispatcher
      /mod_Skinner - custom skins dispatcher
      AsyncModLoader.py - makes it so that game client doesn't appear hanging while the mods are being loaded
      AsyncModLoader_init.py - part of AML, replacement of scripts/client/gui/mods/__init__.py
      mod_AimingAngles.py - horizontal and vertical aim limits on-screen
      mod_AllQuestsProgresses.py - forces quests' conditions from both campaigns to show up simultaneously
      mod_AppreciationBadges.py - adds custom badges to those who install the mod
      mod_BanksLoader.py - automatic installer for .bnk files
      mod_BigTextConsumablesPanel.py - large numbers in consumables panel achieved with pure Python
      mod_color_messages.py - colorizes battle result messages in the Service Channel 
      mod_CamoSelector.py - mod loader stub file for CamoSelector (won't be discovered without it)
      mod_DamagePercentIndicator.py - adds percentage of your full HP to incoming damage indicators
      mod_HangarBoosterViewer.py - (probably obsolete) shows active boosters and their remaining time
      mod_HangarCollision.py - (obsolete) used to show vehicle collision models in Hangar until WG removed them
      mod_HangarGUITweaks.py - some informativity tweaks to Hangar GUI
      mod_HangarScreenshots.py - hides GUI and locks camera position upon button press
      mod_Horns.py - plays horn sound and sends a message to chat upon button press
      mod_IngameGUITextTweaks.py - adds a vehicle class icon and strips out nicknames when needed
      mod_InsigniaOnGun.py - makes gun insignias appear on vehicles that don't deserve them yet
      mod_LampLights.py - allows to attach light sources and models onto tanks
      mod_LogSwapper.py - because placing log for received damage on the top of the screen was a smart move by WG
      mod_PermanentMusic.py - forces ingame music to play throughout the entire battle
      mod_PlayerHPAnnouncer.py - plays a sound when your HP drops below 50, 25 or 10%
      mod_PlayersPanelHP.py - well, the name is self-explanatory
      mod_PY_support_links.py - adds donation links to the mods' settings GUI. Feel free to ignore :3
      mod_RadialMenu.py - custom battle commands menu maker
      mod_RemodEnabler.py - mod loader stub file for RemodEnabler (won't be discovered without it)
      mod_ShowVehicle.py - displays your vehicle's hull and turret in sniper mode
      mod_ShutLoggersUp.py - makes python.log a little less cluttered
      mod_Skinner.py - mod loader stub file for Skinner (won't be discovered without it)
      mod_SoundEventInjector.py - an alternative to editing scipts/item_defs/vehicles/ for audio mod makers
      mod_StatPaints.py - paints vehicles depending on their driver's WGR value
      mod_UT_announcer.py - frag, some medals and battle time sound notifier
      mod_VMTFix.py - Vehicle Model Transparency Fix - because transparent elements don't display on player vehicle
      mod_VoiceOverrider.py - switches some switches in SoundGroups to make different voiceover versions appear
      PlayersPanelAPI.py - says on the tin. simplifies modification of team panels on sides of the screen
    /helpers/i18n:
      __init__.py - transforms helpers.i18n from a module to package and adds a mod loader to it
      _i18nDebugger.py - a simple localisation debugger
      ButtonReplacer.py - localisation editor, replacement to editing .mo files
      HangarPainter.py - hangar text colorizer
    /mods:
      __init__.py - stub file for client.mods package
      CameraNode.py - obsolete mod loader
```
