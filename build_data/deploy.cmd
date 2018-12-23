@echo off
start "" "C:\Program Files\Beyond Compare 4\BCompare.exe" archives\ "D:\Юрино\YandexDisk\PYmods\"
start "" "C:\Program Files\Beyond Compare 4\BCompare.exe" archives_configs\ "D:\Юрино\YandexDisk\PYmods\"
set /p ver=<build_data\GAME_VERSION.conf
"C:\Program Files\Beyond Compare 4\BCompare.exe" build\wotmods\ "D:\Games\World_of_Tanks\mods\%ver%\" /solo
