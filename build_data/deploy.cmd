@echo off
cd ..
start "" "BCompare.exe" build\archives\ "D:\Юрино\YandexDisk\PYmods\"
set /p ver=<build_data\GAME_VERSION.conf
"BCompare.exe" build\wotmods\ "D:\Games\World_of_Tanks\mods\%ver%\" /solo
